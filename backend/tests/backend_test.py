"""
Backend regression tests for Iteration 2 of Narrative.Rx (Dental Claim Assistant).
Covers carrier tuning, section-level regeneration, PATCH history, visit generation,
and PDF/TXT exports.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if "REACT_APP_BACKEND_URL" in os.environ else "https://dent-writeup-tool.preview.emergentagent.com"
API = f"{BASE_URL}/api"

# Long timeout for LLM calls
LLM_TIMEOUT = 90
VISIT_TIMEOUT = 180


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Carriers ----------
class TestCarriers:
    def test_carriers_returns_six(self, session):
        r = session.get(f"{API}/carriers", timeout=20)
        assert r.status_code == 200
        keys = {c["key"] for c in r.json()["carriers"]}
        assert keys == {"generic", "delta", "cigna", "metlife", "aetna", "bcbs"}


# ---------- Generate with carrier ----------
@pytest.fixture(scope="module")
def delta_record(session):
    payload = {
        "procedure_code": "D2740",
        "tooth_number": "14",
        "surfaces": "MODBL",
        "clinical_findings": "Fractured MB cusp, non-restorable with amalgam",
        "radiographic_findings": "Deep decay approaching pulp",
        "carrier": "delta",
        "patient_label": "TEST_Pt_Delta",
        "save_to_history": True,
    }
    r = session.post(f"{API}/generate", json=payload, timeout=LLM_TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


class TestGenerateWithCarrier:
    def test_delta_record_shape(self, delta_record):
        assert delta_record["carrier"] == "delta"
        assert delta_record["procedure_code"] == "D2740"
        assert delta_record["short_narrative"]
        assert delta_record["long_narrative"]
        assert "id" in delta_record
        assert isinstance(delta_record["radiographs"], dict)

    def test_delta_persisted(self, session, delta_record):
        r = session.get(f"{API}/history/{delta_record['id']}", timeout=20)
        assert r.status_code == 200
        assert r.json()["carrier"] == "delta"


# ---------- Regenerate ----------
class TestRegenerate:
    def test_regenerate_short_only(self, session, delta_record):
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Fractured MB cusp, non-restorable with amalgam",
            "carrier": "delta",
            "field": "short",
            "existing_short": delta_record["short_narrative"],
            "existing_long": delta_record["long_narrative"],
        }
        r = session.post(f"{API}/regenerate", json=payload, timeout=LLM_TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["field"] == "short"
        assert isinstance(body["text"], str) and len(body["text"]) > 10

    def test_regenerate_long_only(self, session, delta_record):
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Fractured MB cusp, non-restorable with amalgam",
            "carrier": "delta",
            "field": "long",
            "existing_short": delta_record["short_narrative"],
            "existing_long": delta_record["long_narrative"],
        }
        r = session.post(f"{API}/regenerate", json=payload, timeout=LLM_TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["field"] == "long"
        assert isinstance(body["text"], str) and len(body["text"]) > 20

    def test_regenerate_invalid_field(self, session):
        r = session.post(f"{API}/regenerate", json={
            "procedure_code": "D2740",
            "field": "middle",
        }, timeout=20)
        assert r.status_code == 400


# ---------- PATCH history ----------
class TestPatchHistory:
    def test_patch_updates_short_and_long(self, session, delta_record):
        rid = delta_record["id"]
        new_short = "TEST edited short narrative."
        new_long = "TEST edited long narrative with more detail than before."
        r = session.patch(f"{API}/history/{rid}", json={
            "short_narrative": new_short,
            "long_narrative": new_long,
        }, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["short_narrative"] == new_short
        assert body["long_narrative"] == new_long

        # verify persistence
        r2 = session.get(f"{API}/history/{rid}", timeout=20)
        assert r2.json()["short_narrative"] == new_short

    def test_patch_unknown_id_returns_404(self, session):
        r = session.patch(f"{API}/history/does-not-exist-xyz", json={
            "short_narrative": "x",
        }, timeout=20)
        assert r.status_code == 404


# ---------- Visit generation ----------
@pytest.fixture(scope="module")
def visit_record(session):
    payload = {
        "patient_label": "TEST_Visit_Pt",
        "carrier": "cigna",
        "date_of_service": "2025-01-15",
        "visit_notes": "History of bruxism, high caries risk.",
        "procedures": [
            {"procedure_code": "D2740", "tooth_number": "14", "clinical_findings": "Fractured cusp"},
            {"procedure_code": "D2950", "tooth_number": "19", "clinical_findings": "Insufficient tooth structure for standard build-up"},
            {"procedure_code": "D4341", "clinical_findings": "Generalized 5-7mm pocketing UR quadrant"},
        ],
        "save_to_history": True,
    }
    r = session.post(f"{API}/visits/generate", json=payload, timeout=VISIT_TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


class TestVisitGenerate:
    def test_visit_has_three_records(self, visit_record):
        assert len(visit_record["records"]) == 3
        assert visit_record["patient_label"] == "TEST_Visit_Pt"
        assert visit_record["carrier"] == "cigna"
        for rec in visit_record["records"]:
            assert rec["short_narrative"]
            assert rec["long_narrative"]
            assert rec["carrier"] == "cigna"
            assert rec["patient_label"] == "TEST_Visit_Pt"

    def test_visits_listed(self, session, visit_record):
        r = session.get(f"{API}/visits", timeout=20)
        assert r.status_code == 200
        ids = [v["id"] for v in r.json()]
        assert visit_record["id"] in ids

    def test_visit_records_persisted_in_narratives(self, session, visit_record):
        # first record should be gettable individually
        rec_id = visit_record["records"][0]["id"]
        r = session.get(f"{API}/history/{rec_id}", timeout=20)
        assert r.status_code == 200
        assert r.json()["carrier"] == "cigna"


# ---------- Exports ----------
class TestExports:
    def test_export_pdf_single(self, session, delta_record):
        r = session.post(f"{API}/export/pdf", json=delta_record, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"

    def test_export_txt_single(self, session, delta_record):
        r = session.post(f"{API}/export/txt", json=delta_record, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")
        assert "DENTAL CLAIM NARRATIVE PACKET" in r.text

    def test_export_visit_pdf(self, session, visit_record):
        r = session.post(f"{API}/export/visit/pdf", json=visit_record, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"

    def test_export_visit_txt(self, session, visit_record):
        r = session.post(f"{API}/export/visit/txt", json=visit_record, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")
        assert "MULTI-PROCEDURE VISIT CLAIM PACKET" in r.text


# ---------- Cleanup ----------
def test_cleanup_test_data(session, delta_record, visit_record):
    # Delete narrative records created by tests
    for rid in [delta_record["id"]] + [r["id"] for r in visit_record["records"]]:
        session.delete(f"{API}/history/{rid}", timeout=20)

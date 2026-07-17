"""
Iter 16 backend tests — Practice Settings feature.

Covers:
- GET /api/settings/practice defaults + persistence after PUT
- PUT with all 13 fields
- Per-user isolation
- POST /api/appeals embeds practice name in letter
- Export endpoints (pdf/txt for narrative, visit, appeal) return valid PDFs / plain text
- Regression: /api/generate (admin) still works
"""
import os
import uuid
import time
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # fall back to reading frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1].rstrip("/")
                break

API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASSWORD = "admin123"


# ------------------------- fixtures -------------------------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("access_token")
    assert tok
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="session")
def other_user_session():
    """Register a fresh user to test per-user isolation."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"test_iter16_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "testpass123", "office_name": "TEST_Other_Office"
    })
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("access_token")
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


# ------------------------- Practice Settings CRUD -------------------------
class TestPracticeSettings:

    def test_get_returns_current_or_empty(self, admin_session):
        r = admin_session.get(f"{API}/settings/practice")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
        # All keys defined by the model must be present in the response schema (nullable).
        for k in ["practice_name", "address_line1", "city", "phone", "npi"]:
            assert k in data

    def test_put_persists_all_13_fields(self, admin_session):
        payload = {
            "practice_name": "TEST_Bright Smiles Dental",
            "address_line1": "123 Main St",
            "address_line2": "Suite 200",
            "city": "Springfield",
            "state": "IL",
            "zip_code": "62701",
            "phone": "(555) 000-1111",
            "fax": "(555) 000-2222",
            "email": "billing@brightsmiles.test",
            "npi": "1234567890",
            "tax_id": "12-3456789",
            "provider_name": "Dr. Jane Smith, DDS",
            "provider_license": "IL-DDS-12345",
        }
        r = admin_session.put(f"{API}/settings/practice", json=payload)
        assert r.status_code == 200
        data = r.json()
        for k, v in payload.items():
            assert data.get(k) == v, f"field {k}: expected {v!r}, got {data.get(k)!r}"

        # GET should return the same values
        r2 = admin_session.get(f"{API}/settings/practice")
        assert r2.status_code == 200
        got = r2.json()
        for k, v in payload.items():
            assert got.get(k) == v

    def test_isolation_between_users(self, admin_session, other_user_session):
        # Admin has TEST_Bright Smiles Dental from previous test
        r_admin = admin_session.get(f"{API}/settings/practice")
        assert r_admin.status_code == 200
        assert r_admin.json().get("practice_name") == "TEST_Bright Smiles Dental"

        # Fresh user must start empty
        r_other = other_user_session.get(f"{API}/settings/practice")
        assert r_other.status_code == 200
        assert not r_other.json().get("practice_name")

        # Other user sets their own
        p2 = {"practice_name": "TEST_Other Practice", "phone": "(999) 999-9999"}
        r_put = other_user_session.put(f"{API}/settings/practice", json=p2)
        assert r_put.status_code == 200
        assert r_put.json().get("practice_name") == "TEST_Other Practice"

        # Admin's settings unchanged
        r_admin_again = admin_session.get(f"{API}/settings/practice")
        assert r_admin_again.status_code == 200
        assert r_admin_again.json().get("practice_name") == "TEST_Bright Smiles Dental"

    def test_unauthenticated_rejected(self):
        r = requests.get(f"{API}/settings/practice")
        assert r.status_code in (401, 403)


# ------------------------- Appeal LLM prompt embeds practice name -------------------------
class TestAppealEmbedsPracticeName:

    @pytest.fixture(scope="class")
    def narrative_record(self, admin_session):
        # Generate a narrative to appeal against.
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Extensive MOD caries with cusp involvement; tooth non-restorable with direct restoration.",
            "radiographic_findings": "Interproximal caries approaching pulp on distal.",
            "carrier": "generic",
            "save_to_history": True,
        }
        r = admin_session.post(f"{API}/generate", json=payload)
        assert r.status_code == 200, f"/generate failed: {r.status_code} {r.text[:200]}"
        return r.json()

    def test_appeal_letter_mentions_practice_name(self, admin_session, narrative_record):
        # Ensure practice settings still set (was in earlier test).
        r_check = admin_session.get(f"{API}/settings/practice")
        assert r_check.status_code == 200
        assert r_check.json().get("practice_name") == "TEST_Bright Smiles Dental"

        payload = {
            "narrative_id": narrative_record["id"],
            "denial_reason": "Insufficient documentation of medical necessity for D2740 crown.",
            "denial_code": "D2740-01",
            "save_to_history": False,
        }
        r = admin_session.post(f"{API}/appeals", json=payload, timeout=90)
        assert r.status_code == 200, f"/appeals failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        letter = data.get("letter") or ""
        assert letter, "empty letter"
        # Should not contain the placeholder default anymore
        assert "[Office Name]" not in letter, "letter still uses '[Office Name]' placeholder"
        # Should contain practice name (or at least a substring — LLM might paraphrase)
        assert "Bright Smiles Dental" in letter or "TEST_Bright Smiles Dental" in letter, (
            f"letter does not reference practice name. Excerpt: {letter[:600]}"
        )


# ------------------------- Export endpoints -------------------------
class TestExports:

    @pytest.fixture(scope="class")
    def narrative(self, admin_session):
        r = admin_session.post(f"{API}/generate", json={
            "procedure_code": "D2740",
            "tooth_number": "3",
            "clinical_findings": "Fractured cusp, non-restorable with direct filling.",
            "carrier": "generic",
            "save_to_history": True,
        })
        assert r.status_code == 200
        return r.json()

    @pytest.fixture(scope="class")
    def appeal(self, admin_session, narrative):
        r = admin_session.post(f"{API}/appeals", json={
            "narrative_id": narrative["id"],
            "denial_reason": "Not medically necessary.",
            "save_to_history": True,
        }, timeout=90)
        assert r.status_code == 200
        return r.json()

    def test_export_narrative_pdf(self, admin_session, narrative):
        r = admin_session.post(f"{API}/export/pdf", json=narrative)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_export_narrative_txt(self, admin_session, narrative):
        r = admin_session.post(f"{API}/export/txt", json=narrative)
        assert r.status_code == 200
        text = r.text
        assert "TEST_Bright Smiles Dental" in text, "practice header missing from TXT export"

    def test_export_visit_pdf(self, admin_session, narrative):
        # Build a minimal visit-shaped payload
        visit_payload = {
            "id": "test-visit-" + uuid.uuid4().hex[:8],
            "patient_label": "TEST Patient",
            "carrier": "generic",
            "records": [narrative],
        }
        r = admin_session.post(f"{API}/export/visit/pdf", json=visit_payload)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_export_visit_txt(self, admin_session, narrative):
        visit_payload = {
            "id": "test-visit-" + uuid.uuid4().hex[:8],
            "patient_label": "TEST Patient",
            "carrier": "generic",
            "records": [narrative],
        }
        r = admin_session.post(f"{API}/export/visit/txt", json=visit_payload)
        assert r.status_code == 200
        assert "TEST_Bright Smiles Dental" in r.text

    def test_export_appeal_pdf(self, admin_session, appeal):
        r = admin_session.post(f"{API}/export/appeal/pdf", json=appeal)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_export_appeal_txt(self, admin_session, appeal):
        r = admin_session.post(f"{API}/export/appeal/txt", json=appeal)
        assert r.status_code == 200
        assert "TEST_Bright Smiles Dental" in r.text


# ------------------------- Regression: /generate + list appeals still work -------------------------
class TestRegression:

    def test_generate_works(self, admin_session):
        r = admin_session.post(f"{API}/generate", json={
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Extensive caries, non-restorable.",
            "carrier": "generic",
            "save_to_history": False,
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("procedure_code") == "D2740"
        assert data.get("short_narrative")
        assert data.get("long_narrative")

    def test_list_appeals(self, admin_session):
        r = admin_session.get(f"{API}/appeals")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ------------------------- Cleanup -------------------------
@pytest.fixture(scope="session", autouse=True)
def _cleanup(admin_session):
    yield
    # Reset practice settings so we don't pollute
    try:
        admin_session.put(f"{API}/settings/practice", json={})
    except Exception:
        pass

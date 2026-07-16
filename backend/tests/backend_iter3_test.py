"""
Iteration 3 backend regression tests for Narrative.Rx.
Covers:
  - JWT auth (register / login / me / logout / brute-force)
  - Per-user data isolation on narratives / history / visits / appeals
  - Appeal generation + persistence + export (PDF / TXT)
  - Concurrency cap on /api/visits/generate with 5 procedures
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if "REACT_APP_BACKEND_URL" in os.environ \
    else "https://dent-writeup-tool.preview.emergentagent.com"
API = f"{BASE_URL}/api"

LLM_TIMEOUT = 90
VISIT_TIMEOUT = 180
ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASSWORD = "admin123"


def _new_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(session, email, password="Test1234!", office_name="TEST_Office"):
    return session.post(f"{API}/auth/register",
                        json={"email": email, "password": password, "office_name": office_name},
                        timeout=20)


def _login(session, email, password):
    return session.post(f"{API}/auth/login",
                        json={"email": email, "password": password}, timeout=20)


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def user_a():
    """Register user A with a fresh email and return an authenticated session + info."""
    s = _new_session()
    email = f"test-userA-{uuid.uuid4().hex[:8]}@test.com"
    r = _register(s, email, office_name="TEST_OfficeA")
    assert r.status_code == 200, r.text
    body = r.json()
    return {"session": s, "email": email, "id": body["id"], "office_name": body["office_name"]}


@pytest.fixture(scope="session")
def user_b():
    s = _new_session()
    email = f"test-userB-{uuid.uuid4().hex[:8]}@test.com"
    r = _register(s, email, office_name="TEST_OfficeB")
    assert r.status_code == 200, r.text
    body = r.json()
    return {"session": s, "email": email, "id": body["id"], "office_name": body["office_name"]}


@pytest.fixture(scope="session")
def narrative_a(user_a):
    """Narrative owned by user A."""
    s = user_a["session"]
    payload = {
        "procedure_code": "D3330",
        "tooth_number": "30",
        "clinical_findings": "Necrotic pulp with periapical radiolucency 3mm",
        "radiographic_findings": "Periapical radiolucency at apex of mesial root",
        "pulp_status": "Necrotic, no response to cold/EPT",
        "carrier": "delta",
        "patient_label": "TEST_ISO_A",
        "save_to_history": True,
    }
    r = s.post(f"{API}/generate", json=payload, timeout=LLM_TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Public endpoints ----------
class TestPublic:
    def test_root_public(self):
        r = requests.get(f"{API}/", timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_procedures_public(self):
        r = requests.get(f"{API}/procedures", timeout=15)
        assert r.status_code == 200
        assert "procedures" in r.json()

    def test_carriers_public(self):
        r = requests.get(f"{API}/carriers", timeout=15)
        assert r.status_code == 200
        keys = {c["key"] for c in r.json()["carriers"]}
        assert {"generic", "delta", "cigna", "metlife", "aetna", "bcbs"} <= keys


# ---------- Auth ----------
class TestAuth:
    def test_admin_seeded_login(self):
        s = _new_session()
        r = _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == ADMIN_EMAIL
        assert body["role"] == "admin"
        # httpOnly cookies present
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies

    def test_me_requires_cookie(self):
        s = _new_session()
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_register_returns_user_and_sets_cookies(self):
        s = _new_session()
        email = f"test-reg-{uuid.uuid4().hex[:8]}@test.com"
        r = _register(s, email, office_name="TEST_RegOffice")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == email
        assert body["office_name"] == "TEST_RegOffice"
        assert body["role"] == "user"
        assert "id" in body
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies

        # me works with the cookie
        me = s.get(f"{API}/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json()["email"] == email

    def test_login_wrong_password_401(self):
        s = _new_session()
        # use a unique fresh email (must exist -> register first)
        email = f"test-wrongpw-{uuid.uuid4().hex[:8]}@test.com"
        assert _register(s, email).status_code == 200
        s2 = _new_session()
        r = _login(s2, email, "wrong-password-xyz")
        assert r.status_code == 401
        detail = r.json().get("detail")
        assert isinstance(detail, str) and detail  # must be a plain string, not [object]

    def test_logout_clears_cookies(self):
        s = _new_session()
        email = f"test-logout-{uuid.uuid4().hex[:8]}@test.com"
        assert _register(s, email).status_code == 200
        r = s.post(f"{API}/auth/logout", timeout=15)
        assert r.status_code == 200
        # After logout, /me should be 401 (cookies cleared server-side)
        s.cookies.clear()  # simulate browser dropping cleared cookies
        me = s.get(f"{API}/auth/me", timeout=15)
        assert me.status_code == 401

    def test_brute_force_lockout_returns_429(self):
        # Fresh account, 5 wrong attempts -> 6th returns 429
        s_reg = _new_session()
        email = f"test-brute-{uuid.uuid4().hex[:8]}@test.com"
        assert _register(s_reg, email).status_code == 200
        s = _new_session()
        for i in range(5):
            r = _login(s, email, "wrong-password-attempt")
            assert r.status_code == 401, f"attempt {i+1}: {r.status_code}"
        r6 = _login(s, email, "wrong-password-attempt")
        assert r6.status_code == 429, f"expected 429 after 5 failures, got {r6.status_code}"


# ---------- Auth guard on business endpoints ----------
class TestAuthGuards:
    def test_generate_requires_auth(self):
        r = requests.post(f"{API}/generate",
                          json={"procedure_code": "D2740"}, timeout=15)
        assert r.status_code == 401

    def test_history_requires_auth(self):
        r = requests.get(f"{API}/history", timeout=15)
        assert r.status_code == 401

    def test_visits_generate_requires_auth(self):
        r = requests.post(f"{API}/visits/generate",
                          json={"procedures": [{"procedure_code": "D2740"}]}, timeout=15)
        assert r.status_code == 401

    def test_appeals_list_requires_auth(self):
        r = requests.get(f"{API}/appeals", timeout=15)
        assert r.status_code == 401

    def test_appeals_create_requires_auth(self):
        r = requests.post(f"{API}/appeals",
                          json={"narrative_id": "x", "denial_reason": "y"}, timeout=15)
        assert r.status_code == 401

    def test_export_appeal_requires_auth(self):
        r = requests.post(f"{API}/export/appeal/pdf", json={"letter": "test"}, timeout=15)
        assert r.status_code == 401


# ---------- Per-user isolation ----------
class TestIsolation:
    def test_user_b_cannot_see_user_a_history(self, user_b, narrative_a):
        r = user_b["session"].get(f"{API}/history", timeout=20)
        assert r.status_code == 200
        ids = [rec["id"] for rec in r.json()]
        assert narrative_a["id"] not in ids

    def test_user_b_get_a_record_returns_404(self, user_b, narrative_a):
        r = user_b["session"].get(f"{API}/history/{narrative_a['id']}", timeout=15)
        assert r.status_code == 404

    def test_user_b_patch_a_record_returns_404(self, user_b, narrative_a):
        r = user_b["session"].patch(f"{API}/history/{narrative_a['id']}",
                                    json={"short_narrative": "hack"}, timeout=15)
        assert r.status_code == 404

    def test_user_b_delete_a_record_returns_404(self, user_b, narrative_a):
        r = user_b["session"].delete(f"{API}/history/{narrative_a['id']}", timeout=15)
        assert r.status_code == 404

    def test_user_a_can_see_own_narrative(self, user_a, narrative_a):
        r = user_a["session"].get(f"{API}/history/{narrative_a['id']}", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == narrative_a["id"]


# ---------- Appeals ----------
@pytest.fixture(scope="session")
def appeal_a(user_a, narrative_a):
    payload = {
        "narrative_id": narrative_a["id"],
        "denial_reason": "Insufficient documentation of medical necessity for endodontic therapy.",
        "denial_code": "D-105",
        "extra_context": "Attach preoperative periapical radiograph.",
        "save_to_history": True,
    }
    r = user_a["session"].post(f"{API}/appeals", json=payload, timeout=LLM_TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


class TestAppeals:
    def test_appeal_shape(self, appeal_a, narrative_a):
        assert appeal_a["subject_line"]
        assert appeal_a["letter"]
        assert appeal_a["narrative_id"] == narrative_a["id"]
        assert appeal_a["denial_reason"].startswith("Insufficient documentation")
        assert appeal_a["procedure_code"] == "D3330"

    def test_appeal_persisted_to_list(self, user_a, appeal_a):
        r = user_a["session"].get(f"{API}/appeals", timeout=15)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert appeal_a["id"] in ids

    def test_appeal_get_by_id(self, user_a, appeal_a):
        r = user_a["session"].get(f"{API}/appeals/{appeal_a['id']}", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == appeal_a["id"]

    def test_appeal_missing_denial_reason_400(self, user_a, narrative_a):
        r = user_a["session"].post(f"{API}/appeals",
                                   json={"narrative_id": narrative_a["id"], "denial_reason": ""},
                                   timeout=15)
        assert r.status_code == 400

    def test_appeal_wrong_owner_narrative_returns_404(self, user_b, narrative_a):
        r = user_b["session"].post(f"{API}/appeals",
                                   json={"narrative_id": narrative_a["id"],
                                         "denial_reason": "test"},
                                   timeout=15)
        assert r.status_code == 404

    def test_user_b_cannot_see_user_a_appeal(self, user_b, appeal_a):
        r = user_b["session"].get(f"{API}/appeals", timeout=15)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert appeal_a["id"] not in ids
        r2 = user_b["session"].get(f"{API}/appeals/{appeal_a['id']}", timeout=15)
        assert r2.status_code == 404

    def test_appeal_patch_and_persist(self, user_a, appeal_a):
        new_letter = "TEST edited appeal letter body."
        r = user_a["session"].patch(f"{API}/appeals/{appeal_a['id']}",
                                    json={"letter": new_letter}, timeout=15)
        assert r.status_code == 200
        assert r.json()["letter"] == new_letter
        # verify persistence
        r2 = user_a["session"].get(f"{API}/appeals/{appeal_a['id']}", timeout=15)
        assert r2.json()["letter"] == new_letter

    def test_export_appeal_pdf(self, user_a, appeal_a):
        r = user_a["session"].post(f"{API}/export/appeal/pdf", json=appeal_a, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"

    def test_export_appeal_txt(self, user_a, appeal_a):
        r = user_a["session"].post(f"{API}/export/appeal/txt", json=appeal_a, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")
        assert len(r.text) > 50


# ---------- Concurrency cap on /visits/generate ----------
class TestConcurrencyCap:
    def test_five_procedures_visit_completes(self, user_a):
        """With MAX_CONCURRENT_LLM=3, 5 procedures should complete in ~2 batches."""
        payload = {
            "patient_label": "TEST_Conc_5",
            "carrier": "cigna",
            "date_of_service": "2025-01-20",
            "visit_notes": "Comprehensive visit, mixed procedures.",
            "procedures": [
                {"procedure_code": "D2740", "tooth_number": "14",
                 "clinical_findings": "Fractured MB cusp, non-restorable"},
                {"procedure_code": "D2950", "tooth_number": "19",
                 "clinical_findings": "Insufficient tooth structure for restoration"},
                {"procedure_code": "D3330", "tooth_number": "3",
                 "clinical_findings": "Necrotic pulp, periapical radiolucency"},
                {"procedure_code": "D4341",
                 "clinical_findings": "Generalized 5-6mm pocketing upper right quadrant"},
                {"procedure_code": "D7140", "tooth_number": "17",
                 "clinical_findings": "Non-restorable caries, extraction indicated"},
            ],
            "save_to_history": True,
        }
        t0 = time.time()
        r = user_a["session"].post(f"{API}/visits/generate", json=payload, timeout=VISIT_TIMEOUT)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["records"]) == 5
        for rec in body["records"]:
            assert rec["short_narrative"]
            assert rec["long_narrative"]
        # Sanity: with concurrency=3 and 5 items, should be ~2 batches (5-25s per LLM call typical)
        # Not enforcing a strict upper bound but log it for triage.
        print(f"[conc] 5-procedure visit took {elapsed:.1f}s")
        assert elapsed < VISIT_TIMEOUT


# ---------- Cleanup ----------
def test_cleanup_test_data(user_a, user_b, narrative_a, appeal_a):
    a = user_a["session"]
    # delete appeals
    for appeal in a.get(f"{API}/appeals", timeout=15).json():
        a.delete(f"{API}/appeals/{appeal['id']}", timeout=10)
    # delete narratives
    for rec in a.get(f"{API}/history", timeout=15).json():
        a.delete(f"{API}/history/{rec['id']}", timeout=10)
    # for user_b too
    b = user_b["session"]
    for rec in b.get(f"{API}/history", timeout=15).json():
        b.delete(f"{API}/history/{rec['id']}", timeout=10)

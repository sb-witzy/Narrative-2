"""
Iteration 7 backend regression tests.

Scope (post-refactor: useCallback/useMemo + stable row _key + defensive var init):
1. Login -> Generate D2740 (primary flow).
2. Refresh: rotates access with Secure=True on HTTPS + returns _user_out shape (id/email).
3. Refresh with valid token whose user was deleted -> 401 detail 'User not found'
   (verifies defensively-initialized user variable in server.refresh_token).
4. Bulk Visit generate: 2 procedures + shared visit_notes -> both narratives returned,
   VisitProcedure ConfigDict(extra='ignore') tolerates unknown fields like _key.
5. Appeal from saved narrative_id -> letter created, save_to_history=True persists.
6. Auto-refresh path: no access, valid refresh -> /api/refresh 200 then /api/generate 200.
"""
import os
import re
import uuid
import time
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASS = "admin123"


def _parse_set_cookie_header(headers):
    raw = headers.get("set-cookie")
    if not raw:
        return []
    parts = re.split(r",(?=\s*[A-Za-z0-9_\-]+=)", raw)
    return [p.strip() for p in parts]


def _cookie_flags(lines, name):
    for line in lines:
        if line.lower().startswith(name.lower() + "="):
            attrs = [a.strip().lower() for a in line.split(";")]
            return {
                "secure": any(a == "secure" for a in attrs),
                "httponly": any(a == "httponly" for a in attrs),
                "samesite": next((a.split("=", 1)[1] for a in attrs if a.startswith("samesite=")), None),
                "raw": line,
            }
    return None


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, r.text
    return s


# ---------- Primary regression ----------
class TestGenerateAfterLogin:
    def test_login_then_generate_d2740(self, admin_session):
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Deep MOD decay; visible cracked cusp on radiograph",
            "carrier": "Delta Dental",
            "save_to_history": False,
        }
        r = admin_session.post(f"{BASE_URL}/api/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["procedure_code"] == "D2740"
        assert isinstance(data.get("long_narrative"), str) and len(data["long_narrative"]) > 40
        assert isinstance(data.get("short_narrative"), str) and len(data["short_narrative"]) > 10


# ---------- Cookie Secure + refresh Secure ----------
class TestCookieAndRefresh:
    def test_login_sets_secure_true_on_https(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
        assert r.status_code == 200
        lines = _parse_set_cookie_header(r.headers)
        for name in ("access_token", "refresh_token"):
            flags = _cookie_flags(lines, name)
            assert flags is not None, f"{name} missing in Set-Cookie"
            assert flags["secure"] is True, f"{name} Secure=False. raw={flags['raw']}"
            assert flags["httponly"] is True

    def test_refresh_rotates_and_returns_user_out(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
        assert r.status_code == 200
        first = s.cookies.get("access_token")
        time.sleep(1)
        r2 = s.post(f"{BASE_URL}/api/auth/refresh", timeout=30)
        assert r2.status_code == 200, r2.text
        # response body is _user_out shape (id, email, ...)
        body = r2.json()
        assert "id" in body and "email" in body
        assert body["email"] == ADMIN_EMAIL
        # rotation
        second = s.cookies.get("access_token")
        assert second and second != first
        # secure attr on new cookie
        flags = _cookie_flags(_parse_set_cookie_header(r2.headers), "access_token")
        assert flags["secure"] is True

    def test_refresh_missing_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/auth/refresh", timeout=30)
        assert r.status_code == 401


# ---------- Defensive user init: refresh with valid token but deleted user -> 401 ----------
class TestRefreshUserNotFound:
    """
    Register a throwaway user, capture the refresh cookie, delete the user in DB,
    then call /api/auth/refresh with that cookie. Must return 401 detail 'User not found'.
    """
    def test_deleted_user_refresh_returns_401(self):
        email = f"TEST_iter7_{uuid.uuid4().hex[:8]}@example.com"
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/register",
                   json={"email": email, "password": "TestPass123!", "office_name": "iter7"},
                   timeout=30)
        if r.status_code == 429:
            pytest.skip("Register rate limit hit; skipping deleted-user refresh test")
        assert r.status_code == 200, r.text
        user_id = r.json()["id"]
        # sanity: refresh works while user exists
        rok = s.post(f"{BASE_URL}/api/auth/refresh", timeout=30)
        assert rok.status_code == 200

        # Delete the user via direct DB access
        client = MongoClient(MONGO_URL)
        try:
            db = client[DB_NAME]
            result = db.users.delete_one({"_id": ObjectId(user_id)})
            assert result.deleted_count == 1, f"failed to delete user {user_id}"
        finally:
            client.close()

        # Refresh must now 401 with 'User not found'
        r401 = s.post(f"{BASE_URL}/api/auth/refresh", timeout=30)
        assert r401.status_code == 401, r401.text
        detail = r401.json().get("detail", "")
        assert "not found" in detail.lower(), f"unexpected detail: {detail}"


# ---------- Bulk visit generate ----------
class TestBulkVisit:
    def test_generate_visit_two_procedures(self, admin_session):
        payload = {
            "patient_label": "Pt #TEST7",
            "carrier": "Delta Dental",
            "date_of_service": "2026-01-15",
            "visit_notes": "History of bruxism; high caries risk.",
            "procedures": [
                {
                    "procedure_code": "D2740",
                    "tooth_number": "14",
                    "clinical_findings": "MOD fracture with cracked cusp",
                    "radiographic_findings": "No periapical pathology",
                },
                {
                    "procedure_code": "D2950",
                    "tooth_number": "19",
                    "surfaces": "MO",
                    "clinical_findings": "Extensive coronal breakdown; buildup required to retain crown",
                },
            ],
            "save_to_history": False,
        }
        r = admin_session.post(f"{BASE_URL}/api/visits/generate", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["records"]) == 2
        codes = sorted(rec["procedure_code"] for rec in data["records"])
        assert codes == ["D2740", "D2950"]
        for rec in data["records"]:
            assert isinstance(rec.get("long_narrative"), str)
            assert len(rec["long_narrative"]) > 30

    def test_visit_procedure_extra_ignore_tolerates_unknown_fields(self, admin_session):
        """Verifies BulkVisit.jsx safety-net: even if _key leaks through, VisitProcedure
        ConfigDict(extra='ignore') must accept the payload."""
        payload = {
            "patient_label": "Pt #TEST7-b",
            "carrier": "generic",
            "procedures": [{
                "procedure_code": "D2740",
                "tooth_number": "14",
                "clinical_findings": "MOD fracture",
                "_key": "some-uuid-leak",           # unknown field
                "unknown_field": "should be ignored",
            }],
            "save_to_history": False,
        }
        r = admin_session.post(f"{BASE_URL}/api/visits/generate", json=payload, timeout=90)
        assert r.status_code == 200, r.text


# ---------- Appeal flow ----------
class TestAppealFlow:
    def test_appeal_from_saved_narrative(self, admin_session):
        # save a narrative
        g = admin_session.post(f"{BASE_URL}/api/generate", json={
            "procedure_code": "D2740", "tooth_number": "14",
            "clinical_findings": "Cracked cusp with MOD decay",
            "carrier": "Delta Dental", "save_to_history": True,
        }, timeout=90)
        assert g.status_code == 200
        narrative_id = g.json()["id"]

        # draft appeal by narrative_id
        r = admin_session.post(f"{BASE_URL}/api/appeals", json={
            "narrative_id": narrative_id,
            "denial_reason": "Not medically necessary",
            "denial_code": "M15",
            "save_to_history": True,
        }, timeout=120)
        assert r.status_code == 200, r.text
        appeal = r.json()
        assert appeal["narrative_id"] == narrative_id
        assert isinstance(appeal["letter"], str) and len(appeal["letter"]) > 100
        assert isinstance(appeal["subject_line"], str) and len(appeal["subject_line"]) > 5

        # verify list contains it
        lst = admin_session.get(f"{BASE_URL}/api/appeals", timeout=30)
        assert lst.status_code == 200
        assert any(a["id"] == appeal["id"] for a in lst.json())

        # export PDF
        pdf = admin_session.post(f"{BASE_URL}/api/export/appeal/pdf", json=appeal, timeout=60)
        assert pdf.status_code == 200
        assert pdf.headers.get("content-type", "").startswith("application/pdf")
        assert len(pdf.content) > 500


# ---------- Auto-refresh interceptor mechanics (server-side portion) ----------
class TestAutoRefreshMechanics:
    """
    Simulate the frontend interceptor server-side: delete only access_token,
    call generate (expect 401), call refresh (expect 200), retry generate (expect 200).
    """
    def test_delete_access_then_refresh_then_generate(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
        assert r.status_code == 200
        # kill access cookie only
        s.cookies.set("access_token", "", domain=s.cookies.list_domains()[0])
        del s.cookies["access_token"]
        assert s.cookies.get("access_token") is None
        assert s.cookies.get("refresh_token") is not None

        # first generate attempt -> 401
        r1 = s.post(f"{BASE_URL}/api/generate", json={
            "procedure_code": "D2740", "tooth_number": "14",
            "clinical_findings": "x", "carrier": "generic", "save_to_history": False,
        }, timeout=30)
        assert r1.status_code == 401

        # refresh
        r2 = s.post(f"{BASE_URL}/api/auth/refresh", timeout=30)
        assert r2.status_code == 200
        assert s.cookies.get("access_token")

        # retry generate
        r3 = s.post(f"{BASE_URL}/api/generate", json={
            "procedure_code": "D2740", "tooth_number": "14",
            "clinical_findings": "Deep MOD decay",
            "carrier": "Delta Dental", "save_to_history": False,
        }, timeout=90)
        assert r3.status_code == 200, r3.text

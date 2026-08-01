"""Iter 18 live regression tests: existing endpoints + new /api/system/* endpoints
via the public REACT_APP_BACKEND_URL."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback for local pytest run inside container
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASS = "admin123"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


# -------- System endpoints (new) --------

class TestSystemVersion:
    def test_version_authenticated(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/system/version", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("is_installer_build", "version", "is_git_repo", "github_repo"):
            assert k in data, f"missing {k} in {data}"
        assert data["is_installer_build"] is False
        assert data["is_git_repo"] is True
        assert isinstance(data["github_repo"], str) and data["github_repo"]

    def test_check_updates_dev_no_origin(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/system/check-updates", timeout=60)
        # In dev (no installer build) it should NOT crash; expect 400/502 with descriptive msg.
        # Per spec: 502 preferred.
        assert r.status_code in (400, 502), f"expected 400/502, got {r.status_code}: {r.text}"
        # Must not be a 500.
        assert r.status_code != 500
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        assert "detail" in body or "error" in body or r.text

    def test_update_requires_windows(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/system/update", timeout=30)
        # Linux dev: expect 400 "only supported on Windows" style
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        body = r.text.lower()
        assert "window" in body or "installer" in body or "platform" in body

    def test_check_updates_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/system/check-updates", timeout=30)
        assert r.status_code in (401, 403)

    def test_update_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/system/update", timeout=30)
        assert r.status_code in (401, 403)


# -------- Regression: existing endpoints still work --------

class TestRegression:
    def test_auth_me(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 200
        assert r.json().get("email") == ADMIN_EMAIL

    def test_history_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/history", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_appeal_patterns_endpoint(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/appeals/patterns",
            params={"carrier": "delta", "procedure_code": "D2740"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        for k in ("total", "won", "lost", "pending", "win_rate"):
            assert k in data

    def test_generate_narrative(self, admin_session):
        payload = {
            "procedure_code": "D2740",
            "clinical_findings": "TEST_iter18 regression - fractured mesial cusp, existing MOD amalgam."
        }
        r = admin_session.post(f"{BASE_URL}/api/generate", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("id")
        assert data.get("short_narrative")
        assert data.get("long_narrative")
        # No marker tags leaked
        for f in ("short_narrative", "long_narrative"):
            for tag in ("[SHORT]", "[/SHORT]", "[LONG]", "[/LONG]"):
                assert tag not in data[f]

    def test_appeal_generate(self, admin_session):
        # Create a narrative first
        n = admin_session.post(f"{BASE_URL}/api/generate", json={
            "procedure_code": "D2950",
            "clinical_findings": "TEST_iter18 appeal seed - >50% coronal structure lost."
        }, timeout=120)
        assert n.status_code == 200
        nid = n.json()["id"]
        r = admin_session.post(f"{BASE_URL}/api/appeals", json={
            "narrative_id": nid, "carrier": "delta",
            "denial_reason": "Not medically necessary per carrier guidelines."
        }, timeout=120)
        assert r.status_code == 200, r.text
        a = r.json()
        assert a.get("id") and a.get("letter") and a.get("subject_line")
        # PATCH outcome
        p = admin_session.patch(f"{BASE_URL}/api/appeals/{a['id']}",
                                json={"outcome": "pending"}, timeout=30)
        assert p.status_code == 200

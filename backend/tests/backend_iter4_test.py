"""
Iteration 4 backend tests — targeted at the two bug fixes:
  BUG FIX 1: /api/auth/refresh works and issues a new access cookie
             (interceptor logic itself is frontend, but backend side must be solid).
  BUG FIX 2: Brute-force lockout works behind K8s ingress on the PUBLIC URL
             (uses X-Forwarded-For for real client IP + per-email backstop counter).
Regression smoke:
  - Admin login (admin@dental.com / admin123) works and can hit /api/generate.
  - /api/auth/me works after login.
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASSWORD = "admin123"
LLM_TIMEOUT = 90


def _new_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- BUG FIX 1 backend side: refresh endpoint ----------
class TestRefreshEndpoint:
    def test_refresh_returns_new_access_cookie(self):
        """POST /api/auth/refresh with valid refresh cookie must return 200 and set new access cookie."""
        s = _new_session()
        # Login as admin
        r = s.post(f"{API}/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
        assert r.status_code == 200, r.text
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies
        # Simulate expired access token by deleting it from the client cookie jar
        s.cookies.pop("access_token", None)
        assert "access_token" not in s.cookies

        # Refresh
        r = s.post(f"{API}/auth/refresh", timeout=20)
        assert r.status_code == 200, r.text
        assert "access_token" in s.cookies, "refresh must set a new access_token cookie"
        new_access = s.cookies.get("access_token")
        assert new_access and len(new_access) > 20

        # Retry: original authenticated request should now succeed
        r = s.get(f"{API}/auth/me", timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["email"] == ADMIN_EMAIL

    def test_refresh_without_cookie_returns_401(self):
        s = _new_session()
        r = s.post(f"{API}/auth/refresh", timeout=20)
        assert r.status_code == 401
        detail = r.json().get("detail", "")
        assert "refresh" in detail.lower() or "not" in detail.lower()

    def test_missing_both_tokens_authenticated_route_401(self):
        """When both access AND refresh cookies absent, /api/generate returns 401 → frontend
        interceptor is responsible for redirecting to /login. Backend just needs to fail cleanly."""
        s = _new_session()
        # No cookies at all
        r = s.post(f"{API}/generate", json={"procedure_code": "D2740"}, timeout=30)
        assert r.status_code == 401

    def test_expired_access_but_valid_refresh_flow(self):
        """Simulate the exact interceptor scenario: valid refresh, missing access, then /api/generate
        should be reachable AFTER refresh call using the same session cookie jar."""
        s = _new_session()
        r = s.post(f"{API}/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
        assert r.status_code == 200
        # Delete access cookie (simulates expiry)
        s.cookies.pop("access_token", None)

        # First request without access — should 401
        r = s.get(f"{API}/auth/me", timeout=20)
        assert r.status_code == 401

        # Refresh (what the interceptor does)
        r = s.post(f"{API}/auth/refresh", timeout=20)
        assert r.status_code == 200

        # Retry — should succeed (what the interceptor does)
        r = s.get(f"{API}/auth/me", timeout=20)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL


# ---------- BUG FIX 2: brute-force lockout on public URL ----------
class TestBruteForceLockoutBehindIngress:
    def test_lockout_after_5_failures_via_public_url(self):
        """Fresh unique email — 5 wrong passwords in a row must yield 429 on the 6th attempt.
        This must work over the public URL where each request may hit a different ingress pod."""
        email = f"bf-test-{uuid.uuid4().hex[:8]}@example.com"
        # Register a real user with a known password (so we can prove the lockout, not that user doesn't exist)
        s0 = _new_session()
        r = s0.post(f"{API}/auth/register",
                    json={"email": email, "password": "CorrectPass1!", "office_name": "TEST_BF"},
                    timeout=20)
        assert r.status_code == 200, r.text
        s0.cookies.clear()

        # Now hammer with wrong password from fresh sessions (each session = potentially different pod IP)
        statuses = []
        for i in range(7):
            s = _new_session()
            r = s.post(f"{API}/auth/login",
                       json={"email": email, "password": "WrongPass!" + str(i)},
                       timeout=20)
            statuses.append(r.status_code)
        # Expect: first 5 = 401, from 6th onward = 429
        # But allow some flexibility: at least one of attempts 6+ must be 429
        first_five = statuses[:5]
        after = statuses[5:]
        assert all(s == 401 for s in first_five), f"First 5 attempts should be 401, got: {statuses}"
        assert 429 in after, (
            f"Expected 429 on attempts 6+ due to brute-force lockout behind ingress. "
            f"Got sequence: {statuses}. Bypass still possible!"
        )

    def test_correct_password_still_locked_out(self):
        """After lockout, even the correct password must be rejected with 429."""
        email = f"bf-test2-{uuid.uuid4().hex[:8]}@example.com"
        s0 = _new_session()
        r = s0.post(f"{API}/auth/register",
                    json={"email": email, "password": "RightPassword1!", "office_name": "TEST_BF2"},
                    timeout=20)
        assert r.status_code == 200

        # 5 wrong logins
        for i in range(5):
            s = _new_session()
            s.post(f"{API}/auth/login",
                   json={"email": email, "password": "wrong" + str(i)}, timeout=20)

        # Correct password should now be locked (429)
        s = _new_session()
        r = s.post(f"{API}/auth/login",
                   json={"email": email, "password": "RightPassword1!"}, timeout=20)
        assert r.status_code == 429, (
            f"Correct password should be locked after 5 failures. Got {r.status_code}: {r.text}"
        )


# ---------- Regression: admin end-to-end ----------
class TestAdminSmoke:
    def test_admin_login_and_generate(self):
        s = _new_session()
        r = s.post(f"{API}/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["email"] == ADMIN_EMAIL

        r = s.get(f"{API}/auth/me", timeout=20)
        assert r.status_code == 200

        # Full narrative generation
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "surfaces": "MODL",
            "symptoms": "sensitivity to cold",
            "clinical_findings": "large defective amalgam, cracked cusp",
            "radiographic_findings": "recurrent decay under existing restoration",
            "carrier": "generic",
            "save_to_history": False,
        }
        r = s.post(f"{API}/generate", json=payload, timeout=LLM_TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["procedure_code"] == "D2740"
        assert isinstance(body["short_narrative"], str) and len(body["short_narrative"]) > 20
        assert isinstance(body["long_narrative"], str) and len(body["long_narrative"]) > 20

    def test_public_endpoints_still_work(self):
        s = _new_session()
        r = s.get(f"{API}/procedures", timeout=10)
        assert r.status_code == 200
        assert "procedures" in r.json()
        r = s.get(f"{API}/carriers", timeout=10)
        assert r.status_code == 200

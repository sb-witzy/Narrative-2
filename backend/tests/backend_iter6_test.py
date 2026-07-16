"""
Iteration 6 backend regression tests.

Focus (bug: "Generate button makes you sign in and does not generate the narrative"):
1. Secure cookie flag behavior:
   - HTTPS (public URL / X-Forwarded-Proto: https) -> Secure=True on cookies
   - HTTP (localhost:8001 direct)               -> Secure=False on cookies
2. Login -> Generate D2740 works with the new secure cookies.
3. Refresh endpoint rotates access cookie with Secure=True on HTTPS.
4. Refresh missing token -> 401 (used by frontend to redirect to /login?reason=expired).
5. Register flow smoke: fresh user cookie has Secure=True on HTTPS + Generate 200.
6. Appeal creation smoke under the new cookies.
"""
import os
import re
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://dent-writeup-tool.preview.emergentagent.com").rstrip("/")
LOCAL_URL = "http://localhost:8001"
ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASS = "admin123"


def _parse_set_cookie_header(headers):
    """Return list of raw Set-Cookie header strings (case-insensitive)."""
    # requests concatenates multi-value headers with ", " which breaks Set-Cookie parsing;
    # use raw response.raw.headers.getlist when available. Fall back to .get_all via _store.
    raw = headers.get("set-cookie")
    if not raw:
        return []
    # Split on ", " but not the ", " inside Expires=... — cookies here don't set Expires (Max-Age used).
    # Safer: split on newlines from raw headers if we had them. For our controlled cookies, comma-split is OK
    # because we don't emit Expires attributes.
    parts = re.split(r",(?=\s*[A-Za-z0-9_\-]+=)", raw)
    return [p.strip() for p in parts]


def _cookie_flags(set_cookie_lines, cookie_name):
    for line in set_cookie_lines:
        if line.lower().startswith(cookie_name.lower() + "="):
            attrs = [a.strip().lower() for a in line.split(";")]
            return {
                "secure": any(a == "secure" for a in attrs),
                "httponly": any(a == "httponly" for a in attrs),
                "samesite": next((a.split("=", 1)[1] for a in attrs if a.startswith("samesite=")), None),
                "path": next((a.split("=", 1)[1] for a in attrs if a.startswith("path=")), None),
                "raw": line,
            }
    return None


# ---------- Cookie Secure flag ----------

class TestCookieSecureFlag:
    """Verify Set-Cookie Secure attribute flips based on request scheme."""

    def test_https_login_sets_secure_true(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        lines = _parse_set_cookie_header(r.headers)
        assert lines, "No Set-Cookie header on HTTPS login"
        access = _cookie_flags(lines, "access_token")
        refresh = _cookie_flags(lines, "refresh_token")
        assert access is not None, f"access_token cookie missing. Set-Cookie: {lines}"
        assert refresh is not None, f"refresh_token cookie missing. Set-Cookie: {lines}"
        assert access["secure"] is True, f"access_token Secure=False on HTTPS. raw={access['raw']}"
        assert refresh["secure"] is True, f"refresh_token Secure=False on HTTPS. raw={refresh['raw']}"
        assert access["httponly"] is True
        assert refresh["httponly"] is True
        assert access["samesite"] == "lax"

    def test_http_localhost_login_sets_secure_false(self):
        try:
            r = requests.post(
                f"{LOCAL_URL}/api/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            pytest.skip(f"localhost:8001 not reachable directly: {e}")
        assert r.status_code == 200, r.text
        lines = _parse_set_cookie_header(r.headers)
        access = _cookie_flags(lines, "access_token")
        assert access is not None, f"access_token cookie missing. Set-Cookie: {lines}"
        # On plain HTTP with no X-Forwarded-Proto header, secure must be False
        assert access["secure"] is False, f"access_token Secure=True on plain HTTP localhost. raw={access['raw']}"

    def test_x_forwarded_proto_https_forces_secure(self):
        """Even hitting localhost, if X-Forwarded-Proto: https is set (like ingress), Secure must be True."""
        try:
            r = requests.post(
                f"{LOCAL_URL}/api/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
                headers={"X-Forwarded-Proto": "https"},
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            pytest.skip(f"localhost:8001 not reachable directly: {e}")
        assert r.status_code == 200
        access = _cookie_flags(_parse_set_cookie_header(r.headers), "access_token")
        assert access is not None
        assert access["secure"] is True, f"X-Forwarded-Proto=https did not flip Secure. raw={access['raw']}"

    def test_refresh_endpoint_rotates_with_secure_true(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
        assert r.status_code == 200
        first_access = s.cookies.get("access_token")
        assert first_access
        # small delay so iat/exp changes
        time.sleep(1)
        r2 = s.post(f"{BASE_URL}/api/auth/refresh", timeout=30)
        assert r2.status_code == 200, r2.text
        lines = _parse_set_cookie_header(r2.headers)
        access = _cookie_flags(lines, "access_token")
        assert access is not None, f"refresh did not set access_token cookie. Set-Cookie: {lines}"
        assert access["secure"] is True, f"refresh Secure=False on HTTPS. raw={access['raw']}"
        new_access = s.cookies.get("access_token")
        assert new_access and new_access != first_access, "access token was not rotated"

    def test_refresh_missing_cookie_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/auth/refresh", timeout=30)
        assert r.status_code == 401, r.text


# ---------- Primary bug regression: login -> generate ----------

class TestGenerateNarrativeAfterLogin:
    def test_login_then_generate_d2740(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
        assert r.status_code == 200, r.text
        assert s.cookies.get("access_token")

        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Deep decay MOD; cracked cusp visible on X-ray",
            "carrier": "Delta Dental",
            "save_to_history": False,
        }
        gr = s.post(f"{BASE_URL}/api/generate", json=payload, timeout=90)
        assert gr.status_code == 200, gr.text
        data = gr.json()
        assert "long_narrative" in data and isinstance(data["long_narrative"], str) and len(data["long_narrative"]) > 40
        assert data["procedure_code"] == "D2740"

    def test_generate_401_without_cookies_triggers_refresh_path(self):
        """No cookies at all -> /api/generate returns 401 (the frontend interceptor will then try refresh)."""
        r = requests.post(
            f"{BASE_URL}/api/generate",
            json={"procedure_code": "D2740", "tooth_number": "14",
                  "clinical_findings": "x", "carrier": "Delta Dental", "save_to_history": False},
            timeout=30,
        )
        assert r.status_code == 401, r.text


# ---------- Register smoke + generate ----------

class TestRegisterFlowSmoke:
    def test_register_new_user_and_generate(self):
        # Use a highly unique email to avoid burning through IP-based rate limits and duplicate errors
        email = f"TEST_iter6_{uuid.uuid4().hex[:10]}@example.com"
        s = requests.Session()
        r = s.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": "TestPass123!", "office_name": "Iter6 Test Office"},
            timeout=30,
        )
        if r.status_code == 429:
            pytest.skip("Register rate limit hit for this IP — skipping register smoke.")
        assert r.status_code == 200, r.text
        lines = _parse_set_cookie_header(r.headers)
        access = _cookie_flags(lines, "access_token")
        assert access is not None, f"register set no access_token cookie. Set-Cookie: {lines}"
        assert access["secure"] is True, f"register cookie Secure=False on HTTPS. raw={access['raw']}"

        gr = s.post(
            f"{BASE_URL}/api/generate",
            json={"procedure_code": "D2740", "tooth_number": "14",
                  "clinical_findings": "Deep decay", "carrier": "Delta Dental", "save_to_history": False},
            timeout=90,
        )
        assert gr.status_code == 200, gr.text
        assert "long_narrative" in gr.json()


# ---------- Appeal smoke ----------

class TestAppealSmoke:
    def test_create_appeal_after_login(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
        assert r.status_code == 200
        # First generate a narrative to appeal against
        g = s.post(
            f"{BASE_URL}/api/generate",
            json={"procedure_code": "D2740", "tooth_number": "14",
                  "clinical_findings": "Deep decay; cracked cusp on X-ray",
                  "carrier": "Delta Dental", "save_to_history": True},
            timeout=90,
        )
        assert g.status_code == 200, g.text
        narrative = g.json()
        payload = {
            "narrative": narrative,
            "denial_reason": "Not medically necessary",
            "save_to_history": False,
        }
        r2 = s.post(f"{BASE_URL}/api/appeals", json=payload, timeout=90)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert any(k in data for k in ("letter", "appeal_letter", "long_narrative", "id"))

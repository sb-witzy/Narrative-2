"""
Iteration 10 backend tests: Bearer-token fallback for cookie-blocked browsers.

Bug context: some users are logged out on every /api/generate click because their browser
silently drops httpOnly cookies (Safari ITP, incognito, Chrome tracking protection, etc.).
Fix under test: /api/auth/login|register|refresh now also return `access_token` in the
JSON body so the frontend can attach it as `Authorization: Bearer <token>`. Cookies remain
the primary transport; Bearer is a fallback.

Verifies:
  - POST /api/auth/login returns {..., "access_token": "<jwt>"} and Set-Cookie both.
  - POST /api/auth/register returns access_token in body.
  - POST /api/auth/refresh returns access_token in body.
  - Bearer-only (no cookies) auth works for /api/auth/me and /api/generate.
  - Cookie-only auth still works (backwards compat).
  - remember=True on login still yields 30d refresh cookie + access_token in body.
"""
import os
import re
import uuid
import jwt
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    from pathlib import Path
    from dotenv import dotenv_values
    fe_env = dotenv_values(Path("/app/frontend/.env"))
    BASE_URL = fe_env.get("REACT_APP_BACKEND_URL")
BASE_URL = BASE_URL.rstrip("/")

ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASSWORD = "admin123"

REFRESH_30D = 30 * 24 * 3600
TOLERANCE = 60


def _set_cookie_headers(response):
    raw = response.raw.headers.getlist("Set-Cookie") if hasattr(response.raw.headers, "getlist") else None
    if raw:
        return raw
    hdr = response.headers.get("Set-Cookie", "")
    return re.split(r",(?=\s*[A-Za-z0-9_\-]+=)", hdr) if hdr else []


def _max_age_for(headers_list, cookie_name):
    for h in headers_list:
        if h.strip().startswith(f"{cookie_name}="):
            m = re.search(r"Max-Age=(\d+)", h, re.I)
            if m:
                return int(m.group(1))
    return None


# ---------- Login: body has access_token ----------
class TestLoginReturnsAccessToken:
    def test_login_returns_access_token_in_body(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("email") == ADMIN_EMAIL
        assert "id" in body
        access = body.get("access_token")
        assert isinstance(access, str) and len(access) > 20, "access_token missing/invalid in login body"

        # Verify JWT decodable and looks like access token
        payload = jwt.decode(access, options={"verify_signature": False})
        assert payload.get("type") == "access"
        assert payload.get("email") == ADMIN_EMAIL
        assert payload.get("sub") == body["id"]

        # Cookies also present (primary transport still works)
        headers = _set_cookie_headers(r)
        joined = " ".join(headers)
        assert "access_token=" in joined
        assert "refresh_token=" in joined

    def test_login_with_remember_returns_access_token_and_30d_refresh(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": True},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body.get("access_token"), str) and len(body["access_token"]) > 20

        headers = _set_cookie_headers(r)
        refresh_max = _max_age_for(headers, "refresh_token")
        assert refresh_max is not None
        assert abs(refresh_max - REFRESH_30D) <= TOLERANCE, (
            f"remember=true refresh should be ~30d, got {refresh_max}"
        )


# ---------- Register: body has access_token ----------
class TestRegisterReturnsAccessToken:
    def test_register_returns_access_token_in_body(self):
        unique = uuid.uuid4().hex[:10]
        email = f"TEST_iter10_{unique}@dental.com"
        r = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": "TestPass123!", "office_name": "Iter10 Office"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Backend may normalise the email to lowercase — compare case-insensitively.
        assert body.get("email", "").lower() == email.lower()
        access = body.get("access_token")
        assert isinstance(access, str) and len(access) > 20, "access_token missing in register body"
        payload = jwt.decode(access, options={"verify_signature": False})
        assert payload.get("type") == "access"
        assert payload.get("email", "").lower() == email.lower()


# ---------- Bearer-only: no cookies, header alone should authenticate ----------
class TestBearerOnlyAuth:
    def _login_get_token(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15,
        )
        assert r.status_code == 200
        return r.json()["access_token"]

    def test_me_with_bearer_only(self):
        token = self._login_get_token()
        # Fresh session with NO cookies, only Authorization header
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == ADMIN_EMAIL

    def test_generate_with_bearer_only(self):
        token = self._login_get_token()
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Large MOD amalgam with recurrent decay; cusp fracture on mesio-buccal.",
            "radiographic_findings": "Radiolucency under existing restoration.",
            "carrier": "generic",
            "save_to_history": False,
        }
        # No cookies attached — must succeed via header
        r = requests.post(
            f"{BASE_URL}/api/generate",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=90,
        )
        assert r.status_code == 200, f"generate failed with bearer-only: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert data["procedure_code"] == "D2740"
        assert isinstance(data.get("short_narrative"), str) and len(data["short_narrative"]) > 20
        assert isinstance(data.get("long_narrative"), str) and len(data["long_narrative"]) > 40

    def test_generate_without_any_credentials_401(self):
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "irrelevant",
            "carrier": "generic",
            "save_to_history": False,
        }
        r = requests.post(f"{BASE_URL}/api/generate", json=payload, timeout=30)
        assert r.status_code == 401, f"expected 401 without auth, got {r.status_code}"


# ---------- Refresh: body has new access_token, remember preserved ----------
class TestRefreshReturnsAccessToken:
    def test_refresh_returns_access_token_in_body(self):
        s = requests.Session()
        r = s.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15,
        )
        assert r.status_code == 200
        original_access = r.json()["access_token"]

        r2 = s.post(f"{BASE_URL}/api/auth/refresh", timeout=15)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        new_access = body.get("access_token")
        assert isinstance(new_access, str) and len(new_access) > 20, "refresh body missing access_token"
        # Should still return the user object
        assert body.get("email") == ADMIN_EMAIL

        # Decode: still an access token
        payload = jwt.decode(new_access, options={"verify_signature": False})
        assert payload.get("type") == "access"
        assert payload.get("email") == ADMIN_EMAIL


# ---------- Regression: cookie-only auth still works ----------
class TestCookieOnlyRegression:
    def test_generate_with_cookies_only(self):
        s = requests.Session()
        r = s.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15,
        )
        assert r.status_code == 200
        # Explicitly do NOT reuse the access_token from body — rely on cookies
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Large MOD amalgam with recurrent decay.",
            "carrier": "generic",
            "save_to_history": False,
        }
        gr = s.post(f"{BASE_URL}/api/generate", json=payload, timeout=90)
        assert gr.status_code == 200, gr.text
        data = gr.json()
        assert data["procedure_code"] == "D2740"


# ---------- Refresh with only refresh_token cookie (access cookie deleted) ----------
class TestRefreshWorksWithoutAccessCookie:
    def test_refresh_when_only_refresh_cookie_present(self):
        s = requests.Session()
        r = s.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15,
        )
        assert r.status_code == 200
        # Simulate strict browser dropping access_token: keep only refresh cookie.
        refresh_val = s.cookies.get("refresh_token")
        assert refresh_val
        # Use a fresh call with ONLY refresh_token cookie via explicit cookies dict.
        r2 = requests.post(
            f"{BASE_URL}/api/auth/refresh",
            cookies={"refresh_token": refresh_val},
            timeout=15,
        )
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert isinstance(body.get("access_token"), str) and len(body["access_token"]) > 20

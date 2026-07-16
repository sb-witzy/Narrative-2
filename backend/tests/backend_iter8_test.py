"""
Iteration 8 backend tests: 'Remember this device' 30-day refresh cookie option.

Verifies:
  - Login WITHOUT remember: refresh cookie Max-Age ~7d (604800), JWT payload has remember=False
  - Login WITH remember: refresh cookie Max-Age ~30d (2592000), JWT payload has remember=True
  - /api/auth/refresh preserves remember flag on subsequent refreshes
  - access_token cookie Max-Age unchanged (~1800) in both cases
  - Regression: admin login works and end-to-end narrative generation still works
"""
import os
import re
import jwt
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fallback for pytest running with backend/.env only
    from pathlib import Path
    from dotenv import dotenv_values
    fe_env = dotenv_values(Path("/app/frontend/.env"))
    BASE_URL = fe_env.get("REACT_APP_BACKEND_URL")
BASE_URL = BASE_URL.rstrip("/")

ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASSWORD = "admin123"

REFRESH_7D = 7 * 24 * 3600            # 604800
REFRESH_30D = 30 * 24 * 3600          # 2592000
ACCESS_TTL = 30 * 60                  # 1800
TOLERANCE = 30                        # seconds


def _login(remember: bool):
    """Login and return (response, set_cookie_headers)."""
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": remember},
        timeout=15,
    )
    return s, r


def _set_cookie_headers(response):
    """Return list of individual Set-Cookie header strings."""
    # requests merges Set-Cookie into a single string via .get; use raw
    raw = response.raw.headers.getlist("Set-Cookie") if hasattr(response.raw.headers, "getlist") else None
    if raw:
        return raw
    # fallback: parse from response.headers
    hdr = response.headers.get("Set-Cookie", "")
    # Split on comma only when followed by a cookie name= pattern
    return re.split(r",(?=\s*[A-Za-z0-9_\-]+=)", hdr) if hdr else []


def _max_age_for(headers_list, cookie_name):
    for h in headers_list:
        if h.strip().startswith(f"{cookie_name}="):
            m = re.search(r"Max-Age=(\d+)", h, re.I)
            if m:
                return int(m.group(1))
    return None


class TestRememberFlag:
    """Cookie Max-Age + JWT payload behaviour for the remember flag."""

    def test_login_without_remember_sets_7d_refresh(self):
        s, r = _login(remember=False)
        assert r.status_code == 200, r.text
        headers = _set_cookie_headers(r)
        refresh_max = _max_age_for(headers, "refresh_token")
        access_max = _max_age_for(headers, "access_token")

        assert refresh_max is not None, f"refresh_token cookie missing. headers={headers}"
        assert abs(refresh_max - REFRESH_7D) <= TOLERANCE, (
            f"expected ~{REFRESH_7D}s (7d), got {refresh_max}"
        )
        assert access_max is not None
        assert abs(access_max - ACCESS_TTL) <= TOLERANCE, (
            f"access token TTL changed: expected ~{ACCESS_TTL}, got {access_max}"
        )

        # Decode refresh JWT (no verify — we don't have the secret in tests)
        refresh_jwt = s.cookies.get("refresh_token")
        assert refresh_jwt
        payload = jwt.decode(refresh_jwt, options={"verify_signature": False})
        assert payload.get("type") == "refresh"
        assert payload.get("remember") is False, f"remember should be False, got {payload!r}"

    def test_login_with_remember_sets_30d_refresh(self):
        s, r = _login(remember=True)
        assert r.status_code == 200, r.text
        headers = _set_cookie_headers(r)
        refresh_max = _max_age_for(headers, "refresh_token")
        access_max = _max_age_for(headers, "access_token")

        assert refresh_max is not None
        assert abs(refresh_max - REFRESH_30D) <= TOLERANCE, (
            f"expected ~{REFRESH_30D}s (30d), got {refresh_max}"
        )
        assert access_max is not None
        assert abs(access_max - ACCESS_TTL) <= TOLERANCE, (
            f"access token TTL changed: expected ~{ACCESS_TTL}, got {access_max}"
        )

        refresh_jwt = s.cookies.get("refresh_token")
        assert refresh_jwt
        payload = jwt.decode(refresh_jwt, options={"verify_signature": False})
        assert payload.get("type") == "refresh"
        assert payload.get("remember") is True, f"remember should be True, got {payload!r}"


class TestRefreshPreservesRemember:
    """/api/auth/refresh must re-issue cookies with the same remember TTL."""

    def test_refresh_with_remember_true_keeps_30d(self):
        s, r = _login(remember=True)
        assert r.status_code == 200

        # Delete access cookie to force pure-refresh path (not strictly needed)
        r2 = s.post(f"{BASE_URL}/api/auth/refresh", timeout=15)
        assert r2.status_code == 200, r2.text
        headers = _set_cookie_headers(r2)
        refresh_max = _max_age_for(headers, "refresh_token")
        access_max = _max_age_for(headers, "access_token")
        assert refresh_max is not None
        assert abs(refresh_max - REFRESH_30D) <= TOLERANCE, (
            f"refresh should keep 30d TTL, got {refresh_max}"
        )
        assert access_max is not None
        assert abs(access_max - ACCESS_TTL) <= TOLERANCE

        # New refresh JWT should still have remember=true
        new_refresh = s.cookies.get("refresh_token")
        payload = jwt.decode(new_refresh, options={"verify_signature": False})
        assert payload.get("remember") is True

    def test_refresh_with_remember_false_keeps_7d(self):
        s, r = _login(remember=False)
        assert r.status_code == 200

        r2 = s.post(f"{BASE_URL}/api/auth/refresh", timeout=15)
        assert r2.status_code == 200
        headers = _set_cookie_headers(r2)
        refresh_max = _max_age_for(headers, "refresh_token")
        assert refresh_max is not None
        assert abs(refresh_max - REFRESH_7D) <= TOLERANCE, (
            f"refresh should keep 7d TTL, got {refresh_max}"
        )

        new_refresh = s.cookies.get("refresh_token")
        payload = jwt.decode(new_refresh, options={"verify_signature": False})
        assert payload.get("remember") is False


class TestRegression:
    """Admin login still works end-to-end with and without remember."""

    @pytest.mark.parametrize("remember", [False, True])
    def test_admin_login_and_generate(self, remember):
        s, r = _login(remember=remember)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == ADMIN_EMAIL
        assert "id" in body

        # /auth/me works
        me = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json()["email"] == ADMIN_EMAIL

        # End-to-end narrative generation (LLM call — can be slow)
        payload = {
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Large MOD amalgam with recurrent decay; cusp fracture on mesio-buccal.",
            "radiographic_findings": "Radiolucency under existing restoration.",
            "carrier": "generic",
            "save_to_history": False,
        }
        gr = s.post(f"{BASE_URL}/api/generate", json=payload, timeout=60)
        assert gr.status_code == 200, gr.text
        data = gr.json()
        assert data["procedure_code"] == "D2740"
        assert isinstance(data.get("short_narrative"), str) and len(data["short_narrative"]) > 20
        assert isinstance(data.get("long_narrative"), str) and len(data["long_narrative"]) > 40

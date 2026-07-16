"""Iteration 5 backend hardening tests:
- Explicit CORS allowlist (with allow_credentials=True)
- Register rate limit: 5 signups/IP/hour, 6th returns 429
- Register rate limit does not affect login
- Access token TTL == 30 minutes (was 12h)
- Full regression smoke: admin login -> generate -> appeal
"""
import os
import re
import time
import jwt
import requests
import pytest
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://dent-writeup-tool.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASSWORD = "admin123"

# JWT secret & Mongo for direct verification / cleanup
JWT_SECRET = "cf3081b8ea3f026177bd2a6b63a62b16bb62c8e9193993f8a1b8633331157c2f"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def cleanup_before_and_after(mongo_db):
    """Purge any prior rate-limit records so we get a clean 5+1 window."""
    mongo_db.register_attempts.delete_many({})
    # Clean any leftover ratelimit test users
    mongo_db.users.delete_many({"email": {"$regex": "^ratelimit-"}})
    yield
    mongo_db.register_attempts.delete_many({})
    mongo_db.users.delete_many({"email": {"$regex": "^ratelimit-"}})


# ---------- 1. Smoke: admin login works ----------
def test_admin_login_smoke():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    assert data["role"] == "admin"
    assert "access_token" in s.cookies
    assert "refresh_token" in s.cookies


# ---------- 2. Access token TTL == 30 minutes ----------
def test_access_token_ttl_30_minutes():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    access = s.cookies.get("access_token")
    assert access
    payload = jwt.decode(access, JWT_SECRET, algorithms=["HS256"])
    exp = payload["exp"]
    now = int(datetime.now(timezone.utc).timestamp())
    ttl_seconds = exp - now
    # 30 minutes = 1800 sec. Allow small delta for network + skew.
    assert 1500 < ttl_seconds < 1900, (
        f"access token TTL not ~30 min. Got {ttl_seconds}s (exp={exp}, now={now})"
    )
    assert payload["type"] == "access"
    assert payload["email"] == ADMIN_EMAIL


def test_refresh_token_ttl_7_days():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    refresh = s.cookies.get("refresh_token")
    assert refresh
    payload = jwt.decode(refresh, JWT_SECRET, algorithms=["HS256"])
    ttl = payload["exp"] - int(datetime.now(timezone.utc).timestamp())
    # ~7 days
    assert 6 * 86400 < ttl < 8 * 86400, f"refresh TTL not ~7d. Got {ttl}s"
    assert payload["type"] == "refresh"


# ---------- 3. CORS behavior (verified at APP layer via localhost:8001) ----------
# NOTE: The Cloudflare/K8s ingress at the public URL overrides app CORS headers
# with 'Access-Control-Allow-Origin: *'. That is a platform artifact, not an app
# defect. To validate the app-level allowlist we hit the FastAPI service directly.
LOCAL_API = "http://localhost:8001/api"


def test_cors_allowed_origin_reflected_local():
    origin = "https://dent-writeup-tool.preview.emergentagent.com"
    r = requests.options(
        f"{LOCAL_API}/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code in (200, 204), f"preflight status={r.status_code} body={r.text}"
    assert r.headers.get("access-control-allow-origin") == origin
    assert r.headers.get("access-control-allow-credentials", "").lower() == "true"


def test_cors_disallowed_origin_rejected_local():
    r = requests.options(
        f"{LOCAL_API}/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    # Starlette returns 400 "Disallowed CORS origin" for un-allowlisted origins.
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text!r}"
    allow_origin = r.headers.get("access-control-allow-origin", "")
    assert "evil.example.com" not in allow_origin, (
        f"disallowed origin was echoed by app! allow_origin={allow_origin}"
    )


def test_cors_localhost_origin_allowed():
    """localhost:3000 is in the allowlist for local dev."""
    origin = "http://localhost:3000"
    r = requests.options(
        f"{LOCAL_API}/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == origin
    assert r.headers.get("access-control-allow-credentials", "").lower() == "true"


# ---------- 4. Register rate limit ----------
def test_register_rate_limit_6th_returns_429(cleanup_before_and_after, mongo_db):
    ts = int(time.time())
    session = requests.Session()
    successes = 0
    for i in range(5):
        payload = {
            "email": f"ratelimit-{i}-{ts}@test.com",
            "password": "testpass123",
            "office_name": f"RateLimit Office {i}",
        }
        r = session.post(f"{API}/auth/register", json=payload)
        # Expect 200 (new) or 400 (duplicate); anything else is a real error.
        assert r.status_code in (200, 400), (
            f"attempt {i}: unexpected status {r.status_code}: {r.text}"
        )
        if r.status_code == 200:
            successes += 1
    assert successes >= 1, "no register attempt succeeded — env may be in bad state"

    # Confirm register_attempts collection has 5 rows for this IP window
    count = mongo_db.register_attempts.count_documents({})
    assert count == 5, f"expected 5 register_attempts, got {count}"

    # 6th attempt — must be 429
    r6 = requests.post(
        f"{API}/auth/register",
        json={
            "email": f"ratelimit-6-{ts}@test.com",
            "password": "testpass123",
            "office_name": "RateLimit Office 6",
        },
    )
    assert r6.status_code == 429, (
        f"6th register attempt should be 429, got {r6.status_code} {r6.text}"
    )
    body = r6.json()
    detail = (body.get("detail") or "").lower()
    assert "too many" in detail or "signup" in detail or "hour" in detail, (
        f"429 detail message missing rate-limit hint: {body}"
    )


def test_register_rate_limit_does_not_block_login(cleanup_before_and_after):
    """After the rate limit is tripped, admin login still works."""
    # Reuse the state from previous test: 5+ register_attempts exist.
    r = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200, (
        f"login should be unaffected by register rate limit. Got {r.status_code}: {r.text}"
    )


def test_register_attempts_purge_logic(mongo_db):
    """Directly test purge: insert a stale row, call the endpoint, verify it's gone."""
    from datetime import timedelta
    stale_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    # Use a distinct IP so we do not interfere with current-run rate-limit state
    fake_ip = "203.0.113.99"
    mongo_db.register_attempts.insert_one({"ip": fake_ip, "at": stale_ts})
    # Insert three recent ones too
    now_ts = datetime.now(timezone.utc).isoformat()
    for _ in range(3):
        mongo_db.register_attempts.insert_one({"ip": fake_ip, "at": now_ts})
    # Now call the helper indirectly via a register from that IP by spoofing X-Forwarded-For.
    ts = int(time.time())
    r = requests.post(
        f"{API}/auth/register",
        json={"email": f"purgetest-{ts}@test.com", "password": "testpass123"},
        headers={"X-Forwarded-For": fake_ip},
    )
    # Should succeed (only 3 recent) — stale row must have been purged.
    assert r.status_code in (200, 400), f"unexpected {r.status_code}: {r.text}"
    stale_left = mongo_db.register_attempts.count_documents(
        {"ip": fake_ip, "at": stale_ts}
    )
    assert stale_left == 0, "stale register_attempts row was not purged"
    # Cleanup
    mongo_db.register_attempts.delete_many({"ip": fake_ip})
    mongo_db.users.delete_many({"email": {"$regex": "^purgetest-"}})


# ---------- 5. Full regression smoke: login -> generate -> appeal -> export ----------
def test_full_smoke_generate_appeal_export():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200

    gen_payload = {
        "procedure_code": "D2740",
        "tooth_number": "14",
        "surfaces": "MODL",
        "clinical_findings": "Large existing amalgam, recurrent decay, cracked cusp",
        "radiographic_findings": "Radiolucency under existing restoration",
        "carrier": "generic",
        "save_to_history": True,
    }
    g = s.post(f"{API}/generate", json=gen_payload, timeout=90)
    assert g.status_code == 200, f"generate failed: {g.status_code} {g.text[:300]}"
    narrative = g.json()
    assert narrative["procedure_code"] == "D2740"
    assert narrative["short_narrative"]
    assert narrative["long_narrative"]
    narrative_id = narrative["id"]

    ap = s.post(
        f"{API}/appeals",
        json={
            "narrative_id": narrative_id,
            "denial_reason": "Not medically necessary",
            "denial_code": "D001",
            "save_to_history": True,
        },
        timeout=90,
    )
    assert ap.status_code == 200, f"appeal failed: {ap.status_code} {ap.text[:300]}"
    appeal = ap.json()
    assert appeal["letter"]
    assert appeal["subject_line"]

    pdf = s.post(f"{API}/export/pdf", json=narrative)
    assert pdf.status_code == 200
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert len(pdf.content) > 500


# ---------- 6. Auth me still works with new short TTL ----------
def test_auth_me_after_login():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    me = s.get(f"{API}/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL


def test_refresh_endpoint_rotates_access_token():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    original_access = s.cookies.get("access_token")
    # Force a small wait so exp differs
    time.sleep(1)
    rr = s.post(f"{API}/auth/refresh")
    assert rr.status_code == 200, f"refresh failed: {rr.status_code} {rr.text}"
    new_access = s.cookies.get("access_token")
    assert new_access and new_access != original_access
    payload = jwt.decode(new_access, JWT_SECRET, algorithms=["HS256"])
    ttl = payload["exp"] - int(datetime.now(timezone.utc).timestamp())
    assert 1500 < ttl < 1900, f"refreshed access TTL not ~30 min: {ttl}"

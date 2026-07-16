"""
Custom email/password JWT auth for Narrative.Rx.
Per-playbook: bcrypt hashing, JWT access + refresh, httpOnly cookies, cookie-first extraction.
"""

import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import HTTPException, Request

JWT_ALGORITHM = "HS256"
ACCESS_MINUTES = 30           # short-lived; refresh interceptor renews silently
REFRESH_DAYS = 7
LOCKOUT_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
REGISTER_LIMIT_PER_HOUR = 5   # max signups per IP per hour


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response, access_token: str, refresh_token: str, secure: bool = True) -> None:
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        secure=secure, samesite="lax", max_age=ACCESS_MINUTES * 60, path="/",
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=secure, samesite="lax", max_age=REFRESH_DAYS * 24 * 3600, path="/",
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def cookie_secure_for(request) -> bool:
    """True for HTTPS requests (production), False for plain HTTP (local dev).
    Trusts X-Forwarded-Proto since the app runs behind an ingress that terminates TLS.
    """
    xfp = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    if xfp:
        return xfp == "https"
    return request.url.scheme == "https"


def _extract_token(request: Request, cookie_name: str = "access_token") -> str | None:
    token = request.cookies.get(cookie_name)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    return token


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload


def make_get_current_user(db):
    async def get_current_user(request: Request) -> dict:
        token = _extract_token(request, "access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        payload = decode_token(token, "access")
        try:
            user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid user id")
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    return get_current_user


def _client_ip(request) -> str:
    """Resolve the real client IP behind an ingress/proxy."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else "unknown"


# ---------- Brute-force protection ----------
async def is_locked_out(db, identifier: str) -> bool:
    doc = await db.login_attempts.find_one({"identifier": identifier})
    if not doc:
        return False
    if doc.get("locked_until"):
        locked_until = doc["locked_until"]
        if isinstance(locked_until, str):
            locked_until = datetime.fromisoformat(locked_until)
        if locked_until > datetime.now(timezone.utc):
            return True
    return False


async def register_failed_attempt(db, identifier: str) -> None:
    doc = await db.login_attempts.find_one({"identifier": identifier})
    now = datetime.now(timezone.utc)
    if not doc:
        await db.login_attempts.insert_one({
            "identifier": identifier, "count": 1, "last_attempt": now.isoformat()
        })
        return
    count = doc.get("count", 0) + 1
    update = {"count": count, "last_attempt": now.isoformat()}
    if count >= LOCKOUT_ATTEMPTS:
        update["locked_until"] = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
    await db.login_attempts.update_one({"identifier": identifier}, {"$set": update})


async def clear_login_attempts(db, identifier: str) -> None:
    await db.login_attempts.delete_one({"identifier": identifier})


# ---------- Registration rate limiting ----------
async def check_and_record_register(db, ip: str) -> bool:
    """Return True if allowed, False if rate-limited.

    Rolling 1-hour window per IP; max REGISTER_LIMIT_PER_HOUR signups.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=1)
    # Purge stale entries for this IP
    await db.register_attempts.delete_many({
        "ip": ip,
        "at": {"$lt": window_start.isoformat()},
    })
    count = await db.register_attempts.count_documents({"ip": ip})
    if count >= REGISTER_LIMIT_PER_HOUR:
        return False
    await db.register_attempts.insert_one({"ip": ip, "at": now.isoformat()})
    return True


# ---------- Admin/demo seeding ----------
async def seed_default_user(db) -> dict | None:
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return None
    existing = await db.users.find_one({"email": admin_email.lower()})
    if existing is None:
        doc = {
            "email": admin_email.lower(),
            "password_hash": hash_password(admin_password),
            "name": "Demo Office",
            "office_name": "Demo Office",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await db.users.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )
    existing["_id"] = str(existing["_id"])
    existing.pop("password_hash", None)
    return existing


async def ensure_indexes(db) -> None:
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.register_attempts.create_index("ip")
    await db.narratives.create_index("user_id")
    await db.visits.create_index("user_id")
    await db.appeals.create_index("user_id")

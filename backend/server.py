from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import re
import json
import logging
import uuid
import asyncio
import subprocess
import sys
import shutil
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import Response as StarletteResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict, EmailStr

from procedures import PROCEDURES, get_procedure
from narrative_service import (
    generate_narrative, regenerate_field, generate_appeal_letter, CARRIER_GUIDANCE,
    stream_narrative, stream_regenerate_field, stream_appeal_letter, parse_marker_text,
)
from pdf_service import (
    build_pdf, build_visit_pdf, build_txt, build_visit_txt,
    build_appeal_pdf, build_appeal_txt,
)
import auth as auth_mod


mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Dental Narrative Assistant")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

get_current_user = auth_mod.make_get_current_user(db)


# ---------- Pydantic Models ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    office_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False


class UserOut(BaseModel):
    id: str
    email: str
    office_name: Optional[str] = None
    role: str = "user"


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    procedure_code: str
    tooth_number: Optional[str] = None
    surfaces: Optional[str] = None
    symptoms: Optional[str] = None
    clinical_findings: Optional[str] = None
    radiographic_findings: Optional[str] = None
    pulp_status: Optional[str] = None
    perio_findings: Optional[str] = None
    prior_treatment: Optional[str] = None
    date_of_service: Optional[str] = None
    additional_notes: Optional[str] = None
    patient_label: Optional[str] = None
    carrier: Optional[str] = "generic"
    save_to_history: bool = True


class RegenerateRequest(GenerateRequest):
    field: str
    existing_short: Optional[str] = None
    existing_long: Optional[str] = None
    save_to_history: bool = False


class UpdateNarrativeRequest(BaseModel):
    short_narrative: Optional[str] = None
    long_narrative: Optional[str] = None


class VisitProcedure(BaseModel):
    model_config = ConfigDict(extra="ignore")
    procedure_code: str
    tooth_number: Optional[str] = None
    surfaces: Optional[str] = None
    symptoms: Optional[str] = None
    clinical_findings: Optional[str] = None
    radiographic_findings: Optional[str] = None
    pulp_status: Optional[str] = None
    perio_findings: Optional[str] = None
    prior_treatment: Optional[str] = None
    additional_notes: Optional[str] = None


class VisitGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_label: Optional[str] = None
    carrier: Optional[str] = "generic"
    date_of_service: Optional[str] = None
    visit_notes: Optional[str] = None
    procedures: List[VisitProcedure]
    save_to_history: bool = True


class AppealRequest(BaseModel):
    narrative_id: Optional[str] = None
    # If no narrative_id, caller must provide the full narrative payload
    narrative: Optional[dict] = None
    denial_reason: str
    denial_code: Optional[str] = None
    extra_context: Optional[str] = None
    save_to_history: bool = True


class UpdateAppealRequest(BaseModel):
    letter: Optional[str] = None
    subject_line: Optional[str] = None
    outcome: Optional[str] = None  # "pending" | "won" | "lost"
    outcome_notes: Optional[str] = None


class PracticeSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    practice_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    npi: Optional[str] = None
    tax_id: Optional[str] = None
    provider_name: Optional[str] = None
    provider_license: Optional[str] = None


async def _get_practice_settings(user_id: str) -> dict:
    doc = await db.practice_settings.find_one({"user_id": user_id}, {"_id": 0, "user_id": 0})
    return doc or {}


class RadiographAdvice(BaseModel):
    required: List[str] = []
    recommended: List[str] = []
    note: str = ""


class NarrativeRecord(BaseModel):
    id: str
    user_id: Optional[str] = None
    procedure_code: str
    procedure_name: str
    category: str
    tooth_number: Optional[str] = None
    patient_label: Optional[str] = None
    carrier: Optional[str] = "generic"
    short_narrative: str
    long_narrative: str
    radiographs: RadiographAdvice
    inputs: dict
    created_at: str


class VisitRecord(BaseModel):
    id: str
    user_id: Optional[str] = None
    patient_label: Optional[str] = None
    carrier: Optional[str] = "generic"
    date_of_service: Optional[str] = None
    visit_notes: Optional[str] = None
    records: List[NarrativeRecord]
    created_at: str


class AppealRecord(BaseModel):
    id: str
    user_id: Optional[str] = None
    narrative_id: Optional[str] = None
    procedure_code: Optional[str] = None
    procedure_name: Optional[str] = None
    tooth_number: Optional[str] = None
    carrier: Optional[str] = None
    subject_line: str
    letter: str
    denial_reason: str
    denial_code: Optional[str] = None
    extra_context: Optional[str] = None
    original_short_narrative: Optional[str] = None
    original_long_narrative: Optional[str] = None
    outcome: Optional[str] = "pending"  # "pending" | "won" | "lost"
    outcome_notes: Optional[str] = None
    outcome_updated_at: Optional[str] = None
    created_at: str


# ---------- Startup ----------
@app.on_event("startup")
async def on_startup():
    await auth_mod.ensure_indexes(db)
    await auth_mod.seed_default_user(db)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# ---------- Auth Routes ----------
auth_router = APIRouter(prefix="/api/auth")


def _user_out(user_doc: dict) -> dict:
    return {
        "id": str(user_doc["_id"]),
        "email": user_doc["email"],
        "office_name": user_doc.get("office_name"),
        "role": user_doc.get("role", "user"),
    }


@auth_router.post("/register")
async def register(payload: RegisterRequest, request: Request, response: Response):
    ip = auth_mod._client_ip(request)
    if not await auth_mod.check_and_record_register(db, ip):
        raise HTTPException(
            status_code=429,
            detail="Too many signups from this location. Please try again in an hour.",
        )
    email = payload.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {
        "email": email,
        "password_hash": auth_mod.hash_password(payload.password),
        "office_name": (payload.office_name or "").strip() or None,
        "name": (payload.office_name or email.split("@")[0]).strip(),
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    user_id = str(doc["_id"])
    access = auth_mod.create_access_token(user_id, email)
    refresh = auth_mod.create_refresh_token(user_id)
    auth_mod.set_auth_cookies(response, access, refresh, secure=auth_mod.cookie_secure_for(request))
    return {**_user_out(doc), "access_token": access}


@auth_router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    email = payload.email.lower().strip()
    ip = auth_mod._client_ip(request)
    identifier_ip = f"{ip}:{email}"
    identifier_email = f"email:{email}"
    # Lockout if either IP-based or email-only counter tripped
    if (await auth_mod.is_locked_out(db, identifier_ip) or
            await auth_mod.is_locked_out(db, identifier_email)):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not auth_mod.verify_password(payload.password, user["password_hash"]):
        await auth_mod.register_failed_attempt(db, identifier_ip)
        await auth_mod.register_failed_attempt(db, identifier_email)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await auth_mod.clear_login_attempts(db, identifier_ip)
    await auth_mod.clear_login_attempts(db, identifier_email)
    user_id = str(user["_id"])
    access = auth_mod.create_access_token(user_id, email)
    refresh = auth_mod.create_refresh_token(user_id, remember=payload.remember)
    auth_mod.set_auth_cookies(
        response, access, refresh,
        secure=auth_mod.cookie_secure_for(request),
        remember=payload.remember,
    )
    return {**_user_out(user), "access_token": access}


@auth_router.post("/logout")
async def logout(response: Response, user=Depends(get_current_user)):
    auth_mod.clear_auth_cookies(response)
    return {"ok": True}


@auth_router.get("/me")
async def me(user=Depends(get_current_user)):
    return _user_out({**user, "_id": user["_id"]})


@auth_router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = auth_mod._extract_token(request, "refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = auth_mod.decode_token(token, "refresh")
    user_id = payload["sub"]
    from bson import ObjectId
    user = None
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user id")
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    remember = bool(payload.get("remember", False))
    access = auth_mod.create_access_token(user_id, user["email"])
    refresh = auth_mod.create_refresh_token(user_id, remember=remember)
    auth_mod.set_auth_cookies(
        response, access, refresh,
        secure=auth_mod.cookie_secure_for(request),
        remember=remember,
    )
    return {**_user_out(user), "access_token": access}


app.include_router(auth_router)


# ---------- Practice Settings ----------
@api_router.get("/settings/practice", response_model=PracticeSettings)
async def get_practice_settings(user=Depends(get_current_user)):
    return await _get_practice_settings(user["_id"])


@api_router.put("/settings/practice", response_model=PracticeSettings)
async def update_practice_settings(req: PracticeSettings, user=Depends(get_current_user)):
    payload = req.model_dump()
    await db.practice_settings.update_one(
        {"user_id": user["_id"]},
        {"$set": {**payload, "user_id": user["_id"], "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return payload


# ---------- Helpers ----------
async def _build_narrative_record(payload: dict, save: bool, user_id: str) -> NarrativeRecord:
    procedure = get_procedure(payload["procedure_code"])
    if not procedure:
        raise HTTPException(status_code=400, detail=f"Unknown procedure code: {payload['procedure_code']}")
    result = await generate_narrative(payload, procedure)
    record = NarrativeRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        procedure_code=procedure["code"],
        procedure_name=procedure["name"],
        category=procedure["category"],
        tooth_number=payload.get("tooth_number"),
        patient_label=payload.get("patient_label"),
        carrier=(payload.get("carrier") or "generic").lower(),
        short_narrative=result["short_narrative"],
        long_narrative=result["long_narrative"],
        radiographs=RadiographAdvice(**procedure["radiographs"]),
        inputs={k: v for k, v in payload.items()
                if k not in ("save_to_history",) and v},
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    if save:
        await db.narratives.insert_one(record.model_dump())
    return record


# ---------- Public Routes ----------
@api_router.get("/")
async def root():
    return {"service": "Dental Narrative Assistant", "status": "ok"}


@api_router.get("/procedures")
async def list_procedures():
    return {"procedures": PROCEDURES}


@api_router.get("/carriers")
async def list_carriers():
    return {"carriers": [
        {"key": k, "label": k.title() if k != "bcbs" else "BCBS", "guidance": v}
        for k, v in CARRIER_GUIDANCE.items()
    ]}


# ---------- System / Self-Update ----------
_REPO_ROOT = ROOT_DIR.parent  # /app/backend/.. == repo root


def _git(args: list[str], cwd: Path = _REPO_ROOT, timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git"] + args, cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "git not installed"
    except subprocess.TimeoutExpired:
        return 124, "git command timed out"
    except Exception as e:
        return 1, f"git error: {e}"


def _current_version() -> dict:
    rc_sha, sha = _git(["rev-parse", "HEAD"])
    rc_short, short = _git(["rev-parse", "--short", "HEAD"])
    rc_branch, branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    rc_date, date = _git(["log", "-1", "--format=%cI"])
    rc_msg, msg = _git(["log", "-1", "--format=%s"])
    is_repo = rc_sha == 0
    return {
        "is_git_repo": is_repo,
        "commit": sha if is_repo else None,
        "commit_short": short if rc_short == 0 else None,
        "branch": branch if rc_branch == 0 else None,
        "commit_date": date if rc_date == 0 else None,
        "commit_message": msg if rc_msg == 0 else None,
        "platform": sys.platform,
        "repo_root": str(_REPO_ROOT),
    }


def _require_admin(user: dict):
    if (user.get("role") or "user") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")


@api_router.get("/system/version")
async def system_version(user=Depends(get_current_user)):
    return _current_version()


@api_router.post("/system/check-updates")
async def system_check_updates(user=Depends(get_current_user)):
    cur = _current_version()
    if not cur["is_git_repo"]:
        raise HTTPException(status_code=400, detail="Not a git checkout — self-update unavailable")
    branch = cur["branch"] or "main"
    rc, _out = _git(["fetch", "--quiet", "origin", branch], timeout=30)
    if rc != 0:
        raise HTTPException(status_code=502, detail=f"git fetch failed: {_out}")
    rc, latest_sha = _git(["rev-parse", f"origin/{branch}"])
    if rc != 0:
        raise HTTPException(status_code=502, detail=f"could not read origin: {latest_sha}")
    rc, count_behind = _git(["rev-list", "--count", f"HEAD..origin/{branch}"])
    rc, count_ahead = _git(["rev-list", "--count", f"origin/{branch}..HEAD"])
    behind = int(count_behind) if count_behind.isdigit() else 0
    ahead = int(count_ahead) if count_ahead.isdigit() else 0
    rc, latest_msg = _git(["log", "-1", "--format=%s", latest_sha])
    rc, latest_date = _git(["log", "-1", "--format=%cI", latest_sha])
    return {
        "current": cur["commit"],
        "current_short": cur["commit_short"],
        "latest": latest_sha,
        "latest_short": latest_sha[:7] if latest_sha else None,
        "latest_message": latest_msg if rc == 0 else None,
        "latest_date": latest_date if rc == 0 else None,
        "branch": branch,
        "ahead": ahead,
        "behind": behind,
        "has_update": behind > 0,
    }


@api_router.post("/system/update")
async def system_update(user=Depends(get_current_user)):
    if sys.platform != "win32":
        raise HTTPException(
            status_code=400,
            detail="Self-update is only supported on Windows. Run `./windows/update.bat` manually.",
        )
    updater = _REPO_ROOT / "windows" / "updater.bat"
    if not updater.exists():
        raise HTTPException(status_code=500, detail=f"Updater not found at {updater}")

    # Spawn the batch script DETACHED so it survives this backend's own restart.
    # DETACHED_PROCESS = 0x00000008, CREATE_NEW_PROCESS_GROUP = 0x00000200
    DETACHED = 0x00000008 | 0x00000200
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", str(updater)],
            cwd=str(_REPO_ROOT),
            creationflags=DETACHED,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn updater: {e}")

    return {
        "started": True,
        "message": "Update started. The app will restart in ~30 seconds and be back within 3-5 minutes.",
    }


# ---------- Authenticated Narrative Routes ----------
@api_router.post("/generate", response_model=NarrativeRecord)
async def generate(req: GenerateRequest, user=Depends(get_current_user)):
    try:
        return await _build_narrative_record(req.model_dump(), save=req.save_to_history, user_id=user["_id"])
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Narrative generation failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")


def _sse_event(data: str, event: str = "chunk") -> bytes:
    """Format one Server-Sent Event. Data is escaped so newlines survive."""
    esc = data.replace("\r\n", "\n").replace("\n", "\\n")
    return f"event: {event}\ndata: {esc}\n\n".encode("utf-8")


@api_router.post("/generate/stream")
async def generate_stream(req: GenerateRequest, user=Depends(get_current_user)):
    """Stream narrative tokens as they're generated. Ends with a `done` event carrying the saved record."""
    procedure = get_procedure(req.procedure_code)
    if not procedure:
        raise HTTPException(status_code=400, detail=f"Unknown procedure code: {req.procedure_code}")
    payload = req.model_dump()

    async def event_stream():
        full = []
        try:
            async for chunk in stream_narrative(payload, procedure):
                full.append(chunk)
                yield _sse_event(chunk, "chunk")
            parsed = parse_marker_text("".join(full))
            record = NarrativeRecord(
                id=str(uuid.uuid4()),
                user_id=user["_id"],
                procedure_code=procedure["code"],
                procedure_name=procedure["name"],
                category=procedure["category"],
                tooth_number=payload.get("tooth_number"),
                patient_label=payload.get("patient_label"),
                carrier=(payload.get("carrier") or "generic").lower(),
                short_narrative=parsed["short_narrative"],
                long_narrative=parsed["long_narrative"],
                radiographs=RadiographAdvice(**procedure["radiographs"]),
                inputs={k: v for k, v in payload.items() if k not in ("save_to_history",) and v},
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            if req.save_to_history:
                await db.narratives.insert_one(record.model_dump())
            yield _sse_event(json.dumps(record.model_dump()), "done")
        except Exception as e:
            logger.exception("Streaming narrative failed")
            yield _sse_event(str(e), "error")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@api_router.post("/regenerate/stream")
async def regenerate_stream(req: RegenerateRequest, user=Depends(get_current_user)):
    procedure = get_procedure(req.procedure_code)
    if not procedure:
        raise HTTPException(status_code=400, detail=f"Unknown procedure code: {req.procedure_code}")
    if req.field not in ("short", "long"):
        raise HTTPException(status_code=400, detail="field must be 'short' or 'long'")
    payload = req.model_dump()

    async def event_stream():
        full = []
        try:
            async for chunk in stream_regenerate_field(req.field, payload, procedure):
                full.append(chunk)
                yield _sse_event(chunk, "chunk")
            parsed = parse_marker_text("".join(full))
            key = f"{req.field}_narrative"
            yield _sse_event(json.dumps({"field": req.field, "text": parsed.get(key, "")}), "done")
        except Exception as e:
            logger.exception("Streaming regenerate failed")
            yield _sse_event(str(e), "error")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )



@api_router.post("/regenerate")
async def regenerate(req: RegenerateRequest, user=Depends(get_current_user)):
    procedure = get_procedure(req.procedure_code)
    if not procedure:
        raise HTTPException(status_code=400, detail=f"Unknown procedure code: {req.procedure_code}")
    if req.field not in ("short", "long"):
        raise HTTPException(status_code=400, detail="field must be 'short' or 'long'")
    try:
        text = await regenerate_field(req.field, req.model_dump(), procedure)
        return {"field": req.field, "text": text}
    except Exception as e:
        logger.exception("Regeneration failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")


@api_router.post("/visits/generate", response_model=VisitRecord)
async def generate_visit(req: VisitGenerateRequest, user=Depends(get_current_user)):
    if not req.procedures:
        raise HTTPException(status_code=400, detail="At least one procedure required")
    tasks = []
    for p in req.procedures:
        payload = p.model_dump()
        payload["carrier"] = req.carrier
        payload["patient_label"] = req.patient_label
        payload["date_of_service"] = req.date_of_service
        payload["visit_notes"] = req.visit_notes
        tasks.append(_build_narrative_record(payload, save=False, user_id=user["_id"]))
    try:
        records = await asyncio.gather(*tasks)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Visit generation failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    visit = VisitRecord(
        id=str(uuid.uuid4()),
        user_id=user["_id"],
        patient_label=req.patient_label,
        carrier=(req.carrier or "generic").lower(),
        date_of_service=req.date_of_service,
        visit_notes=req.visit_notes,
        records=records,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    if req.save_to_history:
        await db.visits.insert_one(visit.model_dump())
        for rec in records:
            await db.narratives.insert_one(rec.model_dump())
    return visit


@api_router.get("/history", response_model=List[NarrativeRecord])
async def list_history(limit: int = 100, user=Depends(get_current_user)):
    docs = await db.narratives.find({"user_id": user["_id"]}, {"_id": 0}) \
        .sort("created_at", -1).to_list(limit)
    return docs


@api_router.get("/history/{record_id}", response_model=NarrativeRecord)
async def get_history_item(record_id: str, user=Depends(get_current_user)):
    doc = await db.narratives.find_one({"id": record_id, "user_id": user["_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


@api_router.patch("/history/{record_id}", response_model=NarrativeRecord)
async def update_history_item(record_id: str, req: UpdateNarrativeRequest, user=Depends(get_current_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.narratives.update_one(
        {"id": record_id, "user_id": user["_id"]}, {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.narratives.find_one({"id": record_id, "user_id": user["_id"]}, {"_id": 0})
    return doc


@api_router.delete("/history/{record_id}")
async def delete_history_item(record_id: str, user=Depends(get_current_user)):
    result = await db.narratives.delete_one({"id": record_id, "user_id": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": record_id}


@api_router.get("/visits", response_model=List[VisitRecord])
async def list_visits(limit: int = 50, user=Depends(get_current_user)):
    docs = await db.visits.find({"user_id": user["_id"]}, {"_id": 0}) \
        .sort("created_at", -1).to_list(limit)
    return docs


@api_router.get("/visits/{visit_id}", response_model=VisitRecord)
async def get_visit(visit_id: str, user=Depends(get_current_user)):
    doc = await db.visits.find_one({"id": visit_id, "user_id": user["_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


# ---------- Appeal Letter Routes ----------
@api_router.post("/appeals", response_model=AppealRecord)
async def create_appeal(req: AppealRequest, user=Depends(get_current_user)):
    narrative = None
    if req.narrative_id:
        narrative = await db.narratives.find_one(
            {"id": req.narrative_id, "user_id": user["_id"]}, {"_id": 0},
        )
        if not narrative:
            raise HTTPException(status_code=404, detail="Narrative not found")
    elif req.narrative:
        narrative = req.narrative
    else:
        raise HTTPException(status_code=400, detail="narrative_id or narrative payload required")

    if not req.denial_reason or not req.denial_reason.strip():
        raise HTTPException(status_code=400, detail="denial_reason is required")

    office_name = user.get("office_name") or "[Office Name]"
    practice = await _get_practice_settings(user["_id"])
    prior_wins = await _prior_wins_for(user["_id"], (narrative.get("carrier") or "generic").lower(), narrative.get("procedure_code"))
    try:
        result = await generate_appeal_letter(
            narrative,
            req.denial_reason,
            req.denial_code or "",
            req.extra_context or "",
            office_name=practice.get("practice_name") or office_name,
            practice=practice,
            prior_wins=prior_wins,
        )
    except Exception as e:
        logger.exception("Appeal generation failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    appeal = AppealRecord(
        id=str(uuid.uuid4()),
        user_id=user["_id"],
        narrative_id=req.narrative_id,
        procedure_code=narrative.get("procedure_code"),
        procedure_name=narrative.get("procedure_name"),
        tooth_number=narrative.get("tooth_number"),
        carrier=(narrative.get("carrier") or "generic").lower(),
        subject_line=result["subject_line"],
        letter=result["letter"],
        denial_reason=req.denial_reason.strip(),
        denial_code=req.denial_code,
        extra_context=req.extra_context,
        original_short_narrative=narrative.get("short_narrative"),
        original_long_narrative=narrative.get("long_narrative"),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    if req.save_to_history:
        await db.appeals.insert_one(appeal.model_dump())
    return appeal


async def _prior_wins_for(user_id: str, carrier: Optional[str], procedure_code: Optional[str]) -> list[dict]:
    """Fetch this office's WON appeals for the same carrier + procedure_code — used as few-shot."""
    if not carrier or not procedure_code:
        return []
    q = {"user_id": user_id, "carrier": carrier, "procedure_code": procedure_code, "outcome": "won"}
    docs = await db.appeals.find(q, {"_id": 0, "letter": 1, "subject_line": 1}) \
        .sort("outcome_updated_at", -1).to_list(2)
    return docs


@api_router.post("/appeals/stream")
async def create_appeal_stream(req: AppealRequest, user=Depends(get_current_user)):
    narrative = None
    if req.narrative_id:
        narrative = await db.narratives.find_one({"id": req.narrative_id, "user_id": user["_id"]}, {"_id": 0})
        if not narrative:
            raise HTTPException(status_code=404, detail="Narrative not found")
    elif req.narrative:
        narrative = req.narrative
    else:
        raise HTTPException(status_code=400, detail="narrative_id or narrative payload required")
    if not req.denial_reason or not req.denial_reason.strip():
        raise HTTPException(status_code=400, detail="denial_reason is required")

    office_name = user.get("office_name") or "[Office Name]"
    practice = await _get_practice_settings(user["_id"])
    prior_wins = await _prior_wins_for(user["_id"], (narrative.get("carrier") or "generic").lower(), narrative.get("procedure_code"))

    async def event_stream():
        full = []
        try:
            async for chunk in stream_appeal_letter(
                narrative, req.denial_reason, req.denial_code or "", req.extra_context or "",
                office_name=practice.get("practice_name") or office_name,
                practice=practice, prior_wins=prior_wins,
            ):
                full.append(chunk)
                yield _sse_event(chunk, "chunk")
            parsed = parse_marker_text("".join(full))
            appeal = AppealRecord(
                id=str(uuid.uuid4()),
                user_id=user["_id"],
                narrative_id=req.narrative_id,
                procedure_code=narrative.get("procedure_code"),
                procedure_name=narrative.get("procedure_name"),
                tooth_number=narrative.get("tooth_number"),
                carrier=(narrative.get("carrier") or "generic").lower(),
                subject_line=parsed["subject_line"],
                letter=parsed["letter"],
                denial_reason=req.denial_reason.strip(),
                denial_code=req.denial_code,
                extra_context=req.extra_context,
                original_short_narrative=narrative.get("short_narrative"),
                original_long_narrative=narrative.get("long_narrative"),
                outcome="pending",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            if req.save_to_history:
                await db.appeals.insert_one(appeal.model_dump())
            yield _sse_event(json.dumps(appeal.model_dump()), "done")
        except Exception as e:
            logger.exception("Streaming appeal failed")
            yield _sse_event(str(e), "error")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@api_router.get("/appeals/patterns")
async def appeal_patterns(carrier: Optional[str] = None, procedure_code: Optional[str] = None,
                          user=Depends(get_current_user)):
    """Return win/loss/pending stats and recent winning-appeal excerpts for a (carrier, procedure) pair."""
    q: dict = {"user_id": user["_id"]}
    if carrier: q["carrier"] = carrier.lower()
    if procedure_code: q["procedure_code"] = procedure_code
    total = await db.appeals.count_documents(q)
    won = await db.appeals.count_documents({**q, "outcome": "won"})
    lost = await db.appeals.count_documents({**q, "outcome": "lost"})
    pending = await db.appeals.count_documents({**q, "outcome": {"$in": ["pending", None]}})
    winning = await db.appeals.find({**q, "outcome": "won"}, {"_id": 0}) \
        .sort("outcome_updated_at", -1).to_list(3)
    return {
        "carrier": carrier,
        "procedure_code": procedure_code,
        "total": total,
        "won": won,
        "lost": lost,
        "pending": pending,
        "win_rate": (won / (won + lost)) if (won + lost) > 0 else None,
        "winning_appeals": [
            {
                "id": w["id"], "subject_line": w.get("subject_line", ""),
                "letter_excerpt": (w.get("letter") or "")[:400],
                "outcome_updated_at": w.get("outcome_updated_at"),
            } for w in winning
        ],
    }



@api_router.get("/appeals", response_model=List[AppealRecord])
async def list_appeals(limit: int = 100, user=Depends(get_current_user)):
    docs = await db.appeals.find({"user_id": user["_id"]}, {"_id": 0}) \
        .sort("created_at", -1).to_list(limit)
    return docs


@api_router.get("/appeals/{appeal_id}", response_model=AppealRecord)
async def get_appeal(appeal_id: str, user=Depends(get_current_user)):
    doc = await db.appeals.find_one({"id": appeal_id, "user_id": user["_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


@api_router.patch("/appeals/{appeal_id}", response_model=AppealRecord)
async def update_appeal(appeal_id: str, req: UpdateAppealRequest, user=Depends(get_current_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "outcome" in updates:
        if updates["outcome"] not in ("pending", "won", "lost"):
            raise HTTPException(status_code=400, detail="outcome must be pending, won, or lost")
        updates["outcome_updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.appeals.update_one(
        {"id": appeal_id, "user_id": user["_id"]}, {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.appeals.find_one({"id": appeal_id, "user_id": user["_id"]}, {"_id": 0})
    return doc


@api_router.delete("/appeals/{appeal_id}")
async def delete_appeal(appeal_id: str, user=Depends(get_current_user)):
    result = await db.appeals.delete_one({"id": appeal_id, "user_id": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": appeal_id}


# ---------- Export ----------
@api_router.post("/export/pdf")
async def export_pdf(payload: dict, user=Depends(get_current_user)):
    practice = await _get_practice_settings(user["_id"])
    pdf_bytes = build_pdf(payload, practice=practice)
    filename = f"claim-{payload.get('procedure_code', 'narrative')}-{payload.get('id', 'draft')[:8]}.pdf"
    return StarletteResponse(pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api_router.post("/export/txt")
async def export_txt(payload: dict, user=Depends(get_current_user)):
    practice = await _get_practice_settings(user["_id"])
    text = build_txt(payload, practice=practice)
    filename = f"claim-{payload.get('procedure_code', 'narrative')}-{payload.get('id', 'draft')[:8]}.txt"
    return StarletteResponse(text, media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api_router.post("/export/visit/pdf")
async def export_visit_pdf(payload: dict, user=Depends(get_current_user)):
    practice = await _get_practice_settings(user["_id"])
    pdf_bytes = build_visit_pdf(payload, practice=practice)
    filename = f"visit-packet-{payload.get('id', 'draft')[:8]}.pdf"
    return StarletteResponse(pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api_router.post("/export/visit/txt")
async def export_visit_txt(payload: dict, user=Depends(get_current_user)):
    practice = await _get_practice_settings(user["_id"])
    text = build_visit_txt(payload, practice=practice)
    filename = f"visit-packet-{payload.get('id', 'draft')[:8]}.txt"
    return StarletteResponse(text, media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api_router.post("/export/appeal/pdf")
async def export_appeal_pdf(payload: dict, user=Depends(get_current_user)):
    practice = await _get_practice_settings(user["_id"])
    pdf_bytes = build_appeal_pdf(payload, practice=practice)
    filename = f"appeal-{payload.get('procedure_code', 'letter')}-{payload.get('id', 'draft')[:8]}.pdf"
    return StarletteResponse(pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api_router.post("/export/appeal/txt")
async def export_appeal_txt(payload: dict, user=Depends(get_current_user)):
    practice = await _get_practice_settings(user["_id"])
    text = build_appeal_txt(payload, practice=practice)
    filename = f"appeal-{payload.get('procedure_code', 'letter')}-{payload.get('id', 'draft')[:8]}.txt"
    return StarletteResponse(text, media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Serve React build (native / single-process deployment) ----------
# When SERVE_FRONTEND is truthy and frontend/build exists, this same FastAPI
# process serves the SPA at /, so a Windows Server install needs only one service.
# Safe to leave enabled: if the build dir isn't there, this is a no-op.
FRONTEND_BUILD = ROOT_DIR.parent / "frontend" / "build"
if os.environ.get("SERVE_FRONTEND", "").lower() in ("1", "true", "yes") and FRONTEND_BUILD.exists():
    _static_dir = FRONTEND_BUILD / "static"
    if _static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(_static_dir)), name="react-static")

    @app.get("/{full_path:path}")
    async def _spa_fallback(full_path: str):
        # Never shadow API routes
        if full_path.startswith("api") or full_path.startswith("static"):
            raise HTTPException(status_code=404)
        candidate = FRONTEND_BUILD / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_BUILD / "index.html")


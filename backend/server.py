from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone

from procedures import PROCEDURES, get_procedure
from narrative_service import generate_narrative, regenerate_field, CARRIER_GUIDANCE
from pdf_service import build_pdf, build_visit_pdf, build_txt, build_visit_txt


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Dental Narrative Assistant")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---------- Models ----------
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
    field: str  # "short" | "long"
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


class RadiographAdvice(BaseModel):
    required: List[str] = []
    recommended: List[str] = []
    note: str = ""


class NarrativeRecord(BaseModel):
    id: str
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
    patient_label: Optional[str] = None
    carrier: Optional[str] = "generic"
    date_of_service: Optional[str] = None
    visit_notes: Optional[str] = None
    records: List[NarrativeRecord]
    created_at: str


# ---------- Helpers ----------
async def _build_narrative_record(payload: dict, save: bool) -> NarrativeRecord:
    procedure = get_procedure(payload["procedure_code"])
    if not procedure:
        raise HTTPException(status_code=400, detail=f"Unknown procedure code: {payload['procedure_code']}")
    result = await generate_narrative(payload, procedure)
    record = NarrativeRecord(
        id=str(uuid.uuid4()),
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


# ---------- Routes ----------
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


@api_router.post("/generate", response_model=NarrativeRecord)
async def generate(req: GenerateRequest):
    try:
        return await _build_narrative_record(req.model_dump(), save=req.save_to_history)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Narrative generation failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")


@api_router.post("/regenerate")
async def regenerate(req: RegenerateRequest):
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
async def generate_visit(req: VisitGenerateRequest):
    if not req.procedures:
        raise HTTPException(status_code=400, detail="At least one procedure required")

    # Build enriched payloads carrying shared visit context
    tasks = []
    for p in req.procedures:
        payload = p.model_dump()
        payload["carrier"] = req.carrier
        payload["patient_label"] = req.patient_label
        payload["date_of_service"] = req.date_of_service
        payload["visit_notes"] = req.visit_notes
        tasks.append(_build_narrative_record(payload, save=False))

    try:
        records = await asyncio.gather(*tasks)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Visit generation failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    visit = VisitRecord(
        id=str(uuid.uuid4()),
        patient_label=req.patient_label,
        carrier=(req.carrier or "generic").lower(),
        date_of_service=req.date_of_service,
        visit_notes=req.visit_notes,
        records=records,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    if req.save_to_history:
        await db.visits.insert_one(visit.model_dump())
        # also index individual records for the single-narrative history view
        for rec in records:
            await db.narratives.insert_one(rec.model_dump())
    return visit


@api_router.get("/history", response_model=List[NarrativeRecord])
async def list_history(limit: int = 100):
    docs = await db.narratives.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return docs


@api_router.get("/history/{record_id}", response_model=NarrativeRecord)
async def get_history_item(record_id: str):
    doc = await db.narratives.find_one({"id": record_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


@api_router.patch("/history/{record_id}", response_model=NarrativeRecord)
async def update_history_item(record_id: str, req: UpdateNarrativeRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.narratives.update_one({"id": record_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.narratives.find_one({"id": record_id}, {"_id": 0})
    return doc


@api_router.delete("/history/{record_id}")
async def delete_history_item(record_id: str):
    result = await db.narratives.delete_one({"id": record_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": record_id}


@api_router.get("/visits", response_model=List[VisitRecord])
async def list_visits(limit: int = 50):
    docs = await db.visits.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return docs


@api_router.get("/visits/{visit_id}", response_model=VisitRecord)
async def get_visit(visit_id: str):
    doc = await db.visits.find_one({"id": visit_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


# ---------- Export ----------
class ExportPayload(BaseModel):
    model_config = ConfigDict(extra="allow")


@api_router.post("/export/pdf")
async def export_pdf(payload: dict):
    pdf_bytes = build_pdf(payload)
    filename = f"claim-{payload.get('procedure_code', 'narrative')}-{payload.get('id', 'draft')[:8]}.pdf"
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.post("/export/txt")
async def export_txt(payload: dict):
    text = build_txt(payload)
    filename = f"claim-{payload.get('procedure_code', 'narrative')}-{payload.get('id', 'draft')[:8]}.txt"
    return Response(
        text,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.post("/export/visit/pdf")
async def export_visit_pdf(payload: dict):
    pdf_bytes = build_visit_pdf(payload)
    filename = f"visit-packet-{payload.get('id', 'draft')[:8]}.pdf"
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.post("/export/visit/txt")
async def export_visit_txt(payload: dict):
    text = build_visit_txt(payload)
    filename = f"visit-packet-{payload.get('id', 'draft')[:8]}.txt"
    return Response(
        text,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

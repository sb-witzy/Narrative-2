from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone

from procedures import PROCEDURES, get_procedure
from narrative_service import generate_narrative


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
    patient_label: Optional[str] = None  # e.g., "Pt #1024" - no PHI
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
    short_narrative: str
    long_narrative: str
    radiographs: RadiographAdvice
    inputs: dict
    created_at: str


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"service": "Dental Narrative Assistant", "status": "ok"}


@api_router.get("/procedures")
async def list_procedures():
    return {"procedures": PROCEDURES}


@api_router.post("/generate", response_model=NarrativeRecord)
async def generate(req: GenerateRequest):
    procedure = get_procedure(req.procedure_code)
    if not procedure:
        raise HTTPException(status_code=400, detail=f"Unknown procedure code: {req.procedure_code}")

    payload = req.model_dump()
    try:
        result = await generate_narrative(payload, procedure)
    except Exception as e:
        logger.exception("Narrative generation failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    record = NarrativeRecord(
        id=str(uuid.uuid4()),
        procedure_code=procedure["code"],
        procedure_name=procedure["name"],
        category=procedure["category"],
        tooth_number=req.tooth_number,
        patient_label=req.patient_label,
        short_narrative=result["short_narrative"],
        long_narrative=result["long_narrative"],
        radiographs=RadiographAdvice(**procedure["radiographs"]),
        inputs={k: v for k, v in payload.items()
                if k not in ("save_to_history",) and v},
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    if req.save_to_history:
        await db.narratives.insert_one(record.model_dump())

    return record


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


@api_router.delete("/history/{record_id}")
async def delete_history_item(record_id: str):
    result = await db.narratives.delete_one({"id": record_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": record_id}


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

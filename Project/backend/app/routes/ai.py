import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.services.ai_service import run_diagnostics_pipeline_background, generate_rca_document

router = APIRouter(prefix="/api/ai", tags=["AI Microservice"])

class DiagnosticRequest(BaseModel):
    incident_id: uuid.UUID

class RCARequest(BaseModel):
    incident_id: uuid.UUID
    user_id: uuid.UUID

class ParseLogsRequest(BaseModel):
    incident_id: uuid.UUID
    raw_text: str

@router.post("/parse_logs")
def parse_logs(req: ParseLogsRequest):
    # Try to extract useful info from raw text
    summary = req.raw_text[:200] + "..." if len(req.raw_text) > 200 else req.raw_text
    return {"summary": "AI Parsed: " + summary}

@router.post("/diagnostics")
def trigger_diagnostics(req: DiagnosticRequest, background_tasks: BackgroundTasks):
    # Triggers the initial triaging (Severity/Category/Similarity)
    background_tasks.add_task(run_diagnostics_pipeline_background, req.incident_id)
    return {"status": "Diagnostics queued"}

@router.post("/generate_rca")
def trigger_rca(req: RCARequest, db: Session = Depends(get_db)):
    # Triggers the full RCA Generation with strict AI validation
    try:
        rca_text = generate_rca_document(db, req.incident_id)
        return {"status": "success", "rca_document": rca_text}
    except Exception as e:
        print("RCA Generation Error:", e)
        raise HTTPException(status_code=500, detail="Failed to generate RCA")

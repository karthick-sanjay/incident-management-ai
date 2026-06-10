import os
import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.incident import Incident, Log, Comment, Prediction, Recommendation, AuditLog
from backend.app.schemas.incident import (
    IncidentCreate, IncidentOut, IncidentListOut, IncidentUpdateStatus,
    CommentCreate, CommentOut, LogOut
)
from backend.app.services.auth_service import get_current_user, RoleChecker
from backend.app.services.log_service import parse_log_content
from backend.app.services.ai_service import run_diagnostics_pipeline_background

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])

@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Initialize basic ticket with temporary categories (resolved by AI in background)
    incident = Incident(
        title=incident_in.title,
        description=incident_in.description,
        status="open",
        severity="medium",  # default
        category="application",  # default
        git_diff=incident_in.git_diff,
        created_by=current_user.id
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    
    # Run AI diagnostics in background
    background_tasks.add_task(run_diagnostics_pipeline_background, incident.id)
    
    # Log Audit entry
    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_INCIDENT",
        details=f"Incident '{incident.title}' created (ID: {incident.id})."
    )
    db.add(audit)
    db.commit()
    
    return incident

@router.get("", response_model=IncidentListOut)
def list_incidents(
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Incident)
    
    # Role isolation rules:
    # Support Engineers only see their assigned tickets. Admins & DevOps see all.
    if current_user.role == "support_engineer":
        query = query.filter(Incident.assigned_to == current_user.id)
        
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    if category:
        query = query.filter(Incident.category == category)
    if search:
        query = query.filter(
            (Incident.title.ilike(f"%{search}%")) | 
            (Incident.description.ilike(f"%{search}%"))
        )
        
    total = query.count()
    offset = (page - 1) * limit
    incidents = query.order_by(Incident.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": incidents
    }

@router.get("/{id}", response_model=IncidentOut)
def get_incident(id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident ticket not found"
        )
        
    # Role check
    if current_user.role == "support_engineer" and incident.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this incident ticket queue"
        )
        
    return incident

@router.put("/{id}/status", response_model=IncidentOut)
def update_incident_status(
    id: uuid.UUID,
    status_in: IncidentUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    # Access checks
    if current_user.role == "support_engineer" and incident.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Reassignment permissions
    if status_in.assigned_to is not None:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only Admins can reassign tickets.")
        # Verify assignee account exists
        assignee = db.query(User).filter(User.id == status_in.assigned_to).first()
        if not assignee:
            raise HTTPException(status_code=400, detail="Target engineer account does not exist")
        incident.assigned_to = status_in.assigned_to
        
    if status_in.status:
        incident.status = status_in.status
        if status_in.status in ["resolved", "closed"]:
            incident.resolved_at = datetime.datetime.now(datetime.timezone.utc)
            
    incident.updated_at = datetime.datetime.now(datetime.timezone.utc)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="UPDATE_STATUS",
        details=f"Incident {incident.id} updated (Status: {incident.status}, Assigned: {incident.assigned_to})."
    )
    db.add(audit)
    db.commit()
    db.refresh(incident)
    
    return incident

@router.post("/{id}/logs", response_model=List[LogOut], status_code=status.HTTP_201_CREATED)
def upload_logs(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident ticket not found")
        
    # Validation file upload constraints (size limit 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    uploaded_logs = []
    
    # Ensure incident logs directory exists
    incident_log_dir = os.path.join(settings.UPLOAD_DIR, str(incident.id))
    os.makedirs(incident_log_dir, exist_ok=True)
    
    for file in files:
        # Verify size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Log file '{file.filename}' exceeds maximum allowed upload size limit (10MB)"
            )
            
        content_bytes = file.file.read()
        try:
            content_str = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1
            content_str = content_bytes.decode("latin-1")
            
        # Parse log content structure
        parsed_summary = parse_log_content(file.filename, content_str)
        
        # Save physical file on host filesystem
        filename_clean = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(incident_log_dir, filename_clean)
        with open(file_path, "wb") as out_file:
            out_file.write(content_bytes)
            
        # Insert log record in database
        db_log = Log(
            incident_id=incident.id,
            filename=file.filename,
            file_path=file_path,
            parsed_content=parsed_summary
        )
        db.add(db_log)
        uploaded_logs.append(db_log)
        
    db.commit()
    
    # Trigger AI re-diagnostics in background incorporating newly uploaded logs
    background_tasks.add_task(run_diagnostics_pipeline_background, incident.id)
    
    return uploaded_logs

@router.post("/{id}/comments", response_model=CommentOut)
def add_comment(
    id: uuid.UUID,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    comment = Comment(
        incident_id=incident.id,
        user_id=current_user.id,
        content=comment_in.content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return comment

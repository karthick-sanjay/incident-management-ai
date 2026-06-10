from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any

class UserMinimal(BaseModel):
    id: UUID
    name: str
    role: str

    model_config = {
        "from_attributes": True
    }

class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    git_diff: Optional[str] = None
    incident_timeline: Optional[str] = None

class IncidentUpdateStatus(BaseModel):
    status: Optional[str] = Field(None, pattern="^(open|in_progress|resolved|closed|archived)$")
    assigned_to: Optional[UUID] = None

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)

class CommentOut(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    user: UserMinimal

    model_config = {
        "from_attributes": True
    }

class LogOut(BaseModel):
    id: UUID
    filename: str
    parsed_content: Dict[str, Any]
    uploaded_at: datetime

    model_config = {
        "from_attributes": True
    }

class PredictionOut(BaseModel):
    severity_pred: str
    severity_conf: float
    category_pred: str
    category_conf: float
    root_cause_pred: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class RecommendationOut(BaseModel):
    recommendation_text: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class IncidentOut(BaseModel):
    id: UUID
    title: str
    description: str
    status: str
    severity: str
    category: str
    root_cause: Optional[str] = None
    git_diff: Optional[str] = None
    incident_timeline: Optional[str] = None
    assigned_to: Optional[UUID] = None
    assignee: Optional[UserMinimal] = None
    created_by: UUID
    creator: UserMinimal
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    logs: List[LogOut] = []
    predictions: List[PredictionOut] = []
    recommendations: List[RecommendationOut] = []
    comments: List[CommentOut] = []

    model_config = {
        "from_attributes": True
    }

class IncidentListOut(BaseModel):
    total: int
    page: int
    limit: int
    data: List[IncidentOut]

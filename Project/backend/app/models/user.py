import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # admin, support_engineer, devops_engineer
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    incidents_assigned = relationship("Incident", foreign_keys="[Incident.assigned_to]", back_populates="assignee")
    incidents_created = relationship("Incident", foreign_keys="[Incident.created_by]", back_populates="creator")
    comments = relationship("Comment", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

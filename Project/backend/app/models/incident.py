import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="open", index=True)  # open, in_progress, resolved, closed, archived
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    category = Column(String(30), nullable=False, index=True)  # database, network, application, security, infrastructure
    root_cause = Column(Text, nullable=True)
    git_diff = Column(Text, nullable=True)
    incident_timeline = Column(Text, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="incidents_assigned")
    creator = relationship("User", foreign_keys=[created_by], back_populates="incidents_created")
    logs = relationship("Log", back_populates="incident", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="incident", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="incident", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="incident", cascade="all, delete-orphan")
    historical_matches = relationship(
        "HistoricalReference", 
        foreign_keys="[HistoricalReference.incident_id]", 
        back_populates="incident",
        cascade="all, delete-orphan"
    )
    rca = relationship("RCA", back_populates="incident", uselist=False, cascade="all, delete-orphan")

class Log(Base):
    __tablename__ = "logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    parsed_content = Column(JSONB, nullable=False)  # Telemetry data like warning/error count
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    incident = relationship("Incident", back_populates="logs")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    severity_pred = Column(String(20), nullable=False)
    severity_conf = Column(Float, nullable=False)
    category_pred = Column(String(30), nullable=False)
    category_conf = Column(Float, nullable=False)
    root_cause_pred = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    incident = relationship("Incident", back_populates="predictions")

class HistoricalReference(Base):
    __tablename__ = "historical_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    historical_incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)

    # Relationships
    incident = relationship("Incident", foreign_keys=[incident_id], back_populates="historical_matches")
    historical_incident = relationship("Incident", foreign_keys=[historical_incident_id])

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    recommendation_text = Column(Text, nullable=False)
    feedback_rating = Column(Integer, nullable=True)  # rating from 1 to 5
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    incident = relationship("Incident", back_populates="recommendations")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    incident = relationship("Incident", back_populates="comments")
    user = relationship("User", back_populates="comments")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)  # LOGIN, CREATE_INCIDENT, etc.
    details = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="audit_logs")

class RCA(Base):
    __tablename__ = "rcas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, nullable=False)
    document_content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    incident = relationship("Incident", back_populates="rca")
    creator = relationship("User")

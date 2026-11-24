import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

class PatientMemory(Base):
    __tablename__ = "patient_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # menstrual, physical_symptom, lifestyle, medical_history, lab_finding
    key = Column(String(100), nullable=False, index=True)      # e.g. cycle_length, cycle_irregularity, period_pain, acne, sleep_duration
    value = Column(Text, nullable=False)                       # e.g. "40-55 days", "severe menstrual pain", "6 hours"
    source_type = Column(String(50), nullable=False)           # patient_reported, clinician_confirmed, lab_derived, ai_inferred
    source_reference = Column(String(100), nullable=True)      # e.g. message_id, consultation_id, report_id
    confidence_status = Column(String(20), default="high")     # high, medium, low
    verified_status = Column(Boolean, default=False)           # True if confirmed by patient or clinician
    consent_status = Column(Boolean, default=True)            # True if approved by user, False if disabled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="patient_memories")
    sources = relationship("MemorySource", back_populates="memory", cascade="all, delete-orphan")

class MemorySource(Base):
    __tablename__ = "memory_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    memory_id = Column(String(36), ForeignKey("patient_memories.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    reference_id = Column(String(100), nullable=True)
    snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    memory = relationship("PatientMemory", back_populates="sources")

class MedicalKnowledgeDocument(Base):
    __tablename__ = "medical_knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    title = Column(String(200), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # pcos_guidelines, who_menstrual, nih_reproductive, red_flags
    content = Column(Text, nullable=False)
    source_name = Column(String(100), nullable=False)          # e.g. "WHO", "Rotterdam PCOS Consensus", "DGHS Bangladesh"
    source_url = Column(String(255), nullable=True)
    citation_label = Column(String(200), nullable=False)
    version = Column(String(20), default="1.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

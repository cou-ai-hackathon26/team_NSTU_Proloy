import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base

class User(Base):
    """
    Pseudonymous user model.
    NO PII: No name, phone number, email or physical address.
    Only a random client-generated or server-generated UUID.
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    pin_hash = Column(String(128), nullable=True)
    role = Column(String(20), default="patient", index=True)  # patient, doctor, researcher, admin
    age_group = Column(String(20), nullable=True)
    language = Column(String(10), default="bn")

    # Cascading relationships so "Delete all my data" completely wipes everything
    period_logs = relationship("PeriodLog", back_populates="user", cascade="all, delete-orphan")
    mood_logs = relationship("MoodLog", back_populates="user", cascade="all, delete-orphan")
    habit_logs = relationship("HabitLog", back_populates="user", cascade="all, delete-orphan")
    pcos_checks = relationship("PCOSCheck", back_populates="user", cascade="all, delete-orphan")
    pregnancy_logs = relationship("PregnancyLog", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    patient_profile = relationship("PatientProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    consent_records = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")
    symptom_logs = relationship("SymptomLog", back_populates="user", cascade="all, delete-orphan")
    lifestyle_logs = relationship("LifestyleLog", back_populates="user", cascade="all, delete-orphan")
    medical_reports = relationship("MedicalReport", back_populates="user", cascade="all, delete-orphan")
    consultations = relationship("Consultation", back_populates="patient", cascade="all, delete-orphan")
    health_assessments = relationship("HealthAssessment", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("ConversationSession", back_populates="user", cascade="all, delete-orphan")
    patient_memories = relationship("PatientMemory", back_populates="user", cascade="all, delete-orphan")
    private_voice_sessions = relationship("PrivateVoiceSession", back_populates="user", cascade="all, delete-orphan")
    voice_interaction_records = relationship("VoiceInteractionRecord", back_populates="user", cascade="all, delete-orphan")
    crisis_assessment_records = relationship("CrisisAssessmentRecord", back_populates="user", cascade="all, delete-orphan")
    privacy_preferences = relationship("UserPrivacyPreference", uselist=False, back_populates="user", cascade="all, delete-orphan")

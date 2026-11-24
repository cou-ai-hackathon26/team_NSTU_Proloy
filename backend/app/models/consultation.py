import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Integer, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    full_name = Column(String(100), nullable=False)
    bmdc_reg_number = Column(String(50), unique=True, nullable=False, index=True)
    specialization = Column(String(100), default="Obstetrics & Gynecology")
    qualifications = Column(String(200), nullable=False)  # MBBS, FCPS (Obs & Gynae), DGO, etc.
    experience_years = Column(Integer, default=5)
    hospital_affiliation = Column(String(200), nullable=True)
    consultation_fee = Column(Float, default=0.0)
    bio = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=True)
    profile_image_url = Column(String(255), nullable=True)

    availabilities = relationship("DoctorAvailability", back_populates="doctor", cascade="all, delete-orphan")
    consultations = relationship("Consultation", back_populates="doctor")

class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(String(10), nullable=False)  # "18:00"
    end_time = Column(String(10), nullable=False)    # "21:00"
    slot_duration_minutes = Column(Integer, default=20)
    is_active = Column(Boolean, default=True)

    doctor = relationship("Doctor", back_populates="availabilities")

class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    patient_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    scheduled_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), default="pending")  # pending, confirmed, completed, cancelled
    meeting_link = Column(String(255), nullable=True)
    chief_complaint = Column(Text, nullable=False)
    patient_shared_history_json = Column(Text, default="{}")  # Explicit patient-consented snapshot
    doctor_notes = Column(Text, nullable=True)
    followup_instructions = Column(Text, nullable=True)

    patient = relationship("User", back_populates="consultations")
    doctor = relationship("Doctor", back_populates="consultations")

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Integer, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

class SymptomLog(Base):
    __tablename__ = "symptom_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    category = Column(String(50), nullable=False)  # acne, hirsutism, pelvic_pain, hair_thinning, mood_swing, fatigue, bloating
    severity = Column(Integer, nullable=False)     # 1 to 5
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="symptom_logs")

class LifestyleLog(Base):
    __tablename__ = "lifestyle_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    sleep_hours = Column(Float, nullable=True)
    sleep_quality = Column(Integer, nullable=True)     # 1 to 5
    stress_level = Column(Integer, nullable=True)      # 1 to 5
    exercise_minutes = Column(Integer, default=0)
    diet_pattern = Column(String(30), nullable=True)   # balanced, fast_food, irregular
    water_liters = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="lifestyle_logs")

class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    report_type = Column(String(50), nullable=False)   # hormonal_panel, ultrasound, blood_glucose, lipid_profile, thyroid, general
    file_name = Column(String(255), nullable=True)
    extracted_values_json = Column(Text, default="{}") # JSON of lab values e.g. LH, FSH, TSH, Fasting Glucose
    ai_interpretation = Column(Text, nullable=True)    # Evidence-based educational interpretation
    clinical_limitations = Column(Text, nullable=True) # Explicit disclaimer on diagnostic limitations
    is_reviewed_by_doctor = Column(Boolean, default=False)

    user = relationship("User", back_populates="medical_reports")

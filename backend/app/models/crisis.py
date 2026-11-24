import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, JSON, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class CrisisAssessmentRecord(Base):
    """
    Dedicated mental health crisis assessment record:
    - Stores 4-tier risk classification: LEVEL_0, LEVEL_1, LEVEL_2, LEVEL_3
    - Explainable signal categories & calibrated confidence
    - Zero sensitive PII logged
    """
    __tablename__ = "crisis_assessment_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String(36), nullable=True, index=True)
    risk_level = Column(String(20), nullable=False, index=True)  # LEVEL_0, LEVEL_1, LEVEL_2, LEVEL_3
    confidence = Column(Float, default=1.0)
    detected_signal_categories = Column(JSON, default=list)  # ["passive_resignation", "burdensomeness", etc.]
    assessment_status = Column(String(30), default="monitored")  # monitored, de_escalated, safety_engaged
    clarification_prompt_bn = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="crisis_assessment_records")

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.db.session import Base

class PCOSCheck(Base):
    __tablename__ = "pcos_checks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    inputs_json = Column(Text, nullable=False)  # inputs provided by user
    risk_score = Column(Float, nullable=False)   # 0.0 to 1.0 probability
    risk_band = Column(String(20), nullable=False)  # low, medium, high
    explanation_bn = Column(Text, nullable=False)   # Plain Bangla explanation
    contributing_factors = Column(Text, default="[]")  # JSON list of factors

    user = relationship("User", back_populates="pcos_checks")

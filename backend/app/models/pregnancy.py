import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, DateTime, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

class PregnancyLog(Base):
    __tablename__ = "pregnancy_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lmp_date = Column(Date, nullable=False)   # Last Menstrual Period
    edd = Column(Date, nullable=False)        # Estimated Due Date (Naegele's rule)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="pregnancy_logs")

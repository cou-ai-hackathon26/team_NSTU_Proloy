from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base

class UserPrivacyPreference(Base):
    """
    Granular user privacy preferences for shared device environments:
    - Voice response permissions
    - Discreet mode defaults
    - Sensitive screen content concealment
    - Custom session timeout durations
    """
    __tablename__ = "user_privacy_preferences"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    voice_response_enabled = Column(Boolean, default=True)
    discreet_mode_enabled = Column(Boolean, default=True)
    sensitive_content_hidden = Column(Boolean, default=True)
    session_timeout = Column(Integer, default=300)  # seconds
    crisis_support_preferences = Column(JSON, default=lambda: {
        "allow_emergency_helpline": True,
        "preferred_helpline": "109",
        "bystander_safe_audio": True
    })
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="privacy_preferences")

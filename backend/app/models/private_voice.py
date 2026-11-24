import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class PrivateVoiceSession(Base):
    """
    Short-lived, privacy-first voice interaction session on shared devices.
    Ephemeral by default, auto-expires after timeout (e.g. 300s).
    """
    __tablename__ = "private_voice_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token_hash = Column(String(128), nullable=False, index=True)
    session_status = Column(String(20), default="active", index=True)  # active, expired, exited
    privacy_mode = Column(String(20), default="discreet")  # discreet, standard, whisper
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="private_voice_sessions")
    interaction_records = relationship("VoiceInteractionRecord", back_populates="session", cascade="all, delete-orphan")

class VoiceInteractionRecord(Base):
    """
    Interaction metadata record.
    Zero raw audio persistence. Only stores extracted health intent and redaction token.
    """
    __tablename__ = "voice_interaction_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("private_voice_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    transcription_reference = Column(String(128), nullable=True)  # anonymized hash reference, never raw audio
    intent = Column(String(50), nullable=False)  # cycle_update, symptom_report, mood_log, health_query
    processing_status = Column(String(30), default="processed")  # processed, clarification_needed, confirmed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("PrivateVoiceSession", back_populates="interaction_records")
    user = relationship("User", back_populates="voice_interaction_records")

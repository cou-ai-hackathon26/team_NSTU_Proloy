import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Date, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

class PeriodLog(Base):
    __tablename__ = "period_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    flow = Column(String(20), default="medium")  # light, medium, heavy
    symptoms = Column(Text, default="[]")  # JSON encoded list of symptoms
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="period_logs")

class MoodLog(Base):
    __tablename__ = "mood_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False)
    mood_score = Column(Integer, nullable=False)  # 1 to 5: 1=very sad, 5=very happy
    tags = Column(Text, default="[]")  # JSON encoded tags: sleep, stress, pain, family
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="mood_logs")

class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False)
    sleep_hrs = Column(Integer, nullable=True)
    exercise_minutes = Column(Integer, nullable=True)
    diet_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="habit_logs")

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # period_alert, hydration, iron_folic, checkup, mood_check
    schedule_time = Column(String(50), nullable=True)  # e.g., "09:00"
    enabled = Column(Boolean, default=True)
    title_bn = Column(String(100), nullable=False)
    discreet_message_bn = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="reminders")

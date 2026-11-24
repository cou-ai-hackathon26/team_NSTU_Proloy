from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
import datetime as dt

class PeriodLogCreate(BaseModel):
    start_date: dt.date
    end_date: Optional[dt.date] = None
    flow: Optional[str] = Field("medium", description="light, medium, heavy")
    symptoms: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None

class PeriodLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    start_date: dt.date
    end_date: Optional[dt.date] = None
    flow: str
    symptoms: List[str]
    notes: Optional[str] = None
    created_at: dt.datetime

class CycleAnalysisResponse(BaseModel):
    cycles_recorded: int
    average_cycle_length: Optional[float] = None
    std_dev: Optional[float] = None
    predicted_next_period_start: Optional[dt.date] = None
    predicted_next_period_end: Optional[dt.date] = None
    ovulation_window_start: Optional[dt.date] = None
    ovulation_window_end: Optional[dt.date] = None
    is_irregular: bool = False
    warning_flag: Optional[str] = None
    explanation_bn: str

class MoodLogCreate(BaseModel):
    date: Optional[dt.date] = None
    mood_score: int = Field(..., ge=1, le=5, description="1=খুব খারাপ, 2=খারাপ, 3=স্বাভাবিক, 4=ভালো, 5=খুব ভালো")
    tags: Optional[List[str]] = Field(default_factory=list)
    note: Optional[str] = None

class MoodLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    date: dt.date
    mood_score: int
    tags: List[str]
    note: Optional[str] = None
    created_at: dt.datetime

class MoodAnalysisResponse(BaseModel):
    seven_day_avg: Optional[float] = None
    thirty_day_avg: Optional[float] = None
    trend_direction: str  # improving, declining, stable, unknown
    phase_correlation_bn: Optional[str] = None
    gentle_suggestion_bn: str

class ReminderCreate(BaseModel):
    type: str = Field(..., description="period_alert, hydration, iron_folic, checkup, mood_check")
    schedule_time: Optional[str] = Field("09:00", description="Time string HH:MM")
    enabled: bool = True
    title_bn: str
    discreet_message_bn: str

class ReminderUpdate(BaseModel):
    enabled: Optional[bool] = None
    schedule_time: Optional[str] = None

class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    type: str
    schedule_time: Optional[str] = None
    enabled: bool
    title_bn: str
    discreet_message_bn: str
    created_at: dt.datetime

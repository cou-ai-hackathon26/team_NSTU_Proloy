from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class VoiceSessionStartRequest(BaseModel):
    privacy_mode: Optional[str] = Field("discreet", description="discreet, standard, whisper")
    timeout_seconds: Optional[int] = Field(300, description="Session timeout in seconds")

class VoiceSessionResponse(BaseModel):
    session_id: str
    session_token: str
    status: str
    privacy_mode: str
    expires_at: datetime
    message_bn: str

class VoiceTranscribeRequest(BaseModel):
    session_id: Optional[str] = None
    direct_transcript: Optional[str] = None

class VoiceTranscribeResponse(BaseModel):
    transcript: str
    language: str = "bn"
    confidence: float = 0.95
    redaction_reference: str

class VoiceIntentRequest(BaseModel):
    transcript: str
    session_id: Optional[str] = None

class ExtractedHealthInfo(BaseModel):
    event_type: Optional[str] = Field(None, description="cycle_start, cycle_end, symptom, mood, sleep, general_query")
    period_start_date: Optional[date] = None
    period_end_date: Optional[date] = None
    cycle_length_days: Optional[int] = None
    bleeding_intensity: Optional[str] = None  # spotting, light, medium, heavy
    pain_intensity: Optional[int] = None  # 0 to 10
    associated_symptoms: List[str] = []
    mood: Optional[str] = None  # happy, neutral, sad, anxious, distressed
    sleep_pattern: Optional[str] = None  # normal, insomnia, disturbed
    is_ambiguous: bool = False
    clarification_question_bn: Optional[str] = None
    confirmation_required: bool = False

class VoiceIntentResponse(BaseModel):
    intent: str
    extracted_info: ExtractedHealthInfo
    can_auto_commit: bool
    prompt_to_user_bn: Optional[str] = None

class VoiceCycleUpdateRequest(BaseModel):
    session_id: Optional[str] = None
    period_start_date: Optional[date] = None
    period_end_date: Optional[date] = None
    cycle_length_days: Optional[int] = None
    flow_intensity: Optional[str] = None
    pain_score: Optional[int] = None
    symptoms: List[str] = []
    mood: Optional[str] = None
    sleep_status: Optional[str] = None
    is_confirmed: bool = Field(True, description="Explicit user confirmation for saving to medical health history")

class VoiceCycleUpdateResponse(BaseModel):
    success: bool
    message_bn: str
    logged_entities: Dict[str, Any]
    pcos_risk_flag: Optional[str] = None

class VoiceSessionExitRequest(BaseModel):
    session_id: str
    clear_in_memory_state: bool = True

class VoiceSessionExitResponse(BaseModel):
    success: bool
    session_status: str = "exited"
    message_bn: str
    quick_exit_triggered: bool = True

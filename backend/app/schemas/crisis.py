from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CrisisAssessRequest(BaseModel):
    text: str
    conversation_id: Optional[str] = None
    previous_history: Optional[List[Dict[str, str]]] = None

class CrisisAssessResponse(BaseModel):
    risk_level: str = Field(..., description="LEVEL_0, LEVEL_1, LEVEL_2, LEVEL_3")
    level_numeric: int = Field(..., description="0=none, 1=mild, 2=significant, 3=immediate danger")
    confidence: float
    detected_signal_categories: List[str]
    is_hypothetical: bool = False
    is_veiled: bool = False
    covert_alert: bool = False
    action_required: bool
    clarification_prompt_bn: Optional[str] = None
    safety_response_bn: Optional[str] = None
    emergency_helpline: Optional[str] = None
    bystander_safe_audio_bn: Optional[str] = None

class CrisisAssessmentItem(BaseModel):
    id: str
    risk_level: str
    confidence: float
    signal_categories: List[str]
    created_at: datetime

class CrisisHistoryResponse(BaseModel):
    total_assessments: int
    recent_assessments: List[CrisisAssessmentItem]

class CrisisSafetyResponseRequest(BaseModel):
    risk_level: str
    clarification_response: Optional[str] = None
    is_immediate_danger: Optional[bool] = None

class CrisisSafetyResponse(BaseModel):
    response_text_bn: str
    support_number: Optional[str] = None
    support_label_bn: Optional[str] = None
    covert_mode: bool = False

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class PrivacyPreferencesRequest(BaseModel):
    voice_response_enabled: Optional[bool] = Field(None, description="Whether spoken audio replies are enabled")
    discreet_mode_enabled: Optional[bool] = Field(None, description="Discreet neutral labels on screen")
    sensitive_content_hidden: Optional[bool] = Field(None, description="Mask sensitive menstrual terms on shared screen")
    session_timeout: Optional[int] = Field(None, ge=60, le=1800, description="Session timeout in seconds")
    crisis_support_preferences: Optional[Dict[str, Any]] = None

class PrivacyPreferencesResponse(BaseModel):
    user_id: str
    voice_response_enabled: bool
    discreet_mode_enabled: bool
    sensitive_content_hidden: bool
    session_timeout: int
    crisis_support_preferences: Dict[str, Any]
    updated_at: datetime

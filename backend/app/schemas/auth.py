from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AnonymousRegisterRequest(BaseModel):
    pin: Optional[str] = Field(None, min_length=4, max_length=6, description="Optional 4-6 digit numeric PIN")
    age_group: Optional[str] = Field(None, description="Optional age group e.g. 15-19, 20-29, 30+")
    language: Optional[str] = Field("bn", description="Preferred language, defaults to Bangla")

class LoginRequest(BaseModel):
    user_id: str
    pin: str

class SetPinRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, description="4-6 digit numeric PIN")

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    created_at: datetime
    message: str = "সফলভাবে লগইন করা হয়েছে"

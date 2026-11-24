# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChatMessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str

class ChatMessageResponse(BaseModel):
    conversation_id: str
    response: str
    context_used: Dict[str, bool]
    sources: List[str] = Field(default_factory=list)
    safety_flags: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0

class ConversationCreateRequest(BaseModel):
    title: Optional[str] = None

class ConversationSessionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

class ConversationMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: List[str] = Field(default_factory=list)
    created_at: datetime

class PatientMemoryResponse(BaseModel):
    id: str
    category: str
    key: str
    value: str
    source_type: str
    confidence_status: str
    verified_status: bool
    consent_status: bool
    created_at: datetime
    updated_at: datetime

class PatientMemoryUpdateRequest(BaseModel):
    value: Optional[str] = None
    verified_status: Optional[bool] = None
    consent_status: Optional[bool] = None

class MemoryConsentRequest(BaseModel):
    consent_enabled: bool

class PatientHealthHistoryResponse(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    memories: List[PatientMemoryResponse] = Field(default_factory=list)
    symptoms: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_count: int = 0

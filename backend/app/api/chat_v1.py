# -*- coding: utf-8 -*-
"""
Context-Aware Chat and Patient Memory API (v1):
- Persistent conversation creation and retrieval
- Multi-turn context retention
- Long-term patient memory review, correction, and deletion
- Longitudinal health history timeline
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.models.user import User
from app.models.conversation import ConversationSession, ConversationMessage, ConversationSummary
from app.models.patient_memory import PatientMemory
from app.models.patient import PatientProfile
from app.models.health_logs import SymptomLog
from app.api.deps import get_current_user
from app.ai.conversation_manager import conversation_manager
from app.ai.memory_manager import memory_manager
from app.schemas.chat_v1 import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationSessionResponse,
    ConversationMessageResponse,
    PatientMemoryResponse,
    PatientMemoryUpdateRequest,
    MemoryConsentRequest,
    PatientHealthHistoryResponse
)

router = APIRouter(prefix="/api/v1", tags=["Context-Aware Chat & Memory v1"])

# ----------------------------------------------------
# 1. CONTEXT-AWARE CHAT MESSAGE
# ----------------------------------------------------
@router.post("/chat/message", response_model=ChatMessageResponse)
async def send_chat_message(
    req: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Primary Context-Aware AI Gynecologist Chat Endpoint:
    - Retains conversation context across turns and sessions.
    - Uses 3-layer memory (Short-term turns, Patient-approved Long-term memory, Summaries).
    - Injects grounded clinical evidence from DGHS/WHO/Rotterdam.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty."
        )

    result = await conversation_manager.process_message(
        db=db,
        user_id=current_user.id,
        message=req.message.strip(),
        conversation_id=req.conversation_id
    )

    return ChatMessageResponse(
        conversation_id=result.conversation_id,
        response=result.response,
        context_used=result.context_used,
        sources=result.sources,
        safety_flags=result.safety_flags,
        latency_ms=result.latency_ms
    )

# ----------------------------------------------------
# 2. CONVERSATION MANAGEMENT
# ----------------------------------------------------
@router.post("/conversations", response_model=ConversationSessionResponse)
def create_conversation(
    req: Optional[ConversationCreateRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Explicitly initializes a new persistent conversation session."""
    title = (req.title if req and req.title else "New Consultation").strip()
    session = ConversationSession(
        user_id=current_user.id,
        title=title,
        status="active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return ConversationSessionResponse(
        id=session.id,
        title=session.title,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0
    )

@router.get("/conversations", response_model=List[ConversationSessionResponse])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all conversations for the authenticated patient."""
    sessions = (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == current_user.id)
        .order_by(desc(ConversationSession.updated_at))
        .all()
    )
    result = []
    for s in sessions:
        count = db.query(ConversationMessage).filter(ConversationMessage.session_id == s.id).count()
        result.append(ConversationSessionResponse(
            id=s.id,
            title=s.title or "General Consultation",
            status=s.status,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=count
        ))
    return result

@router.get("/conversations/{conversation_id}", response_model=ConversationSessionResponse)
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves conversation session details by ID (Patient-isolated)."""
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.id == conversation_id, ConversationSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    count = db.query(ConversationMessage).filter(ConversationMessage.session_id == session.id).count()
    return ConversationSessionResponse(
        id=session.id,
        title=session.title or "General Consultation",
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=count
    )

@router.get("/conversations/{conversation_id}/messages", response_model=List[ConversationMessageResponse])
def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves historical messages for a conversation session."""
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.id == conversation_id, ConversationSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    msgs = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == conversation_id, ConversationMessage.user_id == current_user.id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    result = []
    for m in msgs:
        citations = json.loads(m.citations_json) if m.citations_json else []
        result.append(ConversationMessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            citations=citations,
            created_at=m.created_at
        ))
    return result

@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a conversation session and cascades all messages & summaries."""
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.id == conversation_id, ConversationSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    
    db.query(ConversationMessage).filter(ConversationMessage.session_id == conversation_id).delete()
    db.query(ConversationSummary).filter(ConversationSummary.session_id == conversation_id).delete()
    db.delete(session)
    db.commit()
    return {"status": "success", "message": "Conversation session and messages deleted."}

# ----------------------------------------------------
# 3. PATIENT MEMORY MANAGEMENT (LAYER 2)
# ----------------------------------------------------
@router.get("/patient/memories", response_model=List[PatientMemoryResponse])
def get_patient_memories(
    include_disabled: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns stored health memories for patient review."""
    mems = memory_manager.get_patient_memories(db, user_id=current_user.id, include_disabled=include_disabled)
    return [
        PatientMemoryResponse(
            id=m.id,
            category=m.category,
            key=m.key,
            value=m.value,
            source_type=m.source_type,
            confidence_status=m.confidence_status,
            verified_status=m.verified_status,
            consent_status=m.consent_status,
            created_at=m.created_at,
            updated_at=m.updated_at
        )
        for m in mems
    ]

@router.patch("/patient/memories/{memory_id}", response_model=PatientMemoryResponse)
def update_patient_memory(
    memory_id: str,
    req: PatientMemoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows patient to correct a memory or revoke consent for its use."""
    mem = memory_manager.update_memory(
        db=db,
        memory_id=memory_id,
        user_id=current_user.id,
        value=req.value,
        verified=req.verified_status,
        consent_status=req.consent_status
    )
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found.")
    return PatientMemoryResponse(
        id=mem.id,
        category=mem.category,
        key=mem.key,
        value=mem.value,
        source_type=mem.source_type,
        confidence_status=mem.confidence_status,
        verified_status=mem.verified_status,
        consent_status=mem.consent_status,
        created_at=mem.created_at,
        updated_at=mem.updated_at
    )

@router.delete("/patient/memories/{memory_id}")
def delete_patient_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a specific patient memory item."""
    success = memory_manager.delete_memory(db, memory_id=memory_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found.")
    return {"status": "success", "message": "Memory item successfully deleted."}

@router.post("/patient/memory-consent")
def set_patient_memory_consent(
    req: MemoryConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enables or disables long-term patient memory recording globally."""
    db.query(PatientMemory).filter(PatientMemory.user_id == current_user.id).update(
        {"consent_status": req.consent_enabled}
    )
    db.commit()
    status_str = "enabled" if req.consent_enabled else "disabled"
    return {"status": "success", "consent_enabled": req.consent_enabled, "message": f"Long-term memory has been {status_str}."}

@router.delete("/patient/account-data")
def delete_all_patient_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently deletes all conversation history, summaries, patient memories, and health records for the patient."""
    db.query(ConversationMessage).filter(ConversationMessage.user_id == current_user.id).delete()
    db.query(ConversationSummary).filter(ConversationSummary.user_id == current_user.id).delete()
    db.query(ConversationSession).filter(ConversationSession.user_id == current_user.id).delete()
    db.query(PatientMemory).filter(PatientMemory.user_id == current_user.id).delete()
    db.query(SymptomLog).filter(SymptomLog.user_id == current_user.id).delete()
    db.commit()
    return {"status": "success", "message": "All patient health data and conversation history have been permanently wiped."}

# ----------------------------------------------------
# 4. PATIENT HEALTH HISTORY TIMELINE
# ----------------------------------------------------
@router.get("/patient/health-history", response_model=PatientHealthHistoryResponse)
def get_patient_health_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Aggregates profile, verified memories, and symptoms into a unified longitudinal view."""
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    p_dict = {
        "age": profile.age,
        "blood_group": profile.blood_group,
        "known_allergies": profile.known_allergies,
        "baseline_summary": profile.baseline_summary
    } if profile else None

    mems = memory_manager.get_patient_memories(db, user_id=current_user.id, include_disabled=False)
    mem_responses = [
        PatientMemoryResponse(
            id=m.id,
            category=m.category,
            key=m.key,
            value=m.value,
            source_type=m.source_type,
            confidence_status=m.confidence_status,
            verified_status=m.verified_status,
            consent_status=m.consent_status,
            created_at=m.created_at,
            updated_at=m.updated_at
        )
        for m in mems
    ]

    symptoms = (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == current_user.id)
        .order_by(desc(SymptomLog.logged_at))
        .limit(10)
        .all()
    )
    symptom_dicts = [{"category": s.category, "severity": s.severity, "notes": s.notes, "logged_at": s.logged_at.isoformat()} for s in symptoms]

    conv_count = db.query(ConversationSession).filter(ConversationSession.user_id == current_user.id).count()

    return PatientHealthHistoryResponse(
        profile=p_dict,
        memories=mem_responses,
        symptoms=symptom_dicts,
        conversation_count=conv_count
    )

# -*- coding: utf-8 -*-
"""
Context Builder and Retrieval Engine:
Assembles a unified, structured context package before prompting the LLM:
- Patient-approved profile information
- Active long-term patient memories
- Recent conversation turns
- Previous conversation summaries
- Recent symptom records
- Medical knowledge from RAG
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.patient import PatientProfile
from app.models.health_logs import SymptomLog
from app.ai.memory_manager import memory_manager
from app.ai.rag_engine import rag_engine

class ContextPackage(BaseModel):
    patient_profile: Dict[str, Any] = Field(default_factory=dict)
    patient_memories: List[Dict[str, Any]] = Field(default_factory=list)
    previous_conversation_summary: Optional[str] = None
    recent_messages: List[Dict[str, str]] = Field(default_factory=list)
    recent_symptoms: List[Dict[str, Any]] = Field(default_factory=list)
    relevant_medical_knowledge: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    current_message: str
    context_used: Dict[str, bool] = Field(default_factory=dict)

class ContextBuilder:
    def build_context(
        self,
        db: Session,
        user_id: str,
        session_id: str,
        current_message: str,
        history_limit: int = 12
    ) -> ContextPackage:
        context_used = {
            "recent_history": False,
            "patient_memory": False,
            "conversation_summary": False,
            "medical_knowledge": False
        }

        # 1. Patient Profile
        patient_profile_dict = {}
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()
        if profile:
            patient_profile_dict = {
                "age": profile.age,
                "blood_group": profile.blood_group,
                "known_allergies": profile.known_allergies,
                "baseline_summary": profile.baseline_summary
            }

        # 2. Long-Term Patient Memories (Patient-approved)
        memories = memory_manager.get_patient_memories(db, user_id=user_id, include_disabled=False)
        memory_list = []
        for m in memories:
            memory_list.append({
                "id": m.id,
                "category": m.category,
                "key": m.key,
                "value": m.value,
                "source_type": m.source_type,
                "verified_status": m.verified_status
            })
        if memory_list:
            context_used["patient_memory"] = True

        # 3. Recent Conversation Messages (Short-Term Memory)
        recent_db_msgs = memory_manager.get_recent_messages(db, session_id=session_id, user_id=user_id, limit=history_limit)
        recent_msg_dicts = []
        for msg in recent_db_msgs:
            recent_msg_dicts.append({"role": msg.role, "content": msg.content})
        if recent_msg_dicts:
            context_used["recent_history"] = True

        # 4. Previous Conversation Summary
        summary_obj = memory_manager.get_latest_summary(db, session_id=session_id, user_id=user_id)
        summary_text = summary_obj.summary_text if summary_obj else None
        if summary_text:
            context_used["conversation_summary"] = True

        # 5. Recent Symptoms Logged
        symptoms = (
            db.query(SymptomLog)
            .filter(SymptomLog.user_id == user_id)
            .order_by(SymptomLog.logged_at.desc())
            .limit(5)
            .all()
        )
        symptom_list = [{"category": s.category, "severity": s.severity, "notes": s.notes} for s in symptoms]

        # 6. RAG Medical Knowledge Retrieval
        effective_query = current_message
        # If query is short (e.g. "could this be pcos?"), append key memory cues for better RAG retrieval
        if memory_list and len(current_message.split()) < 10:
            memory_cues = " ".join([m["value"] for m in memory_list[:3]])
            effective_query = f"{current_message} {memory_cues}"

        rag_chunks, citations = rag_engine.retrieve_medical_knowledge(effective_query, db=db, top_k=2)
        if rag_chunks:
            context_used["medical_knowledge"] = True

        return ContextPackage(
            patient_profile=patient_profile_dict,
            patient_memories=memory_list,
            previous_conversation_summary=summary_text,
            recent_messages=recent_msg_dicts,
            recent_symptoms=symptom_list,
            relevant_medical_knowledge=rag_chunks,
            citations=citations,
            current_message=current_message,
            context_used=context_used
        )

context_builder = ContextBuilder()

# -*- coding: utf-8 -*-
"""
Conversation Manager:
Orchestrates multi-turn context retention, three-layer memory read/write,
medical safety screening, and LLM inference.
"""

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.conversation import ConversationSession, ConversationMessage
from app.services.crisis_detector import detect_crisis
from app.ai.llm_provider import unified_llm
from app.ai.prompt_manager import build_system_prompt, format_context_for_prompt
from app.ai.context_builder import context_builder
from app.ai.memory_manager import memory_manager

class ChatExecutionResult(BaseModel):
    conversation_id: str
    response: str
    context_used: Dict[str, bool]
    sources: List[str] = Field(default_factory=list)
    safety_flags: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0

class ConversationManager:
    async def process_message(
        self,
        db: Session,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> ChatExecutionResult:
        start_time = time.perf_counter()

        # 1. Resolve or Create Conversation Session
        session = None
        if conversation_id:
            session = (
                db.query(ConversationSession)
                .filter(ConversationSession.id == conversation_id, ConversationSession.user_id == user_id)
                .first()
            )
        
        if not session:
            # Create a new persistent session
            session_title = message[:40] + "..." if len(message) > 40 else message
            session = ConversationSession(
                user_id=user_id,
                title=session_title,
                status="active"
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        
        active_session_id = session.id

        # 2. Safety & Crisis Detection
        safety_result = detect_crisis(message)
        if safety_result.risk_level == "high":
            if safety_result.is_veiled_crisis and safety_result.emergency_payload and safety_result.emergency_payload.bystander_safe_audio_bn:
                reply_text = safety_result.emergency_payload.bystander_safe_audio_bn
                safety_flags = ["veiled_crisis_detected", "covert_safety_alert"]
            else:
                reply_text = (
                    "আপু, আপনার কষ্ট আমরা বুঝতে পারছি। আপনি একা নন, আপনার জীবন অত্যন্ত মূল্যবান। "
                    "অনুগ্রহ করে নিজের কোনো ক্ষতি করবেন না। নিচের জরুরি বোতামটিতে চাপ দিয়ে অথবা সরাসরি ৯৯৯ নম্বরে কল করুন। "
                    "আমরা আপনার পাশে আছি।"
                )
                safety_flags = ["crisis_detected", "urgent_intervention_needed"]
            # Save user message & assistant safety reply
            user_msg = memory_manager.save_message(db, active_session_id, user_id, "user", message)
            asst_msg = memory_manager.save_message(db, active_session_id, user_id, "assistant", reply_text)
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return ChatExecutionResult(
                conversation_id=active_session_id,
                response=reply_text,
                context_used={"recent_history": False, "patient_memory": False, "conversation_summary": False, "medical_knowledge": False},
                sources=[],
                safety_flags=safety_flags,
                latency_ms=elapsed
            )

        # 3. Assemble Context Package (Three Memory Layers + Profile + Symptoms + RAG)
        context_pkg = context_builder.build_context(
            db=db,
            user_id=user_id,
            session_id=active_session_id,
            current_message=message
        )

        # 4. Prepare System Prompt and Injected Context
        system_base = build_system_prompt()
        context_str = format_context_for_prompt(context_pkg.model_dump())
        full_system_prompt = f"{system_base}\n\n{context_str}" if context_str else system_base

        # 5. Execute LLM with Fallback & Resilience
        llm_resp = await unified_llm.generate_with_fallback(
            prompt=message,
            system_prompt=full_system_prompt,
            history=context_pkg.recent_messages[-10:] if context_pkg.recent_messages else None
        )
        reply_text = llm_resp.text

        # 6. Save Turn to Database (Layer 1: Short-term memory)
        user_msg = memory_manager.save_message(db, active_session_id, user_id, "user", message)
        asst_msg = memory_manager.save_message(
            db, active_session_id, user_id, "assistant", reply_text,
            citations=context_pkg.citations,
            tokens=llm_resp.tokens_used,
            latency_ms=llm_resp.latency_ms
        )

        # 7. Extract & Persist Patient Facts (Layer 2: Long-term memory)
        memory_manager.extract_and_persist_facts(
            db=db,
            user_id=user_id,
            user_text=message,
            message_id=user_msg.id
        )

        # 8. Check and Update Conversation Summary (Layer 3: Summary memory)
        memory_manager.update_summary_if_needed(
            db=db,
            session_id=active_session_id,
            user_id=user_id,
            force=False
        )

        elapsed = (time.perf_counter() - start_time) * 1000.0
        return ChatExecutionResult(
            conversation_id=active_session_id,
            response=reply_text,
            context_used=context_pkg.context_used,
            sources=context_pkg.citations,
            safety_flags=[],
            latency_ms=elapsed
        )

conversation_manager = ConversationManager()

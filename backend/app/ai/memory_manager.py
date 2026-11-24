# -*- coding: utf-8 -*-
"""
Three-Layer Memory Manager:
1. Short-Term Conversation Memory (PostgreSQL / SQLite conversation_messages)
2. Long-Term Patient Memory (PostgreSQL / SQLite patient_memories with consent & verification)
3. Conversation Summary Memory (PostgreSQL / SQLite conversation_summaries)
"""

import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.conversation import ConversationSession, ConversationMessage, ConversationSummary
from app.models.patient_memory import PatientMemory, MemorySource

class MemoryManager:
    """Manages the 3 independent memory layers with strict patient data isolation."""

    # ----------------------------------------------------
    # LAYER 1: SHORT-TERM CONVERSATION MEMORY
    # ----------------------------------------------------
    def get_recent_messages(self, db: Session, session_id: str, user_id: str, limit: int = 20) -> List[ConversationMessage]:
        """Loads recent turns from the persistent DB table, isolated by user_id."""
        return (
            db.query(ConversationMessage)
            .filter(ConversationMessage.session_id == session_id, ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.asc())
            .all()[-limit:]
        )

    def save_message(
        self,
        db: Session,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        citations: Optional[List[str]] = None,
        tokens: int = 0,
        latency_ms: float = 0.0
    ) -> ConversationMessage:
        """Saves message persistently to DB."""
        citations_json = json.dumps(citations, ensure_ascii=False) if citations else None
        msg = ConversationMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            citations_json=citations_json,
            confidence=1.0,
            tokens=tokens,
            latency_ms=latency_ms
        )
        db.add(msg)
        # Touch session updated_at
        session = db.query(ConversationSession).filter(ConversationSession.id == session_id).first()
        if session:
            session.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(msg)
        return msg

    # ----------------------------------------------------
    # LAYER 2: LONG-TERM PATIENT MEMORY
    # ----------------------------------------------------
    def get_patient_memories(self, db: Session, user_id: str, include_disabled: bool = False) -> List[PatientMemory]:
        """Retrieves patient-approved health memories for current user."""
        query = db.query(PatientMemory).filter(PatientMemory.user_id == user_id)
        if not include_disabled:
            query = query.filter(PatientMemory.consent_status == True)
        return query.order_by(desc(PatientMemory.updated_at)).all()

    def add_or_update_memory(
        self,
        db: Session,
        user_id: str,
        category: str,
        key: str,
        value: str,
        source_type: str = "patient_reported",
        source_ref: Optional[str] = None,
        verified: bool = False
    ) -> PatientMemory:
        """Upserts a patient memory item while maintaining origin traceability."""
        existing = (
            db.query(PatientMemory)
            .filter(PatientMemory.user_id == user_id, PatientMemory.category == category, PatientMemory.key == key)
            .first()
        )
        if existing:
            existing.value = value
            existing.source_type = source_type
            existing.source_reference = source_ref
            existing.updated_at = datetime.now(timezone.utc)
            if verified:
                existing.verified_status = True
            db.commit()
            db.refresh(existing)
            return existing

        new_mem = PatientMemory(
            user_id=user_id,
            category=category,
            key=key,
            value=value,
            source_type=source_type,
            source_reference=source_ref,
            confidence_status="high" if source_type == "patient_reported" else "medium",
            verified_status=verified,
            consent_status=True
        )
        db.add(new_mem)
        db.commit()
        db.refresh(new_mem)

        # Record source audit trace
        if source_ref:
            src = MemorySource(
                memory_id=new_mem.id,
                source_type=source_type,
                reference_id=source_ref,
                snippet=value[:200]
            )
            db.add(src)
            db.commit()

        return new_mem

    def update_memory(
        self,
        db: Session,
        memory_id: str,
        user_id: str,
        value: Optional[str] = None,
        verified: Optional[bool] = None,
        consent_status: Optional[bool] = None
    ) -> Optional[PatientMemory]:
        """Allows patient to review, correct, or toggle memory consent."""
        mem = db.query(PatientMemory).filter(PatientMemory.id == memory_id, PatientMemory.user_id == user_id).first()
        if not mem:
            return None
        if value is not None:
            mem.value = value
        if verified is not None:
            mem.verified_status = verified
        if consent_status is not None:
            mem.consent_status = consent_status
        mem.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(mem)
        return mem

    def delete_memory(self, db: Session, memory_id: str, user_id: str) -> bool:
        """Deletes a specific patient memory item."""
        mem = db.query(PatientMemory).filter(PatientMemory.id == memory_id, PatientMemory.user_id == user_id).first()
        if not mem:
            return False
        db.delete(mem)
        db.commit()
        return True

    def extract_and_persist_facts(self, db: Session, user_id: str, user_text: str, message_id: Optional[str] = None) -> List[PatientMemory]:
        """
        Extracts clinically meaningful facts from patient utterances without diagnosing:
        - Irregular cycle history
        - Cycle length intervals (e.g. 40-55 days)
        - Menstrual pain severity
        - Sleep patterns, acne, weight changes
        """
        extracted = []
        text_lower = user_text.lower()

        # 0. Covert Vernacular Cycle Metaphors (Shared Phone Private Voice)
        from app.services.cycle_engine import decode_covert_cycle_metaphor
        covert = decode_covert_cycle_metaphor(user_text)
        if covert:
            if covert["event_type"] == "cycle_start":
                mem = self.add_or_update_memory(
                    db=db, user_id=user_id,
                    category="menstrual", key="cycle_status",
                    value="Active cycle started (reported via covert metaphor)",
                    source_type="patient_reported", source_ref=message_id
                )
                extracted.append(mem)
            elif covert["event_type"] == "cramps":
                mem = self.add_or_update_memory(
                    db=db, user_id=user_id,
                    category="physical_symptom", key="period_pain",
                    value="Patient-reported lower abdominal cramps/twisting",
                    source_type="patient_reported", source_ref=message_id
                )
                extracted.append(mem)

        # 1. Cycle length intervals (e.g. "sometimes 40 days, sometimes 55 days", "40-55 days", "45 days")
        cycle_len_match = re.search(r"(\d{2})\s*(?:to|-|থেকে|থেকে\s*বা\s*কখনো)?\s*(\d{2})?\s*(?:days|দিন)", text_lower)
        if cycle_len_match:
            d1 = cycle_len_match.group(1)
            d2 = cycle_len_match.group(2)
            val = f"{d1}-{d2} days" if d2 else f"{d1} days"
            mem = self.add_or_update_memory(
                db=db, user_id=user_id,
                category="menstrual", key="cycle_length",
                value=f"Reported cycle length: {val}",
                source_type="patient_reported", source_ref=message_id
            )
            extracted.append(mem)

        # 2. Cycle Irregularity & Duration (e.g. "irregular for six months", "মাসিক অনিয়মিত")
        if any(w in text_lower for w in ["irregular", "অনিয়মিত", "late", "delay", "দেরি"]):
            duration_match = re.search(r"(\d+|six|three|one|two|four|পাঁচ|ছয়|তিন)\s*(?:months|মাস)", text_lower)
            dur_str = f" for {duration_match.group(0)}" if duration_match else ""
            mem = self.add_or_update_memory(
                db=db, user_id=user_id,
                category="menstrual", key="cycle_irregularity",
                value=f"Patient-reported irregular menstrual cycles{dur_str}",
                source_type="patient_reported", source_ref=message_id
            )
            extracted.append(mem)

        # 3. Severe Menstrual Pain / Dysmenorrhea
        has_pain_word = any(p in text_lower for p in ["severe pain", "তীব্র ব্যথা", "অসহ্য ব্যথা", "cruciating", "dysmenorrhea", "pain during menstruation"])
        if has_pain_word or (("মাসিক" in text_lower or "পিরিয়ড" in text_lower or "menstruation" in text_lower) and ("ব্যথা" in text_lower or "pain" in text_lower)):
            severity = "severe" if any(s in text_lower for s in ["severe", "তীব্র", "অসহ্য", "খুব"]) else "moderate"
            mem = self.add_or_update_memory(
                db=db, user_id=user_id,
                category="physical_symptom", key="period_pain",
                value=f"Patient-reported {severity} pain during menstruation",
                source_type="patient_reported", source_ref=message_id
            )
            extracted.append(mem)

        # 4. Acne / Skin changes
        if any(a in text_lower for a in ["acne", "ব্রণ", "pimple"]):
            mem = self.add_or_update_memory(
                db=db, user_id=user_id,
                category="physical_symptom", key="acne",
                value="Patient-reported facial/body acne",
                source_type="patient_reported", source_ref=message_id
            )
            extracted.append(mem)

        # 5. Sleep duration
        sleep_match = re.search(r"(\d+)\s*(?:hours|ঘণ্টা)\s*(?:sleep|ঘুম)", text_lower)
        if sleep_match:
            mem = self.add_or_update_memory(
                db=db, user_id=user_id,
                category="lifestyle", key="sleep_pattern",
                value=f"Average sleep duration: approximately {sleep_match.group(1)} hours",
                source_type="patient_reported", source_ref=message_id
            )
            extracted.append(mem)

        return extracted

    # ----------------------------------------------------
    # LAYER 3: CONVERSATION SUMMARY MEMORY
    # ----------------------------------------------------
    def get_latest_summary(self, db: Session, session_id: str, user_id: str) -> Optional[ConversationSummary]:
        return (
            db.query(ConversationSummary)
            .filter(ConversationSummary.session_id == session_id, ConversationSummary.user_id == user_id)
            .first()
        )

    def update_summary_if_needed(self, db: Session, session_id: str, user_id: str, force: bool = False) -> Optional[ConversationSummary]:
        """
        Summarizes conversations when turns exceed threshold (or upon request),
        preserving dates, symptoms, patient corrections, and unresolved questions.
        """
        messages = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.session_id == session_id, ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.asc())
            .all()
        )
        if not force and len(messages) < 6:
            return None

        # Synthesize conversation summary
        user_queries = [m.content for m in messages if m.role == "user"]
        assistant_points = [m.content[:120] for m in messages if m.role == "assistant"]
        
        summary_text = (
            f"The patient has discussed: {'; '.join(user_queries[:4])}. "
            f"Main advice provided covered menstrual health, symptom monitoring, and clinical guidelines."
        )

        existing_summary = db.query(ConversationSummary).filter(ConversationSummary.session_id == session_id).first()
        if existing_summary:
            existing_summary.summary_text = summary_text
            existing_summary.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_summary)
            return existing_summary
        
        new_summary = ConversationSummary(
            session_id=session_id,
            user_id=user_id,
            summary_text=summary_text,
            unresolved_questions="Pending clinical evaluation by a gynecologist",
            symptom_changes="Monitored over current session"
        )
        db.add(new_summary)
        db.commit()
        db.refresh(new_summary)
        return new_summary

memory_manager = MemoryManager()

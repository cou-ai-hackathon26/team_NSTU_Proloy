import time
import re
from typing import List, Dict, Optional, Any
from app.schemas.chat import ChatMessage

TOPIC_KEYWORDS = {
    "abdominal_pain": ["পেট ব্যথা", "পেটে ব্যথা", "তলপেট ব্যথা", "তলপেটে ব্যথা", "কামড়ায়", "চাবায়", "মোচড়", "পেট খারাপ", "পেট কামড়ানো", "পেট চাবানো"],
    "menstrual_pain": ["মাসিক ব্যথা", "মাসিকের ব্যথা", "পিরিয়ড ব্যথা", "পিরিয়ডের ব্যথা", "ডিসমেনোরিয়া"],
    "menstrual_basics": ["মাসিক", "পিরিয়ড", "প্যাড", "রক্তস্রাব"],
    "pcos": ["পিসিওএস", "pcos", "লোম", "ব্রণ", "ওজন", "ডিম্বাশয়", "অনিয়মিত", "পিসিওডি", "pcod", "ডিম্বাণু", "ওভুলেশন", "সিস্ট"],
    "pregnancy": ["গর্ভ", "গর্ভবতী", "প্রেগন্যান্ট", "বাচ্চা", "ডেলিভারি", "প্রসব", "বমি", "নড়াচড়া", "ইডিডি"],
    "emotional_distress": ["ডিপ্রেশন", "মন খারাপ", "কান্না", "কষ্ট", "হতাশা", "অপমান", "খোঁটা", "শান্তি নেই", "একা একা", "একাকীত্ব"],
    "hygiene_uti": ["সাদা স্রাব", "স্রাব", "চুলকানি", "জ্বালাপোড়া", "প্রস্রাব", "ইউটিআই", "uti"],
    "cooking_nutrition": ["রান্না", "খাবার", "ডিম", "শাক", "খিচুড়ি", "ডাল", "পুষ্টি"],
    "sleep_insomnia": ["ঘুম", "ঘুম আসে না", "অনিদ্রা", "রাত জাগা", "ক্লান্ত"],
    "baby_care": ["বাচ্চা কাঁদে", "শিশুর যত্ন", "শান্ত হচ্ছে না", "দুধ খায় না"],
    "chores_fatigue": ["ঘরের কাজ", "কাজ করেছি", "ঝাড়ু", "কাপড় ধোয়া", "সংসার", "গা ব্যথা", "হাত পা ব্যথা", "কোমর ব্যথা", "ক্লান্তি"],
    "digestive_gas": ["গ্যাস", "পেট ফাঁপা", "টক ঢেকুর", "বুক জ্বলে", "হজম", "গ্যাস্ট্রিক", "বদহজম"],
    "fitness_body": ["মোটা", "ওজন", "রোগা", "ফিট", "মেদ", "ভুড়ি", "ত্বক", "চোখ জ্বালা"],
    "celebration": ["জন্মদিন", "বিয়ে", "ঈদ", "পূজা", "নববর্ষ", "সুসংবাদ", "আনন্দ"],
    "general_chitchat": ["কেমন আছো", "গল্প", "বন্ধু", "সই", "গান", "হাসি", "আড্ডা", "কী করছো", "হুম", "আচ্ছা"]
}

class SessionMemory:
    """
    Expanded, Long-Horizon In-Memory Conversational Intelligence Buffer.
    - Stores up to 15 full multi-turn dialogues (30 messages) per session in RAM.
    - Extended 24-hour retention (86,400s) for continuous day-long companionship.
    - Tracks topics, reported symptoms, emotional states, and user context.
    - Strict Zero-PII: No phone numbers, real names, or disk persistence.
    """
    def __init__(self, max_turns: int = 15, ttl_seconds: int = 86400):
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _detect_topic(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        
        # Explicit period / menstrual tokens
        has_period = any(m in text_lower for m in ["মাসিক", "পিরিয়ড", "ডিসমেনোরিয়া", "ব্লিডিং", "প্যাড", "রক্তস্রাব"])
        
        # Abdominal pain & belly symptoms (flexible token & stem matching)
        has_belly = any(b in text_lower for b in ["পেট", "তলপেট"])
        has_belly_symptom = any(s in text_lower for s in ["ব্যথা", "কামড়া", "চাবা", "মোচড়", "খারাপ", "ফাঁপা", "ভারী", "অস্বস্তি", "জ্বালা"])
        has_abdominal = (has_belly and has_belly_symptom) or any(k in text_lower for k in ["কামড়ায়", "চাবায়", "পেট খারাপ", "পেট কামড়ানো", "পেট চাবানো"])
        
        # Never jump to period when abdominal pain is mentioned without explicit menstrual words
        if has_abdominal and not has_period:
            return "abdominal_pain"
        
        if has_period:
            if any(p in text_lower for p in ["ব্যথা", "তলপেট", "কামড়া", "চাবা", "ডিসমেনোরিয়া"]):
                return "menstrual_pain"
            return "menstrual_basics"

        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return topic
        return None

    def get_history(self, session_id: str) -> List[ChatMessage]:
        if not session_id or session_id not in self._sessions:
            return []
        
        session = self._sessions[session_id]
        if time.time() - session["last_active"] > self.ttl_seconds:
            del self._sessions[session_id]
            return []
        
        session["last_active"] = time.time()
        return session["messages"]

    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Returns deep context profile of the ongoing conversation."""
        if not session_id or session_id not in self._sessions:
            return {
                "turn_count": 0,
                "last_topic": None,
                "all_topics": [],
                "recent_symptoms": [],
                "history": []
            }
        
        session = self._sessions[session_id]
        return {
            "turn_count": len(session["messages"]) // 2,
            "last_topic": session.get("last_topic"),
            "all_topics": session.get("topics", []),
            "recent_symptoms": session.get("symptoms", []),
            "history": session.get("messages", [])
        }

    def add_turn(self, session_id: str, user_text: str, reply_text: str, detected_topic: Optional[str] = None):
        if not session_id:
            return
        
        now = time.time()
        # Clean expired sessions
        expired = [sid for sid, data in self._sessions.items() if now - data["last_active"] > self.ttl_seconds]
        for sid in expired:
            self._sessions.pop(sid, None)

        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "created_at": now,
                "last_active": now,
                "messages": [],
                "topics": [],
                "symptoms": [],
                "last_topic": None
            }
        
        session = self._sessions[session_id]
        session["last_active"] = now
        session["messages"].append(ChatMessage(role="user", content=user_text))
        session["messages"].append(ChatMessage(role="assistant", content=reply_text))

        # Detect and store topic
        topic = detected_topic or self._detect_topic(user_text)
        if topic:
            session["last_topic"] = topic
            if topic not in session["topics"]:
                session["topics"].append(topic)

        # Track symptoms mentioned
        symptom_markers = ["ব্যথা", "বমি", "জ্বর", "রক্ত", "স্রাব", "চুলকানি", "দুর্বলতা", "মাথা ঘোরে", "ঘুম নেই"]
        for s in symptom_markers:
            if s in user_text and s not in session["symptoms"]:
                session["symptoms"].append(s)

        # Keep up to max_turns * 2 messages
        max_msgs = self.max_turns * 2
        if len(session["messages"]) > max_msgs:
            session["messages"] = session["messages"][-max_msgs:]

    def get_pending_cycle(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id or session_id not in self._sessions:
            return None
        return self._sessions[session_id].get("pending_cycle")

    def set_pending_cycle(self, session_id: str, cycle_data: Optional[Dict[str, Any]]):
        if not session_id:
            return
        now = time.time()
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "created_at": now,
                "last_active": now,
                "messages": [],
                "topics": ["menstrual_basics"],
                "symptoms": [],
                "last_topic": "menstrual_basics",
                "pending_cycle": cycle_data
            }
        else:
            self._sessions[session_id]["pending_cycle"] = cycle_data
            self._sessions[session_id]["last_active"] = now

    def clear_pending_cycle(self, session_id: str):
        if session_id in self._sessions:
            self._sessions[session_id]["pending_cycle"] = None

    def clear_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

session_memory = SessionMemory()

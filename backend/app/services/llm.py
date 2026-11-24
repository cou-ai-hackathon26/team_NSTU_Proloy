import os
import re
import httpx
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.rag import rag_service
from app.services.crisis_detector import detect_crisis
from app.services.chitchat import get_chitchat_response, is_medical_query, get_open_ended_companion_response
from app.services.emotional_intelligence import analyze_female_emotion, build_emotional_comfort_response
from app.schemas.chat import ChatMessage, ChatResponse

SYSTEM_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "prompts", "system_bn.md"
)

# Reusable connection-pooled HTTP client for low-latency API calls
_HTTPX_CLIENT: Optional[httpx.AsyncClient] = None

def get_httpx_client() -> httpx.AsyncClient:
    global _HTTPX_CLIENT
    if _HTTPX_CLIENT is None or _HTTPX_CLIENT.is_closed:
        limits = httpx.Limits(max_keepalive_connections=15, max_connections=30)
        _HTTPX_CLIENT = httpx.AsyncClient(limits=limits, timeout=12.0)
    return _HTTPX_CLIENT

def get_system_prompt() -> str:
    if os.path.exists(SYSTEM_PROMPT_PATH):
        try:
            with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return "You are Shoi, a warm, caring Bangla health assistant for women in rural Bangladesh."

class LLMService:
    def __init__(self):
        self.system_prompt = get_system_prompt()

    async def generate_response(
        self,
        message: str,
        history: Optional[List[ChatMessage]] = None
    ) -> ChatResponse:
        """
        Executes the multi-tiered pipeline:
        1. Layered safety check (crisis & self-harm detection)
        2. Conversational Intent & Greetings Check (Everyday natural Bangla talk)
        3. RAG retrieval over grounded Bangla medical KB
        4. External LLM generation (Gemini, OpenAI) or Grounded Fallback / Companion Engine
        """
        # Step 1: Safety & Crisis Check (Suicide & Self-Harm)
        safety_result = detect_crisis(message)
        if safety_result.risk_level == "high":
            if safety_result.is_veiled_crisis and safety_result.emergency_payload and safety_result.emergency_payload.bystander_safe_audio_bn:
                reply_text = safety_result.emergency_payload.bystander_safe_audio_bn
            else:
                reply_text = (
                    "আপু, আপনার কষ্ট আমরা বুঝতে পারছি। আপনি একা নন, আপনার জীবন অত্যন্ত মূল্যবান। "
                    "অনুগ্রহ করে নিজের কোনো ক্ষতি করবেন না। নিচের লাল বোতামটিতে চাপ দিলে আপনার ফোন থেকে সরাসরি ৯৯৯ নম্বরে ফ্রিতে কল চলে যাবে। "
                    "আমরা এবং সাহায্যকারী দল আপনার পাশে আছি।"
                )
            return ChatResponse(
                reply=reply_text,
                confidence=1.0,
                risk_level="high",
                emergency_payload=safety_result.emergency_payload
            )

        # Step 1.5: Female Emotional Intelligence & Cause-Aware Motivational Stories
        emotion_ctx = analyze_female_emotion(message)
        if emotion_ctx:
            comfort_reply = build_emotional_comfort_response(emotion_ctx)
            return ChatResponse(
                reply=comfort_reply,
                citations=[],
                confidence=0.95,
                risk_level="none",
                emergency_payload=None
            )

        # Step 1.8: Covert Vernacular Cycle Metaphor Resolver (Shared Phone Private Voice)
        from app.services.cycle_engine import decode_covert_cycle_metaphor
        covert_event = decode_covert_cycle_metaphor(message)
        if covert_event:
            return ChatResponse(
                reply=covert_event["confirmation_bn"],
                citations=[],
                confidence=0.98,
                risk_level="none",
                emergency_payload=None
            )

        # Step 1.9: Pure Voice Backchannels (Instant sub-100ms listening acknowledgments for bare grunts)
        norm_msg = message.strip().lower()
        if norm_msg in ["হুম", "হু", "আচ্ছা", "হুমম", "ঠিক আছে", "ok", "okay"]:
            chitchat = get_chitchat_response(message)
            if chitchat:
                reply_text, conf = chitchat
                return ChatResponse(
                    reply=reply_text,
                    citations=[],
                    confidence=conf,
                    risk_level="none",
                    emergency_payload=None
                )

        # Multi-turn context resolution for short voice follow-ups
        effective_query = message
        if history and len(message.strip().split()) <= 5:
            last_user_msg = next((h.content for h in reversed(history) if h.role == "user"), None)
            if last_user_msg:
                effective_query = f"{last_user_msg} {message}"

        # Step 2: RAG Retrieval for Medical/Health Context
        chunks, is_confident = rag_service.retrieve(effective_query, top_k=2)
        citations = [f"{c['title']} ({c['source']})" for c in chunks] if is_confident else []
        context_text = "\n\n".join([f"[{c['title']} - {c['source']}]:\n{c['text']}" for c in chunks]) if chunks else ""

        has_llm_key = bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY)
        reply_text = None

        # Step 3: PRIMARY ROUTE - Direct LLM Generation (Gemini 3.1 Flash-Lite, OpenAI, Ollama)
        # LLM answers all conversational, medical, lifestyle, cooking, symptom, and wellness queries dynamically
        if has_llm_key:
            if settings.GEMINI_API_KEY:
                try:
                    reply_text = await self._call_gemini(message, context_text, history)
                except Exception as e:
                    print(f"Gemini API call failed: {e}")

            if not reply_text and settings.OPENAI_API_KEY:
                try:
                    reply_text = await self._call_openai(message, context_text, history)
                except Exception as e:
                    print(f"OpenAI API call failed: {e}")

        # Support local Ollama / OpenAI-compatible / Unified LLM if cloud unavailable
        if not reply_text and (
            getattr(settings, "LLM_PROVIDER", "").lower() in ["ollama", "openai_compatible"]
            or not has_llm_key
        ):
            try:
                from app.ai.llm_provider import unified_llm
                llm_res = await unified_llm.generate_with_fallback(
                    prompt=message,
                    system_prompt=f"{self.system_prompt}\n\n=== Context ===\n{context_text}",
                    history=[{"role": h.role, "content": h.content} for h in (history or [])]
                )
                if llm_res and llm_res.text:
                    reply_text = llm_res.text
            except Exception as e:
                print(f"Unified LLM fallback failed: {e}")

        # Step 4: RESILIENT FALLBACK ROUTE (ONLY when LLM is unavailable, timed out, or offline)
        if not reply_text:
            # Check chitchat intents for everyday conversational fallback
            chitchat = get_chitchat_response(message)
            if chitchat:
                reply_text, conf = chitchat
                return ChatResponse(
                    reply=reply_text,
                    citations=[],
                    confidence=conf,
                    risk_level="none",
                    emergency_payload=None
                )

            if is_confident and chunks:
                # Grounded medical response from verified WHO/DGHS chunks
                reply_text = self._build_grounded_fallback_reply(message, chunks)
                return ChatResponse(
                    reply=reply_text,
                    citations=citations,
                    confidence=0.9,
                    risk_level=safety_result.risk_level,
                    emergency_payload=safety_result.emergency_payload
                )
            elif is_medical_query(message):
                # Unrecognized clinical question: safety disclaimer
                return ChatResponse(
                    reply=(
                        "আপু, আপনার এই বিষয়টি সম্পর্কে আমার কাছে সুনির্দিষ্ট চিকিৎসা তথ্য নেই। "
                        "ভুল তথ্যের কোনো ঝুঁকি না নিয়ে নিকটস্থ কমিউনিটি ক্লিনিক বা স্বাস্থ্যকর্মীর পরামর্শ নেওয়া সবচেয়ে নিরাপদ হবে।"
                    ),
                    citations=[],
                    confidence=0.3,
                    risk_level=safety_result.risk_level
                )
            else:
                # General everyday conversational remarks
                companion_reply = get_open_ended_companion_response(message)
                return ChatResponse(
                    reply=companion_reply,
                    citations=[],
                    confidence=0.85,
                    risk_level="none",
                    emergency_payload=None
                )

        if reply_text:
            reply_text = re.sub(r'\s*\([^\)]*সূত্র:[^\)]*\)', '', reply_text).strip()
            reply_text = re.sub(r'\s*\([^\)]*Source:[^\)]*\)', '', reply_text).strip()

        return ChatResponse(
            reply=reply_text,
            citations=citations,
            confidence=0.9 if is_confident else 0.7,
            risk_level=safety_result.risk_level,
            emergency_payload=safety_result.emergency_payload
        )

    def _is_english(self, text: str) -> bool:
        eng_chars = len(re.findall(r'[a-zA-Z]', text))
        bn_chars = len(re.findall(r'[\u0980-\u09ff]', text))
        return eng_chars > 3 and eng_chars > bn_chars

    async def _call_gemini(self, message: str, context: str, history: Optional[List[ChatMessage]]) -> Optional[str]:
        model = getattr(settings, "GEMINI_MODEL", None) or getattr(settings, "LLM_MODEL", "gemini-flash-lite-latest")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
        
        sys_instruction = (
            f"{self.system_prompt}\n\n"
            f"=== Medical Health Context (WHO/DGHS) ===\n{context or 'No clinical context, friendly guidance.'}\n\n"
            f"Instructions:\n"
            f"1. You are Shoi (সই), a warm, compassionate, sisterly reproductive health AI assistant for women in Bangladesh.\n"
            f"2. Never repeat or echo the user's question; deliver direct, friendly, and practical advice.\n"
            f"3. Never pretend to be a licensed medical doctor or prescribe prescription drugs. Recommend consulting a qualified gynecologist when appropriate.\n"
            f"4. Language: Always respond in natural, sympathetic Bengali (or English if user queries in English).\n"
            f"5. Speed & Brevity: Keep your answer warm and direct in 2-3 short, spoken sentences (maximum 35-45 words) so that mobile voice users hear their answer fast without long listening delays."
        )
        
        contents = []
        if history:
            for h in history[-3:]:
                role = "user" if h.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": h.content}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        
        payload = {
            "system_instruction": {"parts": [{"text": sys_instruction}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 180}
        }
        
        timeout_val = getattr(settings, "LLM_TIMEOUT_SECONDS", 10.0)
        client = get_httpx_client()
        # Attempt with 1 retry for transient spikes (503/429)
        for attempt in range(2):
            try:
                resp = await client.post(url, json=payload, timeout=timeout_val)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    clean_text = re.sub(r'^(?:প্রশ্ন|উত্তর|Regarding|Question|Answer)[:\-–\s]+', '', text, flags=re.IGNORECASE).strip()
                    return clean_text
                elif resp.status_code in [503, 429] and attempt == 0:
                    import asyncio
                    await asyncio.sleep(0.6)
                    continue
                else:
                    print(f"Gemini API returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"Gemini attempt {attempt + 1} exception: {e}")
                if attempt == 0:
                    import asyncio
                    await asyncio.sleep(0.5)
                    continue
        return None

    async def _call_openai(self, message: str, context: str, history: Optional[List[ChatMessage]]) -> Optional[str]:
        url = f"{settings.OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        
        sys_msg = (
            f"{self.system_prompt}\n\n"
            f"=== Context ===\n{context or 'General friendly conversation.'}\n\n"
            f"Respond in the user's language (Bangla or English). Never pretend to be a human doctor."
        )
        messages = [{"role": "system", "content": sys_msg}]
        if history:
            for h in history[-3:]:
                messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 350
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        return None

    def _build_grounded_fallback_reply(self, message: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Creates an empathetic, medically precise bilingual response using matched knowledge base chunks.
        Strictly provides the direct answer without repeating or echoing the user's question.
        """
        top_chunk = chunks[0]
        raw_ans = top_chunk.get("answer") or top_chunk.get("text", "")

        # Clean any stray "প্রশ্ন: ... \n\nউত্তর:" or "Regarding '...':"
        clean_ans = raw_ans
        if "উত্তর:" in clean_ans:
            clean_ans = re.sub(r"^.*?উত্তর:\s*", "", clean_ans, flags=re.DOTALL)
        clean_ans = re.sub(r"^প্রশ্ন:[^\n]+\n*", "", clean_ans).strip()
        clean_ans = re.sub(r"^Regarding\s+['\"][^'\"]+['\"]:\s*", "", clean_ans).strip()
        clean_ans = re.sub(r'\s*\([^\)]*সূত্র:[^\)]*\)', '', clean_ans).strip()
        clean_ans = re.sub(r'\s*\([^\)]*Source:[^\)]*\)', '', clean_ans).strip()

        if self._is_english(message):
            return clean_ans

        greeting = "আপু, "
        if clean_ans.startswith("আপু"):
            body = clean_ans
        else:
            body = f"{greeting}{clean_ans}"
        return body

llm_service = LLMService()

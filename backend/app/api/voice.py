from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, status, Depends
from typing import Optional, Tuple, Dict, Any, List
import uuid
import json
import re
from datetime import date, timedelta, datetime, timezone
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.tracker import PeriodLog
from app.models.patient_memory import PatientMemory
from app.api.deps import get_optional_user
from app.schemas.chat import VoiceResponse
from app.services.asr import transcribe_audio
from app.services.llm import llm_service
from app.services.tts import text_to_speech_base64
from app.services.session_memory import session_memory
from app.services.voice_extraction_engine import parse_bangla_date_reference
from app.services.rag import normalize_bangla_text
from app.services.cycle_engine import decode_covert_cycle_metaphor

router = APIRouter(prefix="/voice", tags=["Voice First Pipeline"])

BN_MONTHS = [
    "", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"
]
BN_DIGITS = {'0':'০','1':'১','2':'২','3':'৩','4':'৪','5':'৫','6':'৬','7':'৭','8':'৮','9':'৯'}

def format_date_bn(d: date) -> str:
    day_str = "".join(BN_DIGITS.get(c, c) for c in str(d.day))
    month_str = BN_MONTHS[d.month] if 1 <= d.month <= 12 else str(d.month)
    return f"{day_str} {month_str}"

def _commit_period_start(
    target_date: date,
    flow: str,
    session_id: str,
    current_user: Optional[User],
    db: Session
) -> Tuple[str, Dict[str, Any]]:
    session_memory.clear_pending_cycle(session_id)
    user = current_user
    if not user:
        user = db.query(User).order_by(User.created_at.desc()).first()

    logged = {}
    if user:
        existing = db.query(PeriodLog).filter(
            PeriodLog.user_id == user.id,
            PeriodLog.start_date == target_date
        ).first()
        if existing:
            existing.flow = flow
            existing.notes = "ভয়েস ইন্টারঅ্যাকশনে হালনাগাদ"
            logged = {"id": existing.id, "start_date": str(target_date), "flow": flow, "updated": True}
        else:
            new_log = PeriodLog(
                user_id=user.id,
                start_date=target_date,
                flow=flow,
                notes="ভয়েস প্রশ্নোত্তরের মাধ্যমে সংরক্ষিত"
            )
            db.add(new_log)
            logged = {"start_date": str(target_date), "flow": flow, "created": True}

        mem = db.query(PatientMemory).filter(
            PatientMemory.user_id == user.id,
            PatientMemory.key == "last_period_date"
        ).first()
        if mem:
            mem.value = str(target_date)
            mem.updated_at = datetime.now(timezone.utc)
        else:
            db.add(PatientMemory(
                user_id=user.id,
                category="menstrual",
                key="last_period_date",
                value=str(target_date),
                source_type="patient_reported",
                confidence_status="high",
                verified_status=True
            ))
        db.commit()

    date_str = format_date_bn(target_date)
    reply = f"আপনার পিরিয়ড শুরুর তারিখ {date_str} সফলভাবে সংরক্ষণ করা হয়েছে আপু। আপনার মাসিক ক্যালেন্ডার ও চক্রের হিসাব আপডেট হয়েছে। নিজের যত্ন নেবেন।"
    return (reply, {
        "status": "saved",
        "action": "cycle_start",
        "start_date": str(target_date),
        "flow": flow,
        "logged_entities": logged
    })

def _commit_period_end(
    end_date: date,
    session_id: str,
    current_user: Optional[User],
    db: Session
) -> Tuple[str, Dict[str, Any]]:
    session_memory.clear_pending_cycle(session_id)
    user = current_user
    if not user:
        user = db.query(User).order_by(User.created_at.desc()).first()

    logged = {}
    if user:
        latest = db.query(PeriodLog).filter(
            PeriodLog.user_id == user.id
        ).order_by(PeriodLog.start_date.desc()).first()

        if latest and not latest.end_date:
            latest.end_date = end_date
            logged = {"id": latest.id, "start_date": str(latest.start_date), "end_date": str(end_date)}
        else:
            new_log = PeriodLog(
                user_id=user.id,
                start_date=end_date - timedelta(days=4),
                end_date=end_date,
                flow="medium",
                notes="ভয়েস প্রশ্নোত্তরে সমাপ্তি রেকর্ডকৃত"
            )
            db.add(new_log)
            logged = {"start_date": str(new_log.start_date), "end_date": str(end_date)}
        db.commit()

    date_str = format_date_bn(end_date)
    reply = f"আপনার পিরিয়ড সমাপ্তির তারিখ {date_str} সফলভাবে সংরক্ষণ করা হয়েছে আপু। আপনার পিরিয়ড সংক্রান্ত কোনো স্বাস্থ্য প্রশ্ন থাকলে নির্দ্বিধায় বলতে পারেন।"
    return (reply, {
        "status": "saved",
        "action": "cycle_end",
        "end_date": str(end_date),
        "logged_entities": logged
    })

def handle_voice_cycle_dialogue(
    transcript: str,
    session_id: str,
    current_user: Optional[User],
    db: Session
) -> Optional[Tuple[str, Dict[str, Any]]]:
    norm = normalize_bangla_text(transcript.lower().strip())
    pending = session_memory.get_pending_cycle(session_id)

    # 1. Handle Active Multi-Turn Flow
    if pending:
        stage = pending.get("stage")

        if stage == "awaiting_date":
            if re.search(r"\b(না|থাক|দরকার\s*নেই|পরে|বাতিল)\b", norm):
                session_memory.clear_pending_cycle(session_id)
                return ("ঠিক আছে আপু, পরবর্তীতে যখনই প্রয়োজন হবে জানাবেন।", {"status": "cancelled"})

            target_date, is_amb, prompt = parse_bangla_date_reference(transcript)
            if not target_date and re.search(r"\b(আজ|আজকে|আজকেই)\b", norm):
                target_date = date.today()
            elif not target_date and re.search(r"\b(গতকাল|কালকে|কাল)\b", norm):
                target_date = date.today() - timedelta(days=1)
            elif not target_date and decode_covert_cycle_metaphor(transcript):
                target_date = date.today()

            if target_date:
                flow = "medium"
                if re.search(r"(বেশি|প্রচুর|ভারী|অতিরিক্ত)", norm): flow = "heavy"
                elif re.search(r"(হালকা|কম|স্পটিং)", norm): flow = "light"

                if re.search(r"(সংরক্ষণ|সেভ|রেকর্ড|লিখে\s*রাখো)\s*(?:করো|করুন|নাও)", norm):
                    return _commit_period_start(target_date, flow, session_id, current_user, db)

                date_str = format_date_bn(target_date)
                pending["start_date"] = str(target_date)
                pending["flow"] = flow
                pending["stage"] = "awaiting_confirmation"
                session_memory.set_pending_cycle(session_id, pending)

                question = f"{date_str} তারিখকে কি আপনার পিরিয়ড শুরুর দিন হিসেবে সংরক্ষণ করব আপু? রক্তপ্রবাহ কেমন হচ্ছে—হালকা, স্বাভাবিক নাকি বেশি?"
                return (question, {
                    "status": "pending_confirmation",
                    "summary": f"পিরিয়ড শুরু: {date_str}",
                    "start_date": str(target_date),
                    "flow": flow
                })
            else:
                return ("আপনার পিরিয়ড কি আজকে শুরু হয়েছে, নাকি গতকাল বা অন্য কোনো তারিখে? দয়া করে দিনটি বলুন।", {
                    "status": "prompt_date",
                    "summary": "পিরিয়ড শুরুর দিন বলুন"
                })

        elif stage == "awaiting_confirmation":
            if re.search(r"\b(না|ভুল|দরকার\s*নেই|করো\s*না|রাখব\s*না|বাতিল)\b", norm) and not re.search(r"\b(না\s*সমস্যা\s*নেই|না\s*ঠিক\s*আছে)\b", norm):
                session_memory.clear_pending_cycle(session_id)
                return ("ঠিক আছে আপু, তথ্যটি সংরক্ষণ করা হলো না। আপনার অন্য কোনো প্রশ্ন থাকলে বলুন।", {"status": "cancelled"})

            is_confirmed = bool(re.search(r"\b(হ্যাঁ|হ্যা|হুম|হাঁ|আচ্ছা|ঠিক\s*আছে|সংরক্ষণ|সেভ|কনফার্ম|করুন|করো|গতকালই|আজকেই|স্বাভাবিক|বেশি|হালকা|হয়েছে)\b", norm))
            if is_confirmed:
                if pending.get("event_type") == "cycle_end":
                    end_d = date.fromisoformat(pending.get("end_date", str(date.today())))
                    return _commit_period_end(end_d, session_id, current_user, db)
                else:
                    start_d = date.fromisoformat(pending.get("start_date", str(date.today())))
                    flow = pending.get("flow", "medium")
                    if re.search(r"(বেশি|প্রচুর|ভারী|অতিরিক্ত)", norm): flow = "heavy"
                    elif re.search(r"(হালকা|কম|স্পটিং)", norm): flow = "light"
                    elif re.search(r"(স্বাভাবিক|মাঝারি)", norm): flow = "medium"
                    return _commit_period_start(start_d, flow, session_id, current_user, db)

    # 2. Check Initiating Tracking Requests
    if re.search(r"(পিরিয়ড|মাসিক|ডেট)\s*(?:ট্র্যাক|হিসাব|লিখতে|রেকর্ড|যুক্ত|তথ্য\s*(?:দিতে|রাখতে|নেওয়া))", norm) or re.search(r"পিরিয়ডের\s*(?:হিসাব|তথ্য|রেকর্ড)", norm):
        session_memory.set_pending_cycle(session_id, {"event_type": "cycle_start", "stage": "awaiting_date"})
        return (
            "অবশ্যই আপু! আপনার পিরিয়ড কি আজকে শুরু হয়েছে, নাকি অন্য কোনো তারিখে শুরু হয়েছিল? আমাকে বলুন।",
            {"status": "prompt_date", "summary": "পিরিয়ড শুরু হওয়ার দিন বলুন"}
        )

    # 3. Informational queries bypass cycle tracking
    is_informative_question = bool(re.search(r"(\?|কী|কি\s|কেন|উপায়|কেমন|উচিত|কখন|পরামর্শ|পদ্ধতি|লক্ষণ|কারণ)", norm)) and not re.search(r"(শুরু|শেষ|হচ্ছে|হয়েছে|হইছে|হয়নি|ডেট)", norm)
    if is_informative_question:
        return None

    # 4. Period Start Mentions
    if re.search(r"(পিরিয়ড\s*শুরু|মাসিক\s*শুরু|পিরিয়ড\s*হচ্ছে|মাসিক\s*হচ্ছে|রক্তস্রাব\s*শুরু|ডেট\s*শুরু|আজকে\s*হলো|আজকে\s*হইছে|কাল\s*থেকে\s*হচ্ছে|লাল\s*ফুল\s*ফুটেছে)", norm):
        target_date, is_amb, prompt = parse_bangla_date_reference(transcript)
        if not target_date and re.search(r"\b(গতকাল|কালকে|কাল)\b", norm):
            target_date = date.today() - timedelta(days=1)
        elif not target_date:
            target_date = date.today()

        flow = "medium"
        if re.search(r"(বেশি|প্রচুর|ভারী|অতিরিক্ত)", norm): flow = "heavy"
        elif re.search(r"(হালকা|কম|স্পটিং)", norm): flow = "light"

        date_str = format_date_bn(target_date)

        if re.search(r"(সংরক্ষণ|সেভ|রেকর্ড|লিখে\s*রাখো)\s*(?:করো|করুন|নাও)", norm):
            return _commit_period_start(target_date, flow, session_id, current_user, db)

        session_memory.set_pending_cycle(session_id, {
            "event_type": "cycle_start",
            "start_date": str(target_date),
            "flow": flow,
            "stage": "awaiting_confirmation"
        })
        question = f"{date_str} তারিখকে কি আপনার পিরিয়ড শুরুর দিন হিসেবে সংরক্ষণ করব আপু? রক্তপ্রবাহ কেমন হচ্ছে—হালকা, স্বাভাবিক নাকি বেশি?"
        return (question, {
            "status": "pending_confirmation",
            "summary": f"পিরিয়ড শুরু: {date_str}",
            "start_date": str(target_date),
            "flow": flow
        })

    # 5. Period End Mentions
    if re.search(r"(পিরিয়ড\s*শেষ|মাসিক\s*শেষ|রক্ত\s*বন্ধ|পবিত্র\s*হয়েছি|গোসল\s*করেছি|শেষ\s*হয়েছে|শেষ\s*হইছে)", norm):
        end_date = date.today()
        date_str = format_date_bn(end_date)
        if re.search(r"(সংরক্ষণ|সেভ|রেকর্ড|লিখে\s*রাখো)\s*(?:করো|করুন|নাও)", norm):
            return _commit_period_end(end_date, session_id, current_user, db)

        session_memory.set_pending_cycle(session_id, {
            "event_type": "cycle_end",
            "end_date": str(end_date),
            "stage": "awaiting_confirmation"
        })
        question = f"আজকে ({date_str}) কি আপনার পিরিয়ড সমাপ্তির তারিখ হিসেবে সংরক্ষণ করব আপু?"
        return (question, {
            "status": "pending_confirmation",
            "summary": f"পিরিয়ড সমাপ্তি: {date_str}",
            "end_date": str(end_date)
        })

    # 6. Amenorrhea / Delayed Period
    if re.search(r"(এখনো\s*পিরিয়ড\s*হয়নি|পিরিয়ড\s*দেরি\s*হচ্ছে|মাসিক\s*দেরি|ডেট\s*পার\s*হয়ে\s*গেছে|ডেট\s*মিস|পিরিয়ড\s*আসেনি)", norm):
        return (
            "পিরিয়ড দেরির সাধারণ কারণ হতে পারে অতিরিক্ত মানসিক চাপ, অনিদ্রা, পুষ্টির ঘাটতি বা হরমোনের তারতম্য। যদি এক সপ্তাহের বেশি দেরি হয়ে যায় বা প্রেগন্যান্সির সম্ভাবনা থাকে, তবে টেস্ট করিয়ে নেওয়া ভালো। আপনি কি তলপেটে কোনো অস্বস্তি বা ব্যথা অনুভব করছেন?",
            {"status": "info", "event_type": "cycle_delayed"}
        )

    return None

def generate_voice_suggestions(topic: Optional[str], text: str) -> list[str]:
    if not topic:
        return [
            "🌸 কেমন আছো সই?",
            "🩸 পিরিয়ডের ব্যথা কমানোর উপায়",
            "🤰 গর্ভকালীন যত্ন কেমন হবে?"
        ]
    if topic == "abdominal_pain":
        return [
            "বাইরের অস্বাস্থ্যকর খাবার খেয়েছেন কি?",
            "গ্যাস বা এসিডিটির সমস্যা আছে কি?",
            "ব্যথাটা পেটের ঠিক কোন অংশে হচ্ছে?"
        ]
    elif topic == "menstrual_basics":
        return [
            "স্বাভাবিক মাসিক চক্র কতদিনের?",
            "মাসিকে কেমন যত্ন নেওয়া উচিত?",
            "প্যাড ব্যবহারের সঠিক নিয়ম"
        ]
    elif topic == "menstrual_pain":
        return [
            "গরম পানির সেঁক কীভাবে নেব?",
            "মাসিকে কী কী খাবার খাওয়া ভালো?",
            "কখন ডাক্তারের কাছে যাওয়া দরকার?"
        ]
    elif topic == "pcos":
        return [
            "পিসিওএস এর প্রাথমিক লক্ষণ কি?",
            "ওজন কমানোর সহজ উপায় কি?",
            "মাসিক নিয়মিত করার উপায় বলো"
        ]
    elif topic == "pregnancy":
        return [
            "গর্ভকালীন ৫টি প্রধান বিপদচিহ্ন কি?",
            "বাচ্চার নড়াচড়া কখন বোঝা যায়?",
            "গর্ভবতী মায়ের পুষ্টিকর খাদ্যতালিকা"
        ]
    elif topic == "emotional_distress":
        return [
            "মন ভালো করার গল্প শোনাও",
            "একটু সান্ত্বনা দাও",
            "আমার মন খুব ভার লাগছে"
        ]
    elif topic == "hygiene_uti":
        return [
            "সাদা স্রাব হলে কী করণীয়?",
            "প্রস্রাবে জ্বালাপোড়া কমানোর ঘরোয়া উপায়",
            "প্যাড ব্যবহারের সঠিক নিয়ম"
        ]
    elif topic == "cooking_nutrition":
        return [
            "সহজ পুষ্টিকর রান্নার উপায় বলো",
            "রক্ত বাড়াতে কী খাওয়া উচিত?",
            "ডিম ও শাকের সহজ রেসিপি"
        ]
    elif topic == "sleep_insomnia":
        return [
            "ঘুমের আগে কী করলে ভালো ঘুম হয়?",
            "অনিদ্রা দূর করার উপায়",
            "মাথা ঠান্ডা রাখার টিপস"
        ]
    elif topic == "baby_care":
        return [
            "বাচ্চা কান্না করলে কীভাবে শান্ত করব?",
            "বাচ্চার পেটে গ্যাস হলে কী করণীয়?",
            "শিশুর প্রাথমিক যত্ন"
        ]
    else:
        return [
            "একটু গল্প করো",
            "একটা মজার কথা বলো",
            "শরীর ভালো রাখার টিপস দাও"
        ]

@router.post("", response_model=VoiceResponse)
async def process_voice_message(
    request: Request,
    audio_file: Optional[UploadFile] = File(None),
    direct_transcript: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Voice-first pipeline for low-literacy rural women:
    1. Supports audio file upload (WAV/OGG/M4A/WebM) OR form transcript OR JSON body
    2. ASR transcribes to Bangla (audio destroyed immediately)
    3. Handles interactive Voice Q&A for menstrual cycle tracking & confirmations
    4. Crisis evaluation & RAG retrieval
    5. Neural Bangla TTS synthesizes natural audio response
    6. Returns transcript, reply text, cycle action metadata, and base64 audio
    """
    transcript = ""
    session_id = request.headers.get("x-session-id") or ""

    # Check if request is JSON body
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            transcript = body.get("direct_transcript") or body.get("message") or body.get("text") or body.get("query") or ""
            transcript = transcript.strip()
            if not session_id and body.get("session_id"):
                session_id = body.get("session_id")
        except Exception:
            pass

    if not session_id:
        session_id = str(uuid.uuid4())

    if not transcript:
        if audio_file:
            audio_bytes = await audio_file.read()
            if len(audio_bytes) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="অডিও ফাইলটি খালি ছিল"
                )
            transcript, _ = transcribe_audio(audio_bytes, audio_file.filename or "recording.wav")
        elif direct_transcript:
            transcript = direct_transcript.strip()

    if not transcript:
        fallback_msg = "দুঃখিত আপু, আপনার কথাটি স্পষ্ট শুনতে পাইনি। দয়া করে আরেকবার বলবেন কি?"
        audio_b64 = await text_to_speech_base64(fallback_msg)
        return VoiceResponse(
            transcript="",
            reply_text=fallback_msg,
            audio_base64=audio_b64,
            citations=[],
            risk_level="none",
            session_id=session_id
        )

    # Interactive Voice Q&A Menstrual Tracking Flow
    cycle_dialogue = handle_voice_cycle_dialogue(transcript, session_id, current_user, db)
    if cycle_dialogue:
        reply_bn, action_payload = cycle_dialogue
        session_memory.add_turn(session_id, transcript, reply_bn, detected_topic="menstrual_basics")
        session_ctx = session_memory.get_session_context(session_id)
        suggestions = generate_voice_suggestions("menstrual_basics", transcript)
        audio_b64 = await text_to_speech_base64(reply_bn)
        return VoiceResponse(
            transcript=transcript,
            reply_text=reply_bn,
            audio_base64=audio_b64,
            citations=[],
            risk_level="none",
            session_id=session_id,
            suggestions=suggestions,
            detected_topic="menstrual_basics",
            turn_count=session_ctx["turn_count"],
            cycle_action=action_payload
        )

    # Multi-turn context memory
    history = session_memory.get_history(session_id)

    # Generate grounded response with multi-turn continuity
    chat_resp = await llm_service.generate_response(message=transcript, history=history)

    # Record turn into ephemeral in-memory session
    session_memory.add_turn(session_id, transcript, chat_resp.reply)
    session_ctx = session_memory.get_session_context(session_id)
    suggestions = generate_voice_suggestions(session_ctx["last_topic"], transcript)

    # Synthesize Bangla speech reply
    audio_b64 = await text_to_speech_base64(chat_resp.reply)

    return VoiceResponse(
        transcript=transcript,
        reply_text=chat_resp.reply,
        audio_base64=audio_b64,
        citations=chat_resp.citations or [],
        risk_level=chat_resp.risk_level,
        emergency_payload=chat_resp.emergency_payload,
        session_id=session_id,
        suggestions=suggestions,
        detected_topic=session_ctx["last_topic"],
        turn_count=session_ctx["turn_count"]
    )

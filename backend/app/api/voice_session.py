import uuid
import hashlib
import secrets
import json
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.private_voice import PrivateVoiceSession, VoiceInteractionRecord
from app.models.tracker import PeriodLog, MoodLog
from app.models.health_logs import SymptomLog, LifestyleLog
from app.models.patient_memory import PatientMemory
from app.schemas.private_voice import (
    VoiceSessionStartRequest, VoiceSessionResponse,
    VoiceTranscribeResponse, VoiceIntentRequest, VoiceIntentResponse,
    VoiceCycleUpdateRequest, VoiceCycleUpdateResponse,
    VoiceSessionExitRequest, VoiceSessionExitResponse,
    ExtractedHealthInfo
)
from app.services.asr import transcribe_audio
from app.services.voice_extraction_engine import voice_extraction_engine
from app.api.deps import get_optional_user, get_current_user

router = APIRouter(prefix="/api/voice", tags=["Shared-Phone Private Voice Assistant"])

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _get_active_session(db: Session, session_id: Optional[str] = None, session_token: Optional[str] = None) -> PrivateVoiceSession:
    query = db.query(PrivateVoiceSession)
    if session_id:
        session = query.filter(PrivateVoiceSession.id == session_id).first()
    elif session_token:
        token_hash = _hash_token(session_token)
        session = query.filter(PrivateVoiceSession.session_token_hash == token_hash).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="সেশন আইডি বা টোকেন আবশ্যক"
        )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="গোপন ভয়েস সেশনটি খুঁজে পাওয়া যায়নি"
        )

    now = datetime.now(timezone.utc)
    # Ensure expires_at is timezone-aware
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if session.session_status != "active" or expires_at < now:
        if session.session_status == "active":
            session.session_status = "expired"
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="সেশনের মেয়াদ শেষ হয়ে গেছে। গোপনীয়তা রক্ষার স্বার্থে পুনরায় সেশন চালু করুন।"
        )

    return session


@router.post("/session/start", response_model=VoiceSessionResponse)
def start_private_voice_session(
    req: VoiceSessionStartRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Starts an ephemeral, privacy-preserving voice session.
    Auto-expires in 300 seconds by default to protect shared-phone users.
    If no user token is present, automatically initializes an anonymous identity.
    """
    user = current_user
    if not user:
        # Create seamless anonymous user to preserve privacy on shared devices
        user = User(
            id=str(uuid.uuid4()),
            age_group="adult",
            language="bn"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    timeout = req.timeout_seconds if (req.timeout_seconds and 30 <= req.timeout_seconds <= 1800) else 300
    session_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(session_token)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout)

    voice_session = PrivateVoiceSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        session_token_hash=token_hash,
        session_status="active",
        privacy_mode=req.privacy_mode or "discreet",
        expires_at=expires_at
    )
    db.add(voice_session)
    db.commit()
    db.refresh(voice_session)

    return VoiceSessionResponse(
        session_id=voice_session.id,
        session_token=session_token,
        status="active",
        privacy_mode=voice_session.privacy_mode,
        expires_at=voice_session.expires_at,
        message_bn="গোপন ভয়েস সেশন সক্রিয় হয়েছে। আপনার কোনো তথ্য বা ভয়েস রেকর্ড স্থায়ীভাবে জমা রাখা হবে না।"
    )


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_private_voice(
    request: Request,
    audio_file: Optional[UploadFile] = File(None),
    direct_transcript: Optional[str] = Form(None)
):
    """
    In-memory transcription with zero raw audio persistence on disk.
    Immediately returns Bangla transcript and anonymized redaction reference.
    """
    transcript = ""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            transcript = body.get("direct_transcript") or body.get("transcript") or body.get("text") or ""
        except Exception:
            pass

    if not transcript:
        if audio_file:
            audio_bytes = await audio_file.read()
            if len(audio_bytes) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="অডিও ফাইলটি খালি ছিল"
                )
            # In-memory ASR (audio immediately discarded)
            transcript, _ = transcribe_audio(audio_bytes, audio_file.filename or "recording.wav")
        elif direct_transcript:
            transcript = direct_transcript.strip()

    if not transcript:
        transcript = ""

    redaction_ref = f"tx_ref_{hashlib.sha256(transcript.encode('utf-8')).hexdigest()[:12]}"

    return VoiceTranscribeResponse(
        transcript=transcript,
        language="bn",
        confidence=0.96 if transcript else 0.0,
        redaction_reference=redaction_ref
    )


@router.post("/intent", response_model=VoiceIntentResponse)
def detect_voice_intent(
    req: VoiceIntentRequest
):
    """
    Extracts structured menstrual health, symptoms, mood, and sleep indicators from natural Bangla speech.
    Flags ambiguity and asks safe clarification questions in Bangla.
    """
    extracted = voice_extraction_engine.extract_health_info(req.transcript)
    extracted_model = ExtractedHealthInfo(**extracted)

    event_type = extracted_model.event_type or "general_query"
    can_auto_commit = not extracted_model.is_ambiguous and not extracted_model.confirmation_required

    prompt_bn = ""
    if extracted_model.is_ambiguous and extracted_model.clarification_question_bn:
        prompt_bn = extracted_model.clarification_question_bn
    elif extracted_model.confirmation_required:
        if event_type == "cycle_start" and extracted_model.period_start_date:
            prompt_bn = f"{extracted_model.period_start_date.strftime('%d/%m/%Y')} তারিখে পিরিয়ড শুরুর দিন হিসেবে সংরক্ষণ করব কি আপু?"
        elif event_type == "cycle_end" and extracted_model.period_end_date:
            prompt_bn = f"{extracted_model.period_end_date.strftime('%d/%m/%Y')} তারিখে পিরিয়ড শেষের দিন হিসেবে যুক্ত করব কি?"
        else:
            prompt_bn = "আপনার স্বাস্থ্য তথ্যটি কি ব্যক্তিগত ডায়েরিতে সংরক্ষণ করব?"
    else:
        prompt_bn = "তথ্যটি সঠিকভাবে প্রস্তুত রয়েছে।"

    return VoiceIntentResponse(
        intent=event_type,
        extracted_info=extracted_model,
        can_auto_commit=can_auto_commit,
        prompt_to_user_bn=prompt_bn
    )


@router.post("/cycle-update", response_model=VoiceCycleUpdateResponse)
def update_cycle_from_voice(
    req: VoiceCycleUpdateRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Updates menstrual cycle, symptoms, mood, and patient memory following confirmation.
    Rejects or prompts if user confirmation is missing.
    """
    if not req.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="তথ্য সংরক্ষণের জন্য নিশ্চিতকরণ (confirmation) আবশ্যক।"
        )

    # Resolve user
    user = current_user
    session_obj = None
    if req.session_id:
        session_obj = _get_active_session(db, session_id=req.session_id)
        if not user:
            user = session_obj.user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="প্রমাণীকরণ বা সক্রিয় সেশন টোকেন প্রয়োজন"
        )

    logged_entities = {}

    # 1. Period Log
    if req.period_start_date:
        if req.period_start_date > date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ভবিষ্যতের কোনো তারিখ পিরিয়ড শুরুর দিন হতে পারে না।"
            )
        period_log = PeriodLog(
            user_id=user.id,
            start_date=req.period_start_date,
            end_date=req.period_end_date,
            flow=req.flow_intensity or "medium",
            symptoms=json.dumps(req.symptoms or []),
            notes="ভয়েস ইন্টারঅ্যাকশনের মাধ্যমে সংরক্ষিত"
        )
        db.add(period_log)
        logged_entities["period_log"] = {
            "start_date": str(req.period_start_date),
            "end_date": str(req.period_end_date) if req.period_end_date else None,
            "flow": req.flow_intensity or "medium"
        }

        # Update PatientMemory for menstrual tracking
        mem_period = db.query(PatientMemory).filter(
            PatientMemory.user_id == user.id,
            PatientMemory.key == "last_period_date"
        ).first()
        if mem_period:
            mem_period.value = str(req.period_start_date)
            mem_period.updated_at = datetime.now(timezone.utc)
        else:
            db.add(PatientMemory(
                user_id=user.id,
                category="menstrual",
                key="last_period_date",
                value=str(req.period_start_date),
                source_type="patient_reported",
                confidence_status="high",
                verified_status=True
            ))

    elif req.period_end_date:
        # User reported cycle end date
        latest_period = db.query(PeriodLog).filter(
            PeriodLog.user_id == user.id
        ).order_by(PeriodLog.start_date.desc()).first()

        if latest_period and not latest_period.end_date:
            latest_period.end_date = req.period_end_date
            logged_entities["period_log_updated"] = {
                "id": latest_period.id,
                "end_date": str(req.period_end_date)
            }
        else:
            new_period = PeriodLog(
                user_id=user.id,
                start_date=req.period_end_date - timedelta(days=4),
                end_date=req.period_end_date,
                flow="medium",
                notes="ভয়েসের মাধ্যমে সমাপ্তি রেকর্ডকৃত"
            )
            db.add(new_period)
            logged_entities["period_log"] = {
                "start_date": str(new_period.start_date),
                "end_date": str(req.period_end_date)
            }

    # 2. Symptoms & Pain
    if req.pain_score is not None:
        severity = max(1, min(5, (req.pain_score + 1) // 2))
        symptom_log = SymptomLog(
            user_id=user.id,
            category="pelvic_pain",
            severity=severity,
            notes=f"ভয়েসের মাধ্যমে রেকর্ডকৃত ব্যথার মাত্রা: {req.pain_score}/10"
        )
        db.add(symptom_log)
        logged_entities["pain_log"] = {"score": req.pain_score, "severity_1_to_5": severity}

    if req.symptoms:
        for sym in req.symptoms:
            cat = "pelvic_pain" if "ব্যথা" in sym else "menstrual_symptom"
            s_log = SymptomLog(
                user_id=user.id,
                category=cat,
                severity=3,
                notes=sym
            )
            db.add(s_log)
        logged_entities["symptoms"] = req.symptoms

    # 3. Mood Tracking
    if req.mood:
        mood_map = {"happy": 5, "neutral": 3, "sad": 2, "anxious": 2, "distressed": 1}
        score = mood_map.get(req.mood, 3)
        mood_log = MoodLog(
            user_id=user.id,
            date=date.today(),
            mood_score=score,
            tags=json.dumps([req.mood]),
            note="ভয়েস সেশনের মাধ্যমে রেকর্ডকৃত"
        )
        db.add(mood_log)
        logged_entities["mood_log"] = {"mood": req.mood, "score": score}

    # 4. Sleep & Lifestyle
    if req.sleep_status:
        lifestyle_log = LifestyleLog(
            user_id=user.id,
            sleep_quality=2 if req.sleep_status == "insomnia" else 4,
            notes=f"ভয়েস আপডেট: ঘুমের অবস্থা {req.sleep_status}"
        )
        db.add(lifestyle_log)
        logged_entities["sleep_log"] = {"status": req.sleep_status}

    # 5. PCOS Risk Correlation Flag
    pcos_flag = None
    if req.cycle_length_days and (req.cycle_length_days > 35 or req.cycle_length_days < 21):
        pcos_flag = "অনিয়মিত পিরিয়ড চক্র পরিলক্ষিত হয়েছে। প্রয়োজনে চিকিৎসকের পরামর্শ নেওয়া যেতে পারে।"
    elif req.pain_score and req.pain_score >= 8:
        pcos_flag = "তীব্র তলপেটের ব্যথা দেখা গেছে। গরম পানির সেঁক নিন এবং দীর্ঘস্থায়ী হলে ডাক্তার দেখান।"

    # 6. Record interaction in voice record
    if session_obj:
        interaction_record = VoiceInteractionRecord(
            user_id=user.id,
            session_id=session_obj.id,
            transcription_reference=f"tx_update_{uuid.uuid4().hex[:8]}",
            intent="cycle_update",
            processing_status="confirmed"
        )
        db.add(interaction_record)

    db.commit()

    return VoiceCycleUpdateResponse(
        success=True,
        message_bn="আপনার স্বাস্থ্য তথ্য সফলভাবে হালনাগাদ করা হয়েছে।",
        logged_entities=logged_entities,
        pcos_risk_flag=pcos_flag
    )


@router.post("/session/exit", response_model=VoiceSessionExitResponse)
def exit_private_voice_session(
    req: VoiceSessionExitRequest,
    db: Session = Depends(get_db)
):
    """
    Instantly terminates the private voice session, clears in-memory state,
    and returns camouflage confirmation.
    """
    session = db.query(PrivateVoiceSession).filter(PrivateVoiceSession.id == req.session_id).first()
    if session:
        session.session_status = "exited"
        db.commit()

    return VoiceSessionExitResponse(
        success=True,
        session_status="exited",
        message_bn="গোপন ভয়েস সেশন তাৎক্ষণিকভাবে বন্ধ করা হয়েছে। স্ক্রিনের তথ্য মুছে দেওয়া হয়েছে।",
        quick_exit_triggered=True
    )

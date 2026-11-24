import json
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.tracker import PeriodLog, MoodLog, Reminder
from app.schemas.tracker import (
    PeriodLogCreate, PeriodLogResponse, CycleAnalysisResponse,
    MoodLogCreate, MoodLogResponse, MoodAnalysisResponse,
    ReminderCreate, ReminderUpdate, ReminderResponse
)
from app.services.cycle_engine import analyze_cycles
from app.services.mood_engine import analyze_moods
from app.api.deps import get_current_user

router = APIRouter(prefix="/track", tags=["Health & Wellness Trackers"])

# --- Period Tracking ---

@router.post("/period", response_model=PeriodLogResponse)
def log_period(
    req: PeriodLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if req.start_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ভবিষ্যতের কোনো তারিখ পিরিয়ড শুরুর দিন হিসেবে দেওয়া যাবে না।"
        )
    if req.end_date and req.end_date < req.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="পিরিয়ডের শেষের তারিখ শুরুর তারিখের আগের হতে পারে না।"
        )

    log = PeriodLog(
        user_id=current_user.id,
        start_date=req.start_date,
        end_date=req.end_date,
        flow=req.flow or "medium",
        symptoms=json.dumps(req.symptoms or []),
        notes=req.notes
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return PeriodLogResponse(
        id=log.id,
        user_id=log.user_id,
        start_date=log.start_date,
        end_date=log.end_date,
        flow=log.flow,
        symptoms=json.loads(log.symptoms or "[]"),
        notes=log.notes,
        created_at=log.created_at
    )

@router.get("/period", response_model=List[PeriodLogResponse])
def get_periods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(PeriodLog).filter(PeriodLog.user_id == current_user.id).order_by(PeriodLog.start_date.desc()).all()
    return [
        PeriodLogResponse(
            id=log.id,
            user_id=log.user_id,
            start_date=log.start_date,
            end_date=log.end_date,
            flow=log.flow,
            symptoms=json.loads(log.symptoms or "[]"),
            notes=log.notes,
            created_at=log.created_at
        ) for log in logs
    ]

@router.get("/period/analysis", response_model=CycleAnalysisResponse)
def get_cycle_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(PeriodLog).filter(PeriodLog.user_id == current_user.id).order_by(PeriodLog.start_date.asc()).all()
    periods = [(log.start_date, log.end_date) for log in logs]
    return analyze_cycles(periods)

# --- Mood Tracking ---

@router.post("/mood", response_model=MoodLogResponse)
def log_mood(
    req: MoodLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    log_date = req.date or date.today()
    if log_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ভবিষ্যতের কোনো তারিখের মেজাজ রেকর্ড করা যাবে না।"
        )

    log = MoodLog(
        user_id=current_user.id,
        date=log_date,
        mood_score=req.mood_score,
        tags=json.dumps(req.tags or []),
        note=req.note
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return MoodLogResponse(
        id=log.id,
        user_id=log.user_id,
        date=log.date,
        mood_score=log.mood_score,
        tags=json.loads(log.tags or "[]"),
        note=log.note,
        created_at=log.created_at
    )

@router.get("/mood", response_model=List[MoodLogResponse])
def get_moods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(MoodLog).filter(MoodLog.user_id == current_user.id).order_by(MoodLog.date.desc()).all()
    return [
        MoodLogResponse(
            id=log.id,
            user_id=log.user_id,
            date=log.date,
            mood_score=log.mood_score,
            tags=json.loads(log.tags or "[]"),
            note=log.note,
            created_at=log.created_at
        ) for log in logs
    ]

@router.get("/mood/analysis", response_model=MoodAnalysisResponse)
def get_mood_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    mood_logs = db.query(MoodLog).filter(MoodLog.user_id == current_user.id).order_by(MoodLog.date.asc()).all()
    mood_tuples = [(log.date, log.mood_score) for log in mood_logs]
    
    # Get period forecast for correlation if available
    period_logs = db.query(PeriodLog).filter(PeriodLog.user_id == current_user.id).order_by(PeriodLog.start_date.asc()).all()
    cycle_analysis = analyze_cycles([(p.start_date, p.end_date) for p in period_logs])

    return analyze_moods(
        mood_tuples,
        last_period_start=period_logs[-1].start_date if period_logs else None,
        predicted_next_period_start=cycle_analysis.predicted_next_period_start
    )

# --- Discreet Reminders & Health Instructions (Prompt 11) ---

DEFAULT_REMINDERS = [
    {
        "type": "period_alert",
        "schedule_time": "09:00",
        "title_bn": "মাসিক চক্র পূর্বাভাস",
        "discreet_message_bn": "সই: আপনার দৈনন্দিন স্বাস্থ্য চেক-ইন সম্পন্ন করুন।"
    },
    {
        "type": "hydration",
        "schedule_time": "11:00",
        "title_bn": "পানি পান ও পুষ্টি",
        "discreet_message_bn": "সই: পর্যাপ্ত বিশুদ্ধ পানি পান করেছেন তো?"
    },
    {
        "type": "iron_folic",
        "schedule_time": "14:00",
        "title_bn": "আয়রন ও ফলিক এসিড বড়ি",
        "discreet_message_bn": "সই: নিয়মিত পুষ্টিকর খাবার ও ভিটামিন গ্রহণ করুন।"
    },
    {
        "type": "checkup",
        "schedule_time": "10:00",
        "title_bn": "স্বাস্থ্যকেন্দ্র চেকআপ রুটিন",
        "discreet_message_bn": "সই: স্বাস্থ্যকর্মীর সাথে আপনার রুটিন সাক্ষাতের সময় হয়েছে।"
    },
    {
        "type": "mood_check",
        "schedule_time": "20:00",
        "title_bn": "সন্ধ্যার মন পর্যবেক্ষণ",
        "discreet_message_bn": "সই: আজকের দিনটি আপনার কেমন কাটল? একটু সময় নিয়ে নিজের খোঁজ নিন।"
    }
]

@router.get("/reminders", response_model=List[ReminderResponse])
def get_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reminders = db.query(Reminder).filter(Reminder.user_id == current_user.id).all()
    if not reminders:
        for r_data in DEFAULT_REMINDERS:
            r = Reminder(
                user_id=current_user.id,
                type=r_data["type"],
                schedule_time=r_data["schedule_time"],
                enabled=True,
                title_bn=r_data["title_bn"],
                discreet_message_bn=r_data["discreet_message_bn"]
            )
            db.add(r)
        db.commit()
        reminders = db.query(Reminder).filter(Reminder.user_id == current_user.id).all()
    return reminders

@router.post("/reminders", response_model=ReminderResponse)
def create_reminder(
    req: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    r = Reminder(
        user_id=current_user.id,
        type=req.type,
        schedule_time=req.schedule_time,
        enabled=req.enabled,
        title_bn=req.title_bn,
        discreet_message_bn=req.discreet_message_bn
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@router.put("/reminders/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: str,
    req: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    r = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="রিমাইন্ডার খুঁজে পাওয়া যায়নি")
    if req.enabled is not None:
        r.enabled = req.enabled
    if req.schedule_time is not None:
        r.schedule_time = req.schedule_time
    db.commit()
    db.refresh(r)
    return r

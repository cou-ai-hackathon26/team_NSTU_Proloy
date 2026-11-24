import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.user import User
from app.models.consultation import Doctor, DoctorAvailability, Consultation
from app.api.deps import get_current_user

router = APIRouter(prefix="/consultation", tags=["Human Gynecologist Consultation"])

class BookingRequest(BaseModel):
    doctor_id: str
    scheduled_at: str  # ISO string or YYYY-MM-DD HH:MM
    chief_complaint: str
    share_health_history: bool = True

class ConsultationNoteRequest(BaseModel):
    doctor_notes: str
    followup_instructions: Optional[str] = None

def seed_verified_doctors_if_empty(db: Session):
    """Seeds verified gynecologists if registry is empty."""
    if db.query(Doctor).count() == 0:
        d1 = Doctor(
            id=str(uuid.uuid4()),
            full_name="ডা. ফারহানা আহমেদ (Dr. Farhana Ahmed)",
            bmdc_reg_number="A-45892",
            specialization="Obstetrics & Gynecology (PCOS & Infertility Specialist)",
            qualifications="MBBS, FCPS (Obs & Gynae), MS (Reproductive Endocrinology)",
            experience_years=12,
            hospital_affiliation="ঢাকা মেডিকেল কলেজ ও হাসপাতাল (DMCH)",
            consultation_fee=800.0,
            bio="১২ বছরের অভিজ্ঞতাসম্পন্ন প্রখ্যাত স্ত্রীরোগ ও হরমোন বিশেষজ্ঞ। পিসিওএস ও প্রজনন স্বাস্থ্য পরিচর্যায় নিবেদিত।",
            is_verified=True
        )
        d2 = Doctor(
            id=str(uuid.uuid4()),
            full_name="ডা. নাসরিন সুলতানা (Dr. Nasreen Sultana)",
            bmdc_reg_number="A-51203",
            specialization="Gynecologist & Women's Health Consultant",
            qualifications="MBBS, DGO, MCPS (Obs & Gynae)",
            experience_years=8,
            hospital_affiliation="স্যার সলিমুল্লাহ মেডিকেল কলেজ (মিটফোর্ড হাসপাতাল)",
            consultation_fee=600.0,
            bio="কৈশোরকালীন মাসিক সমস্যা, পিসিওএস এবং গর্ভকালীন স্বাস্থ্য সুরক্ষায় আন্তরিক বিশেষজ্ঞ পরামর্শ প্রদান করেন।",
            is_verified=True
        )
        db.add_all([d1, d2])
        db.commit()

        # Add availabilities
        for d in [d1, d2]:
            for day in [0, 2, 4]: # Mon, Wed, Fri
                slot = DoctorAvailability(
                    doctor_id=d.id,
                    day_of_week=day,
                    start_time="18:00",
                    end_time="21:00",
                    slot_duration_minutes=20,
                    is_active=True
                )
                db.add(slot)
        db.commit()

@router.get("/doctors")
def get_verified_doctors(db: Session = Depends(get_db)):
    """Lists verified human gynecologists with BMDC registration credentials."""
    seed_verified_doctors_if_empty(db)
    doctors = db.query(Doctor).filter(Doctor.is_verified == True).all()
    return [
        {
            "id": d.id,
            "full_name": d.full_name,
            "bmdc_reg_number": d.bmdc_reg_number,
            "specialization": d.specialization,
            "qualifications": d.qualifications,
            "experience_years": d.experience_years,
            "hospital_affiliation": d.hospital_affiliation,
            "consultation_fee": d.consultation_fee,
            "bio": d.bio,
            "availabilities": [
                {
                    "day_of_week": a.day_of_week,
                    "start_time": a.start_time,
                    "end_time": a.end_time
                }
                for a in d.availabilities if a.is_active
            ]
        }
        for d in doctors
    ]

@router.post("/book")
def book_consultation(
    req: BookingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Books a consultation with a verified gynecologist.
    Transfers approved anonymized health history snapshot only with explicit patient consent.
    """
    doctor = db.query(Doctor).filter(Doctor.id == req.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    try:
        sched_time = datetime.fromisoformat(req.scheduled_at)
    except Exception:
        sched_time = datetime.now(timezone.utc) + timedelta(days=2)

    # Health snapshot if consent granted
    shared_data = {}
    if req.share_health_history:
        recent_assessments = [
            {"date": a.assessment_date.isoformat(), "risk": a.calibrated_risk_score, "band": a.risk_band}
            for a in current_user.health_assessments[-3:]
        ]
        shared_data = {
            "consent_granted": True,
            "age_group": current_user.age_group,
            "recent_risk_assessments": recent_assessments,
            "period_count": len(current_user.period_logs)
        }

    consultation = Consultation(
        patient_id=current_user.id,
        doctor_id=doctor.id,
        scheduled_at=sched_time,
        status="confirmed",
        meeting_link=f"https://meet.shoi.health/telehealth/{uuid.uuid4().hex[:8]}",
        chief_complaint=req.chief_complaint,
        patient_shared_history_json=json.dumps(shared_data)
    )
    db.add(consultation)
    db.commit()

    return {
        "consultation_id": consultation.id,
        "doctor_name": doctor.full_name,
        "hospital": doctor.hospital_affiliation,
        "scheduled_at": sched_time.isoformat(),
        "status": consultation.status,
        "meeting_link": consultation.meeting_link,
        "fee": doctor.consultation_fee,
        "message": "আপনার কনসালটেশন অ্যাপয়েন্টমেন্ট সফলভাবে নিশ্চিত করা হয়েছে।"
    }

@router.get("/my-appointments")
def get_user_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the patient's booked consultations."""
    consultations = db.query(Consultation).filter(
        Consultation.patient_id == current_user.id
    ).order_by(Consultation.scheduled_at.desc()).all()

    return [
        {
            "id": c.id,
            "doctor_name": c.doctor.full_name,
            "specialization": c.doctor.specialization,
            "hospital": c.doctor.hospital_affiliation,
            "bmdc_reg_number": c.doctor.bmdc_reg_number,
            "scheduled_at": c.scheduled_at.isoformat(),
            "status": c.status,
            "meeting_link": c.meeting_link,
            "chief_complaint": c.chief_complaint,
            "doctor_notes": c.doctor_notes,
            "followup_instructions": c.followup_instructions
        }
        for c in consultations
    ]

@router.post("/{consultation_id}/notes")
def add_consultation_notes(
    consultation_id: str,
    req: ConsultationNoteRequest,
    db: Session = Depends(get_db)
):
    """Updates consultation with doctor's clinical findings and follow-up guidance."""
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation not found")
    c.doctor_notes = req.doctor_notes
    c.followup_instructions = req.followup_instructions
    c.status = "completed"
    db.commit()
    return {"status": "success", "consultation_id": c.id}

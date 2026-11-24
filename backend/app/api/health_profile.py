import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientProfile, ConsentRecord
from app.models.health_logs import SymptomLog, LifestyleLog
from app.models.tracker import PeriodLog, MoodLog
from app.models.ml_ops import HealthAssessment
from app.api.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["Longitudinal Patient Health Profile"])

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None
    known_allergies: Optional[str] = None
    baseline_summary: Optional[str] = None

class ConsentUpdateRequest(BaseModel):
    consent_type: str  # data_retention, conversation_history, doctor_sharing, research
    is_granted: bool

@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves patient profile with active consent preferences."""
    profile = current_user.patient_profile
    consents = {c.consent_type: c.is_granted for c in current_user.consent_records}
    
    # default consents if not explicitly recorded
    for default_c in ["data_retention", "conversation_history", "doctor_sharing", "research"]:
        if default_c not in consents:
            consents[default_c] = True

    return {
        "user_id": current_user.id,
        "role": current_user.role,
        "language": current_user.language,
        "age_group": current_user.age_group,
        "profile": {
            "full_name": profile.full_name if profile else None,
            "age": profile.age if profile else None,
            "height_cm": profile.height_cm if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
            "blood_group": profile.blood_group if profile else None,
            "emergency_contact": profile.emergency_contact if profile else None,
            "known_allergies": profile.known_allergies if profile else None,
            "baseline_summary": profile.baseline_summary if profile else None
        } if profile else None,
        "consents": consents
    }

@router.post("/me")
def update_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates or updates patient profile information."""
    profile = current_user.patient_profile
    if not profile:
        profile = PatientProfile(user_id=current_user.id)
        db.add(profile)
    
    if req.full_name is not None: profile.full_name = req.full_name
    if req.age is not None: profile.age = req.age
    if req.height_cm is not None: profile.height_cm = req.height_cm
    if req.weight_kg is not None: profile.weight_kg = req.weight_kg
    if req.blood_group is not None: profile.blood_group = req.blood_group
    if req.emergency_contact is not None: profile.emergency_contact = req.emergency_contact
    if req.known_allergies is not None: profile.known_allergies = req.known_allergies
    if req.baseline_summary is not None: profile.baseline_summary = req.baseline_summary

    db.commit()
    db.refresh(profile)
    return {"status": "success", "message": "প্রোফাইল সফলভাবে আপডেট করা হয়েছে।"}

@router.post("/consent")
def update_consent(
    req: ConsentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates granular patient consent (e.g. disable conversational history retention)."""
    rec = db.query(ConsentRecord).filter(
        ConsentRecord.user_id == current_user.id,
        ConsentRecord.consent_type == req.consent_type
    ).first()

    now = datetime.now(timezone.utc)
    if not rec:
        rec = ConsentRecord(
            user_id=current_user.id,
            consent_type=req.consent_type,
            is_granted=req.is_granted,
            granted_at=now if req.is_granted else None,
            revoked_at=now if not req.is_granted else None
        )
        db.add(rec)
    else:
        rec.is_granted = req.is_granted
        if req.is_granted:
            rec.granted_at = now
            rec.revoked_at = None
        else:
            rec.revoked_at = now
    
    db.commit()
    return {"status": "success", "consent_type": req.consent_type, "is_granted": req.is_granted}

@router.get("/timeline")
def get_patient_timeline(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns an aggregated longitudinal health timeline:
    - Menstrual cycle history
    - Symptom frequency & trends
    - Sleep & lifestyle records
    - Historical PCOS assessment risk trajectory
    """
    periods = db.query(PeriodLog).filter(PeriodLog.user_id == current_user.id).order_by(PeriodLog.start_date.desc()).all()
    symptoms = db.query(SymptomLog).filter(SymptomLog.user_id == current_user.id).order_by(SymptomLog.logged_at.desc()).all()
    lifestyles = db.query(LifestyleLog).filter(LifestyleLog.user_id == current_user.id).order_by(LifestyleLog.logged_at.desc()).all()
    assessments = db.query(HealthAssessment).filter(HealthAssessment.user_id == current_user.id).order_by(HealthAssessment.assessment_date.desc()).all()

    return {
        "menstrual_cycles": [
            {
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "cycle_length": p.cycle_length,
                "period_length": p.period_length,
                "flow_intensity": p.flow_intensity,
                "pain_level": p.pain_level
            }
            for p in periods
        ],
        "symptoms": [
            {
                "id": s.id,
                "logged_at": s.logged_at.isoformat(),
                "category": s.category,
                "severity": s.severity,
                "notes": s.notes
            }
            for s in symptoms
        ],
        "lifestyle": [
            {
                "id": l.id,
                "logged_at": l.logged_at.isoformat(),
                "sleep_hours": l.sleep_hours,
                "stress_level": l.stress_level,
                "exercise_minutes": l.exercise_minutes,
                "diet_pattern": l.diet_pattern
            }
            for l in lifestyles
        ],
        "risk_trajectory": [
            {
                "id": a.id,
                "date": a.assessment_date.isoformat(),
                "risk_score": a.calibrated_risk_score,
                "risk_percentage": round(a.calibrated_risk_score * 100, 1),
                "risk_band": a.risk_band,
                "factors": json.loads(a.contributing_factors_json or "[]")
            }
            for a in assessments
        ]
    }

@router.get("/export")
def export_my_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports all personal medical and lifestyle records as a structured JSON object."""
    profile_data = get_my_profile(current_user, db)
    timeline_data = get_patient_timeline(current_user, db)

    return {
        "export_metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "standard": "HIPAA/GDPR Patient Right of Access Standard"
        },
        "user_profile": profile_data,
        "health_timeline": timeline_data
    }

@router.delete("/delete-all")
def wipe_all_patient_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently deletes the patient account and all associated health records,
    conversations, and logs (Right to be Forgotten).
    """
    user_id = current_user.id
    db.delete(current_user)
    db.commit()
    return {"status": "success", "message": "আপনার সমস্ত ব্যক্তিগত ও স্বাস্থ্য সংক্রান্ত তথ্য সম্পূর্ণ মুছে ফেলা হয়েছে।"}

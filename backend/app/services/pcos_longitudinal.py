import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.health_logs import SymptomLog, LifestyleLog
from app.models.tracker import PeriodLog
from app.models.pcos import PCOSCheck
from app.models.ml_ops import HealthAssessment, ModelVersion
from ml.pcos.models import explain_single_patient

CLINICAL_DISCLAIMER_BN = (
    "সতর্কতা ও চিকিৎসা সংক্রান্ত নির্দেশনা: এই বিশ্লেষণটি একটি শিক্ষামূলক ও স্ক্রিনিং পূর্বাভাস মাত্র, "
    "এটি কোনোভাবেই চিকিৎসকের চূড়ান্ত রোগ নির্ণয় (Diagnosis) বা প্রেসক্রিপশন নয়। মাসিকের অনিয়ম বা ওজন বৃদ্ধি মানেই পিসিওএস নয়; "
    "থাইরয়েড বা অন্যান্য হরমোনজনিত সমস্যাও থাকতে পারে। সঠিক রোগ নির্ণয়ের জন্য আল্ট্রাসনোগ্রাম ও হরমোন টেস্টসহ একজন নিবন্ধিত স্ত্রীরোগ বিশেষজ্ঞের (Gynecologist) পরামর্শ নিন।"
)

CLINICAL_DISCLAIMER_EN = (
    "Medical Disclaimer: This risk evaluation is an educational screening tool and does NOT constitute a medical diagnosis. "
    "Menstrual irregularity, weight gain, or acne can be caused by various endocrine, thyroid, or lifestyle conditions. "
    "A formal PCOS diagnosis requires a clinical evaluation, pelvic ultrasound, and hormonal assessment by a licensed gynecologist."
)

def evaluate_longitudinal_pcos_risk(
    user_id: str,
    db: Session,
    current_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Performs longitudinal evaluation across multiple patient logs and historical assessments:
    1. Aggregates menstrual cycles, symptom logs, lifestyle factors, and lab reports.
    2. Identifies symptom frequency and trajectory (worsening, stable, improving).
    3. Detects missing clinical information.
    4. Evaluates calibrated risk using the ML screening pipeline with SHAP explanation.
    5. Stores longitudinal health assessment with clinical disclaimers.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Gather historical logs
    periods = db.query(PeriodLog).filter(PeriodLog.user_id == user_id).order_by(PeriodLog.start_date.desc()).limit(6).all()
    symptoms = db.query(SymptomLog).filter(SymptomLog.user_id == user_id).order_by(SymptomLog.logged_at.desc()).limit(20).all()
    lifestyles = db.query(LifestyleLog).filter(LifestyleLog.user_id == user_id).order_by(LifestyleLog.logged_at.desc()).limit(10).all()
    past_assessments = db.query(HealthAssessment).filter(HealthAssessment.user_id == user_id).order_by(HealthAssessment.assessment_date.desc()).limit(5).all()

    # 2. Extract features from longitudinal records or current payload
    payload = current_data or {}
    
    # Menstrual regularity calculation
    cycle_lengths = [p.cycle_length for p in periods if p.cycle_length and p.cycle_length > 0]
    avg_cycle_length = float(np.mean(cycle_lengths)) if cycle_lengths else float(payload.get("cycle_length_days", 28))
    
    is_irregular = False
    if len(cycle_lengths) >= 2:
        variance = float(np.std(cycle_lengths))
        is_irregular = variance > 7 or any(c > 35 or c < 21 for c in cycle_lengths)
    else:
        is_irregular = payload.get("cycle_irregular", False) or payload.get("cycle_regularity", "regular").lower() == "irregular"

    # Symptom counts
    recent_categories = {s.category for s in symptoms}
    has_acne = "acne" in recent_categories or bool(payload.get("pimples_acne"))
    has_hirsutism = "hirsutism" in recent_categories or bool(payload.get("excess_hair_growth"))
    has_skin_darkening = "skin_darkening" in recent_categories or bool(payload.get("skin_darkening"))
    has_hair_loss = "hair_thinning" in recent_categories or bool(payload.get("hair_loss"))

    # Lifestyle info
    fast_food = payload.get("fast_food_frequent", False)
    if not fast_food and lifestyles:
        fast_food = any(l.diet_pattern == "fast_food" for l in lifestyles)
    
    regular_exercise = payload.get("regular_exercise", False)
    if not regular_exercise and lifestyles:
        regular_exercise = any(l.exercise_minutes >= 30 for l in lifestyles)

    # Missing information checklist
    missing_info = []
    if len(periods) < 3 and "cycle_length_days" not in payload:
        missing_info.append("টানা ৩ মাসের মাসিকের রেকর্ড (At least 3 consecutive menstrual cycle logs)")
    if "weight_kg" not in payload and "height_cm" not in payload:
        missing_info.append("উচ্চতা ও ওজনের সঠিক মাপ (Height and weight to calculate BMI)")
    if not lifestyles and "sleep_hours" not in payload:
        missing_info.append("ঘুম ও জীবনযাত্রার তথ্য (Sleep duration and lifestyle patterns)")
    if "family_history_pcos" not in payload:
        missing_info.append("পারিবারিক পিসিওএস বা ডায়াবেটিসের ইতিহাস (Family history of PCOS/Diabetes)")

    # 3. Assemble ML feature dict
    import numpy as np
    height_m = float(payload.get("height_cm", 155.0)) / 100.0
    weight_kg = float(payload.get("weight_kg", 55.0))
    bmi = round(weight_kg / (height_m * height_m), 2)

    ml_features = {
        "age": float(payload.get("age", 25)),
        "bmi": bmi,
        "cycle_irregular": 1.0 if is_irregular else 0.0,
        "cycle_length_days": avg_cycle_length,
        "weight_gain": 1.0 if payload.get("weight_gain", False) else 0.0,
        "excess_hair_growth": 1.0 if has_hirsutism else 0.0,
        "skin_darkening": 1.0 if has_skin_darkening else 0.0,
        "hair_loss": 1.0 if has_hair_loss else 0.0,
        "pimples_acne": 1.0 if has_acne else 0.0,
        "fast_food_frequent": 1.0 if fast_food else 0.0,
        "regular_exercise": 1.0 if regular_exercise else 0.0
    }

    # 4. Predict calibrated risk and SHAP attribution
    ml_result = explain_single_patient(ml_features)
    risk_score = ml_result["calibrated_risk_score"]
    risk_band = ml_result["risk_band"]
    factors = ml_result["top_contributing_factors"]

    # 5. Trajectory comparison with past assessment
    trajectory = "baseline"
    if past_assessments:
        last_score = past_assessments[0].calibrated_risk_score
        diff = risk_score - last_score
        if diff > 0.08:
            trajectory = "worsening"
        elif diff < -0.08:
            trajectory = "improving"
        else:
            trajectory = "stable"

    # Actionable next steps
    next_steps_bn = (
        "১. প্রতিদিনের খাবারে চিনি ও ভাজাপোড়া কমিয়ে শাকসবজি ও পর্যাপ্ত প্রোটিন যুক্ত করুন।\n"
        "২. সপ্তাহে অন্তত ১৫০ মিনিট স্বাভাবিক হাঁটা বা শারীরিক সক্রিয়তা বজায় রাখুন।\n"
        "৩. মাসিকের তারিখ, ব্যথা ও প্রবাহের সঠিক হিসাব ডায়রিতে বা অ্যাপে নিয়মিত লিখে রাখুন।\n"
        "৪. একজন রেজিস্টার্ড স্ত্রীরোগ বিশেষজ্ঞ (Gynecologist) দেখিয়ে প্রয়োজনীয় রক্তের হরমোন পরীক্ষা (LH/FSH, TSH) ও আল্ট্রাসাউন্ড করান।"
    )
    next_steps_en = (
        "1. Reduce refined sugars and ultra-processed foods; incorporate leafy vegetables and lean protein.\n"
        "2. Maintain at least 150 minutes of moderate aerobic exercise per week.\n"
        "3. Keep continuous logs of menstrual dates, duration, flow, and pain.\n"
        "4. Schedule a consultation with a registered Gynecologist for a comprehensive hormonal and pelvic ultrasound evaluation."
    )

    # 6. Save Assessment Record in DB
    assessment = HealthAssessment(
        user_id=user_id,
        assessment_date=now,
        input_features_json=json.dumps(ml_features),
        calibrated_risk_score=risk_score,
        risk_band=risk_band,
        contributing_factors_json=json.dumps(factors),
        missing_information_json=json.dumps(missing_info),
        next_steps_bn=next_steps_bn,
        next_steps_en=next_steps_en,
        clinical_disclaimer=CLINICAL_DISCLAIMER_BN
    )
    db.add(assessment)
    db.commit()

    return {
        "assessment_id": assessment.id,
        "calibrated_risk_score": risk_score,
        "risk_percentage": round(risk_score * 100, 1),
        "risk_band": risk_band,
        "trajectory": trajectory,
        "contributing_factors": factors,
        "missing_information": missing_info,
        "next_steps_bn": next_steps_bn,
        "next_steps_en": next_steps_en,
        "clinical_disclaimer_bn": CLINICAL_DISCLAIMER_BN,
        "clinical_disclaimer_en": CLINICAL_DISCLAIMER_EN,
        "model_version": ml_result["model_version"],
        "model_type": ml_result["model_type"],
        "assessment_date": now.isoformat()
    }

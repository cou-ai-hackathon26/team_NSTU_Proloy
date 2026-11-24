import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.user import User
from app.models.ml_ops import HealthAssessment
from app.api.deps import get_optional_user, get_current_user
from app.services.pcos_longitudinal import evaluate_longitudinal_pcos_risk

router = APIRouter(prefix="/pcos-tracker", tags=["Longitudinal PCOS Risk Tracker"])

class LongitudinalPCOSRequest(BaseModel):
    age: Optional[float] = Field(25.0, ge=12, le=60)
    height_cm: Optional[float] = Field(155.0, ge=100, le=220)
    weight_kg: Optional[float] = Field(55.0, ge=30, le=200)
    cycle_regularity: Optional[str] = "regular"  # "regular" or "irregular"
    cycle_length_days: Optional[float] = Field(28.0, ge=15, le=120)
    weight_gain: Optional[bool] = False
    excess_hair_growth: Optional[bool] = False
    skin_darkening: Optional[bool] = False
    hair_loss: Optional[bool] = False
    pimples_acne: Optional[bool] = False
    fast_food_frequent: Optional[bool] = False
    regular_exercise: Optional[bool] = False
    family_history_pcos: Optional[bool] = None

@router.post("/evaluate")
def evaluate_risk(
    req: LongitudinalPCOSRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates personalized longitudinal PCOS possibility based on multi-factor patient data.
    Provides calibrated probability, SHAP factors, missing information, and clinical disclaimers.
    Never equates symptoms directly to diagnosis.
    """
    result = evaluate_longitudinal_pcos_risk(
        user_id=current_user.id,
        db=db,
        current_data=req.model_dump()
    )
    return result

@router.get("/history")
def get_risk_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns historical risk trajectory over time."""
    records = db.query(HealthAssessment).filter(
        HealthAssessment.user_id == current_user.id
    ).order_by(HealthAssessment.assessment_date.asc()).all()

    return [
        {
            "id": r.id,
            "assessment_date": r.assessment_date.isoformat(),
            "risk_score": r.calibrated_risk_score,
            "risk_percentage": round(r.calibrated_risk_score * 100, 1),
            "risk_band": r.risk_band,
            "contributing_factors": json.loads(r.contributing_factors_json or "[]"),
            "missing_information": json.loads(r.missing_information_json or "[]"),
            "clinical_disclaimer": r.clinical_disclaimer
        }
        for r in records
    ]

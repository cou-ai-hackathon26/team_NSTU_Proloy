import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.pcos import PCOSCheck
from app.schemas.pcos import PCOSInput, PCOSResponse
from app.services.pcos_model import predict_pcos_risk
from app.api.deps import get_optional_user

router = APIRouter(prefix="/pcos", tags=["PCOS Risk Screening"])

@router.post("/predict", response_model=PCOSResponse)
def evaluate_pcos(
    req: PCOSInput,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates PCOS/PCOD risk level.
    Stores record anonymously if authenticated, or returns immediate screening.
    Always includes doctor consultation advice and non-diagnostic disclaimers.
    """
    result = predict_pcos_risk(req)

    if current_user:
        check = PCOSCheck(
            user_id=current_user.id,
            inputs_json=json.dumps(req.model_dump()),
            risk_score=result.risk_score,
            risk_band=result.risk_band,
            explanation_bn=result.explanation_bn,
            contributing_factors=json.dumps(result.contributing_factors)
        )
        db.add(check)
        db.commit()

    return result

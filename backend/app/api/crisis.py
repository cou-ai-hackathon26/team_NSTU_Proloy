import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.crisis import CrisisAssessmentRecord
from app.schemas.crisis import (
    CrisisAssessRequest, CrisisAssessResponse,
    CrisisAssessmentItem, CrisisHistoryResponse,
    CrisisSafetyResponseRequest, CrisisSafetyResponse
)
from app.services.crisis_classifier_engine import crisis_classifier_engine
from app.api.deps import get_current_user, get_optional_user

router = APIRouter(prefix="/api/crisis", tags=["Indirect Bangla Mental Health Crisis Engine"])

@router.post("/assess", response_model=CrisisAssessResponse)
def assess_crisis_signal(
    req: CrisisAssessRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates Bangla text using the 4-tier Crisis Risk Classification:
    - LEVEL_0: Normal health/wellness inquiry
    - LEVEL_1: Mild emotional distress (grief, stress, weariness)
    - LEVEL_2: Significant distress (veiled ideation, burdensomeness, desire to vanish)
    - LEVEL_3: Immediate danger / Lethal means / Critical crisis

    Handles culturally indirect expressions, negation, and educational contexts.
    """
    result = crisis_classifier_engine.assess_crisis(req.text, req.previous_history)

    # Record assessment in database
    user = current_user
    if user:
        record = CrisisAssessmentRecord(
            id=str(uuid.uuid4()),
            user_id=user.id,
            conversation_id=req.conversation_id,
            risk_level=result["risk_level"],
            confidence=result["confidence"],
            detected_signal_categories=result["detected_signal_categories"],
            assessment_status="safety_engaged" if result["level_numeric"] >= 2 else "monitored",
            clarification_prompt_bn=result.get("clarification_prompt_bn"),
            created_at=datetime.now(timezone.utc)
        )
        db.add(record)
        db.commit()

    return CrisisAssessResponse(**result)


@router.get("/assessment-history", response_model=CrisisHistoryResponse)
def get_crisis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns anonymized history of crisis assessments for longitudinal safety tracking.
    """
    records = db.query(CrisisAssessmentRecord).filter(
        CrisisAssessmentRecord.user_id == current_user.id
    ).order_by(CrisisAssessmentRecord.created_at.desc()).limit(30).all()

    items = [
        CrisisAssessmentItem(
            id=r.id,
            risk_level=r.risk_level,
            confidence=r.confidence,
            signal_categories=r.detected_signal_categories or [],
            created_at=r.created_at
        )
        for r in records
    ]

    return CrisisHistoryResponse(
        total_assessments=len(items),
        recent_assessments=items
    )


@router.post("/safety-response", response_model=CrisisSafetyResponse)
def generate_crisis_safety_response(
    req: CrisisSafetyResponseRequest
):
    """
    Provides culturally calibrated crisis support messages.
    For LEVEL_3 or immediate danger: returns bystander-safe covert de-escalation message
    and national helplines (109 for women & children, 999 emergency).
    """
    risk = req.risk_level.upper()

    if risk == "LEVEL_3" or req.is_immediate_danger:
        return CrisisSafetyResponse(
            response_text_bn=(
                "আপু, আমি বুঝতে পারছি আপনি তীব্র মানসিক যন্ত্রণার মধ্যে আছেন। আপনি একা নন। "
                "একটু গভীর শ্বাস নিন। আপনার নিরাপত্তা ও জীবন আমাদের কাছে সবচেয়ে মূল্যবান। "
                "দয়া করে অবিলম্বে জাতীয় হেল্পলাইন ১০৯ অথবা জরুরি সেবা ৯৯৯-এ কথা বলুন।"
            ),
            support_number="109",
            support_label_bn="নারী ও শিশু বিষয়ক জাতীয় হেল্পলাইন (১০৯) ও জরুরি সেবা (৯৯৯)",
            covert_mode=True
        )
    elif risk == "LEVEL_2":
        return CrisisSafetyResponse(
            response_text_bn=(
                "আপু, আপনার কষ্ট আমি গভীরভাবে অনুভব করছি। নিজেকে কখনো বোঝা মনে করবেন না। "
                "কোনো কষ্ট বা চাপ একা বয়ে বেড়াবেন না। আপনি চাইলে আমার সাথে আরো কথা বলতে পারেন, "
                "অথবা একজন বিশ্বস্ত মানুষ কিংবা ১০৯ হেল্পলাইনে কথা বলতে পারেন।"
            ),
            support_number="109",
            support_label_bn="মানসিক স্বাস্থ্য ও নারী সহায়তা হেল্পলাইন (১০৯)",
            covert_mode=True
        )
    elif risk == "LEVEL_1":
        return CrisisSafetyResponse(
            response_text_bn=(
                "আপু, মন খারাপ থাকা স্বাভাবিক। অনেক সময় ক্লান্তি বা হরমোনের পরিবর্তনের কারণেও এমন লাগতে পারে। "
                "একটু বিশ্রাম নিন, এক গ্লাস পানি পান করুন। আমি সবসময় আপনার কথা শোনার জন্য আছি।"
            ),
            support_number=None,
            support_label_bn=None,
            covert_mode=False
        )
    else:
        return CrisisSafetyResponse(
            response_text_bn="আমি আপনার পাশে আছি। আপনার স্বাস্থ্য বা মনের বিষয়ে যেকোনো কথা বলতে পারেন।",
            support_number=None,
            support_label_bn=None,
            covert_mode=False
        )

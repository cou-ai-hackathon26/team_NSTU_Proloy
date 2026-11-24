from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.privacy import UserPrivacyPreference
from app.schemas.privacy import PrivacyPreferencesRequest, PrivacyPreferencesResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/privacy", tags=["User Privacy & Shared Device Preferences"])

@router.get("/preferences", response_model=PrivacyPreferencesResponse)
def get_privacy_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves user's privacy settings:
    - Discreet mode (neutral titles/camouflage)
    - Concealment of sensitive menstrual terms on shared devices
    - Voice response permissions
    - Auto-lock session timeout
    """
    pref = db.query(UserPrivacyPreference).filter(UserPrivacyPreference.user_id == current_user.id).first()
    if not pref:
        # Initialize sensible defaults
        pref = UserPrivacyPreference(
            user_id=current_user.id,
            voice_response_enabled=True,
            discreet_mode_enabled=True,
            sensitive_content_hidden=True,
            session_timeout=300,
            crisis_support_preferences={
                "allow_emergency_helpline": True,
                "preferred_helpline": "109",
                "bystander_safe_audio": True
            }
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    return PrivacyPreferencesResponse(
        user_id=pref.user_id,
        voice_response_enabled=pref.voice_response_enabled,
        discreet_mode_enabled=pref.discreet_mode_enabled,
        sensitive_content_hidden=pref.sensitive_content_hidden,
        session_timeout=pref.session_timeout,
        crisis_support_preferences=pref.crisis_support_preferences or {},
        updated_at=pref.updated_at or datetime.now(timezone.utc)
    )

@router.put("/preferences", response_model=PrivacyPreferencesResponse)
def update_privacy_preferences(
    req: PrivacyPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates granular privacy preferences for shared device protection.
    """
    pref = db.query(UserPrivacyPreference).filter(UserPrivacyPreference.user_id == current_user.id).first()
    if not pref:
        pref = UserPrivacyPreference(user_id=current_user.id)
        db.add(pref)

    if req.voice_response_enabled is not None:
        pref.voice_response_enabled = req.voice_response_enabled
    if req.discreet_mode_enabled is not None:
        pref.discreet_mode_enabled = req.discreet_mode_enabled
    if req.sensitive_content_hidden is not None:
        pref.sensitive_content_hidden = req.sensitive_content_hidden
    if req.session_timeout is not None:
        pref.session_timeout = req.session_timeout
    if req.crisis_support_preferences is not None:
        pref.crisis_support_preferences = req.crisis_support_preferences

    pref.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pref)

    return PrivacyPreferencesResponse(
        user_id=pref.user_id,
        voice_response_enabled=pref.voice_response_enabled,
        discreet_mode_enabled=pref.discreet_mode_enabled,
        sensitive_content_hidden=pref.sensitive_content_hidden,
        session_timeout=pref.session_timeout,
        crisis_support_preferences=pref.crisis_support_preferences or {},
        updated_at=pref.updated_at
    )

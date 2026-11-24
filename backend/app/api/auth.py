import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AnonymousRegisterRequest, LoginRequest, SetPinRequest, AuthTokenResponse
from app.core.security import create_access_token, hash_pin, verify_pin
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Privacy"])

@router.post("/anonymous", response_model=AuthTokenResponse)
def create_anonymous_user(
    req: AnonymousRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Creates a new pseudonymous user with a random UUID.
    No PII (no name, email, phone number) is accepted or recorded.
    """
    pin_hash = hash_pin(req.pin) if req.pin else None
    user_id = str(uuid.uuid4())

    user = User(
        id=user_id,
        pin_hash=pin_hash,
        age_group=req.age_group,
        language=req.language or "bn"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    return AuthTokenResponse(
        access_token=token,
        user_id=user.id,
        created_at=user.created_at,
        message="বেনামী আইডি সফলভাবে তৈরি হয়েছে"
    )

@router.post("/login", response_model=AuthTokenResponse)
def login_with_pin(
    req: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticates a user on their device using their anonymous UUID and optional PIN.
    """
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ব্যবহারকারী খুঁজে পাওয়া যায়নি"
        )
    if user.pin_hash:
        if not verify_pin(req.pin, user.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ভুল পিন কোড"
            )

    token = create_access_token({"sub": user.id})
    return AuthTokenResponse(
        access_token=token,
        user_id=user.id,
        created_at=user.created_at,
        message="সফলভাবে লগইন হয়েছে"
    )

@router.put("/pin")
def set_or_update_pin(
    req: SetPinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sets or updates the 4-6 digit device protection PIN.
    """
    current_user.pin_hash = hash_pin(req.pin)
    db.commit()
    return {"message": "পিন কোড সফলভাবে সংরক্ষিত হয়েছে"}

@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns pseudonymous profile info."""
    return {
        "user_id": current_user.id,
        "age_group": current_user.age_group,
        "language": current_user.language,
        "created_at": current_user.created_at,
        "has_pin": current_user.pin_hash is not None
    }

@router.delete("/me")
def delete_all_my_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently wipes the user and cascades deletion of ALL period logs,
    mood logs, PCOS records, and reminders from the database.
    """
    db.delete(current_user)
    db.commit()
    return {"message": "আপনার সমস্ত তথ্য সম্পূর্ণ এবং স্থায়ীভাবে মুছে ফেলা হয়েছে।"}

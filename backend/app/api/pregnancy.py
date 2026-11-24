from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.pregnancy import PregnancyLog
from app.schemas.pregnancy import PregnancyStartRequest, PregnancyStatusResponse
from app.services.pregnancy_engine import get_pregnancy_status, calculate_edd
from app.api.deps import get_current_user

router = APIRouter(prefix="/preg", tags=["Pregnancy Care & Timeline"])

@router.post("/start", response_model=PregnancyStatusResponse)
def start_pregnancy_tracker(
    req: PregnancyStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()
    if req.lmp_date > today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="শেষ পিরিয়ডের তারিখ (LMP) ভবিষ্যতের কোনো দিন হতে পারে না।"
        )
    if (today - req.lmp_date).days > 310:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="প্রদত্ত তারিখ অনুযায়ী গর্ভকাল ৪২ সপ্তাহের বেশি অতিক্রম করেছে। অবিলম্বে হাসপাতালে যান।"
        )

    existing = db.query(PregnancyLog).filter(
        PregnancyLog.user_id == current_user.id,
        PregnancyLog.active == True
    ).first()

    edd = calculate_edd(req.lmp_date)

    if existing:
        existing.lmp_date = req.lmp_date
        existing.edd = edd
        db.commit()
        db.refresh(existing)
    else:
        new_preg = PregnancyLog(
            user_id=current_user.id,
            lmp_date=req.lmp_date,
            edd=edd,
            active=True
        )
        db.add(new_preg)
        db.commit()

    return get_pregnancy_status(req.lmp_date)

@router.get("/timeline", response_model=Optional[PregnancyStatusResponse])
def get_timeline(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    active_preg = db.query(PregnancyLog).filter(
        PregnancyLog.user_id == current_user.id,
        PregnancyLog.active == True
    ).first()

    if not active_preg:
        return None

    return get_pregnancy_status(active_preg.lmp_date)

@router.delete("/stop")
def stop_pregnancy_tracker(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    active_preg = db.query(PregnancyLog).filter(
        PregnancyLog.user_id == current_user.id,
        PregnancyLog.active == True
    ).first()
    if active_preg:
        active_preg.active = False
        db.commit()
    return {"message": "গর্ভকালীন ট্র্যাকার নিষ্ক্রিয় করা হয়েছে।"}

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.models.health_logs import MedicalReport
from app.api.deps import get_current_user

router = APIRouter(prefix="/medical-reports", tags=["Medical Reports Interpretation"])

class LabReportInput(BaseModel):
    report_type: str  # hormonal_panel, blood_glucose, thyroid, ultrasound, general
    file_name: Optional[str] = "lab_report.pdf"
    lh_level: Optional[float] = None          # mIU/mL
    fsh_level: Optional[float] = None         # mIU/mL
    fasting_glucose: Optional[float] = None   # mg/dL
    tsh_level: Optional[float] = None         # mIU/L
    total_testosterone: Optional[float] = None # ng/dL
    ultrasound_notes: Optional[str] = None
    patient_notes: Optional[str] = None

def generate_educational_interpretation(data: Dict[str, Any]) -> Tuple[str, str]:
    """Generates evidence-based interpretation and explicit diagnostic limitation disclaimers."""
    insights_bn = []
    insights_en = []

    lh = data.get("lh_level")
    fsh = data.get("fsh_level")
    if lh is not None and fsh is not None and fsh > 0:
        ratio = round(lh / fsh, 2)
        if ratio >= 2.0:
            insights_bn.append(f"আপনার এলএইচ ও এফএসএইচ অনুপাত (LH/FSH Ratio) প্রায় {ratio}:১। চিকিৎসাবিজ্ঞান অনুযায়ী ২:১ বা তার বেশি অনুপাত সাধারণত পিসিওএস বা হরমোনের তারতম্যে পরিলক্ষিত হতে পারে।")
            insights_en.append(f"Your LH to FSH ratio is approximately {ratio}:1. A ratio of 2:1 or greater is frequently observed in individuals with hormonal imbalances or PCOS.")
        else:
            insights_bn.append(f"আপনার এলএইচ ও এফএসএইচ অনুপাত {ratio}:১, যা স্বাভাবিক পরিধিতে রয়েছে।")
            insights_en.append(f"Your LH to FSH ratio is {ratio}:1, which is within conventional physiological ranges.")

    glucose = data.get("fasting_glucose")
    if glucose is not None:
        if glucose >= 100:
            insights_bn.append(f"ফাস্টিং ব্লাড গ্লুকোজ {glucose} mg/dL, যা সামান্য বেশি (ইমপেয়ার্ড ফাস্টিং গ্লুকোজ)। পিসিওএসে ইনসুলিন রেজিস্ট্যান্সের কারণে রক্তে গ্লুকোজ বাড়তে পারে।")
            insights_en.append(f"Fasting blood glucose is {glucose} mg/dL (slightly elevated), which may correlate with insulin resistance commonly associated with PCOS.")
        else:
            insights_bn.append(f"ফাস্টিং ব্লাড গ্লুকোজ {glucose} mg/dL স্বাভাবিক মাত্রায় রয়েছে।")
            insights_en.append(f"Fasting blood glucose is {glucose} mg/dL, within normal physiological limits.")

    tsh = data.get("tsh_level")
    if tsh is not None:
        if tsh > 4.5:
            insights_bn.append(f"টিএসএইচ (TSH) মাত্রা {tsh} mIU/L নির্দেশ করে আপনার আন্ডারঅ্যাক্টিভ থাইরয়েড (Hypothyroidism) থাকতে পারে, যা অনেক সময় মাসিকের অনিয়ম সৃষ্টি করে।")
            insights_en.append(f"TSH level of {tsh} mIU/L suggests potential subclinical or overt hypothyroidism, which independently disrupts menstrual regularity.")
        elif tsh < 0.4:
            insights_bn.append(f"টিএসএইচ মাত্রা {tsh} mIU/L নির্দেশ করে থাইরয়েডের অতিসক্রিয়তা থাকতে পারে।")
            insights_en.append(f"TSH level of {tsh} mIU/L indicates potential hyperthyroidism.")

    usg = data.get("ultrasound_notes", "")
    if "follicle" in usg.lower() or "cyst" in usg.lower() or "সিস্ট" in usg or "ডিম্বাশয়" in usg:
        insights_bn.append("আল্ট্রাসাউন্ড রিপোর্টে ডিম্বাশয়ে ছোট ছোট ফলিকল বা সিস্টের কথা উল্লেখ থাকতে পারে। মনে রাখবেন—ডিম্বাশয়ে ফলিকল থাকা মানেই পিসিওএস রোগ নয়; চিকিৎসকের সার্বিক মূল্যায়ন প্রয়োজন।")
        insights_en.append("Ultrasound notes mention follicular appearance. The presence of peripheral follicles is a non-specific radiological finding requiring clinical correlation.")

    if not insights_bn:
        insights_bn.append("আপনার জমা দেওয়া ল্যাব টেস্টের মানগুলো সাধারণ শিক্ষা ও পর্যালোচনার জন্য সংরক্ষিত হয়েছে।")
        insights_en.append("Your recorded laboratory values have been cataloged for your longitudinal clinical tracking.")

    disclaimer_bn = (
        "গুরুত্বপূর্ণ সীমাবদ্ধতা: এই এআই ল্যাব বিশ্লেষণ কোনো মেডিকেল ডায়াগনসিস বা প্রেসক্রিপশন নয়। "
        "ল্যাব রিপোর্টের রেফারেন্স রেঞ্জ প্রতিটি ডায়াগনস্টিক সেন্টারের মেশিন ও পদ্ধতির ওপর নির্ভর করে পরিবর্তিত হতে পারে। "
        "রিপোর্টটি নিয়ে অবশ্যই একজন রেজিস্টার্ড চিকিৎসকের সাথে সরাসরি দেখা করুন।"
    )
    disclaimer_en = (
        "Critical Limitations: This AI report overview is educational and does not constitute a certified medical diagnosis. "
        "Reference ranges vary significantly across diagnostic instruments and regional laboratories. "
        "Always present official printed laboratory reports directly to a licensed healthcare practitioner."
    )

    full_bn = "\n".join(insights_bn)
    full_en = "\n".join(insights_en)
    return f"{full_bn}\n\n{disclaimer_bn}", f"{full_en}\n\n{disclaimer_en}"

@router.post("/upload")
def upload_lab_report(
    req: LabReportInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits laboratory report values and receives an evidence-based educational interpretation
    with strict clinical limitations and disclaimers.
    """
    data = req.model_dump()
    interp_bn, interp_en = generate_educational_interpretation(data)

    report = MedicalReport(
        user_id=current_user.id,
        report_type=req.report_type,
        file_name=req.file_name,
        extracted_values_json=json.dumps(data),
        ai_interpretation=interp_bn,
        clinical_limitations=interp_en,
        is_reviewed_by_doctor=False
    )
    db.add(report)
    db.commit()

    return {
        "report_id": report.id,
        "uploaded_at": report.uploaded_at.isoformat(),
        "report_type": report.report_type,
        "interpretation_bn": interp_bn,
        "interpretation_en": interp_en,
        "extracted_values": data
    }

@router.get("")
def list_my_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all medical reports uploaded by the patient."""
    reports = db.query(MedicalReport).filter(
        MedicalReport.user_id == current_user.id
    ).order_by(MedicalReport.uploaded_at.desc()).all()

    return [
        {
            "id": r.id,
            "uploaded_at": r.uploaded_at.isoformat(),
            "report_type": r.report_type,
            "file_name": r.file_name,
            "extracted_values": json.loads(r.extracted_values_json or "{}"),
            "ai_interpretation": r.ai_interpretation,
            "clinical_limitations": r.clinical_limitations,
            "is_reviewed_by_doctor": r.is_reviewed_by_doctor
        }
        for r in reports
    ]

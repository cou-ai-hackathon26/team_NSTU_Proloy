from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class PregnancyStartRequest(BaseModel):
    lmp_date: date = Field(..., description="Last menstrual period date")

class WeekMilestone(BaseModel):
    week: int
    trimester: int
    baby_size_bn: str
    development_summary_bn: str
    maternal_changes_bn: str
    nutrition_advice_bn: List[str]
    anc_recommended: bool = False
    anc_visit_title_bn: Optional[str] = None
    urgent_warning_signs_bn: List[str]

class PregnancyStatusResponse(BaseModel):
    lmp_date: date
    edd: date
    gestational_weeks: int
    gestational_days: int
    current_trimester: int
    current_milestone: WeekMilestone
    disclaimer_bn: str = "জরুরি সতর্কতা: গর্ভাবস্থায় যেকোনো রক্তক্ষরণ, তীব্র পেট ব্যথা, চোখে ঝাপসা দেখা, বা খিঁচুনি হলে অবিলম্বে নিকটস্থ স্বাস্থ্যকেন্দ্রে যান।"

from pydantic import BaseModel, Field
from typing import Optional, List

class PCOSInput(BaseModel):
    age: int = Field(..., ge=12, le=55, description="Age in years")
    weight_kg: float = Field(..., ge=30, le=200, description="Weight in kg")
    height_cm: float = Field(..., ge=100, le=220, description="Height in cm")
    cycle_regularity: str = Field(..., description="'regular' or 'irregular'")
    cycle_length_days: int = Field(28, ge=15, le=90, description="Average cycle length in days")
    weight_gain: bool = Field(False, description="Recent sudden weight gain")
    excess_hair_growth: bool = Field(False, description="Hirsutism - chin, upper lip, chest")
    skin_darkening: bool = Field(False, description="Acanthosis nigricans - neck, groin")
    hair_loss: bool = Field(False, description="Thinning or male-pattern hair loss")
    pimples_acne: bool = Field(False, description="Persistent cystic acne")
    fast_food_frequency: Optional[str] = Field("occasional", description="rare, occasional, frequent")
    regular_exercise: bool = Field(False, description="At least 30 mins exercise per day")

class PCOSResponse(BaseModel):
    risk_score: float = Field(..., description="0.0 to 1.0 probability")
    risk_band: str = Field(..., description="low, medium, high")
    risk_band_bn: str = Field(..., description="কম ঝুঁকি, মাঝারি ঝুঁকি, বেশি ঝুঁকি")
    contributing_factors: List[str]
    explanation_bn: str
    actionable_advice_bn: List[str]
    disclaimer_bn: str = "সতর্কবার্তা: এটি কোনো চূড়ান্ত রোগ নির্ণয় নয়। এটি শুধুমাত্র একটি প্রাথমিক স্বাস্থ্য ঝুঁকি নির্দেশক। কোনো সিদ্ধান্ত নেওয়ার আগে অবশ্যই একজন রেজিস্টার্ড চিকিৎসকের সাথে পরামর্শ করুন।"

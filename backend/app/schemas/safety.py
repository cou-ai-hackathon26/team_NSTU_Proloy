from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class EmergencyPayload(BaseModel):
    is_emergency: bool = False
    title_bn: str = "আমরা আপনার পাশে আছি"
    message_bn: str = "আপনি একা নন। আপনার কষ্ট আমরা বুঝতে পারছি। এখনই সাহায্য পাওয়ার জন্য নিচের নম্বরে যোগাযোগ করুন।"
    helpline_number: str = "999"
    helpline_label_bn: str = "৯৯৯ এ কল করুন (জাতীয় জরুরি সেবা)"
    mental_health_helpline: str = "109"
    mental_health_label_bn: str = "১০৯ (নারী নির্যাতন প্রতিরোধ ও সহায়তা সেল)"
    support_steps_bn: List[str] = [
        "একটি নিরিবিলি জায়গায় গিয়ে গভীর শ্বাস নিন।",
        "আপনার বিশ্বস্ত কোনো মানুষের সাথে কথা বলুন।",
        "প্রয়োজনে সরাসরি ৯৯৯ বা নিকটস্থ স্বাস্থ্যকর্মীর সহায়তা নিন।"
    ]
    covert_mode: bool = False
    bystander_safe_audio_bn: Optional[str] = None

class SafetyCheckRequest(BaseModel):
    text: str

class SafetyCheckResponse(BaseModel):
    risk_level: str = Field(..., description="none, low, medium, high")
    reason: Optional[str] = None
    action_required: bool = False
    emergency_payload: Optional[EmergencyPayload] = None
    is_veiled_crisis: bool = False
    covert_alert: bool = False

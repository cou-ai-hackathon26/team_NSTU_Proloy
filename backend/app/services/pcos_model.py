import os
import joblib
import numpy as np
from typing import List, Tuple
from app.schemas.pcos import PCOSInput, PCOSResponse

MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "ml", "pcos", "model.joblib"
)

_MODEL_ARTIFACT = None

def load_pcos_model():
    global _MODEL_ARTIFACT
    if _MODEL_ARTIFACT is None and os.path.exists(MODEL_PATH):
        try:
            _MODEL_ARTIFACT = joblib.load(MODEL_PATH)
        except Exception:
            _MODEL_ARTIFACT = None
    return _MODEL_ARTIFACT

def predict_pcos_risk(data: PCOSInput) -> PCOSResponse:
    """
    Evaluates PCOS/PCOD risk based on non-invasive patient-reported features.
    Provides calibrated risk banding, contributing factors, and doctor consultation advice.
    NEVER diagnoses.
    """
    # Calculate BMI: kg / (m^2)
    height_m = data.height_cm / 100.0
    bmi = data.weight_kg / (height_m * height_m)
    
    is_irregular = 1 if data.cycle_regularity.lower() == "irregular" else 0
    fast_food = 1 if data.fast_food_frequency in ["occasional", "frequent"] else 0
    exercise = 1 if data.regular_exercise else 0
    
    features = [
        data.age,
        bmi,
        is_irregular,
        data.cycle_length_days,
        1 if data.weight_gain else 0,
        1 if data.excess_hair_growth else 0,
        1 if data.skin_darkening else 0,
        1 if data.hair_loss else 0,
        1 if data.pimples_acne else 0,
        fast_food,
        exercise
    ]

    artifact = load_pcos_model()
    if artifact and "pipeline" in artifact:
        pipeline = artifact["pipeline"]
        prob = float(pipeline.predict_proba([features])[0][1])
    else:
        # Fallback calibrated clinical heuristics
        score = 0.05
        if is_irregular:
            score += 0.30
        if data.cycle_length_days > 35 or data.cycle_length_days < 21:
            score += 0.15
        if data.excess_hair_growth:
            score += 0.20
        if data.skin_darkening:
            score += 0.15
        if data.weight_gain:
            score += 0.10
        if data.pimples_acne:
            score += 0.08
        if data.hair_loss:
            score += 0.08
        if bmi > 25:
            score += 0.10
        prob = min(0.95, max(0.05, score))

    # Identify contributing factors in plain Bangla
    factors = []
    if is_irregular:
        factors.append("অনিয়মিত মাসিক বা পিরিয়ডের চক্র")
    if data.cycle_length_days > 35:
        factors.append("পিরিয়ডের মধ্যবর্তী ব্যবধান ৩৫ দিনের বেশি হওয়া")
    if data.excess_hair_growth:
        factors.append("মুখে বা শরীরে অতিরিক্ত অবাঞ্ছিত লোম গজানো (হিরসুটিজম)")
    if data.skin_darkening:
        factors.append("ঘাড়ে বা ত্বকের ভাঁজে কালো ছোপ পড়া (অ্যাকান্থোসিস নিগ্রিকানস)")
    if data.weight_gain:
        factors.append("খাদ্যাভ্যাস পরিবর্তন ছাড়াই হঠাৎ দ্রুত ওজন বৃদ্ধি")
    if data.pimples_acne:
        factors.append("অতিরিক্ত ব্রণ বা ফুসকুড়ি")
    if data.hair_loss:
        factors.append("মাথার চুল অস্বাভাবিক পাতলা হওয়া")
    if bmi > 25:
        factors.append("উচ্চতার তুলনায় ওজন কিছুটা বেশি (বিএমআই ২৫ এর বেশি)")

    # Banding
    if prob >= 0.65:
        band = "high"
        band_bn = "বেশি ঝুঁকি"
        explanation = (
            "আপনার দেওয়া তথ্যে পিসিওএস (PCOS) বা হরমোনজনিত সমস্যার বেশ কিছু উল্লেখযোগ্য লক্ষণ দেখা যাচ্ছে। "
            "ভয় পাওয়ার কিছু নেই, তবে সঠিক সময়ে ব্যবস্থা নেওয়া খুব গুরুত্বপূর্ণ।"
        )
    elif prob >= 0.35:
        band = "medium"
        band_bn = "মাঝারি ঝুঁকি"
        explanation = (
            "আপনার শরীরে কিছু মৃদু হরমোন পরিবর্তনের লক্ষণ পরিলক্ষিত হচ্ছে। "
            "জীবনযাত্রার পরিবর্তন এবং চিকিৎসকের পরামর্শ আপনাকে সুস্থ রাখতে সাহায্য করবে।"
        )
    else:
        band = "low"
        band_bn = "কম ঝুঁকি"
        explanation = (
            "আপনার দেওয়া তথ্যানুযায়ী বর্তমানে পিসিওএস এর বড় কোনো লক্ষণ পরিলক্ষিত হচ্ছে না। "
            "পিরিয়ড নিয়মিত রাখতে স্বাস্থ্যকর খাবার খান ও সক্রিয় থাকুন।"
        )

    advice = [
        "প্রতিদিন অন্তত ৩০ মিনিট হালকা হাঁটাচলা বা শারীরিক ব্যায়াম করুন।",
        "মিষ্টি, ভাজাপোড়া এবং প্রক্রিয়াজাত খাবার কমিয়ে শাকসবজি ও ফলমূল বেশি খান।",
        "মানসিক চাপমুক্ত থাকার চেষ্টা করুন এবং রাতে পর্যাপ্ত ঘুমান।"
    ]
    if band in ["medium", "high"]:
        advice.insert(0, "নিকটস্থ স্বাস্থ্যকেন্দ্রে একজন গাইনি চিকিৎসকের সাথে পরামর্শ করে আল্ট্রাসনোগ্রাম ও হরমোন টেস্ট করিয়ে নিশ্চিত হন।")

    return PCOSResponse(
        risk_score=round(prob, 2),
        risk_band=band,
        risk_band_bn=band_bn,
        contributing_factors=factors if factors else ["কোনো দৃশ্যমান অস্বাভাবিক লক্ষণ নেই"],
        explanation_bn=explanation,
        actionable_advice_bn=advice
    )

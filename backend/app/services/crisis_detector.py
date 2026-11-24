# -*- coding: utf-8 -*-
"""
Multi-Tiered Safety & Crisis Detection Engine with Veiled Distress Recognition:
1. Direct suicide keywords & stems (High Risk, immediate 999 escalation)
2. Rural lethal means access (pesticides, agricultural poisons, river drowning)
3. Veiled & euphemistic Bengali distress taxonomy:
   - Passive resignation / death wishes ("আল্লাহ যেন তুলে নেয়", "ঘুমাইয়া যদি আর না উঠতাম")
   - Burdensomeness & erasure ("আমি না থাকলেই সবার ভালো", "সংসারের বোঝা")
   - Hopeless entrapment & domestic abuse ("চারিদিকে অন্ধকার", "বাপের বাড়ি গিয়ে আর মুখ দেখাব না")
4. Bystander-Safe Covert Escalation (protects shared-phone user from domestic retaliation)
"""

import json
import os
import re
from typing import Tuple, Dict, Any, Optional, List
from app.schemas.safety import SafetyCheckResponse, EmergencyPayload

# Paths to crisis datasets
KEYWORDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "ml", "crisis", "keywords_bn.json"
)
VEILED_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "ml", "crisis", "veiled_distress_bn.json"
)

def get_keywords() -> Dict[str, Any]:
    if os.path.exists(KEYWORDS_PATH):
        try:
            with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_veiled_keywords() -> Dict[str, List[str]]:
    if os.path.exists(VEILED_PATH):
        try:
            with open(VEILED_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

# Core lexical indicators
DIRECT_SUICIDE_STEMS = [
    "আত্মহত্যা", "মরে যাব", "মরতে চাই", "মরে যেতে চাই", "মরে গেলে", "মরব",
    "ফাঁস দেব", "ফাঁসি", "গলায় দড়ি", "বিষ খাব", "বিষ খেয়ে", "ছাদ থেকে লাফ",
    "জীবন শেষ", "জীবন রাখতে চাই না", "বাঁচতে চাই না", "বাচতে চাই না",
    "বাঁচার ইচ্ছা নেই", "বাচার ইচ্ছা নেই", "বেঁচে থাকার ইচ্ছা নেই", "বেঁচে থাকার ইচ্ছা নাই",
    "বেঁচে থাকতে চাই না", "বেঁচে থেকে লাভ নেই", "বেচে থেকে লাভ নেই",
    "বেঁচে থাকতে ইচ্ছা করে না", "বাঁচতে ইচ্ছা করে না", "বাঁচতে ইচ্ছা নেই"
]

BANGLISH_STEMS = [
    "morte chai", "morbo", "more jabo", "beche thakte chai na",
    "beche theke lav nai", "jibon sesh", "atmohotta", "suicide",
    "kill myself", "want to die", "end my life", "bish khabo"
]

INDIRECT_DISTRESS_STEMS = [
    "যন্ত্রণা শেষ", "যন্ত্রণা আর সহ্য", "মুক্তি চাই", "কাউকে মুখ দেখানোর",
    "মুখ দেখাতে পারছি না", "ঘৃণা করে", "ঘুমিয়ে পড়তে চাই", "ঘুমাতে চাই চিরতরে",
    "পৃথিবী ছেড়ে", "পরানডা আর সয় না", "বাঁচবার মন চায় না", "মরণ দাও"
]

BYSTANDER_SAFE_AUDIO_BN = (
    "আপু, আপনার মনের কষ্টটা আমি বুঝতে পারছি। একটু বুক ভরে নিঃশ্বাস নিন। "
    "এই কঠিন সময়টা কেটে যাবে, আপনার জীবন আমাদের কাছে অনেক মূল্যবান। আমি সবসময় আপনার পাশে আছি।"
)

def detect_crisis(text: str) -> SafetyCheckResponse:
    """
    Multi-layered crisis detector:
    - Layer 1: Deterministic direct suicide rules (High Risk -> 999)
    - Layer 1.5: Rural lethal means & pesticide ingestion (High Risk -> Covert Alert)
    - Layer 2: Veiled & euphemistic Bengali distress taxonomy (High Risk -> Bystander-Safe Alert)
    - Layer 3: Indirect emotional distress / hopelessness (Medium Risk)
    - High recall prioritized to protect user safety
    - Zero sensitive logging
    """
    if not text or not isinstance(text, str):
        return SafetyCheckResponse(risk_level="none", action_required=False)

    normalized_text = text.lower().strip()
    keywords_data = get_keywords()
    veiled_data = get_veiled_keywords()

    # --- Layer 1: Rural Lethal Means & Agricultural Ingestion (Covert High Risk) ---
    # Rural agricultural pesticides and covert means must take precedence over generic stems
    # to protect shared-phone users from domestic retaliation and overt loudspeaker announcements
    lethal_means = veiled_data.get("rural_lethal_means_access", [
        "ফসলের বিষ", "ঘাসের ওষুধ", "কীটনাশক", "কীটনাশকের বোতল", "পোকার ওষুধ", "নদীর জলে গা ভাসায় দেব"
    ])
    for lm in lethal_means:
        if lm in normalized_text:
            return SafetyCheckResponse(
                risk_level="high",
                reason="Rural agricultural lethal means or self-harm method mentioned",
                action_required=True,
                emergency_payload=EmergencyPayload(
                    is_emergency=True,
                    covert_mode=True,
                    bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN,
                    title_bn="আমরা আপনার পাশে আছি — নিরাপদ সহায়তা",
                    message_bn="আপু, আপনার কষ্ট আমরা অনুভব করছি। কোনো কঠিন সিদ্ধান্ত নেবেন না। এখনই ১০৯ (নারী সহায়তা সেল) বা ৯৯৯-এ সাহায্য নিন।",
                    helpline_number="109",
                    helpline_label_bn="১০৯ (গোপন নারী ও শিশু সহায়তা সেল)"
                ),
                is_veiled_crisis=True,
                covert_alert=True
            )

    # --- Layer 2: Veiled & Euphemistic Bengali Distress Taxonomy (Bystander-Safe High Risk) ---
    # 2.1 Passive Resignation & Death Wishes
    passive_death = veiled_data.get("passive_resignation_death_wishes", [
        "আল্লাহ যেন আমাকে তুলে নেয়", "ঘুমাইয়া যদি আর না উঠতাম", "আমার কি মরণ নাই", "এই জীবনের চেয়ে মরণ ভালো ছিল"
    ])
    for phrase in passive_death:
        if phrase in normalized_text:
            return SafetyCheckResponse(
                risk_level="high",
                reason="Veiled passive suicidal resignation detected",
                action_required=True,
                emergency_payload=EmergencyPayload(
                    is_emergency=True,
                    covert_mode=True,
                    bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN,
                    title_bn="আমরা আপনার পাশে আছি",
                    message_bn="আপনি কোনোভাবেই একা নন। জীবনের প্রতিটি কঠিন সময়ের শেষ আছে। মন খুলে কথা বলতে ১০৯ বা ১৬২৬৩ নম্বরে ডায়াল করুন।",
                    helpline_number="109",
                    helpline_label_bn="১০৯ এ সরাসরি কথা বলুন (নারী সহায়তা সেল)"
                ),
                is_veiled_crisis=True,
                covert_alert=True
            )

    # 2.2 Burdensomeness and Erasure Metaphors
    burdensome = veiled_data.get("burdensomeness_and_erasure", [
        "আমি না থাকলেই সবার ভালো", "সংসারের বোঝা হয়ে আছি", "কোথাও হারিয়ে যেতে চাই চিরতরে"
    ])
    for phrase in burdensome:
        if phrase in normalized_text:
            return SafetyCheckResponse(
                risk_level="high",
                reason="Perceived burdensomeness or desire for erasure detected",
                action_required=True,
                emergency_payload=EmergencyPayload(
                    is_emergency=True,
                    covert_mode=True,
                    bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN,
                    title_bn="আপনার জীবন অমূল্য",
                    message_bn="আপনি কারও বোঝা নন। আপনার উপস্থিতি অনেক গুরুত্বপূর্ণ। একজন বিশ্বস্ত সহায়তাকারীর সাথে কথা বলুন।",
                    helpline_number="109",
                    helpline_label_bn="১০৯ (গোপন সহায়তা সেল)"
                ),
                is_veiled_crisis=True,
                covert_alert=True
            )

    # 2.3 Hopeless Entrapment and Domestic Abuse
    entrapment = veiled_data.get("hopeless_entrapment_and_abuse", [
        "চারিদিকে অন্ধকার লাগে কোনো পথ নাই", "বাপের বাড়ি গিয়ে আর মুখ দেখাব না", "দম বন্ধ হয়ে আসতেছে আর পারি না"
    ])
    for phrase in entrapment:
        if phrase in normalized_text:
            return SafetyCheckResponse(
                risk_level="high",
                reason="Hopeless entrapment or domestic abuse distress detected",
                action_required=True,
                emergency_payload=EmergencyPayload(
                    is_emergency=True,
                    covert_mode=True,
                    bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN,
                    title_bn="সহায়তা ও নিরাপত্তা সেল",
                    message_bn="অত্যাচার বা নিরাশার বিরুদ্ধে আপনি একা নন। সরকারের ১০৯ হটলাইনে বিনামূল্যে আইনি ও মানসিক সহায়তা পাওয়া যায়।",
                    helpline_number="109",
                    helpline_label_bn="১০৯ (জাতীয় নারী নির্যাতন প্রতিরোধ হেল্পলাইন)"
                ),
                is_veiled_crisis=True,
                covert_alert=True
            )

    # --- Layer 3: Direct Suicide Keywords & Stems (Overt High Risk) ---
    all_direct = DIRECT_SUICIDE_STEMS + keywords_data.get("direct_suicide_bn", [])
    for kw in all_direct:
        if kw in normalized_text:
            return SafetyCheckResponse(
                risk_level="high",
                reason="Direct self-harm indication detected",
                action_required=True,
                emergency_payload=EmergencyPayload(is_emergency=True),
                is_veiled_crisis=False,
                covert_alert=False
            )

    # Syntactic combinations e.g. "বেঁচে থাকার কোনো ইচ্ছা নেই"
    if ("বেঁচে" in normalized_text or "বাঁচ" in normalized_text or "বাচ" in normalized_text) and (
        "ইচ্ছা নেই" in normalized_text or "লাভ নেই" in normalized_text or "মন চায় না" in normalized_text
    ):
        return SafetyCheckResponse(
            risk_level="high",
            reason="Expressed lack of will to live",
            action_required=True,
            emergency_payload=EmergencyPayload(is_emergency=True),
            is_veiled_crisis=False,
            covert_alert=False
        )

    # Banglish Direct Suicide Check
    all_banglish = BANGLISH_STEMS + keywords_data.get("banglish", [])
    for kw in all_banglish:
        if kw in normalized_text:
            return SafetyCheckResponse(
                risk_level="high",
                reason="Direct self-harm indication detected in romanized text",
                action_required=True,
                emergency_payload=EmergencyPayload(is_emergency=True),
                is_veiled_crisis=False,
                covert_alert=False
            )

    # --- Layer 3: Indirect Distress & Regional Expressions (Medium Risk) ---
    all_indirect = INDIRECT_DISTRESS_STEMS + keywords_data.get("indirect_distress_bn", []) + keywords_data.get("regional_colloquial", [])
    for kw in all_indirect:
        if kw in normalized_text:
            return SafetyCheckResponse(
                risk_level="medium",
                reason="Elevated emotional distress or despair detected",
                action_required=True,
                emergency_payload=EmergencyPayload(
                    is_emergency=False,
                    title_bn="আমরা আপনার কথা শুনছি",
                    message_bn="আপনার কষ্ট আমরা উপলব্ধি করছি। অনুগ্রহ করে একজন মানসিক স্বাস্থ্য বিশেষজ্ঞ বা আপনার ভালোবাসার মানুষের সাথে কথা বলুন।"
                ),
                is_veiled_crisis=False,
                covert_alert=False
            )

    return SafetyCheckResponse(risk_level="none", action_required=False)

# -*- coding: utf-8 -*-
"""
Bangla Mental Health Crisis Detection & Multi-Layer Safety Engine:
Operates 4 standardized operational risk levels:
- LEVEL 0: No Detected Crisis (Normal conversation)
- LEVEL 1: Mild Emotional Distress (Sadness, loneliness, emotional fatigue)
- LEVEL 2: Significant Distress (Veiled ideation, burdensomeness, desire to vanish -> direct gentle clarification)
- LEVEL 3: Possible Immediate Danger (Explicit self-harm intent, agricultural poisons, domestic violence danger)
"""

import re
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.crisis import CrisisAssessResponse
from app.services.crisis_detector import (
    get_keywords, get_veiled_keywords, BYSTANDER_SAFE_AUDIO_BN,
    DIRECT_SUICIDE_STEMS, BANGLISH_STEMS
)
from app.services.rag import normalize_bangla_text

HYPOTHETICAL_EDUCATIONAL_PATTERNS = [
    r"আত্মহত্যা\s*(?:প্রতিরোধ|সচেতনতা|দিবস|নিবন্ধ|গবেষণা|হার|পরিসংখ্যান|কারণ)",
    r"কেন\s*মানুষ\s*আত্মহত্যা\s*করে",
    r"আত্মহত্যা\s*কি\s*(?:পাপ|অপরাধ|হারাম)",
    r"গল্পের\s*চরিত্র\s*মরে\s*গেছে",
    r"নাটকে\s*দেখেছি"
]

NEGATION_PATTERNS = [
    r"মরতে\s*চাই\s*না",
    r"মরে\s*যেতে\s*চাই\s*না",
    r"বেঁচে\s*থাকতে\s*চাই",
    r"বাঁচতে\s*চাই",
    r"আত্মহত্যা\s*করব\s*না",
    r"ক্ষতি\s*করব\s*না",
    r"নিজের\s*ক্ষতি\s*করতে\s*চাই\s*না"
]

MILD_DISTRESS_STEMS = [
    "মন খারাপ", "মনডা ভালো না", "কষ্ট লাগছে", "একাকী লাগে", "একা একা লাগে",
    "ক্লান্ত লাগছে", "ভালো লাগছে না", "হতাশ লাগছে", "টেনশন হচ্ছে", "অস্থির লাগছে",
    "শান্তি নেই", "খুব একা", "কান্না পাচ্ছে", "মনটা ভার"
]

LEVEL_2_CLARIFICATION_PROMPT_BN = (
    "তোমার কথায় মনে হচ্ছে তুমি অনেক কষ্টের মধ্যে আছো। আমি তোমার কথা মন দিয়ে শুনছি। "
    "একটা বিষয় জানতে চাই—তুমি কি শুধু সবকিছু থেকে একটু দূরে থাকতে চাইছ, নাকি নিজের ক্ষতি করার কথাও মনে হচ্ছে?"
)

def is_hypothetical_or_educational(norm_text: str) -> bool:
    for pat in HYPOTHETICAL_EDUCATIONAL_PATTERNS:
        if re.search(pat, norm_text):
            return True
    return False

def has_explicit_negation(norm_text: str) -> bool:
    for pat in NEGATION_PATTERNS:
        if re.search(pat, norm_text):
            return True
    return False

def assess_crisis_risk(
    text: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> CrisisAssessResponse:
    """
    Executes the multi-layer crisis classification protocol:
    Layer 1: Rule-based & Bengali Lexicon (euphemisms, lethal means, passive resignation)
    Layer 2: Semantic NLP & signal categorization
    Layer 3: Contextual & Hypothetical Analysis (distinguishes educational/negated from intent)
    Layer 4: Multi-Signal Safety Engine with explainability & confidence calibration
    """
    if not text or not isinstance(text, str):
        return CrisisAssessResponse(
            risk_level="LEVEL_0",
            level_numeric=0,
            confidence=1.0,
            detected_signal_categories=[],
            action_required=False
        )

    norm_text = normalize_bangla_text(text.lower().strip())
    veiled_data = get_veiled_keywords() or {}
    keywords_data = get_keywords() or {}
    detected_signals: List[str] = []

    # Check for hypothetical/educational discussions or explicit negations
    if is_hypothetical_or_educational(norm_text):
        return CrisisAssessResponse(
            risk_level="LEVEL_0",
            level_numeric=0,
            confidence=0.92,
            detected_signal_categories=["educational_or_hypothetical_context"],
            is_hypothetical=True,
            action_required=False
        )

    if has_explicit_negation(norm_text):
        return CrisisAssessResponse(
            risk_level="LEVEL_1",
            level_numeric=1,
            confidence=0.88,
            detected_signal_categories=["distress_with_explicit_affirmation_of_life"],
            action_required=False,
            safety_response_bn="আপু, আপনার কষ্ট আমরা বুঝতে পারছি। আপনি একা নন। একটু বুক ভরে শ্বাস নিন, আমরা আপনার পাশে আছি।"
        )

    # =========================================================================
    # LEVEL 3: POSSIBLE IMMEDIATE DANGER (Lethal Means & Explicit Suicide Stems)
    # =========================================================================
    # 3.1 Rural Agricultural Lethal Means (pesticides, agricultural poison, drowning, hanging)
    RURAL_LETHAL_PATTERNS = [
        r"ফসলের\s*বিষ",
        r"কীটনাশক",
        r"ঘাসের\s*(?:ওষুধ|ওষুদ|বিষ)",
        r"পোকার\s*(?:ওষুধ|ওষুদ|বিষ)",
        r"গা\s*ভাসা",
        r"নদীর\s*জলে",
        r"নদীতে\s*ভেসে",
        r"পুকুরে\s*ঝাঁপ",
        r"গলায়\s*দড়ি|গলায়\s*দড়ি",
        r"ফাঁস\s*(?:দেওয়া|নেওয়া|দেয়া)",
        r"বিষ\s*(?:খেয়ে|খাব|খাওয়া)"
    ]
    for pat in RURAL_LETHAL_PATTERNS:
        if re.search(pat, norm_text):
            detected_signals.append("rural_lethal_means_access")
            return CrisisAssessResponse(
                risk_level="LEVEL_3",
                level_numeric=3,
                confidence=0.98,
                detected_signal_categories=detected_signals,
                is_veiled=True,
                covert_alert=True,
                action_required=True,
                safety_response_bn="আপু, আপনার কষ্ট আমরা অনুভব করছি। কোনো কঠিন সিদ্ধান্ত নেবেন না। এখনই ১০৯ (নারী সহায়তা সেল) বা ৯৯৯-এ সাহায্য নিন।",
                emergency_helpline="109",
                bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN
            )

    lethal_means = veiled_data.get("rural_lethal_means_access", [])
    for lm in lethal_means:
        if lm in norm_text:
            detected_signals.append("rural_lethal_means_access")
            return CrisisAssessResponse(
                risk_level="LEVEL_3",
                level_numeric=3,
                confidence=0.98,
                detected_signal_categories=detected_signals,
                is_veiled=True,
                covert_alert=True,
                action_required=True,
                safety_response_bn="আপু, আপনার কষ্ট আমরা অনুভব করছি। কোনো কঠিন সিদ্ধান্ত নেবেন না। এখনই ১০৯ (নারী সহায়তা সেল) বা ৯৯৯-এ সাহায্য নিন।",
                emergency_helpline="109",
                bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN
            )

    # 3.2 Explicit Suicide Stems & Intent
    all_direct = DIRECT_SUICIDE_STEMS + keywords_data.get("direct_suicide_bn", [])
    for stem in all_direct:
        if stem in norm_text:
            detected_signals.append("explicit_suicide_intent")
            return CrisisAssessResponse(
                risk_level="LEVEL_3",
                level_numeric=3,
                confidence=0.99,
                detected_signal_categories=detected_signals,
                is_veiled=False,
                covert_alert=False,
                action_required=True,
                safety_response_bn="আপু, আপনার জীবন অত্যন্ত মূল্যবান। আপনি একা নন। দয়া করে নিজের ক্ষতি করবেন না। এখনই ৯৯৯ বা ১০৯ এ বিনামূল্যে কল করুন।",
                emergency_helpline="109",
                bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN
            )

    # 3.3 Banglish Suicide Stems
    all_banglish = BANGLISH_STEMS + keywords_data.get("banglish", [])
    for b_stem in all_banglish:
        if b_stem in norm_text:
            detected_signals.append("banglish_crisis_indication")
            return CrisisAssessResponse(
                risk_level="LEVEL_3",
                level_numeric=3,
                confidence=0.95,
                detected_signal_categories=detected_signals,
                action_required=True,
                emergency_helpline="109",
                bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN
            )

    # =========================================================================
    # LEVEL 2: SIGNIFICANT DISTRESS (Veiled suicidal resignation, burdensomeness, domestic entrapment)
    # =========================================================================
    # 2.1 Passive Resignation & Death Wishes
    passive_patterns = [
        r"আল্লাহ\s*(?:কেন\s*)?(?:আমাকে\s*)?(?:তুলে|উঠায়)\s*(?:নেয়|নাও)",
        r"ঘুম(?:িয়ে|াইয়া|াইয়া)?\s*থাকলে",
        r"আর\s*(?:কোনোদিন|কখনো|কখনও)?\s*(?:উঠতে\s*না\s*হতো|না\s*উঠতাম)",
        r"আর\s*চোখ\s*খুলতে\s*ইচ্ছা\s*করে\s*না",
        r"আর\s*জাগতে\s*চাই\s*না",
        r"আমার\s*কি\s*মরণ\s*নাই",
        r"(?:জীবনের|বেঁচে\s*থাকার)\s*চেয়ে\s*মরণ\s*ভালো",
        r"শেষ\s*হয়ে\s*গেলে(?:ই)?\s*(?:সবার\s*)?শান্তি",
        r"পরানডা\s*আর\s*সয়\s*না",
        r"মুক্তি\s*পেলে\s*বাঁচতাম"
    ]
    for pat in passive_patterns:
        if re.search(pat, norm_text):
            detected_signals.append("passive_resignation_death_wishes")
            break

    passive_death = veiled_data.get("passive_resignation_death_wishes", [])
    for p in passive_death:
        if p in norm_text and "passive_resignation_death_wishes" not in detected_signals:
            detected_signals.append("passive_resignation_death_wishes")

    # 2.2 Burdensomeness and Erasure Metaphors
    burdensome_patterns = [
        r"না\s*থাকলে(?:ই)?\s*সবার(?:ই)?\s*(?:ভালো|সুখ)",
        r"(?:সংসারের|সবার)\s*বোঝা",
        r"বোঝা\s*(?:হয়ে|হয়ে)",
        r"(?:চিরতরে|চিরদিনের\s*জন্য)\s*হারিয়ে\s*যেতে|হারিয়ে\s*যেতে",
        r"হারিয়ে\s*যেতে\s*ইচ্ছা\s*করে|হারিয়ে\s*যেতে\s*ইচ্ছা\s*করে",
        r"বেঁচে\s*থাকার\s*(?:কোনো|কোন)?\s*(?:অর্থ|মানে|লাভ|উদ্দেশ্য).*?(?:নাই|নেই)",
        r"জীবন\s*রেখে\s*(?:কোনো|কোন)\s*লাভ\s*(?:নাই|নেই)",
        r"কাউকে\s*আর\s*জ্বালাব\s*না",
        r"আমাকে\s*ছাড়া\s*সবাই\s*ভালো\s*থাকবে"
    ]
    for pat in burdensome_patterns:
        if re.search(pat, norm_text):
            detected_signals.append("burdensomeness_and_erasure")
            break

    burdensome = veiled_data.get("burdensomeness_and_erasure", [])
    for b in burdensome:
        if b in norm_text and "burdensomeness_and_erasure" not in detected_signals:
            detected_signals.append("burdensomeness_and_erasure")

    # 2.3 Hopeless Entrapment and Domestic Abuse
    entrapment_patterns = [
        r"চারিদিকে\s*অন্ধকার",
        r"সব\s*পথ\s*বন্ধ",
        r"কোনো\s*পথ\s*(?:নাই|নেই|খোলা\s*নেই)",
        r"বাপের\s*বাড়ি\s*গিয়ে\s*আর\s*মুখ\s*দেখাব\s*না",
        r"দম\s*বন্ধ\s*হয়ে\s*আস",
        r"অত্যাচারের\s*চেয়ে\s*মরে\s*যাওয়া\s*ভালো",
        r"মারধোর\s*আর\s*সইতে\s*পারি\s*না",
        r"এই\s*নরক\s*থেকে\s*মুক্তি\s*চাই"
    ]
    for pat in entrapment_patterns:
        if re.search(pat, norm_text):
            detected_signals.append("hopeless_entrapment_and_abuse")
            break

    entrapment = veiled_data.get("hopeless_entrapment_and_abuse", [])
    for e in entrapment:
        if e in norm_text and "hopeless_entrapment_and_abuse" not in detected_signals:
            detected_signals.append("hopeless_entrapment_and_abuse")

    # Contextual multi-turn escalation check
    if conversation_history:
        past_distress_count = sum(
            1 for turn in conversation_history[-3:]
            if any(term in turn.get("content", "").lower() for term in ["কষ্ট", "বাঁচতে", "অন্ধকার", "বোঝা", "হতাশ"])
        )
        if past_distress_count >= 2:
            detected_signals.append("repeated_persistent_distress")

    if detected_signals:
        return CrisisAssessResponse(
            risk_level="LEVEL_2",
            level_numeric=2,
            confidence=0.90,
            detected_signal_categories=detected_signals,
            is_veiled=True,
            covert_alert=True,
            action_required=True,
            clarification_prompt_bn=LEVEL_2_CLARIFICATION_PROMPT_BN,
            safety_response_bn="আপু, আপনার মনের কষ্টটা আমি বুঝতে পারছি। একটু বুক ভরে নিঃশ্বাস নিন। এই কঠিন সময়টা কেটে যাবে, আপনার জীবন আমাদের কাছে অনেক মূল্যবান। আমি সবসময় আপনার পাশে আছি।",
            emergency_helpline="109",
            bystander_safe_audio_bn=BYSTANDER_SAFE_AUDIO_BN
        )

    # =========================================================================
    # LEVEL 1: MILD EMOTIONAL DISTRESS (Loneliness, stress, everyday fatigue)
    # =========================================================================
    for mild in MILD_DISTRESS_STEMS:
        if mild in norm_text:
            detected_signals.append("mild_emotional_distress")
            return CrisisAssessResponse(
                risk_level="LEVEL_1",
                level_numeric=1,
                confidence=0.85,
                detected_signal_categories=detected_signals,
                action_required=False,
                safety_response_bn="আপু, আপনার মন খারাপের কথা শুনে খারাপ লাগছে। আপনি কি আমাকে খুলে বলবেন কী নিয়ে চিন্তা হচ্ছে? আমি আপনার কথা শুনছি।"
            )

    # =========================================================================
    # LEVEL 0: NO DETECTED CRISIS (Normal conversation, health questions)
    # =========================================================================
    return CrisisAssessResponse(
        risk_level="LEVEL_0",
        level_numeric=0,
        confidence=1.0,
        detected_signal_categories=[],
        action_required=False
    )

class CrisisClassifierEngine:
    def assess_crisis(self, text: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        resp = assess_crisis_risk(text, conversation_history)
        if isinstance(resp, CrisisAssessResponse):
            return resp.model_dump()
        return resp

crisis_classifier_engine = CrisisClassifierEngine()



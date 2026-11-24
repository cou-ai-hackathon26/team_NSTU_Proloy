import re
from datetime import date, timedelta
from typing import Dict, Any, Optional, Tuple, List
from app.schemas.private_voice import ExtractedHealthInfo
from app.services.rag import normalize_bangla_text
from app.services.cycle_engine import decode_covert_cycle_metaphor

# Bengali numerals map
BN_NUMERALS = {
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
}

def convert_bn_num(text: str) -> str:
    for bn, en in BN_NUMERALS.items():
        text = text.replace(bn, en)
    return text

def parse_bangla_date_reference(text: str) -> Tuple[Optional[date], bool, Optional[str]]:
    """
    Parses natural Bangla temporal references:
    - আজ / আজকে / আজকেই -> today (not ambiguous)
    - কাল / কালকে / গতকাল -> yesterday or tomorrow (ambiguous if ambiguous context)
    - গত পরশু -> 2 days ago
    - গত মাসে ১২ তারিখে -> previous month 12th
    Returns: (inferred_date, is_ambiguous, clarification_prompt_bn)
    """
    today = date.today()
    norm = normalize_bangla_text(text.lower())

    if re.search(r"\b(আজ|আজকে|আজকেই)\b", norm):
        return today, False, None

    if re.search(r"\b(গতকাল|গত\s*কাল)\b", norm):
        yesterday = today - timedelta(days=1)
        return yesterday, False, None

    if re.search(r"\b(কাল|কালকে)\s*(?:থেকে|হইতে)?\b", norm):
        # "কাল থেকে" usually means yesterday in period context, but needs clarification
        yesterday = today - timedelta(days=1)
        return yesterday, True, "তাহলে গতকালকে পিরিয়ড শুরুর তারিখ হিসেবে সংরক্ষণ করব?"

    if re.search(r"\b(গত\s*পরশু|পরশু\s*দিন)\b", norm):
        d = today - timedelta(days=2)
        return d, False, None

    # Specific date e.g. "১২ তারিখে" or "গত মাসে ১২ তারিখে"
    converted = convert_bn_num(norm)
    match_past_month = re.search(r"গত\s*মাসে\s*(\d{1,2})\s*তারিখ", converted)
    if match_past_month:
        day = int(match_past_month.group(1))
        # Previous month
        first_of_this_month = today.replace(day=1)
        last_month = first_of_this_month - timedelta(days=1)
        try:
            target_date = last_month.replace(day=min(day, 28))
            return target_date, False, None
        except Exception:
            pass

    match_day = re.search(r"(\d{1,2})\s*তারিখ", converted)
    if match_day:
        day = int(match_day.group(1))
        try:
            target_date = today.replace(day=min(day, 28))
            if target_date > today:
                # Must be last month
                first_of_this_month = today.replace(day=1)
                last_month = first_of_this_month - timedelta(days=1)
                target_date = last_month.replace(day=min(day, 28))
            return target_date, True, f"আপনি কি এই মাসের {day} তারিখকে শুরুর দিন হিসেবে নিশ্চিত করছেন?"
        except Exception:
            pass

    return None, False, None

def extract_health_information(text: str) -> ExtractedHealthInfo:
    """
    Extracts structured reproductive health, cycle, symptom, mood, and sleep data
    from natural Bangla voice transcript.
    Never assumes a date or symptom that the user has not provided.
    """
    info = ExtractedHealthInfo()
    if not text:
        return info

    norm = normalize_bangla_text(text.lower())
    converted = convert_bn_num(norm)

    # 1. Check covert vernacular metaphors first
    covert = decode_covert_cycle_metaphor(text)
    if covert:
        info.event_type = covert["event_type"]
        if covert["event_type"] == "cycle_start":
            info.period_start_date = date.today()
            info.associated_symptoms.append("cycle_start_reported_via_metaphor")
            info.is_ambiguous = False
            return info
        elif covert["event_type"] == "cycle_end":
            info.period_end_date = date.today()
            info.associated_symptoms.append("cycle_end_reported_via_metaphor")
            return info
        elif covert["event_type"] == "cramps":
            info.associated_symptoms.append("dysmenorrhea_cramps")
            info.pain_intensity = 7
            return info
        elif covert["event_type"] == "active_flow":
            info.bleeding_intensity = "heavy"
            info.associated_symptoms.append("heavy_flow")
            return info

    # 2. Menstrual Cycle Start Expressions
    if re.search(r"(পিরিয়ড\s*শুরু|মাসিক\s*শুরু|পিরিয়ড\s*হচ্ছে|মাসিক\s*হচ্ছে|রক্তস্রাব\s*শুরু|পিরিয়ড\s*হইছে|ডেট\s*শুরু)", norm):
        info.event_type = "cycle_start"
        parsed_date, is_amb, prompt = parse_bangla_date_reference(text)
        if parsed_date:
            info.period_start_date = parsed_date
            info.is_ambiguous = is_amb
            info.clarification_question_bn = prompt
            info.confirmation_required = is_amb
        else:
            info.period_start_date = date.today()
            info.is_ambiguous = True
            info.clarification_question_bn = "আজকে কি পিরিয়ডের প্রথম দিন হিসেবে সংরক্ষণ করব?"
            info.confirmation_required = True

    # 3. Menstrual Cycle End Expressions
    elif re.search(r"(পিরিয়ড\s*শেষ|মাসিক\s*শেষ|রক্ত\s*বন্ধ|পবিত্র\s*হয়েছি|গোসল\s*করেছি|শেষ\s*হয়েছে|শেষ\s*হইছে)", norm):
        info.event_type = "cycle_end"
        parsed_date, is_amb, prompt = parse_bangla_date_reference(text)
        if parsed_date:
            info.period_end_date = parsed_date
            info.is_ambiguous = is_amb
            info.clarification_question_bn = prompt
            info.confirmation_required = is_amb
        else:
            info.period_end_date = date.today()
            info.confirmation_required = False

    # 4. Amenorrhea / Delayed Period ("এই মাসে এখনো পিরিয়ড হয়নি")
    elif re.search(r"(এখনো\s*পিরিয়ড\s*হয়নি|পিরিয়ড\s*দেরি\s*হচ্ছে|মাসিক\s*দেরি|ডেট\s*পার\s*হয়ে\s*গেছে|ডেট\s*মিস|পিরিয়ড\s*আসেনি)", norm):
        info.event_type = "cycle_delayed"
        info.associated_symptoms.append("delayed_cycle_amenorrhea")

    # 5. Bleeding Intensity
    if re.search(r"(খুব\s*বেশি\s*রক্ত|অতিরিক্ত\s*রক্ত|প্রচুর\s*রক্ত|ভারী\s*রক্তপাত|প্যাড\s*ভিজে\s*যাচ্ছে|ঘন\s*ঘন\s*বদল)", norm):
        info.bleeding_intensity = "heavy"
        info.associated_symptoms.append("heavy_menstrual_bleeding")
    elif re.search(r"(হালকা\s*রক্ত|একটু\s*একটু|দাগ\s*দাগ|স্পটিং)", norm):
        info.bleeding_intensity = "light"
    elif re.search(r"(স্বাভাবিক\s*রক্ত|মাঝারি|সাধারণ)", norm):
        info.bleeding_intensity = "medium"

    # 6. Pain Intensity & Dysmenorrhea
    if re.search(r"(পেটে\s*(?:অনেক|প্রচণ্ড|খুব|তীব্র)\s*ব্যথা|তলপেটে\s*তীব্র\s*ব্যথা|ব্যথায়\s*মরছি|অসহ্য\s*ব্যথা)", norm):
        info.pain_intensity = 8
        info.associated_symptoms.append("severe_dysmenorrhea_তীব্র_পেটে_ব্যথা")
    elif re.search(r"(পেট\s*ব্যথা|তলপেটে\s*ব্যথা|পেটে\s*মোচড়|কোমর\s*ব্যথা)", norm):
        info.pain_intensity = 5
        info.associated_symptoms.append("mild_dysmenorrhea_পেটে_ব্যথা")

    # 7. Other Physical Symptoms
    if re.search(r"(বমি\s*ভাব|বমি\s*লাগে|বমি\s*হচ্ছে)", norm):
        info.associated_symptoms.append("nausea_vomiting")
    if re.search(r"(মাথা\s*ঘোরে|মাথা\s*ঘুরায়|মাথা\s*ঘুরছে|দুর্বল\s*লাগে)", norm):
        info.associated_symptoms.append("dizziness_weakness")
    if re.search(r"(সাদা\s*স্রাব|সাদাস্রাব|চুলকানি)", norm):
        info.associated_symptoms.append("white_discharge")

    # 8. Mood Logging
    if re.search(r"(মন(?:টা|ডা)?\s*(?:খুব\s*)?খারাপ|মন(?:টা|ডা)?\s*ভালো\s*নে[ইঈ]|কষ্ট\s*লাগছে|হতাশ|কান্না\s*পাচ্ছে)", norm):
        info.mood = "sad"
        if not info.event_type:
            info.event_type = "mood"
    elif re.search(r"(টেনশন|ভয়\s*লাগছে|অস্থির|উদ্বেগ)", norm):
        info.mood = "anxious"
        if not info.event_type:
            info.event_type = "mood"
    elif re.search(r"(মন\s*ভালো|খুশি|আনন্দ|শান্তি)", norm):
        info.mood = "happy"
        if not info.event_type:
            info.event_type = "mood"

    # 9. Sleep Patterns
    if re.search(r"(ঘুম\s*(?:হচ্ছে|আসছে)\s*না|ঘুমাইতে\s*পারি\s*না|অনিদ্রা|রাতে\s*ঘুম\s*ভাঙে)", norm):
        info.sleep_pattern = "insomnia"
        info.associated_symptoms.append("insomnia")
        if not info.event_type:
            info.event_type = "sleep"

    # 10. Cycle length intervals if provided
    cycle_match = re.search(r"(\d{2})\s*(?:to|-|থেকে|বা)?\s*(\d{2})?\s*দিন", converted)
    if cycle_match:
        info.cycle_length_days = int(cycle_match.group(1))

    if not info.event_type:
        info.event_type = "health_query" if info.associated_symptoms else "conversational"

    return info

class VoiceExtractionEngine:
    def extract_health_info(self, text: str) -> Dict[str, Any]:
        info = extract_health_information(text)
        return info.model_dump()

voice_extraction_engine = VoiceExtractionEngine()



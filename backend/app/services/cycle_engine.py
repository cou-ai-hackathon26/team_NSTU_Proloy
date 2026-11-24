from datetime import date, timedelta
from typing import List, Optional, Tuple
import statistics
from app.schemas.tracker import CycleAnalysisResponse

BN_MONTHS = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
    5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
    9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"
}

def format_bn_date(d: date, include_year: bool = True) -> str:
    m = BN_MONTHS.get(d.month, str(d.month))
    if include_year:
        return f"{d.day} {m}, {d.year}"
    return f"{d.day} {m}"

def analyze_cycles(
    periods: List[Tuple[date, Optional[date]]],
    as_of: Optional[date] = None
) -> CycleAnalysisResponse:
    """
    Analyzes historical period start dates to predict the next period,
    estimate the ovulation window, and flag irregularities.
    
    Periods must be sorted by start_date ascending.
    Each element is (start_date, end_date).
    """
    if as_of is None:
        as_of = date.today()

    n = len(periods)
    if n == 0:
        return CycleAnalysisResponse(
            cycles_recorded=0,
            explanation_bn="এখনো কোনো পিরিয়ডের তথ্য যোগ করা হয়নি। আপনার শেষ পিরিয়ডের তারিখ লিখে রাখুন।"
        )
    
    if n < 3:
        last_start = periods[-1][0]
        approx_next = last_start + timedelta(days=28)
        approx_ovul = approx_next - timedelta(days=14)
        return CycleAnalysisResponse(
            cycles_recorded=n,
            predicted_next_period_start=approx_next,
            predicted_next_period_end=approx_next + timedelta(days=4),
            ovulation_window_start=approx_ovul - timedelta(days=2),
            ovulation_window_end=approx_ovul + timedelta(days=2),
            explanation_bn=f"আপনি {n}টি পিরিয়ডের হিসাব দিয়েছেন। সঠিক পূর্বাভাস পেতে অন্তত ৩টি চক্র দরকার। সাধারণ ২৮ দিনের হিসাব অনুযায়ী সম্ভাব্য তারিখ দেখানো হলো।"
        )

    # Calculate intervals between consecutive start dates
    cycle_lengths = []
    for i in range(1, n):
        length = (periods[i][0] - periods[i - 1][0]).days
        if length > 0:
            cycle_lengths.append(length)

    if not cycle_lengths:
        return CycleAnalysisResponse(
            cycles_recorded=n,
            explanation_bn="পিরিয়ডের তারিখগুলো যাচাই করুন।"
        )

    avg_length = statistics.mean(cycle_lengths)
    std_dev = statistics.stdev(cycle_lengths) if len(cycle_lengths) > 1 else 0.0

    is_irregular = False
    warning_flag = None
    warning_notes = []

    if avg_length < 21:
        is_irregular = True
        warning_flag = "short_cycle"
        warning_notes.append("আপনার পিরিয়ড খুব ঘন ঘন হচ্ছে (২১ দিনের কম ব্যবধান)।")
    elif avg_length > 35:
        is_irregular = True
        warning_flag = "long_cycle"
        warning_notes.append("আপনার পিরিয়ড অনেক দেরিতে হচ্ছে (৩৫ দিনের বেশি ব্যবধান)।")

    if std_dev > 5.0:
        is_irregular = True
        if not warning_flag:
            warning_flag = "high_variability"
        warning_notes.append("আপনার চক্রের ব্যবধান প্রতি মাসে বেশ ওঠানামা করছে।")

    # Check for missed period (> 90 days from last period)
    days_since_last = (as_of - periods[-1][0]).days
    if days_since_last > 90:
        is_irregular = True
        warning_flag = "missed_period"
        warning_notes.append("আপনার শেষ পিরিয়ড ৯০ দিনের বেশি আগে হয়েছিল।")

    last_start = periods[-1][0]
    next_start = last_start + timedelta(days=round(avg_length))
    next_end = next_start + timedelta(days=4)

    est_ovulation = next_start - timedelta(days=14)
    ovul_start = est_ovulation - timedelta(days=2)
    ovul_end = est_ovulation + timedelta(days=2)

    explanation_parts = [
        f"আপনার গড় পিরিয়ড চক্র {round(avg_length)} দিনের।",
        f"পরবর্তী সম্ভাব্য পিরিয়ড শুরু হতে পারে {format_bn_date(next_start)} এর আশেপাশে।",
        f"সম্ভাব্য ওভুলেশন (ডিম্বস্ফোটন) এর সময় {format_bn_date(ovul_start, False)} থেকে {format_bn_date(ovul_end, False)}।"
    ]
    if warning_notes:
        explanation_parts.append(" " + " ".join(warning_notes))
        explanation_parts.append("যদি এমন নিয়মিত হতে থাকে, তবে স্বাস্থ্যকেন্দ্রে ডাক্তার দেখানো ভালো।")

    return CycleAnalysisResponse(
        cycles_recorded=n,
        average_cycle_length=round(avg_length, 1),
        std_dev=round(std_dev, 2),
        predicted_next_period_start=next_start,
        predicted_next_period_end=next_end,
        ovulation_window_start=ovul_start,
        ovulation_window_end=ovul_end,
        is_irregular=is_irregular,
        warning_flag=warning_flag,
        explanation_bn="\n".join(explanation_parts)
    )

import re

COVERT_CYCLE_METAPHORS = [
    # 1. Cycle Start (LMP)
    {
        "patterns": [
            r"লাল\s*ফুল\s*ফুটেছে",
            r"মেহমান\s*(?:আসছে|এসেছে|আইছে|আসলো)",
            r"শরীর\s*(?:খারাপ\s*হয়েছে|ভাঙছে|ভাংছে)",
            r"মাসিক\s*(?:শুরু|হয়েছে|আসছে)",
            r"লাল\s*দিন\s*শুরু",
            r"ডেট\s*শুরু\s*হয়েছে"
        ],
        "event_type": "cycle_start",
        "action": "log_period_start",
        "confirmation_bn": "আপনার মাসিকের প্রথম দিনের তথ্য সই মনে রেখেছে। আরাম করুন এবং গরম পানি খান।"
    },
    # 2. Active Bleeding / Heavy Flow
    {
        "patterns": [
            r"কাপড়\s*নষ্ট\s*(?:হয়েছে|হইছে|হচ্ছে)",
            r"অপবিত্র\s*দিন",
            r"বেশি\s*রক্ত\s*(?:যাচ্ছে|পড়ছে)",
            r"বারবার\s*কাপড়\s*বদল",
            r"ভারী\s*কাজ\s*করতে\s*পারব\s*না"
        ],
        "event_type": "active_flow",
        "action": "log_symptom_flow",
        "confirmation_bn": "আপনার তথ্য নথিভুক্ত করা হয়েছে। এই সময়ে ভারী কাজ এড়িয়ে পর্যাপ্ত বিশ্রাম নিন।"
    },
    # 3. Cycle End / Cleansing
    {
        "patterns": [
            r"শরীর\s*পবিত্র\s*হয়েছে",
            r"পবিত্র\s*হয়েছি",
            r"গোসল\s*(?:করেছি|সেরেছি|করলাম)",
            r"শরীর\s*ভালো\s*হয়ে\s*গেছে",
            r"রক্ত\s*বন্ধ\s*হয়েছে",
            r"মাসিক\s*শেষ\s*হয়েছে"
        ],
        "event_type": "cycle_end",
        "action": "log_period_end",
        "confirmation_bn": "মাসিক সম্পন্ন হওয়ার তথ্য সংরক্ষিত হয়েছে।"
    },
    # 4. Dysmenorrhea / Cramps
    {
        "patterns": [
            r"তলপেটে\s*(?:মোচড়|মোচড়\s*দিচ্ছে|চাবায়|কামড়ায়)",
            r"পেট\s*কামড়ায়",
            r"তলপেট\s*চাবায়",
            r"কোমরে\s*(?:টান|ব্যথা)",
            r"তলপেটে\s*খুব\s*ব্যথা"
        ],
        "event_type": "cramps",
        "action": "log_symptom_cramps",
        "confirmation_bn": "পেটের ব্যথার কথা বুঝতে পেরেছি। তলপেটে গরম সেঁক দিন এবং আদা চা খেতে পারেন।"
    }
]

def decode_covert_cycle_metaphor(text: str) -> Optional[dict]:
    """
    Decodes covert rural Bengali metaphors into structured reproductive health cycle events,
    allowing women on shared devices to log cycles without speaking explicit clinical words aloud.
    """
    if not text:
        return None
    norm_text = text.strip().lower()
    for entry in COVERT_CYCLE_METAPHORS:
        for pat in entry["patterns"]:
            if re.search(pat, norm_text):
                return {
                    "event_type": entry["event_type"],
                    "action": entry["action"],
                    "confirmation_bn": entry["confirmation_bn"],
                    "matched_pattern": pat
                }
    return None

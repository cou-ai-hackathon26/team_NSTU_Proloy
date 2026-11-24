from datetime import date, timedelta
from typing import Dict, Any, List
from app.schemas.pregnancy import PregnancyStatusResponse, WeekMilestone

# Comprehensive, medically reviewed week-by-week milestones (Bangla)
# Incorporating WHO and Bangladesh DGHS Maternal Health Guidelines
WEEKLY_DATA: Dict[int, Dict[str, Any]] = {
    4: {
        "trimester": 1,
        "baby_size_bn": "পোস্তদানার মতো ছোট্ট",
        "development_summary_bn": "ভ্রূণ জরায়ুতে প্রতিস্থাপিত হয়েছে এবং প্রাথমিক গঠন শুরু হয়েছে।",
        "maternal_changes_bn": "পিরিয়ড মিস হওয়া, হালকা বমি বমি ভাব বা স্তনে সামান্য স্পর্শকাতরতা লাগতে পারে।",
        "nutrition_advice_bn": ["দৈনিক ফলিক এসিড বড়ি খাওয়া শুরু করুন।", "পর্যাপ্ত পানি ও শাকসবজি খান।"],
        "anc_recommended": True,
        "anc_visit_title_bn": "প্রথম চেকআপ (গর্ভধারণ নিশ্চিত ও প্রাথমিক পরীক্ষা)",
        "urgent_warning_signs_bn": ["যোনিপথে রক্তপাত বা ফোঁটা ফোঁটা রক্ত", "তীব্র তলপেটে ব্যথা"]
    },
    8: {
        "trimester": 1,
        "baby_size_bn": "একটি মিষ্টি আঙুরের সমান (দেড় সেমি)",
        "development_summary_bn": "শিশুর হাত, পা এবং হৃৎস্পন্দন তৈরি হয়েছে। মুখমণ্ডলের আকৃতি তৈরি হচ্ছে।",
        "maternal_changes_bn": "সকালের দিকে ক্লান্তি, বমি ভাব (মর্নিং সিকনেস) এবং বারবার প্রস্রাবের চাপ হতে পারে।",
        "nutrition_advice_bn": ["অল্প অল্প করে বারবার হালকা খাবার খান।", "ভাজাপোড়া ও অতিরিক্ত মসলাদার খাবার এড়িয়ে চলুন।"],
        "anc_recommended": False,
        "anc_visit_title_bn": None,
        "urgent_warning_signs_bn": ["অনবরত বমি হয়ে পানি শূন্যতা", "তীব্র পেটব্যথা বা রক্তপাত"]
    },
    12: {
        "trimester": 1,
        "baby_size_bn": "একটি ছোট লেবুর সমান (প্রায় ৫-৬ সেমি)",
        "development_summary_bn": "শিশুর সব প্রধান অঙ্গপ্রত্যঙ্গ তৈরি হয়ে গেছে। নখ ও সূক্ষ্ম হাড় গঠিত হচ্ছে।",
        "maternal_changes_bn": "প্রথম তিন মাসের বমি ভাব আস্তে আস্তে কমে আসতে পারে, পেটের আকার সামান্য দৃশ্যমান হতে পারে।",
        "nutrition_advice_bn": ["আয়রন ও ক্যালসিয়ামযুক্ত খাবার (যেমন: কচুশাক, ছোট মাছ, ডিম, দুধ) খান।"],
        "anc_recommended": True,
        "anc_visit_title_bn": "প্রথম ত্রৈমাসিক আল্ট্রাসাউন্ড ও রক্তচাপ পরিমাপ",
        "urgent_warning_signs_bn": ["রক্তক্ষরণ", "তীব্র মাথাব্যথা বা দৃষ্টি ঝাপসা লাগা"]
    },
    16: {
        "trimester": 2,
        "baby_size_bn": "একটি আপেলের সমান (প্রায় ১১ সেমি)",
        "development_summary_bn": "শিশু ভেতরে নড়াচড়া করতে পারে এবং চোখের পাতা নড়াতে পারে।",
        "maternal_changes_bn": "শক্তি ফিরে পাওয়া, ত্বক উজ্জ্বল হওয়া এবং পেটের আকার বৃদ্ধি পাওয়া।",
        "nutrition_advice_bn": ["ডাক্তারের পরামর্শ অনুযায়ী নিয়মিত আয়রন-ফলিক এসিড ও ক্যালসিয়াম ট্যাবলেট খান।"],
        "anc_recommended": False,
        "anc_visit_title_bn": None,
        "urgent_warning_signs_bn": ["পানি ভাঙা (অ্যামনিওটিক ফ্লুইড বের হওয়া)", "জ্বর বা প্রস্রাবে তীব্র জ্বালাপোড়া"]
    },
    20: {
        "trimester": 2,
        "baby_size_bn": "একটি কলার সমান (প্রায় ১৬ সেমি)",
        "development_summary_bn": "গর্ভকালের অর্ধেক সময় পার হয়েছে! শিশুর শ্রবণশক্তি তৈরি হয়েছে এবং নড়াচড়া মা অনুভব করতে পারেন (কুইকেনিং)।",
        "maternal_changes_bn": "পেটে শিশুর মৃদু লাথি বা নড়াচড়া টের পাওয়া যায়। হালকা পিঠে ব্যথা হতে পারে।",
        "nutrition_advice_bn": ["প্রোটিনসমৃদ্ধ খাবার (ডাল, ডিম, মাছ, মুরগি) পর্যাপ্ত পরিমাণে খান।"],
        "anc_recommended": True,
        "anc_visit_title_bn": "দ্বিতীয় অ্যান্টিনেটাল চেকআপ (ANC 2 - গর্ভকালীন পরীক্ষা ও অ্যানোমালি স্ক্যান)",
        "urgent_warning_signs_bn": ["শিশুর নড়াচড়া একেবারেই না বোঝা", "যোনিপথে পানি বা রক্ত বের হওয়া"]
    },
    28: {
        "trimester": 3,
        "baby_size_bn": "একটি বড় বেগুনের সমান (প্রায় ৩৫ সেমি, ১ কেজির বেশি)",
        "development_summary_bn": "শিশু চোখ মেলতে পারে এবং আলোর প্রতি সংবেদনশীল। মস্তিষ্কের দ্রুত বিকাশ হচ্ছে।",
        "maternal_changes_bn": "পা ফোলা, পিঠে টান লাগা ও শ্বাস নিতে সামান্য ভারী লাগতে পারে।",
        "nutrition_advice_bn": ["লবণ কম খান যাতে পা না ফোলে। দিনে অন্তত ৮-১০ গ্লাস বিশুদ্ধ পানি পান করুন।"],
        "anc_recommended": True,
        "anc_visit_title_bn": "তৃতীয় অ্যান্টিনেটাল চেকআপ (ANC 3 - রক্তস্বল্পতা ও উচ্চ রক্তচাপ পরীক্ষা)",
        "urgent_warning_signs_bn": ["হাত-পা-মুখ হঠাৎ অস্বাভাবিক ফুলে যাওয়া", "তীব্র মাথাব্যথা", "চোখে ঝাপসা দেখা (এক্লাম্পসিয়া লক্ষণ)"]
    },
    36: {
        "trimester": 3,
        "baby_size_bn": "একটি বড় পেঁপে বা তরমুজের সমান (প্রায় ৪৭ সেমি, ২.৫ কেজি)",
        "development_summary_bn": "শিশুর ফুসফুস প্রায় পুরোপুরি প্রস্তুত। শিশু জন্মের জন্য মাথা নিচের দিকে ঘোরাতে পারে।",
        "maternal_changes_bn": "ঘন ঘন প্রস্রাবের চাপ, পেট শক্ত হয়ে যাওয়া (ব্র্যাক্সটন হিকস সংকোচন)।",
        "nutrition_advice_bn": ["সহজপাচ্য খাবার খান। প্রসবের জন্য মানসিক ও পারিপার্শ্বিক প্রস্তুতি নিন।"],
        "anc_recommended": True,
        "anc_visit_title_bn": "চতুর্থ অ্যান্টিনেটাল চেকআপ (ANC 4 - প্রসবের প্রস্তুতি ও অবস্থান নির্ধারণ)",
        "urgent_warning_signs_bn": ["নিয়মিত বিরতিতে তীব্র প্রসব ব্যথা", "পানি ভেঙে যাওয়া", "রক্তক্ষরণ", "শিশুর নড়াচড়া কমে যাওয়া"]
    }
}

def calculate_edd(lmp: date) -> date:
    """Calculates Estimated Due Date using Naegele's rule (LMP + 280 days)."""
    return lmp + timedelta(days=280)

def get_pregnancy_status(lmp: date, as_of: date = None) -> PregnancyStatusResponse:
    """Calculates gestational age, trimester, and weekly milestone."""
    if as_of is None:
        as_of = date.today()
    
    edd = calculate_edd(lmp)
    total_days = (as_of - lmp).days
    total_days = max(0, min(total_days, 300))  # Clamp to reasonable bounds
    
    weeks = total_days // 7
    days = total_days % 7

    if weeks <= 12:
        trimester = 1
    elif weeks <= 27:
        trimester = 2
    else:
        trimester = 3

    # Find the closest matching milestone
    milestone_week = 4
    for w in sorted(WEEKLY_DATA.keys()):
        if weeks >= w:
            milestone_week = w
        else:
            break
            
    m_info = WEEKLY_DATA[milestone_week]

    milestone = WeekMilestone(
        week=weeks if weeks > 0 else 1,
        trimester=trimester,
        baby_size_bn=m_info["baby_size_bn"],
        development_summary_bn=m_info["development_summary_bn"],
        maternal_changes_bn=m_info["maternal_changes_bn"],
        nutrition_advice_bn=m_info["nutrition_advice_bn"],
        anc_recommended=m_info["anc_recommended"],
        anc_visit_title_bn=m_info["anc_visit_title_bn"],
        urgent_warning_signs_bn=m_info["urgent_warning_signs_bn"]
    )

    return PregnancyStatusResponse(
        lmp_date=lmp,
        edd=edd,
        gestational_weeks=weeks,
        gestational_days=days,
        current_trimester=trimester,
        current_milestone=milestone
    )

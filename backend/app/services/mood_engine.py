from datetime import date, timedelta
from typing import List, Optional, Tuple
import statistics
from app.schemas.tracker import MoodAnalysisResponse

def analyze_moods(
    mood_logs: List[Tuple[date, int]],
    last_period_start: Optional[date] = None,
    predicted_next_period_start: Optional[date] = None,
    as_of: Optional[date] = None
) -> MoodAnalysisResponse:
    """
    Computes 7-day and 30-day mood averages, trends, and cycle-phase correlation.
    mood_logs is a list of (date, score) sorted by date ascending.
    Score is 1 to 5.
    """
    if not mood_logs:
        return MoodAnalysisResponse(
            trend_direction="unknown",
            gentle_suggestion_bn="আজ আপনার মন কেমন? মনের ভাব জানাতে নিয়মিত লগ করুন।"
        )

    today = as_of or date.today()
    seven_days_ago = today - timedelta(days=7)
    thirty_days_ago = today - timedelta(days=30)

    scores_7d = [score for d, score in mood_logs if d >= seven_days_ago]
    scores_30d = [score for d, score in mood_logs if d >= thirty_days_ago]

    avg_7d = statistics.mean(scores_7d) if scores_7d else None
    avg_30d = statistics.mean(scores_30d) if scores_30d else None

    # Trend calculation
    trend_direction = "stable"
    if avg_7d is not None and avg_30d is not None:
        diff = avg_7d - avg_30d
        if diff > 0.4:
            trend_direction = "improving"
        elif diff < -0.4:
            trend_direction = "declining"
        else:
            trend_direction = "stable"
    elif len(mood_logs) >= 2:
        diff = mood_logs[-1][1] - mood_logs[0][1]
        if diff > 0:
            trend_direction = "improving"
        elif diff < 0:
            trend_direction = "declining"

    # Check for consecutive low mood days (e.g., <= 2 for 3 or more recent logs)
    consecutive_low_count = 0
    for _, score in reversed(mood_logs[-5:]):
        if score <= 2:
            consecutive_low_count += 1
        else:
            break

    # Phase correlation check (Luteal phase / PMS dip: 1-7 days before expected period)
    phase_correlation = None
    if predicted_next_period_start:
        days_to_period = (predicted_next_period_start - today).days
        if 0 <= days_to_period <= 7:
            if avg_7d and avg_7d < 3.0:
                phase_correlation = "পিরিয়ড শুরু হওয়ার কয়েকদিন আগে হরমোনের পরিবর্তনের কারণে মেজাজ খিটখিটে বা মন খারাপ হওয়া খুব স্বাভাবিক (পিএমএস)।"
            else:
                phase_correlation = "আপনার পরবর্তী পিরিয়ড কাছাকাছি সময়ে। এই সময়ে শরীর ও মনের যত্ন নিন।"

    # Construct gentle suggestion (gentle, warm, non-judgmental)
    if consecutive_low_count >= 3:
        gentle_suggestion = (
            "কয়েকদিন ধরে আপনার মন ভালো নেই মনে হচ্ছে। মন খারাপ চেপে রাখবেন না। "
            "আপনার কোনো আপনজন বা বিশ্বস্ত মানুষের সাথে কথা বলুন বা মনের কথা ভাগ করে নিলে শান্তি লাগতে পারে। আমরা সব সময় আপনার পাশে আছি।"
        )
    elif trend_direction == "improving":
        gentle_suggestion = "আপনার মেজাজ আগের চেয়ে ভালো দেখা যাচ্ছে! নিজের এই সুন্দর সময়টিকে উপভোগ করুন।"
    elif trend_direction == "declining":
        gentle_suggestion = "সাম্প্রতিক দিনগুলোতে একটু চাপ যাচ্ছে বলে মনে হচ্ছে। পর্যাপ্ত ঘুম ও হালকা বিশ্রাম নিন।"
    else:
        gentle_suggestion = "আপনার মনের যত্ন নিতে প্রতিদিন একটু নিজের পছন্দমতো কিছু সময় কাটান।"

    return MoodAnalysisResponse(
        seven_day_avg=round(avg_7d, 2) if avg_7d is not None else None,
        thirty_day_avg=round(avg_30d, 2) if avg_30d is not None else None,
        trend_direction=trend_direction,
        phase_correlation_bn=phase_correlation,
        gentle_suggestion_bn=gentle_suggestion
    )

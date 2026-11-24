from datetime import date, timedelta
from app.services.mood_engine import analyze_moods

def test_empty_mood():
    res = analyze_moods([])
    assert res.trend_direction == "unknown"

def test_consecutive_low_mood_triggers_gentle_suggestion():
    today = date.today()
    logs = [
        (today - timedelta(days=3), 2),
        (today - timedelta(days=2), 1),
        (today - timedelta(days=1), 2),
        (today, 2)
    ]
    res = analyze_moods(logs)
    assert "মন ভালো নেই" in res.gentle_suggestion_bn
    assert "কথা বলুন" in res.gentle_suggestion_bn

def test_pms_phase_correlation():
    today = date.today()
    period_in_3_days = today + timedelta(days=3)
    logs = [
        (today - timedelta(days=2), 2),
        (today - timedelta(days=1), 2),
        (today, 2)
    ]
    res = analyze_moods(logs, predicted_next_period_start=period_in_3_days)
    assert res.phase_correlation_bn is not None
    assert "হরমোনের পরিবর্তন" in res.phase_correlation_bn or "পিএমএস" in res.phase_correlation_bn

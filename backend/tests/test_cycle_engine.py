from datetime import date, timedelta
from app.services.cycle_engine import analyze_cycles

def test_empty_cycles():
    res = analyze_cycles([])
    assert res.cycles_recorded == 0
    assert "কোনো পিরিয়ডের তথ্য" in res.explanation_bn

def test_few_cycles():
    today = date(2026, 3, 1)
    periods = [(today - timedelta(days=28), None), (today, None)]
    res = analyze_cycles(periods, as_of=today)
    assert res.cycles_recorded == 2
    assert "সঠিক পূর্বাভাস পেতে অন্তত ৩টি চক্র দরকার" in res.explanation_bn

def test_regular_cycles():
    d1 = date(2026, 1, 1)
    d2 = date(2026, 1, 29)  # 28 days
    d3 = date(2026, 2, 26)  # 28 days
    # As of d3 + 5 days
    res = analyze_cycles([(d1, None), (d2, None), (d3, None)], as_of=date(2026, 3, 3))
    assert res.cycles_recorded == 3
    assert res.average_cycle_length == 28.0
    assert res.is_irregular is False
    assert res.predicted_next_period_start == date(2026, 3, 26)

def test_irregular_long_cycle():
    d1 = date(2026, 1, 1)
    d2 = date(2026, 2, 10)  # 40 days
    d3 = date(2026, 3, 25)  # 43 days
    res = analyze_cycles([(d1, None), (d2, None), (d3, None)], as_of=date(2026, 4, 1))
    assert res.is_irregular is True
    assert res.warning_flag in ["long_cycle", "high_variability"]
    assert "৩৫ দিনের বেশি" in res.explanation_bn or "ওঠানামা" in res.explanation_bn

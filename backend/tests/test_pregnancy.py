from datetime import date, timedelta
from app.services.pregnancy_engine import get_pregnancy_status, calculate_edd

def test_naegele_rule_edd():
    lmp = date(2026, 1, 1)
    edd = calculate_edd(lmp)
    assert edd == lmp + timedelta(days=280)

def test_pregnancy_milestone_and_danger_signs():
    today = date(2026, 5, 21)
    lmp = today - timedelta(weeks=12)  # 12 weeks pregnant
    status = get_pregnancy_status(lmp, as_of=today)
    assert status.gestational_weeks == 12
    assert status.current_trimester == 1
    assert "লেবু" in status.current_milestone.baby_size_bn
    assert len(status.current_milestone.urgent_warning_signs_bn) > 0
    assert "জরুরি সতর্কতা" in status.disclaimer_bn

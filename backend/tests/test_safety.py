from app.services.crisis_detector import detect_crisis

def test_direct_crisis_triggers_emergency():
    # Bangla direct self-harm phrases
    res1 = detect_crisis("আমার আর বেঁচে থাকার ইচ্ছা নেই")
    assert res1.risk_level == "high"
    assert res1.action_required is True
    assert res1.emergency_payload is not None
    assert res1.emergency_payload.helpline_number == "999"

    res2 = detect_crisis("আমি আত্মহত্যা করতে চাই")
    assert res2.risk_level == "high"
    assert res2.emergency_payload.is_emergency is True

def test_banglish_crisis_detection():
    res = detect_crisis("ami bish khabo jibon sesh kore debo")
    assert res.risk_level == "high"

def test_safe_menstrual_query_has_no_risk():
    res = detect_crisis("পিরিয়ডের সময় পেটে ব্যথা হলে কি গরম পানির সেঁক দেওয়া যাবে?")
    assert res.risk_level == "none"
    assert res.action_required is False

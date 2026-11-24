import pytest
from app.services.emotional_intelligence import analyze_female_emotion, build_emotional_comfort_response
from app.services.crisis_detector import detect_crisis
from app.services.llm import llm_service

@pytest.mark.asyncio
async def test_in_laws_family_comfort():
    msg = "আমার শাশুড়ি আমাকে দিনরাত খোঁটা দেয়, সংসারে আমার কোনো শান্তি নেই"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "IN_LAWS_FAMILY"
    assert "শ্বশুরবাড়ি" in ctx["category_name"]
    resp = await llm_service.generate_response(msg)
    assert "পারুল" in resp.reply
    assert "আত্মসম্মান" in resp.reply

@pytest.mark.asyncio
async def test_infertility_comfort():
    msg = "বিয়ের ৬ বছর পরও বাচ্চা হচ্ছে না বলে সবাই আমাকে অপয়া বলে"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "INFERTILITY_PREGNANCY"
    resp = await llm_service.generate_response(msg)
    assert "রহিমা" in resp.reply
    assert "অপয়া" in resp.reply

@pytest.mark.asyncio
async def test_pms_hormonal_comfort():
    msg = "মাসিকের আগে কেন আমার এত অকারণ কান্না পায় আর মেজাজ খিটখিটে থাকে?"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "PMS_HORMONAL"
    resp = await llm_service.generate_response(msg)
    assert "পিএমএস" in resp.reply or "PMS" in resp.reply or "হরমোন" in resp.reply

@pytest.mark.asyncio
async def test_postpartum_depression():
    msg = "বাচ্চা হওয়ার পর আমার ভালো লাগে না, নিজেকে খুব খারাপ মা মনে হয়"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "POSTPARTUM_DEPRESSION"
    resp = await llm_service.generate_response(msg)
    assert "মোমবাতি" in resp.reply or "মা হওয়া" in resp.reply

@pytest.mark.asyncio
async def test_heartbreak_betrayal():
    msg = "আমার স্বামী পরকীয়া করে আমাকে ধোঁকা দিয়েছে, আমার মন ভেঙে গেছে"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "HEARTBREAK_BETRAYAL"
    resp = await llm_service.generate_response(msg)
    assert "পদ্মফুল" in resp.reply

@pytest.mark.asyncio
async def test_body_shaming():
    msg = "আমি কালো বলে সবাই আমাকে কুৎসিত বলে, আমার কোনো রূপ নেই"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "BODY_SHAMING"
    resp = await llm_service.generate_response(msg)
    assert "চাঁদ" in resp.reply or "সৌন্দর্য" in resp.reply

@pytest.mark.asyncio
async def test_daughter_child_discrimination():
    msg = "মেয়ে হয়েছে বলে শাশুড়ি আমাকে খোঁটা দিচ্ছে আর কথা বলে না"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "DAUGHTER_CHILD_DISCRIMINATION"
    resp = await llm_service.generate_response(msg)
    assert "সুফিয়া" in resp.reply
    assert "ক্রোমোজোম" in resp.reply

@pytest.mark.asyncio
async def test_financial_dependency_crushed_dreams():
    msg = "বিয়ের পর আমার পড়াশোনা বন্ধ করে দিয়েছে আমার স্বপ্ন সব শেষ"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "FINANCIAL_DEPENDENCY_CRUSHED_DREAMS"
    resp = await llm_service.generate_response(msg)
    assert "রুমানা" in resp.reply

@pytest.mark.asyncio
async def test_domestic_abuse_neglect():
    msg = "আমার স্বামী আমার গায়ে হাত তোলে আর গালি দেয়"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "DOMESTIC_ABUSE_NEGLECT"
    resp = await llm_service.generate_response(msg)
    assert "১০৯" in resp.reply or "নির্যাতন" in resp.reply

@pytest.mark.asyncio
async def test_arranged_marriage_trauma():
    msg = "পাত্রপক্ষ বারবার এসে আমাকে গায়ের রঙের জন্য ফিরিয়ে দেয়"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "ARRANGED_MARRIAGE_TRAUMA"
    resp = await llm_service.generate_response(msg)
    assert "শাম্মী" in resp.reply

@pytest.mark.asyncio
async def test_menopause_depression():
    msg = "বয়স ৪৫ পার হয়েছে মাসিক বন্ধ হয়ে মেজাজ খুব খারাপ থাকে হট ফ্ল্যাশ হয়"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "MENOPAUSE_DEPRESSION"
    resp = await llm_service.generate_response(msg)
    assert "মেনোপজ" in resp.reply

@pytest.mark.asyncio
async def test_guilt_burnout():
    msg = "সবার কাজ করতে করতে আমি শেষ নিজের জন্য কোনো সময় নেই"
    ctx = analyze_female_emotion(msg)
    assert ctx is not None
    assert ctx["cause_key"] == "GUILT_BURNOUT"
    resp = await llm_service.generate_response(msg)
    assert "প্রদীপ" in resp.reply or "ক্লান্তি" in resp.reply

@pytest.mark.asyncio
async def test_direct_emergency_call_payload():
    msg = "আমি বিষ খাব আর বেঁচে থাকার ইচ্ছা নেই"
    c_res = detect_crisis(msg)
    assert c_res.risk_level == "high"
    assert c_res.emergency_payload is not None
    assert c_res.emergency_payload.helpline_number == "999"

    resp = await llm_service.generate_response(msg)
    assert resp.risk_level == "high"
    assert "৯৯৯" in resp.reply
    assert resp.emergency_payload is not None
    assert resp.emergency_payload.helpline_number == "999"
    assert resp.emergency_payload.mental_health_helpline == "109"

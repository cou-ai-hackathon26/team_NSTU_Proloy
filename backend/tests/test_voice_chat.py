import pytest
from app.services.session_memory import SessionMemory, session_memory
from app.services.chitchat import get_chitchat_response, is_medical_query
from app.services.tts import normalize_bangla_speech_text
from app.services.llm import llm_service
from app.schemas.chat import ChatMessage
from fastapi.testclient import TestClient
from app.main import app

def test_session_memory_flow():
    mem = SessionMemory(max_turns=3, ttl_seconds=10)
    sid = "test_sess_01"
    
    assert mem.get_history(sid) == []
    
    mem.add_turn(sid, "আমার তলপেটে ব্যথা", "মাসিকের সময় এমন হতে পারে")
    hist = mem.get_history(sid)
    assert len(hist) == 2
    assert hist[0].role == "user"
    assert hist[0].content == "আমার তলপেটে ব্যথা"
    assert hist[1].role == "assistant"
    assert "মাসিক" in hist[1].content

    # Add multiple turns up to max_turns
    mem.add_turn(sid, "আর কি করব?", "গরম পানির সেঁক নিন")
    mem.add_turn(sid, "কতক্ষণ সেঁক দেব?", "১০ থেকে ১৫ মিনিট")
    mem.add_turn(sid, "ধন্যবাদ সই", "আপনাকেও ধন্যবাদ")
    
    hist = mem.get_history(sid)
    # 3 turns * 2 = 6 messages max
    assert len(hist) == 6
    assert hist[-1].content == "আপনাকেও ধন্যবাদ"

def test_expanded_voice_intents():
    # Cooking / Food
    r1 = get_chitchat_response("আজ কি রান্না করব বলো তো?")
    assert r1 is not None
    assert "ডিম" in r1[0] or "শাক" in r1[0] or "খিচুড়ি" in r1[0] or "ডাল" in r1[0]

    # Sleep / Insomnia
    r2 = get_chitchat_response("আমার রাতে ঘুম আসে না কি করব?")
    assert r2 is not None
    assert "ঘুম" in r2[0] or "পানি" in r2[0] or "শ্বাস" in r2[0]

    # Studies / Exam
    r3 = get_chitchat_response("সামনে পরীক্ষা অনেক ভয় লাগছে")
    assert r3 is not None
    assert "পরীক্ষা" in r3[0] or "পড়াশোনা" in r3[0] or "আস্থা" in r3[0] or "পড়েছ" in r3[0]

    # Anger / Fight
    r4 = get_chitchat_response("আমার খুব রাগ হচ্ছে মেজাজ গরম")
    assert r4 is not None
    assert "পানি" in r4[0] or "রাগ" in r4[0] or "শ্বাস" in r4[0]

    # Baby care
    r5 = get_chitchat_response("বাচ্চা খুব কান্না করছে শান্ত হচ্ছে না")
    assert r5 is not None
    assert "বাচ্চা" in r5[0] or "কোলে" in r5[0]

    # Hair / Skin
    r6 = get_chitchat_response("আমার চুল খুব পড়ছে রূপচর্চার টিপস দাও")
    assert r6 is not None
    assert "চুল" in r6[0] or "তেল" in r6[0] or "পানি" in r6[0]

    # Weakness
    r7 = get_chitchat_response("খুব দুর্বল লাগে মাথা ঘোরে")
    assert r7 is not None
    assert "পানি" in r7[0] or "স্যালাইন" in r7[0] or "দুর্বল" in r7[0] or "মাথা" in r7[0]

    # Prayer / Gratitude
    r8 = get_chitchat_response("আমার জন্য একটু দোয়া করো মন শান্ত হয় যেন")
    assert r8 is not None
    assert "আল্লাহ" in r8[0] or "শান্তি" in r8[0] or "দোয়া" in r8[0] or "প্রার্থনা" in r8[0]

    # Panic / Fast heartbeat
    r9 = get_chitchat_response("আমার বুক ধড়ফড় করছে খুব ভয় লাগছে")
    assert r9 is not None
    assert "ভয়" in r9[0] or "শ্বাস" in r9[0] or "শান্ত" in r9[0]

    # Affection
    r10 = get_chitchat_response("তুমি অনেক মিষ্টি তোমার সাথে কথা বলে ভালো লাগে")
    assert r10 is not None
    assert "আপু" in r10[0]

def test_everyday_conversational_natural_talk():
    # Backchannel & attentive listening
    r1 = get_chitchat_response("হুম")
    assert r1 is not None
    assert "শুনছি" in r1[0] or "বলো" in r1[0]

    r2 = get_chitchat_response("আচ্ছা")
    assert r2 is not None
    assert "আপু" in r2[0]

    # Routine small talk
    r3 = get_chitchat_response("কী করছো এখন?")
    assert r3 is not None
    assert "ফ্রি" in r3[0] or "সময়" in r3[0] or "দিন" in r3[0]

    # Birthday & celebration
    r4 = get_chitchat_response("আজ আমার জন্মদিন")
    assert r4 is not None
    assert "জন্মদিন" in r4[0] or "শুভকামনা" in r4[0]

    # Household chores & body tiredness (not period cramps)
    r5 = get_chitchat_response("আজ অনেক কাজ করেছি শরীর ব্যথা")
    assert r5 is not None
    assert "বিশ্রাম" in r5[0] or "ক্লান্তি" in r5[0] or "খাটুনি" in r5[0] or "পরিশ্রম" in r5[0] or "জিরিয়ে" in r5[0]

    # Gas & Indigestion
    r6 = get_chitchat_response("পেটে গ্যাস হয়েছে পেট ফাঁপা")
    assert r6 is not None
    assert "পানি" in r6[0] or "গ্যাস" in r6[0] or "আরাম" in r6[0]

    # Short voice dismissal
    r7 = get_chitchat_response("না কিছু না")
    assert r7 is not None
    assert "আপু" in r7[0]

    # Fitness & Weight
    r8 = get_chitchat_response("মোটা হয়ে যাচ্ছি ওজন কমাতে চাই")
    assert r8 is not None
    assert "ওজন" in r8[0] or "হাঁটাহাঁটি" in r8[0] or "সুস্থ" in r8[0] or "শরীরের" in r8[0] or "ডায়েট" in r8[0]

def test_tts_normalization_and_micropauses():
    text = "আপু শোনো, জরুরি সেবায় ৯৯৯ কল করো। প্রেসার ও diaper চেক করো।"
    norm = normalize_bangla_speech_text(text)
    # Check vocative comma inserted
    assert "আপু," in norm or "শোনো," in norm
    # Check 999 expanded
    assert "নয় নয় নয়" in norm
    assert "ডায়াপার" in norm

@pytest.mark.asyncio
async def test_multi_turn_llm_resolution():
    history = [
        ChatMessage(role="user", content="মাসিকের সময় তীব্র পেটে ব্যথা হয়"),
        ChatMessage(role="assistant", content="এটি ডিসমেনোরিয়া হতে পারে, গরম পানির সেঁক নেওয়া ভালো।")
    ]
    # Follow-up short question
    resp = await llm_service.generate_response(message="আর কি করব?", history=history)
    assert resp is not None
    assert len(resp.reply) > 10

def test_voice_api_with_session():
    client = TestClient(app)
    response = client.post("/voice", json={"direct_transcript": "হ্যালো সই কেমন আছো?"})
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] is not None
    assert "সই" in data["reply_text"] or "ভালো" in data["reply_text"]
    assert data["audio_base64"] is not None
    assert len(data.get("suggestions", [])) >= 1
    assert data.get("turn_count", 0) >= 1

def test_long_horizon_session_context():
    mem = SessionMemory(max_turns=15, ttl_seconds=86400)
    sid = "long_horizon_user_42"
    
    mem.add_turn(sid, "আমার মাসিকের সময় তলপেট অনেক ব্যথা করে", "গরম পানির সেঁক নিন")
    ctx = mem.get_session_context(sid)
    assert ctx["turn_count"] == 1
    assert ctx["last_topic"] == "menstrual_pain"
    assert "ব্যথা" in ctx["recent_symptoms"]
    assert len(mem.get_history(sid)) == 2

def test_colloquial_dialect_normalization():
    from app.services.rag import normalize_bangla_text
    raw1 = "আমার তলপেট খুব চাবায় আর কামড়ায়"
    norm1 = normalize_bangla_text(raw1)
    assert "ব্যথা" in norm1

    raw2 = "গা মেজমেজ করে আর জর জর লাগে"
    norm2 = normalize_bangla_text(raw2)
    assert "দুর্বলতা" in norm2 or "জ্বর" in norm2

@pytest.mark.asyncio
async def test_regional_dialects_and_banglish_voice_chat():
    # Regional Dialects
    r1 = await llm_service.generate_response("কী করতাছো?")
    assert "ফ্রি" in r1.reply or "বলো" in r1.reply or "দিন" in r1.reply or "বলতে" in r1.reply or "আছি" in r1.reply

    r2 = await llm_service.generate_response("কেমুন আছো?")
    assert "ভালো" in r2.reply or "আছি" in r2.reply

    r3 = await llm_service.generate_response("মনডা ভালো না")
    assert "খারাপ" in r3.reply or "বিশ্রাম" in r3.reply or "মন" in r3.reply

    r4 = await llm_service.generate_response("ভালা আছো নি?")
    assert "ভালো" in r4.reply or "আছি" in r4.reply

    # Banglish Talk
    r5 = await llm_service.generate_response("kemon acho")
    assert "ভালো" in r5.reply or "আছি" in r5.reply

    r6 = await llm_service.generate_response("bored lagche")
    assert "খারাপ" in r6.reply or "বোরিং" in r6.reply or "মন" in r6.reply

    # Personal curiosity & everyday wellness
    r7 = await llm_service.generate_response("তোমার প্রিয় ফুল কি?")
    assert "ফুল" in r7.reply or "বেলি" in r7.reply

    r8 = await llm_service.generate_response("সর্দি লেগেছে নাক বন্ধ")
    assert "গরম" in r8.reply or "চা" in r8.reply or "লবণ" in r8.reply

@pytest.mark.asyncio
async def test_detailed_pcos_knowledge_and_qa():
    # 1. Pregnancy & Fertility in PCOS
    p1 = await llm_service.generate_response("পিসিওএস হলে কি বাচ্চা বা সন্তান হওয়া সম্ভব?")
    assert "গর্ভধারণ" in p1.reply or "ওভুলেশন" in p1.reply or "সন্তান" in p1.reply or "বাচ্চা" in p1.reply
    assert len(p1.citations) > 0

    # 2. PCOS Diet & Nutrition
    p2 = await llm_service.generate_response("পিসিওএস এর খাদ্যতালিকা ও ডায়েট কেমন হবে?")
    assert "খাদ্যতালিকা" in p2.reply or "শাকসবজি" in p2.reply or "চিনি" in p2.reply or "বীজ" in p2.reply
    assert len(p2.citations) > 0

    # 3. PCOD vs PCOS difference
    p3 = await llm_service.generate_response("পিসিওডি এবং পিসিওএস এর পার্থক্য কি?")
    assert "PCOD" in p3.reply or "পার্থক্য" in p3.reply or "সিন্ড্রোম" in p3.reply
    assert len(p3.citations) > 0

    # 4. Hirsutism & Facial Hair in PCOS
    p4 = await llm_service.generate_response("পিসিওএস এ মুখে অবাঞ্ছিত লোম গজায় কেন?")
    assert "লোম" in p4.reply or "হরমোন" in p4.reply or "টেস্টোস্টেরন" in p4.reply
    assert len(p4.citations) > 0

    # 5. Diagnostic Tests for PCOS
    p5 = await llm_service.generate_response("পিসিওএস নিশ্চিত হতে কি কি রক্ত পরীক্ষা ও টেস্ট করতে হয়?")
    assert "আল্ট্রাসনোগ্রাম" in p5.reply or "টেস্ট" in p5.reply or "হরমোন" in p5.reply or "USG" in p5.reply
    assert len(p5.citations) > 0

    # 6. PCOS Cure vs Long-term Control
    p6 = await llm_service.generate_response("পিসিওএস কি চিরতরে ভালো হয় নাকি নিয়ন্ত্রণে রাখতে হয়?")
    assert "নিয়ন্ত্রণ" in p6.reply or "জীবনযাত্রা" in p6.reply or "ডায়াবেটিস" in p6.reply
    assert len(p6.citations) > 0

@pytest.mark.asyncio
async def test_expanded_everyday_conversational_intents():
    # Daily cooking & meal banter
    c1 = await llm_service.generate_response("আজকে কি রান্না করব বল তো?")
    assert "রান্না" in c1.reply or "ডিম" in c1.reply or "ডাল" in c1.reply

    # Weather talk
    c2 = await llm_service.generate_response("আজকে অনেক গরম লাগছে")
    assert "গরম" in c2.reply or "পানি" in c2.reply or "শরবত" in c2.reply

    # Good news & happiness
    c3 = await llm_service.generate_response("আজ একটা সুখবর আছে")
    assert "আনন্দ" in c3.reply or "খুশি" in c3.reply or "সুখবর" in c3.reply

    # Jokes & humor
    c4 = await llm_service.generate_response("একটা মজার কৌতুক শোনাও তো")
    assert "ডাক্তার" in c4.reply or "হাসি" in c4.reply or "কৌতুক" in c4.reply or "হেসে" in c4.reply or "গল্প" in c4.reply or "মজা" in c4.reply

    # Mic check
    c5 = await llm_service.generate_response("আমার কথা কি শুনতে পাচ্ছো?")
    assert "পরিষ্কার" in c5.reply or "শুনতে" in c5.reply or "বলুন" in c5.reply

    # Temporary stepping away
    c6 = await llm_service.generate_response("আমি একটু পর আসছি")
    assert "ঠিক আছে" in c6.reply or "অপেক্ষা" in c6.reply or "খেয়াল" in c6.reply or "অবশ্যই" in c6.reply or "আছি" in c6.reply

@pytest.mark.asyncio
async def test_abdominal_pain_differential_assessment_no_premature_period():
    """
    Critical Safety & Clinical Guardrail:
    When user mentions abdominal / belly pain ("পেটে ব্যথা", "তলপেট চাবানো", "পেট কামড়ানো"):
    1. NEVER assume it is menstrual pain / period automatically.
    2. Inquire about differential causes:
       - Outside/unhygienic food in last 1-2 days (food poisoning/indigestion)
       - Gastric / acidity / indigestion
       - Whether period is approaching or premenstrual symptoms exist
       - Pain location (upper belly, navel, lower belly) and urinary symptoms
    3. Categorize topic as 'abdominal_pain' (NOT 'menstrual_pain').
    4. Provide relevant non-period voice suggestions.
    """
    from app.api.voice import generate_voice_suggestions

    # 1. General abdominal pain: Must NOT jump to period; Must ask differential questions
    res1 = await llm_service.generate_response("আমার পেটে খুব ব্যথা করছে")
    assert "খাবার" in res1.reply or "অস্বাস্থ্যকর" in res1.reply or "আনহাইজেনিক" in res1.reply
    assert "গ্যাস" in res1.reply or "গ্যাস্ট্রিক" in res1.reply or "এসিডিটি" in res1.reply
    assert "মাসিক" in res1.reply or "পিরিয়ড" in res1.reply
    # Must NOT directly claim it is menstrual cramps
    assert "মাসিকের কারণে হচ্ছে" not in res1.reply

    # 2. Lower abdominal cramping without menstrual keywords: Must assess differentials
    res2 = await llm_service.generate_response("তলপেট চাবাচ্ছে আর কামড়াচ্ছে")
    assert "খাবার" in res2.reply or "গ্যাস" in res2.reply or "পিরিয়ড" in res2.reply or "মাসিক" in res2.reply

    # 3. Topic detection check
    topic1 = session_memory._detect_topic("আমার পেটে খুব ব্যথা করছে")
    assert topic1 == "abdominal_pain"
    topic2 = session_memory._detect_topic("তলপেট চাবাচ্ছে")
    assert topic2 == "abdominal_pain"

    # 4. Voice suggestions check
    sugg = generate_voice_suggestions("abdominal_pain", "আমার পেটে ব্যথা")
    assert any("খাবার" in s for s in sugg)
    assert any("গ্যাস" in s for s in sugg)

    # 5. Multi-turn follow-up: Outside food intake answered
    follow_food = await llm_service.generate_response("কালকে বাইরের খোলা ভাজাপোড়া আর চটপটি খেয়েছিলাম")
    assert "খাবার" in follow_food.reply or "স্যালাইন" in follow_food.reply or "পয়জনিং" in follow_food.reply or "পানি" in follow_food.reply

    # 6. Multi-turn follow-up: Gas / Acidity answered
    follow_gas = await llm_service.generate_response("আমার খুব গ্যাস আর বুক জ্বালাপোড়া করছে")
    assert "গ্যাস" in follow_gas.reply or "পানি" in follow_gas.reply or "আদা" in follow_gas.reply

    # 7. Multi-turn follow-up: Menstrual cycle proximity answered
    follow_period = await llm_service.generate_response("আমার মাসিকের সময় ঘনিয়ে এসেছে")
    assert "মাসিক" in follow_period.reply or "সেঁক" in follow_period.reply or "বিশ্রাম" in follow_period.reply

    # 8. Explicit menstrual pain: SHOULD address menstrual pain
    res_menstrual = await llm_service.generate_response("আমার মাসিকের সময় তলপেটে ব্যথা করছে")
    assert "মাসিক" in res_menstrual.reply or "পিরিয়ড" in res_menstrual.reply
    topic_menstrual = session_memory._detect_topic("আমার মাসিকের ব্যথা করছে")
    assert topic_menstrual == "menstrual_pain"


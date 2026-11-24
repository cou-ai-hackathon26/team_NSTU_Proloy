# -*- coding: utf-8 -*-
"""
Automated Test Suite for Shared-Phone Private Voice Use & Veiled Bengali Distress Detection:
1. Rural lethal means detection (pesticides, agricultural poisons, river drowning)
2. Veiled suicidal ideation & passive resignation ("আল্লাহ যেন তুলে নেয়", "ঘুমাইয়া যদি আর না উঠতাম")
3. Perceived burdensomeness & erasure ("আমি না থাকলেই সবার ভালো", "সংসারের বোঝা")
4. Hopeless entrapment & domestic abuse distress ("চারিদিকে অন্ধকার", "বাপের বাড়ি গিয়ে আর মুখ দেখাব না")
5. Bystander-safe covert de-escalation audio (protects user from domestic retaliation)
6. Covert vernacular cycle metaphors ("লাল ফুল ফুটেছে", "মেহমান আসছে", "কাপড় নষ্ট", "পবিত্র হয়েছি")
7. Memory persistence of covert cycle updates
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.crisis_detector import detect_crisis
from app.services.cycle_engine import decode_covert_cycle_metaphor

client = TestClient(app)

def create_auth_headers():
    res = client.post("/auth/anonymous", json={"age_group": "20-29"}).json()
    return {"Authorization": f"Bearer {res['access_token']}"}

# ----------------------------------------------------
# 1. VEILED DISTRESS & RURAL LETHAL MEANS TESTS
# ----------------------------------------------------
def test_rural_lethal_means_detection():
    # Agricultural pesticide / poison phrases
    res1 = detect_crisis("ফসলের বিষ খেয়ে শান্তি পেতাম")
    assert res1.risk_level == "high"
    assert res1.is_veiled_crisis is True
    assert res1.covert_alert is True
    assert res1.emergency_payload.covert_mode is True
    assert res1.emergency_payload.helpline_number == "109"

    res2 = detect_crisis("কীটনাশকের বোতলটা হাতে নিয়ে বসে ছিলাম")
    assert res2.risk_level == "high"
    assert res2.is_veiled_crisis is True

    res3 = detect_crisis("নদীর জলে গা ভাসায় দেব")
    assert res3.risk_level == "high"
    assert res3.is_veiled_crisis is True

def test_passive_resignation_death_wishes():
    # Euphemistic phrases expressing passive death wishes
    queries = [
        "আল্লাহ যেন আমাকে তুলে নেয়",
        "ঘুমাইয়া যদি আর না উঠতাম",
        "আমার কি মরণ নাই",
        "এই জীবনের চেয়ে মরণ ভালো ছিল"
    ]
    for q in queries:
        res = detect_crisis(q)
        assert res.risk_level == "high", f"Failed for query: {q}"
        assert res.is_veiled_crisis is True
        assert res.covert_alert is True
        # Bystander safe audio must be present
        assert res.emergency_payload.bystander_safe_audio_bn is not None
        assert "কষ্টটা আমি বুঝতে পারছি" in res.emergency_payload.bystander_safe_audio_bn

def test_burdensomeness_and_erasure():
    # Veiled burdensomeness
    queries = [
        "আমি না থাকলেই সবার ভালো",
        "সংসারের বোঝা হয়ে আছি",
        "কোথাও হারিয়ে যেতে চাই চিরতরে"
    ]
    for q in queries:
        res = detect_crisis(q)
        assert res.risk_level == "high", f"Failed for query: {q}"
        assert res.is_veiled_crisis is True
        assert res.covert_alert is True

def test_hopeless_entrapment_and_abuse():
    queries = [
        "চারিদিকে অন্ধকার লাগে কোনো পথ নাই",
        "বাপের বাড়ি গিয়ে আর মুখ দেখাব না",
        "দম বন্ধ হয়ে আসতেছে আর পারি না"
    ]
    for q in queries:
        res = detect_crisis(q)
        assert res.risk_level == "high", f"Failed for query: {q}"
        assert res.is_veiled_crisis is True

# ----------------------------------------------------
# 2. BYSTANDER-SAFE SPOKEN AUDIO DE-ESCALATION
# ----------------------------------------------------
def test_bystander_safe_chat_responses():
    headers = create_auth_headers()

    # When user speaks a veiled distress utterance, spoken reply must be calm & de-escalating
    # It must NOT shout "আপনি কি আত্মহত্যা করতে চাচ্ছেন?" aloud on a shared phone
    chat_res = client.post("/chat", json={
        "message": "আল্লাহ যেন আমাকে তুলে নেয়"
    }, headers=headers)
    assert chat_res.status_code == 200
    reply = chat_res.json()["reply"]
    assert "কষ্টটা আমি বুঝতে পারছি" in reply
    assert "আত্মহত্যা" not in reply  # Never shout suicide on shared phone

    # Context-aware v1 endpoint verification
    v1_res = client.post("/api/v1/chat/message", json={
        "message": "সংসারের বোঝা হয়ে আছি, আমি না থাকলেই সবার ভালো"
    }, headers=headers)
    assert v1_res.status_code == 200
    v1_data = v1_res.json()
    assert "veiled_crisis_detected" in v1_data["safety_flags"]
    assert "আত্মহত্যা" not in v1_data["response"]

# ----------------------------------------------------
# 3. COVERT VERNACULAR CYCLE METAPHOR RESOLUTION
# ----------------------------------------------------
def test_covert_cycle_metaphors_decoding():
    # 1. Cycle Start (LMP)
    m1 = decode_covert_cycle_metaphor("আজ লাল ফুল ফুটেছে")
    assert m1 is not None
    assert m1["event_type"] == "cycle_start"
    assert m1["action"] == "log_period_start"

    m2 = decode_covert_cycle_metaphor("মেহমান আসছে ঘরে")
    assert m2 is not None
    assert m2["event_type"] == "cycle_start"

    # 2. Active Flow
    m3 = decode_covert_cycle_metaphor("কাপড় নষ্ট হয়েছে, কাজ করতে পারছি না")
    assert m3 is not None
    assert m3["event_type"] == "active_flow"

    # 3. Cycle End
    m4 = decode_covert_cycle_metaphor("শরীর পবিত্র হয়েছে, গোসল করেছি")
    assert m4 is not None
    assert m4["event_type"] == "cycle_end"
    assert m4["action"] == "log_period_end"

    # 4. Cramps
    m5 = decode_covert_cycle_metaphor("তলপেটে মোচড় দিচ্ছে খুব")
    assert m5 is not None
    assert m5["event_type"] == "cramps"

def test_covert_metaphor_chat_and_memory_persistence():
    headers = create_auth_headers()

    # User speaks covert metaphor in chat
    resp = client.post("/chat", json={
        "message": "আজ লাল ফুল ফুটেছে"
    }, headers=headers)
    assert resp.status_code == 200
    assert "মাসিকের প্রথম দিনের তথ্য" in resp.json()["reply"]

    # In Context-Aware chat, patient memory is persisted
    v1_resp = client.post("/api/v1/chat/message", json={
        "message": "আজ লাল ফুল ফুটেছে"
    }, headers=headers)
    assert v1_resp.status_code == 200

    mem_resp = client.get("/api/v1/patient/memories", headers=headers)
    assert mem_resp.status_code == 200
    memories = mem_resp.json()
    keys = [m["key"] for m in memories]
    assert "cycle_status" in keys

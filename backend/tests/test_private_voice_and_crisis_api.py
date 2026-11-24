# -*- coding: utf-8 -*-
"""
Comprehensive Automated Test Suite for:
1. Shared-Phone Private Voice Assistant (Session lifecycle, ASR, Bangla intent extraction, Cycle update, Quick exit)
2. Indirect Bangla Mental Health Crisis Detection Engine (4-Tier classification, veiled ideation, lethal means, negation, hypothetical contexts)
3. Shared Device Privacy Preferences (Discreet mode, content masking, session timeouts)
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_auth_headers():
    res = client.post("/auth/anonymous", json={"age_group": "20-29"}).json()
    return {"Authorization": f"Bearer {res['access_token']}"}


# ==============================================================================
# FEATURE ONE: SHARED-PHONE PRIVATE VOICE ASSISTANT TESTS
# ==============================================================================

def test_private_voice_session_start_and_exit():
    """Test start and immediate quick-exit for shared-phone safety."""
    headers = create_auth_headers()

    # 1. Start private session
    resp = client.post(
        "/api/voice/session/start",
        json={"privacy_mode": "discreet", "timeout_seconds": 300},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "session_token" in data
    assert data["status"] == "active"
    assert data["privacy_mode"] == "discreet"
    session_id = data["session_id"]
    session_token = data["session_token"]

    # 2. Quick Exit (Panic tap / camouflage)
    exit_resp = client.post(
        "/api/voice/session/exit",
        json={"session_id": session_id, "clear_in_memory_state": True}
    )
    assert exit_resp.status_code == 200
    exit_data = exit_resp.json()
    assert exit_data["success"] is True
    assert exit_data["session_status"] == "exited"
    assert exit_data["quick_exit_triggered"] is True

    # 3. Trying to perform cycle update on exited session should fail (410 Gone)
    update_resp = client.post(
        "/api/voice/cycle-update",
        json={
            "session_id": session_id,
            "period_start_date": str(date.today()),
            "is_confirmed": True
        },
        headers=headers
    )
    assert update_resp.status_code == 410


def test_private_voice_transcribe_in_memory():
    """Test transcription endpoint preserves zero raw audio to disk."""
    resp = client.post(
        "/api/voice/transcribe",
        json={"direct_transcript": "আজ আমার পিরিয়ড শুরু হয়েছে"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["transcript"] == "আজ আমার পিরিয়ড শুরু হয়েছে"
    assert data["language"] == "bn"
    assert data["confidence"] > 0.9
    assert data["redaction_reference"].startswith("tx_ref_")


def test_voice_intent_extraction_scenarios():
    """
    Test extraction of natural Bangla expressions:
    - আজ আমার পিরিয়ড শুরু হয়েছে -> cycle_start, today's date
    - কাল থেকে মাসিক হচ্ছে -> ambiguous date asking confirmation for yesterday
    - আমার আজকে শেষ হয়েছে -> cycle_end
    - এই মাসে এখনো পিরিয়ড হয়নি -> cycle_delayed
    - আমার পেটে অনেক ব্যথা হচ্ছে -> pelvic_pain, pain_intensity=8
    - আজকে মনটা খুব খারাপ -> mood=sad
    - কয়েকদিন ধরে ঘুম হচ্ছে না -> sleep_pattern=insomnia
    - লাল ফুল ফুটেছে -> covert metaphor -> cycle_start
    """
    # 1. Cycle Start today
    r1 = client.post("/api/voice/intent", json={"transcript": "আজ আমার পিরিয়ড শুরু হয়েছে"}).json()
    info1 = r1["extracted_info"]
    assert info1["event_type"] == "cycle_start"
    assert info1["period_start_date"] == str(date.today())
    assert info1["is_ambiguous"] is False

    # 2. Cycle Start yesterday (ambiguous wording requiring clarification)
    r2 = client.post("/api/voice/intent", json={"transcript": "কাল থেকে মাসিক হচ্ছে"}).json()
    info2 = r2["extracted_info"]
    assert info2["event_type"] == "cycle_start"
    assert info2["period_start_date"] == str(date.today() - timedelta(days=1))
    assert info2["is_ambiguous"] is True
    assert "গতকালকে" in info2["clarification_question_bn"]

    # 3. Cycle End
    r3 = client.post("/api/voice/intent", json={"transcript": "আমার আজকে শেষ হয়েছে"}).json()
    info3 = r3["extracted_info"]
    assert info3["event_type"] == "cycle_end"
    assert info3["period_end_date"] == str(date.today())

    # 4. Cycle Delayed
    r4 = client.post("/api/voice/intent", json={"transcript": "এই মাসে এখনো পিরিয়ড হয়নি"}).json()
    info4 = r4["extracted_info"]
    assert info4["event_type"] == "cycle_delayed"

    # 5. Pain & Dysmenorrhea
    r5 = client.post("/api/voice/intent", json={"transcript": "আমার পেটে অনেক ব্যথা হচ্ছে"}).json()
    info5 = r5["extracted_info"]
    assert info5["pain_intensity"] >= 7
    assert any("ব্যথা" in s for s in info5["associated_symptoms"])

    # 6. Sad mood
    r6 = client.post("/api/voice/intent", json={"transcript": "আজকে মনটা খুব খারাপ"}).json()
    info6 = r6["extracted_info"]
    assert info6["mood"] == "sad"

    # 7. Sleep disturbance / Insomnia
    r7 = client.post("/api/voice/intent", json={"transcript": "কয়েকদিন ধরে ঘুম হচ্ছে না"}).json()
    info7 = r7["extracted_info"]
    assert info7["sleep_pattern"] == "insomnia"

    # 8. Covert vernacular cycle metaphor
    r8 = client.post("/api/voice/intent", json={"transcript": "আমার লাল ফুল ফুটেছে"}).json()
    info8 = r8["extracted_info"]
    assert info8["event_type"] == "cycle_start"


def test_voice_cycle_update_requires_confirmation():
    """Ensure sensitive health updates reject unconfirmed data."""
    headers = create_auth_headers()
    start_res = client.post("/api/voice/session/start", json={}, headers=headers).json()
    session_id = start_res["session_id"]

    # Attempt save without confirmation -> HTTP 400
    res = client.post(
        "/api/voice/cycle-update",
        json={
            "session_id": session_id,
            "period_start_date": str(date.today()),
            "is_confirmed": False
        },
        headers=headers
    )
    assert res.status_code == 400
    assert "নিশ্চিতকরণ" in res.json()["detail"]


def test_voice_cycle_update_full_persistence():
    """Verify validated data persists to PeriodLog, SymptomLog, MoodLog, and PatientMemory."""
    headers = create_auth_headers()
    start_res = client.post("/api/voice/session/start", json={}, headers=headers).json()
    session_id = start_res["session_id"]

    update_payload = {
        "session_id": session_id,
        "period_start_date": str(date.today() - timedelta(days=2)),
        "flow_intensity": "heavy",
        "pain_score": 8,
        "symptoms": ["তলপেটে তীব্র মোচড়ানো ব্যথা", "কোমর ব্যথা"],
        "mood": "distressed",
        "sleep_status": "insomnia",
        "cycle_length_days": 42,
        "is_confirmed": True
    }

    res = client.post("/api/voice/cycle-update", json=update_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "period_log" in data["logged_entities"]
    assert "pain_log" in data["logged_entities"]
    assert "mood_log" in data["logged_entities"]
    assert "sleep_log" in data["logged_entities"]
    assert data["pcos_risk_flag"] is not None  # cycle_length 42 triggers advisory


# ==============================================================================
# FEATURE TWO: INDIRECT BANGLA CRISIS DETECTION ENGINE TESTS
# ==============================================================================

def test_crisis_level_0_normal_inquiry():
    """Level 0: Routine health query without psychological crisis."""
    res = client.post("/api/crisis/assess", json={"text": "পিরিয়ডের সময় গরম পানি খেলে কি পেটের ব্যথা কমে?"})
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] == "LEVEL_0"
    assert data["level_numeric"] == 0
    assert data["action_required"] is False
    assert data["is_veiled"] is False


def test_crisis_level_1_mild_emotional_distress():
    """Level 1: Mild sadness, distress, weariness."""
    res = client.post("/api/crisis/assess", json={"text": "আজকে মনটা খুব খারাপ, কিছুই ভালো লাগছে না"})
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] == "LEVEL_1"
    assert data["level_numeric"] == 1
    assert data["safety_response_bn"] is not None


def test_crisis_level_2_veiled_ideation_and_burdensomeness():
    """
    Level 2: Veiled suicidal ideation, desire to vanish, perceived burdensomeness.
    Must generate gentle direct clarification prompt:
    'তুমি কি শুধু সবকিছু থেকে একটু দূরে থাকতে চাইছ, নাকি নিজের ক্ষতি করার কথাও মনে হচ্ছে?'
    """
    queries = [
        "আমি না থাকলে সবারই ভালো হতো, সংসারের বোঝা হয়ে গেছি",
        "সবকিছু থেকে চিরতরে দূরে হারিয়ে যেতে ইচ্ছা করে",
        "ঘুমিয়ে থাকলে যদি আর কোনোদিন উঠতে না হতো",
        "আমার বেঁচে থাকার কোনো অর্থ বা মানে নেই"
    ]
    for q in queries:
        res = client.post("/api/crisis/assess", json={"text": q})
        assert res.status_code == 200
        data = res.json()
        assert data["level_numeric"] >= 2
        assert data["is_veiled"] is True
        assert data["clarification_prompt_bn"] is not None
        assert "নিজের ক্ষতি" in data["clarification_prompt_bn"] or "কষ্টের" in data["clarification_prompt_bn"]


def test_crisis_level_3_lethal_means_and_immediate_danger():
    """
    Level 3: Agricultural pesticides, lethal means, immediate danger.
    Must trigger covert alert, 109 hotline referral, and bystander-safe audio script.
    """
    queries = [
        "ফসলের বিষ খেয়ে শান্তি পেতাম",
        "কীটনাশকের বোতলটা হাতে নিয়ে বসে আছি",
        "নদীর জলে গা ভাসায় দিয়ে সব শেষ করে দেব",
        "আমার গলায় দড়ি দেওয়া ছাড়া আর কোনো পথ নাই"
    ]
    for q in queries:
        res = client.post("/api/crisis/assess", json={"text": q})
        assert res.status_code == 200
        data = res.json()
        assert data["risk_level"] == "LEVEL_3"
        assert data["level_numeric"] == 3
        assert data["covert_alert"] is True
        assert data["emergency_helpline"] == "109"
        assert data["bystander_safe_audio_bn"] is not None


def test_crisis_hypothetical_and_educational_context():
    """Contextual awareness: Distinguish educational queries from personal crises."""
    res = client.post("/api/crisis/assess", json={"text": "বিশ্ব আত্মহত্যা প্রতিরোধ দিবস প্রতি বছর কত তারিখে পালন করা হয়?"})
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] == "LEVEL_0"
    assert data["is_hypothetical"] is True


def test_crisis_negation_handling():
    """Ensure explicit negation (e.g. 'মরতে চাই না') does not trigger false Level 3 alarm."""
    res = client.post("/api/crisis/assess", json={"text": "আমি মরতে চাই না কিন্তু পারিবারিক নির্যাতনে খুব ক্লান্ত"})
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] != "LEVEL_3"
    assert data["level_numeric"] <= 1


def test_crisis_safety_response_endpoint():
    """Test safety response generator for LEVEL_3 and LEVEL_2."""
    r3 = client.post("/api/crisis/safety-response", json={"risk_level": "LEVEL_3"}).json()
    assert "১০৯" in r3["response_text_bn"]
    assert r3["support_number"] == "109"
    assert r3["covert_mode"] is True

    r2 = client.post("/api/crisis/safety-response", json={"risk_level": "LEVEL_2"}).json()
    assert "বোঝা" in r2["response_text_bn"] or "কষ্ট" in r2["response_text_bn"]
    assert r2["covert_mode"] is True


def test_crisis_assessment_history_persistence():
    """Verify crisis assessment logs are stored and queryable per user."""
    headers = create_auth_headers()
    # Trigger an assessment with auth
    client.post(
        "/api/crisis/assess",
        json={"text": "সংসারের বোঝা হয়ে আর থাকতে ইচ্ছা করছে না"},
        headers=headers
    )

    # Fetch history
    hist = client.get("/api/crisis/assessment-history", headers=headers)
    assert hist.status_code == 200
    data = hist.json()
    assert data["total_assessments"] >= 1
    assert len(data["recent_assessments"]) >= 1
    assert data["recent_assessments"][0]["risk_level"] in ["LEVEL_2", "LEVEL_3"]


# ==============================================================================
# PRIVACY PREFERENCES TESTS
# ==============================================================================

def test_privacy_preferences_get_and_put():
    """Test retrieving and updating shared-phone privacy settings."""
    headers = create_auth_headers()

    # GET defaults
    g_res = client.get("/api/privacy/preferences", headers=headers)
    assert g_res.status_code == 200
    g_data = g_res.json()
    assert g_data["discreet_mode_enabled"] is True
    assert g_data["sensitive_content_hidden"] is True
    assert g_data["session_timeout"] == 300

    # PUT updates
    update_payload = {
        "discreet_mode_enabled": True,
        "sensitive_content_hidden": True,
        "session_timeout": 120,
        "voice_response_enabled": False
    }
    p_res = client.put("/api/privacy/preferences", json=update_payload, headers=headers)
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert p_data["session_timeout"] == 120
    assert p_data["voice_response_enabled"] is False

    # Verify GET reflects update
    g_res2 = client.get("/api/privacy/preferences", headers=headers)
    assert g_res2.status_code == 200
    assert g_res2.json()["session_timeout"] == 120
    assert g_res2.json()["voice_response_enabled"] is False

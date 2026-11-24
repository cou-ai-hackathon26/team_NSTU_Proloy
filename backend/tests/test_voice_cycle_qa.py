import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_voice_cycle_qa_flow():
    """
    Verifies that menstrual cycle data can be tracked interactively
    through voice Question & Answer flow:
    1. User speaks cycle start ("আজ আমার পিরিয়ড শুরু হয়েছে")
    2. Assistant asks confirmation and details via voice
    3. User confirms ("হ্যাঁ, রক্তপ্রবাহ স্বাভাবিক")
    4. Data is committed to PeriodLog and PatientMemory
    5. User can query delayed cycle
    """
    session_id = "test-voice-cycle-qa-1"

    # Step 1: User indicates period start
    r1 = client.post(
        "/voice",
        json={"direct_transcript": "আজ আমার পিরিয়ড শুরু হয়েছে", "session_id": session_id}
    ).json()

    assert r1["cycle_action"] is not None
    assert r1["cycle_action"]["status"] == "pending_confirmation"
    assert "সংরক্ষণ করব" in r1["reply_text"]
    assert r1["audio_base64"] is not None

    # Step 2: User confirms
    r2 = client.post(
        "/voice",
        json={"direct_transcript": "হ্যাঁ, সংরক্ষণ করো", "session_id": session_id}
    ).json()

    assert r2["cycle_action"] is not None
    assert r2["cycle_action"]["status"] == "saved"
    assert "সফলভাবে সংরক্ষণ" in r2["reply_text"]

    # Step 3: Initiation request flow
    session_id_2 = "test-voice-cycle-qa-2"
    r3 = client.post(
        "/voice",
        json={"direct_transcript": "আমার পিরিয়ড ট্র্যাক করতে চাই", "session_id": session_id_2}
    ).json()
    assert r3["cycle_action"] is not None
    assert r3["cycle_action"]["status"] == "prompt_date"
    assert "শুরু হয়েছে" in r3["reply_text"]

    # Step 4: User provides date
    r4 = client.post(
        "/voice",
        json={"direct_transcript": "কাল থেকে পিরিয়ড হচ্ছে", "session_id": session_id_2}
    ).json()
    assert r4["cycle_action"] is not None
    assert r4["cycle_action"]["status"] == "pending_confirmation"

    # Step 5: User cancels
    r5 = client.post(
        "/voice",
        json={"direct_transcript": "না, বাতিল করো", "session_id": session_id_2}
    ).json()
    assert r5["cycle_action"] is not None
    assert r5["cycle_action"]["status"] == "cancelled"
    assert "সংরক্ষণ করা হলো না" in r5["reply_text"]

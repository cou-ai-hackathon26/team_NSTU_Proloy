import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_integration_pipeline():
    # 1. Anonymous Registration
    reg_resp = client.post("/auth/anonymous", json={"pin": "4321", "age_group": "20-29"})
    assert reg_resp.status_code == 200
    token = reg_resp.json()["access_token"]
    user_id = reg_resp.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Text Chat with RAG Grounding
    chat_resp = client.post("/chat", json={"message": "পিরিয়ডের ব্যথা কীভাবে উপশম করা যায়?"})
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "ব্যথা" in chat_data["reply"]
    assert len(chat_data["citations"]) > 0

    # 3. Voice Endpoint with Mock Audio Upload
    fake_audio = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    voice_resp = client.post(
        "/voice",
        files={"audio_file": ("test.wav", fake_audio, "audio/wav")}
    )
    assert voice_resp.status_code == 200
    voice_data = voice_resp.json()
    assert "transcript" in voice_data
    assert "reply_text" in voice_data

    # 4. Period Tracker Logging & Analysis
    p_log = client.post(
        "/track/period",
        json={"start_date": "2026-04-01", "flow": "medium", "symptoms": ["তলপেটে ব্যথা"]},
        headers=headers
    )
    assert p_log.status_code == 200

    p_analysis = client.get("/track/period/analysis", headers=headers)
    assert p_analysis.status_code == 200
    assert "explanation_bn" in p_analysis.json()

    # 5. Mood Logging & Analysis
    m_log = client.post(
        "/track/mood",
        json={"mood_score": 4, "tags": ["ঘুম ভালো"]},
        headers=headers
    )
    assert m_log.status_code == 200

    m_analysis = client.get("/track/mood/analysis", headers=headers)
    assert m_analysis.status_code == 200
    assert "gentle_suggestion_bn" in m_analysis.json()

    # 6. Pregnancy Care Timeline
    preg_resp = client.post(
        "/preg/start",
        json={"lmp_date": "2026-03-01"},
        headers=headers
    )
    assert preg_resp.status_code == 200
    assert preg_resp.json()["gestational_weeks"] > 0
    assert "urgent_warning_signs_bn" in preg_resp.json()["current_milestone"]

    # 7. PCOS Risk Screening
    pcos_resp = client.post(
        "/pcos/predict",
        json={
            "age": 25,
            "height_cm": 158,
            "weight_kg": 68,
            "cycle_regularity": "irregular",
            "cycle_length_days": 40,
            "weight_gain": True,
            "excess_hair_growth": True,
            "skin_darkening": False,
            "hair_loss": False,
            "pimples_acne": True,
            "regular_exercise": False
        },
        headers=headers
    )
    assert pcos_resp.status_code == 200
    assert pcos_resp.json()["risk_band"] in ["medium", "high"]
    assert "সতর্কবার্তা" in pcos_resp.json()["disclaimer_bn"]

    # 8. Crisis Safety Trigger
    crisis_resp = client.post("/safety/check", json={"text": "আমি আর বাঁচতে চাই না"})
    assert crisis_resp.status_code == 200
    assert crisis_resp.json()["risk_level"] == "high"
    assert crisis_resp.json()["emergency_payload"]["helpline_number"] == "999"

    # 9. Cascade Data Wipe ("Delete all my data")
    del_resp = client.delete("/auth/me", headers=headers)
    assert del_resp.status_code == 200
    assert "মুছে ফেলা হয়েছে" in del_resp.json()["message"]

    # Verify everything is gone
    check_deleted = client.get("/auth/me", headers=headers)
    assert check_deleted.status_code == 401

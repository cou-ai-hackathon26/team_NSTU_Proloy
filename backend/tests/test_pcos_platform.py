import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_pcos_platform_end_to_end():
    # 1. Register / Authenticate User
    reg_resp = client.post("/auth/anonymous", json={"language": "bn", "age_group": "20-29"})
    assert reg_resp.status_code == 200
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Update Patient Profile
    prof_resp = client.post("/profile/me", headers=headers, json={
        "full_name": "অনামিকা হক (Anamika Haque)",
        "age": 24,
        "height_cm": 158.0,
        "weight_kg": 64.0,
        "blood_group": "B+",
        "baseline_summary": "কৈশোর থেকেই মাসিকের অনিয়ম ও মুখে ব্রণের সমস্যা।"
    })
    assert prof_resp.status_code == 200
    
    get_prof = client.get("/profile/me", headers=headers)
    assert get_prof.status_code == 200
    assert get_prof.json()["profile"]["age"] == 24

    # 3. Granular Consent Management
    consent_resp = client.post("/profile/consent", headers=headers, json={
        "consent_type": "conversation_history",
        "is_granted": True
    })
    assert consent_resp.status_code == 200
    assert consent_resp.json()["is_granted"] is True

    # 4. Longitudinal PCOS Risk Evaluation (Core Feature 2)
    eval_resp = client.post("/pcos-tracker/evaluate", headers=headers, json={
        "age": 24,
        "height_cm": 158.0,
        "weight_kg": 64.0,
        "cycle_regularity": "irregular",
        "cycle_length_days": 48.0,
        "weight_gain": True,
        "excess_hair_growth": True,
        "skin_darkening": True,
        "hair_loss": False,
        "pimples_acne": True,
        "fast_food_frequent": True,
        "regular_exercise": False
    })
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    assert "calibrated_risk_score" in data
    assert data["risk_band"] in ["low", "moderate", "elevated"]
    assert len(data["contributing_factors"]) > 0
    assert "সতর্কতা" in data["clinical_disclaimer_bn"]
    assert "Medical Disclaimer" in data["clinical_disclaimer_en"]
    assert len(data["missing_information"]) > 0

    # 5. Risk History
    hist_resp = client.get("/pcos-tracker/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) >= 1

    # 6. Medical Report Interpretation (Lab Reports with Limitations)
    report_resp = client.post("/medical-reports/upload", headers=headers, json={
        "report_type": "hormonal_panel",
        "lh_level": 12.4,
        "fsh_level": 5.1,
        "fasting_glucose": 105.0,
        "tsh_level": 2.8,
        "ultrasound_notes": "Multiple subcentimeter peripheral follicles visualized in both ovaries."
    })
    assert report_resp.status_code == 200
    r_data = report_resp.json()
    assert "LH/FSH Ratio" in r_data["interpretation_bn"] or "অনুপাত" in r_data["interpretation_bn"]
    assert "সীমাবদ্ধতা" in r_data["interpretation_bn"] or "Limitations" in r_data["interpretation_en"]

    # 7. Verified Gynecologist Consultation (Core Feature 6)
    docs_resp = client.get("/consultation/doctors")
    assert docs_resp.status_code == 200
    doctors = docs_resp.json()
    assert len(doctors) >= 2
    doc = doctors[0]
    assert "A-" in doc["bmdc_reg_number"]

    # Book consultation
    book_resp = client.post("/consultation/book", headers=headers, json={
        "doctor_id": doc["id"],
        "scheduled_at": "2026-11-28T18:30:00",
        "chief_complaint": "অনিয়মিত মাসিক ও পিসিওএস স্ক্রিনিং পরবর্তী বিস্তারিত পরামর্শ চাই।",
        "share_health_history": True
    })
    assert book_resp.status_code == 200
    b_data = book_resp.json()
    assert b_data["status"] == "confirmed"
    assert "meeting_link" in b_data

    # Check patient appointments
    my_appts = client.get("/consultation/my-appointments", headers=headers)
    assert my_appts.status_code == 200
    assert len(my_appts.json()) >= 1

    # 8. ML Admin & Testing Dashboard (Core Feature 5)
    ds_resp = client.get("/ml-admin/datasets")
    assert ds_resp.status_code == 200
    assert len(ds_resp.json()) >= 1

    models_resp = client.get("/ml-admin/models")
    assert models_resp.status_code == 200
    m_data = models_resp.json()
    assert "models_comparison" in m_data
    assert "RandomForest" in m_data["models_comparison"]

    test_pred_resp = client.post("/ml-admin/test-prediction", json={
        "age": 22,
        "bmi": 26.0,
        "cycle_irregular": 1,
        "cycle_length_days": 42.0,
        "weight_gain": 1,
        "excess_hair_growth": 1,
        "skin_darkening": 1,
        "hair_loss": 0,
        "pimples_acne": 1,
        "fast_food_frequent": 0,
        "regular_exercise": 1
    })
    assert test_pred_resp.status_code == 200
    pred_data = test_pred_resp.json()
    assert "calibrated_risk_score" in pred_data
    assert len(pred_data["top_contributing_factors"]) > 0

    # 9. Health Timeline & Export
    timeline_resp = client.get("/profile/timeline", headers=headers)
    assert timeline_resp.status_code == 200

    export_resp = client.get("/profile/export", headers=headers)
    assert export_resp.status_code == 200
    assert "health_timeline" in export_resp.json()

    # 10. Complete Data Wipe (Right to be Forgotten)
    del_resp = client.delete("/profile/delete-all", headers=headers)
    assert del_resp.status_code == 200

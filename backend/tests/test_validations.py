from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_period_validation_future_date():
    reg = client.post("/auth/anonymous", json={"age_group": "20-29"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    future_date = (date.today() + timedelta(days=5)).isoformat()
    resp = client.post(
        "/track/period",
        json={"start_date": future_date, "flow": "medium"},
        headers=headers
    )
    assert resp.status_code == 400
    assert "ভবিষ্যতের কোনো তারিখ" in resp.json()["detail"]

def test_period_validation_end_before_start():
    reg = client.post("/auth/anonymous", json={"age_group": "20-29"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    start = (date.today() - timedelta(days=5)).isoformat()
    end = (date.today() - timedelta(days=8)).isoformat()
    resp = client.post(
        "/track/period",
        json={"start_date": start, "end_date": end, "flow": "medium"},
        headers=headers
    )
    assert resp.status_code == 400
    assert "শেষের তারিখ শুরুর তারিখের আগের হতে পারে না" in resp.json()["detail"]

def test_pregnancy_validation_future_lmp():
    reg = client.post("/auth/anonymous", json={"age_group": "20-29"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    future_lmp = (date.today() + timedelta(days=2)).isoformat()
    resp = client.post(
        "/preg/start",
        json={"lmp_date": future_lmp},
        headers=headers
    )
    assert resp.status_code == 400
    assert "ভবিষ্যতের কোনো দিন" in resp.json()["detail"]

def test_voice_json_payload_support():
    resp = client.post(
        "/voice",
        json={"direct_transcript": "মাসিকের ব্যথা কমানোর উপায় কি?"}
    )
    assert resp.status_code == 200
    assert "ব্যথা" in resp.json()["reply_text"]

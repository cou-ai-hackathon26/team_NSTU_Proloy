from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_anonymous_registration_has_no_pii():
    response = client.post("/auth/anonymous", json={"pin": "1234", "age_group": "20-29"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user_id" in data
    assert "name" not in data
    assert "email" not in data
    assert "phone" not in data

def test_set_and_verify_pin():
    # Register without pin
    reg = client.post("/auth/anonymous", json={"age_group": "20-29"}).json()
    token = reg["access_token"]
    user_id = reg["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set PIN via PUT /auth/pin
    pin_resp = client.put("/auth/pin", json={"pin": "9876"}, headers=headers)
    assert pin_resp.status_code == 200
    assert "সফলভাবে সংরক্ষিত" in pin_resp.json()["message"]

    # Login with new PIN
    login_resp = client.post("/auth/login", json={"user_id": user_id, "pin": "9876"})
    assert login_resp.status_code == 200

    # Login with wrong PIN fails
    wrong_resp = client.post("/auth/login", json={"user_id": user_id, "pin": "0000"})
    assert wrong_resp.status_code == 401

def test_delete_all_my_data():
    reg = client.post("/auth/anonymous", json={"pin": "5678"}).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200

    del_resp = client.delete("/auth/me", headers=headers)
    assert del_resp.status_code == 200
    assert "মুছে ফেলা হয়েছে" in del_resp.json()["message"]

    me_after = client.get("/auth/me", headers=headers)
    assert me_after.status_code == 401

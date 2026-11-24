from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_reminders_lifecycle():
    # 1. Create anonymous user
    reg = client.post("/auth/anonymous", json={"age_group": "20-29"}).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get default discreet reminders (seeds 5 standard reminders)
    res = client.get("/track/reminders", headers=headers)
    assert res.status_code == 200
    reminders = res.json()
    assert len(reminders) == 5
    
    first_id = reminders[0]["id"]
    assert reminders[0]["enabled"] is True
    assert ("সই" in reminders[0]["discreet_message_bn"] or "Shoi" in reminders[0]["discreet_message_bn"])

    # 3. Toggle reminder off
    put_res = client.put(f"/track/reminders/{first_id}", json={"enabled": False}, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["enabled"] is False

    # 4. Verify updated state
    get_res = client.get("/track/reminders", headers=headers)
    disabled_r = [r for r in get_res.json() if r["id"] == first_id][0]
    assert disabled_r["enabled"] is False

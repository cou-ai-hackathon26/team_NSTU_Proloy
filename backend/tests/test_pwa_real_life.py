from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_pwa_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "সই (Shoi)" in response.text
    assert "<!DOCTYPE html>" in response.text

def test_pwa_manifest_endpoint():
    response = client.get("/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert "Shoi" in data["name"] or "সই" in data["name"]
    assert data["display"] == "standalone"
    assert len(data["icons"]) >= 2

def test_pwa_service_worker_endpoint():
    response = client.get("/service-worker.js")
    assert response.status_code == 200
    assert response.headers.get("Service-Worker-Allowed") == "/"
    assert "addEventListener" in response.text

def test_pwa_static_assets():
    res_svg = client.get("/pwa/icon.svg")
    assert res_svg.status_code == 200
    res_png = client.get("/pwa/icon-192.png")
    assert res_png.status_code == 200

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_anonymous_auth_and_period_logging():
    auth_resp = client.post("/auth/anonymous", json={"age_group": "20-29", "language": "bn"})
    assert auth_resp.status_code == 200
    token = auth_resp.json()["access_token"]
    assert token is not None

    headers = {"Authorization": f"Bearer {token}"}
    log_resp = client.post(
        "/track/period",
        headers=headers,
        json={"start_date": "2026-11-01", "end_date": "2026-11-05", "flow": "medium"}
    )
    assert log_resp.status_code == 200

    get_resp = client.get("/track/period", headers=headers)
    assert get_resp.status_code == 200
    assert len(get_resp.json()) >= 1

def test_dom_id_consistency():
    import re
    from pathlib import Path
    pwa_dir = Path("pwa") if Path("pwa").exists() else Path("../pwa")
    html_text = (pwa_dir / "index.html").read_text(encoding="utf-8")
    js_text = (pwa_dir / "app.js").read_text(encoding="utf-8")
    js_ids = set(re.findall(r"document\.getElementById\(['\"]([^'\"]+)['\"]\)", js_text))
    html_ids = set(re.findall(r"id=['\"]([^'\"]+)['\"]", html_text))
    # shoiToast and chatWelcomeCard can be dynamically generated
    missing = (js_ids - html_ids) - {"shoiToast", "chatWelcomeCard"}
    assert len(missing) == 0, f"Missing IDs in HTML: {missing}"

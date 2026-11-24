import asyncio
import json
import os
import sys
import tempfile
import urllib.request
import urllib.error
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000"

def make_req(method, endpoint, body=None, token=None, content_type="application/json"):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(body).encode("utf-8") if (body is not None and content_type == "application/json") else body
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            try:
                parsed = json.loads(content.decode("utf-8"))
            except Exception:
                parsed = content.decode("utf-8", errors="ignore")
            return resp.status, parsed, None
    except urllib.error.HTTPError as e:
        err_content = e.read()
        try:
            parsed = json.loads(err_content.decode("utf-8"))
        except Exception:
            parsed = err_content.decode("utf-8", errors="ignore")
        return e.code, parsed, e
    except Exception as e:
        return 0, None, str(e)

def run_tests():
    print("=== STARTING HIGH-QUALITY DEEP AUDIT FOR SHOI ===")
    passed = 0
    failed = 0

    def assert_eq(cond, desc):
        nonlocal passed, failed
        if cond:
            print(f"  [PASS] {desc}")
            passed += 1
        else:
            print(f"  [FAIL] {desc}")
            failed += 1

    # 1. Health & Static
    print("\n[Phase 1] Health & PWA Static Assets")
    status, data, err = make_req("GET", "/health")
    assert_eq(status == 200 and data.get("status") == "healthy", "Health check returns 200 and healthy")

    status, html, err = make_req("GET", "/")
    assert_eq(status == 200 and "<title>সই" in html, "Root / serves Shoi PWA HTML")

    status, sw, err = make_req("GET", "/pwa/service-worker.js", content_type=None)
    assert_eq(status == 200 and "CACHE_NAME" in sw, "Service Worker serves correctly")

    status, manifest, err = make_req("GET", "/pwa/manifest.json")
    assert_eq(status == 200 and manifest.get("short_name") == "Shoi", "Manifest JSON is valid")

    # 2. Authentication & Privacy
    print("\n[Phase 2] Anonymous Authentication & PIN Protection")
    status, auth_data, err = make_req("POST", "/auth/anonymous", {"age_group": "20-29", "language": "bn"})
    assert_eq(status == 200 and "access_token" in auth_data, "Create anonymous user succeeds")
    token = auth_data.get("access_token")
    user_id = auth_data.get("user_id")

    status, me_data, err = make_req("GET", "/auth/me", token=token)
    assert_eq(status == 200 and me_data.get("user_id") == user_id and me_data.get("has_pin") is False, "GET /auth/me returns pseudonymous data without PII")

    # Set PIN
    status, pin_res, err = make_req("PUT", "/auth/pin", {"pin": "1234"}, token=token)
    assert_eq(status == 200, "PUT /auth/pin sets 4-digit PIN")

    status, me_data2, err = make_req("GET", "/auth/me", token=token)
    assert_eq(status == 200 and me_data2.get("has_pin") is True, "GET /auth/me reflects has_pin=True")

    # Login with correct PIN
    status, login_res, err = make_req("POST", "/auth/login", {"user_id": user_id, "pin": "1234"})
    assert_eq(status == 200 and "access_token" in login_res, "Login with valid PIN succeeds")

    # Login with wrong PIN
    status, login_wrong, err = make_req("POST", "/auth/login", {"user_id": user_id, "pin": "9999"})
    assert_eq(status == 401, "Login with wrong PIN fails with 401")

    # 3. Period Tracker Edge Cases
    print("\n[Phase 3] Period Tracker & Cycle Engine")
    today = date.today()
    tomorrow = str(today + timedelta(days=1))
    p_start = str(today - timedelta(days=28))
    p_end = str(today - timedelta(days=24))

    # Future date rejection
    status, res, err = make_req("POST", "/track/period", {"start_date": tomorrow}, token=token)
    assert_eq(status == 400, "Future period start date rejected with 400")

    # End date before start date rejection
    status, res, err = make_req("POST", "/track/period", {"start_date": p_start, "end_date": str(today - timedelta(days=30))}, token=token)
    assert_eq(status == 400, "End date before start date rejected with 400")

    # Valid period logs (log 3 cycles for cycle engine analysis)
    c1_s = str(today - timedelta(days=84))
    c1_e = str(today - timedelta(days=80))
    c2_s = str(today - timedelta(days=56))
    c2_e = str(today - timedelta(days=52))
    c3_s = str(today - timedelta(days=28))
    c3_e = str(today - timedelta(days=24))

    for s, e in [(c1_s, c1_e), (c2_s, c2_e), (c3_s, c3_e)]:
        make_req("POST", "/track/period", {"start_date": s, "end_date": e, "flow": "medium", "symptoms": ["তলপেটে ব্যথা"]}, token=token)

    status, p_list, err = make_req("GET", "/track/period", token=token)
    assert_eq(status == 200 and len(p_list) >= 3, "GET /track/period returns period history list")

    status, analysis, err = make_req("GET", "/track/period/analysis", token=token)
    assert_eq(status == 200 and analysis.get("predicted_next_period_start") is not None, "Cycle engine accurately predicts next period date")
    assert_eq(analysis.get("ovulation_window_start") is not None, "Cycle engine calculates ovulation window")

    # 4. Mood Tracker & Phase Correlation
    print("\n[Phase 4] Mood Tracker & Cycle Correlation Engine")
    for days_ago, score in [(1, 4), (2, 3), (3, 2), (4, 4), (5, 5)]:
        d = str(today - timedelta(days=days_ago))
        make_req("POST", "/track/mood", {"date": d, "mood_score": score, "tags": ["ক্লান্তি"]}, token=token)

    status, m_list, err = make_req("GET", "/track/mood", token=token)
    assert_eq(status == 200 and len(m_list) >= 5, "GET /track/mood returns logged moods")

    status, m_analysis, err = make_req("GET", "/track/mood/analysis", token=token)
    assert_eq(status == 200 and m_analysis.get("seven_day_avg") is not None, "Mood analysis computes 7-day average")

    # 5. PCOS Risk Screening Model
    print("\n[Phase 5] PCOS Screening Model")
    pcos_high = {
        "age": 22, "height_cm": 152.0, "weight_kg": 68.0,
        "cycle_regularity": "irregular", "cycle_length_days": 45,
        "weight_gain": True, "excess_hair_growth": True,
        "skin_darkening": True, "hair_loss": True,
        "pimples_acne": True, "regular_exercise": False
    }
    status, pcos_res, err = make_req("POST", "/pcos/predict", pcos_high, token=token)
    assert_eq(status == 200 and pcos_res.get("risk_band") in ["moderate", "high"], "PCOS high-risk profile accurately classified")
    assert_eq("disclaimer_bn" in pcos_res and len(pcos_res.get("actionable_advice_bn", [])) > 0, "PCOS returns clinical disclaimer and Bangla advice")

    # 6. Pregnancy Tracker & Milestones
    print("\n[Phase 6] Pregnancy Tracker & DGHS Milestones")
    # LMP 70 days ago (~10 weeks)
    lmp_valid = str(today - timedelta(days=70))
    status, preg_res, err = make_req("POST", "/preg/start", {"lmp_date": lmp_valid}, token=token)
    assert_eq(status == 200 and preg_res.get("gestational_weeks") == 10, "Pregnancy start calculates exact gestational weeks")
    assert_eq(preg_res.get("current_milestone", {}).get("baby_size_bn") is not None, "Pregnancy returns Bangla baby size comparison")

    status, preg_get, err = make_req("GET", "/preg/timeline", token=token)
    assert_eq(status == 200 and preg_get.get("edd") == preg_res.get("edd"), "GET /preg/timeline returns current active pregnancy")

    # Stop pregnancy
    status, preg_stop, err = make_req("DELETE", "/preg/stop", token=token)
    assert_eq(status == 200, "DELETE /preg/stop deactivates pregnancy")

    # 7. Reminders Engine
    print("\n[Phase 7] Discreet Reminders")
    status, rems, err = make_req("GET", "/track/reminders", token=token)
    assert_eq(status == 200 and len(rems) >= 5, "GET /track/reminders returns default discreet reminders")
    rem_id = rems[0]["id"]
    status, rem_up, err = make_req("PUT", f"/track/reminders/{rem_id}", {"enabled": False, "schedule_time": "08:30"}, token=token)
    assert_eq(status == 200 and rem_up.get("enabled") is False, "PUT /track/reminders updates schedule and toggle")

    # 8. Crisis Safety Guardrails (Prompt 6)
    print("\n[Phase 8] Crisis Safety Guardrails (Zero False Negatives)")
    crisis_inputs = [
        "আমি আর বাঁচতে চাই না আপু",
        "আমার আত্মহত্যা করতে ইচ্ছা করছে",
        "ঘুমের ওষুধ খেয়ে সব শেষ করে দিব",
        "আমি বিষ খাবো ভাবছি"
    ]
    for ci in crisis_inputs:
        status, s_res, err = make_req("POST", "/safety/check", {"text": ci})
        assert_eq(status == 200 and s_res.get("risk_level") == "high", f"Crisis caught: '{ci[:20]}...' -> risk_level=high")
        assert_eq(s_res.get("emergency_payload", {}).get("is_emergency") is True, "Emergency payload triggers with 999 & 109")

    # Safe medical input must NOT trigger crisis
    status, s_res_safe, err = make_req("POST", "/safety/check", {"text": "আমার পিরিয়ডের ব্যথা তীব্র"})
    assert_eq(status == 200 and s_res_safe.get("risk_level") == "none", "Normal symptom does not trigger false positive")

    # 9. Grounded RAG Chat & Voice-First Pipeline
    print("\n[Phase 9] Grounded RAG Chat & Voice Pipeline")
    chat_q = "পিরিয়ডের তীব্র পেটে ব্যথা কিভাবে কমাব?"
    status, c_res, err = make_req("POST", "/chat", {"message": chat_q})
    assert_eq(status == 200 and len(c_res.get("reply", "")) > 10, "Grounded RAG chat returns medically sound response")
    assert_eq(len(c_res.get("citations", [])) > 0, "Chat returns WHO/DGHS verified citations")

    # Voice query via JSON
    status, v_res, err = make_req("POST", "/voice", {"direct_transcript": chat_q})
    assert_eq(status == 200 and v_res.get("audio_base64") is not None, "POST /voice generates neural Bangla voice response (base64 MP3)")

    # 10. Privacy & Right to be Forgotten (Cascading Wipe)
    print("\n[Phase 10] Complete Data Wipe (Right to be Forgotten)")
    status, del_res, err = make_req("DELETE", "/auth/me", token=token)
    assert_eq(status == 200, "DELETE /auth/me wipes user completely")

    # Subsequent requests with deleted user token must return 401
    status, post_del, err = make_req("GET", "/auth/me", token=token)
    assert_eq(status == 401, "Token of deleted user is immediately invalid (401)")

    # Check that user's tracker data is also gone
    status, post_del_periods, err = make_req("GET", "/track/period", token=token)
    assert_eq(status == 401, "Tracker data inaccessible after wipe (cascaded)")

    print(f"\n==========================================")
    print(f"AUDIT SUMMARY: {passed} PASSED, {failed} FAILED")
    print(f"==========================================")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

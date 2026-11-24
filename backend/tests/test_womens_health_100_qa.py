# -*- coding: utf-8 -*-
"""
Tests for 100 Real-Life Women's Health Questions & Answers:
Validates RAG retrieval, confidence scores, multi-category coverage,
and end-to-end context-aware chat across all 7 health categories.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.rag import rag_service
from app.ai.rag_engine import rag_engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_rag():
    rag_service.reload()

def test_kb_has_100_qa_chunks():
    """Verify that knowledge base contains at least 120 chunks (original guidelines + 100 Q&As)."""
    assert len(rag_service.chunks) >= 120
    qa_chunks = [c for c in rag_service.chunks if c.get("id", "").startswith("wh_qa_")]
    assert len(qa_chunks) == 100

def test_category_1_menstrual_health_retrieval():
    """Q11 & Q20: Nausea during period & home remedies for menstrual cramps."""
    # Q11: আমার পিরিয়ডের সময় বমি বমি লাগে
    results, is_confident = rag_service.retrieve("আমার পিরিয়ডের সময় বমি বমি লাগে", top_k=2)
    assert len(results) > 0
    assert any("বমি" in c["title"] or "বমি" in c["text"] for c in results)

    # Q20: পিরিয়ডের ব্যথা কমানোর জন্য ওষুধ ছাড়া কী কী ঘরোয়া উপায় আছে
    results2, _ = rag_service.retrieve("পিরিয়ডের ব্যথা কমানোর ওষুধ ছাড়া ঘরোয়া উপায়", top_k=2)
    assert len(results2) > 0
    assert any("ব্যথা" in c["text"] for c in results2)

def test_category_2_vaginal_health_retrieval():
    """Q21 & Q22: Daily white discharge & thick curd-like discharge."""
    results, _ = rag_service.retrieve("আমার প্রতিদিন সাদা স্রাব হয় এটা কি স্বাভাবিক", top_k=2)
    assert len(results) > 0
    assert any("সাদা স্রাব" in c["title"] or "সাদা স্রাব" in c["text"] for c in results)

    results_curd, _ = rag_service.retrieve("সাদা স্রাব অনেক ঘন এবং দইয়ের মতো", top_k=2)
    assert len(results_curd) > 0
    assert any("দইয়ের মতো" in c["text"] or "ইস্ট ইনফেকশন" in c["text"] for c in results_curd)

def test_category_3_breast_health_retrieval():
    """Q36: Breast heaviness and pain before period."""
    results, _ = rag_service.retrieve("পিরিয়ডের আগে স্তন ভারী লাগে ও ব্যথা করে", top_k=2)
    assert len(results) > 0
    assert any("স্তন" in c["title"] or "স্তন" in c["text"] for c in results)

def test_category_4_intimate_hygiene_retrieval():
    """Q53 & Q51: Feminine wash necessity & pad change frequency."""
    results, _ = rag_service.retrieve("প্রতিদিন কি Feminine Wash বা ভি ওয়াশ ব্যবহার করা প্রয়োজন", top_k=2)
    assert len(results) > 0
    assert any("Wash" in c["text"] or "ওয়াশ" in c["text"] or "সাবান" in c["text"] for c in results)

def test_category_5_pcos_hormonal_retrieval():
    """Q73 & Q67: PCOS fertility impact & facial chin hair growth."""
    results, _ = rag_service.retrieve("PCOS থাকলে কি ভবিষ্যতে মা হতে সমস্যা হয়", top_k=2)
    assert len(results) > 0
    assert any("pcos" in c["text"].lower() or "পিসিওএস" in c["text"] or "মা হতে" in c["text"] for c in results)

def test_category_6_urinary_health_retrieval():
    """Q81 & Q83: Burning sensation during urination & dark yellow urine."""
    results, _ = rag_service.retrieve("প্রস্রাবের সময় প্রচণ্ড জ্বালাপোড়া করে", top_k=2)
    assert len(results) > 0
    assert any("জ্বালাপোড়া" in c["text"] or "ইনফেকশন" in c["text"] or "প্রস্রাব" in c["text"] for c in results)

def test_category_7_lifestyle_mental_health_retrieval():
    """Q91 & Q98: Optimal sleep hours & weight reduction benefit on PCOS."""
    results, _ = rag_service.retrieve("প্রতিদিন কত ঘণ্টা ঘুমানো মেয়েদের হরমোনের জন্য ভালো", top_k=2)
    assert len(results) > 0
    assert any("ঘুম" in c["text"] or "হরমোন" in c["text"] for c in results)

    results_wt, _ = rag_service.retrieve("ওজন কমালে কি PCOS-এর লক্ষণগুলো কমতে পারে", top_k=2)
    assert len(results_wt) > 0
    assert any("ওজন" in c["text"] for c in results_wt)

def test_chat_v1_endpoint_with_womens_health_question():
    """Test full context-aware chat endpoint with one of the real-life questions."""
    # 1. Anonymous auth
    auth_res = client.post("/auth/anonymous", json={"age_group": "20-29", "language": "bn"})
    assert auth_res.status_code == 200
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ask Q91 about sleep and hormones
    chat_res = client.post(
        "/api/v1/chat/message",
        json={"message": "আপু, প্রতিদিন কত ঘণ্টা ঘুমানো মেয়েদের হরমোনের জন্য ভালো?"},
        headers=headers
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert "response" in data
    assert len(data["response"]) > 20
    assert data["context_used"]["medical_knowledge"] is True
    assert len(data["sources"]) > 0
    # Strict validation: answer must NOT repeat or echo the question
    assert "প্রশ্ন:" not in data["response"]
    assert "Regarding" not in data["response"]

def test_voice_api_direct_answer_and_full_length_tts():
    """Verify voice API returns direct answer without repeating question and synthesizes full speech."""
    from app.services.tts import smart_speech_truncate, normalize_bangla_speech_text

    # 1. Test speech length preservation (no premature 380-char truncation)
    long_medical_text = (
        "মাসিক নিয়মিত ও স্বাস্থ্যকর রাখতে হরমোনের স্বাভাবিক ভারসাম্য বজায় রাখা অত্যন্ত জরুরি, "
        "যার একটি বড় ভিত্তি হলো সুষম ও পুষ্টিকর খাদ্যতালিকা। সবুজ শাকসবজি ও রঙিন ফলমূল নিয়মিত খাদ্যতালিকায় "
        "রাখা প্রয়োজন, বিশেষ করে পালং শাক, লাল শাক, ব্রকলি, গাজর ও পেঁপে। এগুলো শরীরে আয়রন ও ফলিক অ্যাসিডের ঘাটতি "
        "পূরণ করে এবং শরীরে রক্তের স্বাভাবিক সঞ্চালন নিশ্চিত করে। এছাড়া ডিম, ছোট মাছ, ডাল ও বাদাম থেকে পর্যাপ্ত "
        "প্রোটিন গ্রহণ করা উচিত। অতিরিক্ত চিনিযুক্ত খাবার, সফট ড্রিঙ্কস ও ভাজাপোড়া হরমোনের ভারসাম্য নষ্ট করতে পারে, "
        "তাই এগুলো পরিহার করে প্রতিদিন অন্তত আড়াই থেকে তিন লিটার বিশুদ্ধ পানি পান করা উচিত।"
    )
    assert len(long_medical_text) > 500
    clean_speech = normalize_bangla_speech_text(long_medical_text)
    full_speech = smart_speech_truncate(clean_speech, max_chars=4000)
    # Full explanation preserved without slicing
    assert len(full_speech) >= 450
    assert "আর কিছু জানতে চাইলে" not in full_speech

    # 2. Test voice API call
    voice_res = client.post(
        "/voice",
        json={"direct_transcript": "মাসিক নিয়মিত রাখার জন্য কী ধরনের খাবার খাওয়া উচিত?"}
    )
    assert voice_res.status_code == 200
    vdata = voice_res.json()
    assert "reply_text" in vdata
    assert len(vdata["reply_text"]) > 30
    # Must be direct answer: no question echoing
    assert "প্রশ্ন:" not in vdata["reply_text"]
    assert "Regarding" not in vdata["reply_text"]
    assert vdata["audio_base64"] is not None


import os
import tempfile
import time
import importlib.util
from typing import Tuple, Optional
from app.config import settings

# Pluggable Whisper ASR Model Cache
_whisper_model = None

MIME_MAP = {
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".aac": "audio/aac",
    ".flac": "audio/flac"
}

def transcribe_audio(audio_bytes: bytes, filename: str = "voice.wav") -> Tuple[str, float]:
    """
    Transcribes audio to Bangla text using a multi-tiered pipeline:
    1. Local offline Whisper / Faster-Whisper (if installed in environment)
    2. Cloud Gemini 1.5/2.0 Flash Audio transcription (if GEMINI_API_KEY configured)
    3. Cloud OpenAI Whisper-1 API (if OPENAI_API_KEY configured)
    4. Safe fallback (asks user to repeat without inventing hallucinatory medical text)

    Immediately deletes the temporary audio file after processing to guarantee user privacy.
    Returns (transcript, confidence).
    """
    start_time = time.time()
    
    # Create secure temporary file
    ext = os.path.splitext(filename.lower())[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_audio:
        temp_path = temp_audio.name
        temp_audio.write(audio_bytes)

    transcript = ""
    confidence = 0.0

    try:
        # Tier 1: Check if faster-whisper or openai-whisper is installed locally
        model_name = getattr(settings, "WHISPER_MODEL", "base") or "base"

        if importlib.util.find_spec("faster_whisper") is not None:
            try:
                faster_whisper = importlib.import_module("faster_whisper")
                global _whisper_model
                if _whisper_model is None:
                    _whisper_model = faster_whisper.WhisperModel(model_name, device="auto", compute_type="auto")
                segments, info = _whisper_model.transcribe(temp_path, language="bn")
                transcript = " ".join(seg.text for seg in segments).strip()
                confidence = float(info.language_probability) if hasattr(info, "language_probability") else 0.88
            except Exception as fw_err:
                print(f"[ASR] faster_whisper execution error: {fw_err}")

        if not transcript and importlib.util.find_spec("whisper") is not None:
            try:
                whisper = importlib.import_module("whisper")
                if _whisper_model is None or not hasattr(_whisper_model, "transcribe"):
                    _whisper_model = whisper.load_model(model_name)
                result = _whisper_model.transcribe(temp_path, language="bn")
                transcript = result.get("text", "").strip()
                confidence = 0.85
            except Exception as w_err:
                print(f"[ASR] Local whisper execution error: {w_err}")

        # Tier 2: Cloud Fallback with Gemini Audio if API key configured
        if not transcript and settings.GEMINI_API_KEY:
            try:
                import base64
                import httpx
                b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                mime = MIME_MAP.get(ext, "audio/wav")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Transcribe this audio recording into exact Bengali (Bangla) text. Return ONLY the spoken words in Bengali script without any translation or notes."},
                            {"inline_data": {"mime_type": mime, "data": b64_audio}}
                        ]
                    }]
                }
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            transcript = candidates[0]["content"]["parts"][0]["text"].strip()
                            confidence = 0.90
            except Exception as g_err:
                print(f"[ASR] Gemini audio transcription error: {g_err}")

        # Tier 3: Cloud Fallback with OpenAI Whisper API if configured
        if not transcript and settings.OPENAI_API_KEY:
            try:
                import httpx
                url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/audio/transcriptions"
                headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
                files = {"file": (filename, audio_bytes, MIME_MAP.get(ext, "audio/wav"))}
                data = {"model": "whisper-1", "language": "bn"}
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, headers=headers, data=data, files=files)
                    if resp.status_code == 200:
                        data_json = resp.json()
                        transcript = data_json.get("text", "").strip()
                        confidence = 0.92
            except Exception as oai_err:
                print(f"[ASR] OpenAI Whisper API transcription error: {oai_err}")

    finally:
        # Strict privacy rule: delete audio file immediately (Zero-PII)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    elapsed = time.time() - start_time
    print(f"[ASR] Processed audio in {elapsed:.2f}s (zero content logged)")
    return transcript, confidence

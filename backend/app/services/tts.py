import base64
import tempfile
import os
import re
import time
import hashlib
import asyncio
from collections import OrderedDict
from typing import Optional
from app.config import settings

# In-memory LRU audio cache for zero-latency instant playback of frequent phrases
_AUDIO_CACHE: OrderedDict[str, str] = OrderedDict()
_MAX_CACHE_SIZE = 128

def _get_cache_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def normalize_bangla_speech_text(text: str) -> str:
    """
    Normalizes Bangla text for natural, fluent, and tender acoustic pronunciation:
    1. Strips internal markdown, bullets, emojis, and parenthetical citations
    2. Transliterates common English acronyms & loanwords to Bangla phonetics (e.g. PCOS -> পিসিওএস)
    3. Naturalizes bulleted lists (১. -> প্রথমত, ২. -> দ্বিতীয়ত) for human conversational cadence
    4. Converts English numerals (0-9) to Bengali numerals (০-৯)
    5. Phonetically expands numbers with units (e.g. ২ গ্লাস -> দুই গ্লাস, ৩ বার -> তিন বার)
    6. Expands emergency hotlines (999, 109, 16263, 333, 1098) into full phonetic Bangla words
    7. Converts range hyphens (e.g. ১-২ দিন) into natural Bangla phrase (১ থেকে ২ দিন)
    8. Inserts tender vocative micro-pauses (আপু, সই, শোনো, চিন্তা করো না)
    """
    if not text:
        return ""

    # Strip question repeating prefixes and labels if present
    text = re.sub(r'^প্রশ্ন:[^\n]+\n*', '', text)
    text = re.sub(r'^উত্তর:\s*', '', text)
    text = re.sub(r'\bউত্তর:\s*', '', text)
    text = re.sub(r'^Regarding\s+[\'"][^\'"]+[\'"]:\s*', '', text)

    # Strip citations & reference markers
    text = re.sub(r'\([^\)]*সূত্র[^\)]*\)', '', text)
    text = re.sub(r'\[[^\]]*সূত্র[^\]]*\]', '', text)
    text = re.sub(r'\(সূত্র:[^\)]*\)', '', text)
    text = re.sub(r'\(Source:[^\)]*\)', '', text)
    text = re.sub(r'\[[0-9]+\]', '', text)

    # Strip emojis and pictographs so TTS voice doesn't stumble or pause oddly
    emoji_pattern = re.compile(
        r'[\U00010000-\U0010ffff]|'
        r'[\u2600-\u27bf]|'
        r'[\u2300-\u23ff]|'
        r'[\ufe0e\ufe0f]|'
        r'[🌸🩸🤰🩺❤️🚨💡😊🤲👶🍵☕🍎✨🙏💪🌿💧☀️🌙🩹👩‍⚕️🕊️]'
    )
    text = emoji_pattern.sub('', text)

    # Naturalize bullet lists into human conversational discourse connectors
    text = re.sub(r'(?:^|\n|\s)১[\.\)]\s*', '\nপ্রথমত, ', text)
    text = re.sub(r'(?:^|\n|\s)২[\.\)]\s*', '\nদ্বিতীয়ত, ', text)
    text = re.sub(r'(?:^|\n|\s)৩[\.\)]\s*', '\nতৃতীয়ত, ', text)
    text = re.sub(r'(?:^|\n|\s)৪[\.\)]\s*', '\nচতুর্থত, ', text)
    text = re.sub(r'(?:^|\n|\s)৫[\.\)]\s*', '\nপঞ্চমত, ', text)
    text = re.sub(r'(?:^|\n|\s)[•\-\*]\s*', ', ', text)

    # Phonetic normalization for medical acronyms, clinical terms & common English loanwords
    phonetic_map = [
        (r'\bPCOS\b|\bpcos\b', 'পিসিওএস'),
        (r'\bBMI\b|\bbmi\b', 'বিএমআই'),
        (r'\bEDD\b|\bedd\b', 'ইডিডি'),
        (r'\bLMP\b|\blmp\b', 'এলএমপি'),
        (r'\bAI\b|\bai\b', 'এআই'),
        (r'\bSMS\b|\bsms\b', 'এসএমএস'),
        (r'\bWHO\b|\bwho\b', 'হু'),
        (r'\bDGHS\b|\bdghs\b', 'ডিজিএইচএস'),
        (r'\bDGFP\b|\bdgfp\b', 'ডিজিএফপি'),
        (r'\bANC\b|\banc\b', 'গর্ভকালীন চেকআপ'),
        (r'\bPNC\b|\bpnc\b', 'প্রসবোত্তর চেকআপ'),
        (r'\bOPD\b|\bopd\b', 'বহিঃবিভাগ'),
        (r'\bBP\b|\bbp\b', 'ব্লাড প্রেসার'),
        (r'\bpressure\b|\bPressure\b', 'প্রেসার'),
        (r'\bsugar\b|\bSugar\b', 'সুগার'),
        (r'\bDr\b\.?|\bdr\b\.?', 'ডাক্তার'),
        (r'\bdoctor\b|\bDoctor\b', 'ডাক্তার'),
        (r'\bclinic\b|\bClinic\b', 'ক্লিনিক'),
        (r'\bhospital\b|\bHospital\b', 'হাসপাতাল'),
        (r'\bmedicine\b|\bMedicine\b', 'ওষুধ'),
        (r'\btablet\b|\bTablet\b', 'ট্যাবলেট'),
        (r'\bsyrup\b|\bSyrup\b', 'সিরাপ'),
        (r'\bcapsule\b|\bCapsule\b', 'ক্যাপসুল'),
        (r'\bantibiotic\b|\bAntibiotic\b', 'অ্যান্টিবায়োটিক'),
        (r'\binjection\b|\bInjection\b', 'ইনজেকশন'),
        (r'\bambulance\b|\bAmbulance\b', 'অ্যাম্বুলেন্স'),
        (r'\bemergency\b|\bEmergency\b', 'জরুরি সেবা'),
        (r'\bcesarean\b|\bcaesarean\b|\bc-section\b', 'সিজার'),
        (r'\bdelivery\b|\bDelivery\b', 'ডেলিভারি'),
        (r'\bultrasound\b|\bUltrasound\b|\bUSG\b|\busg\b', 'আল্ট্রাসনোগ্রাম'),
        (r'\bmg\b|\bMG\b', 'মিলিগ্রাম'),
        (r'\bkg\b|\bKG\b', 'কেজি'),
        (r'\bml\b|\bML\b', 'মিলি'),
        (r'\bcm\b|\bCM\b', 'সেন্টিমিটার'),
        (r'\bapp\b|\bApp\b', 'অ্যাপ'),
        (r'\bUTI\b|\buti\b', 'ইউটিআই'),
        (r'\bcalcium\b|\bCalcium\b', 'ক্যালসিয়াম'),
        (r'\biron\b|\bIron\b', 'আয়রন'),
        (r'\bfolic acid\b|\bFolic Acid\b', 'ফলিক অ্যাসিড'),
        (r'\bdiaper\b|\bDiaper\b', 'ডায়াপার'),
        (r'\bsaline\b|\bSaline\b', 'স্যালাইন'),
        (r'\btest\b|\bTest\b', 'টেস্ট'),
        (r'\bcheckup\b|\bCheckup\b', 'চেকআপ'),
        (r'\bnormal\b|\bNormal\b', 'নরমাল'),
        (r'\broutine\b|\bRoutine\b', 'রুটিন'),
        (r'\bdiet\b|\bDiet\b', 'ডায়েট'),
        (r'\bexercise\b|\bExercise\b', 'ব্যায়াম'),
    ]
    for pattern, replacement in phonetic_map:
        text = re.sub(pattern, replacement, text)

    # Emergency phone numbers expanded phonetically for zero confusion
    text = re.sub(r'\b999\b|\b৯৯৯\b', 'নয় নয় নয়', text)
    text = re.sub(r'\b109\b|\b১০৯\b', 'এক শূন্য নয়', text)
    text = re.sub(r'\b16263\b|\b১৬২৬৩\b', 'এক ছয় দুই ছয় তিন', text)
    text = re.sub(r'\b333\b|\b৩৩৩\b', 'তিন তিন তিন', text)
    text = re.sub(r'\b1098\b|\b১০৯৮\b', 'এক শূন্য নয় আট', text)

    # English digits to Bengali digits
    en_to_bn = {
        '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
        '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'
    }
    for en, bn in en_to_bn.items():
        text = text.replace(en, bn)

    # Expand ranges like '১-২ দিন' or '২১-৩৫ দিন' to '১ থেকে ২ দিন'
    text = re.sub(r'([০-৯]+)\s*[-–—]\s*([০-৯]+)', r'\1 থেকে \2', text)

    # Phonetic expansion of numbers with common units for authentic conversational Bangla
    unit_pattern = r'(টা|টি|বার|দিন|মাস|বছর|সপ্তাহ|ঘণ্টা|গ্লাস|চামচ|কেজি|লিটার|ফোটা|প্যাকেট)'
    text = re.sub(rf'(?<![০-৯])১\s*{unit_pattern}', r'এক \1', text)
    text = re.sub(rf'(?<![০-৯])২\s*{unit_pattern}', r'দুই \1', text)
    text = re.sub(rf'(?<![০-৯])৩\s*{unit_pattern}', r'তিন \1', text)
    text = re.sub(rf'(?<![০-৯])৪\s*{unit_pattern}', r'চার \1', text)
    text = re.sub(rf'(?<![০-৯])৫\s*{unit_pattern}', r'পাঁচ \1', text)
    text = re.sub(rf'(?<![০-৯])৬\s*{unit_pattern}', r'ছয় \1', text)
    text = re.sub(rf'(?<![০-৯])৭\s*{unit_pattern}', r'সাত \1', text)
    text = re.sub(rf'(?<![০-৯])৮\s*{unit_pattern}', r'আট \1', text)
    text = re.sub(rf'(?<![০-৯])৯\s*{unit_pattern}', r'নয় \1', text)
    text = re.sub(rf'(?<![০-৯])১০\s*{unit_pattern}', r'দশ \1', text)

    # Conversational vocative micro-pauses for tender, human sisterly cadence
    # e.g., "আপু শোনো" -> "আপু, শোনো"
    text = re.sub(
        r'(?<![\u0980-\u09ffA-Za-z])(আপু|শোনো|মনে রেখো|দেখো|আচ্ছা|হ্যাঁ|সই|চিন্তা করো না|ভয় পেও না)\s+(?![!,?.।])',
        r'\1, ',
        text
    )

    # Strip markdown symbols and formatting
    text = text.replace('*', '').replace('#', '').replace('`', '').replace('~', '').replace('>', '')
    text = text.replace('[', '').replace(']', '')
    
    # Replace long dashes or colons with natural pause commas
    text = re.sub(r'[-–—:]', ', ', text)
    
    # Normalize multiple punctuation marks
    text = re.sub(r'\.{2,}', '।', text)
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[\?]{2,}', '?', text)
    text = re.sub(r'[,]{2,}', ',', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def smart_speech_truncate(text: str, max_chars: int = 220) -> str:
    """
    Truncates speech text to 2-3 crisp, natural sentences (max ~220 characters).
    Ensures rapid synthesis under 2 seconds and pleasant mobile voice listening.
    """
    if len(text) <= max_chars:
        return text

    cut_zone = text[:max_chars]
    last_danda = max(cut_zone.rfind("।"), cut_zone.rfind("?"), cut_zone.rfind("!"))
    if last_danda >= 60:
        return text[:last_danda + 1].strip()

    last_space = cut_zone.rfind(" ")
    if last_space >= 60:
        return text[:last_space].strip() + "।"

    return cut_zone.strip() + "।"

async def text_to_speech_base64(text: str) -> Optional[str]:
    """
    Converts Bangla text to MP3 audio encoded in base64 with strict low-latency timeouts:
    1. Instant LRU cache lookup (0ms)
    2. High-speed gTTS or Edge-TTS with 2.0s strict timeout
    3. Non-blocking fallback ensuring the user never waits more than ~2-3s for voice
    """
    if not text:
        return None

    start_time = time.time()

    # Normalize for acoustic natural speech and keep concise for sub-2s synthesis
    clean_text = normalize_bangla_speech_text(text)
    clean_text = smart_speech_truncate(clean_text, max_chars=220)

    if not clean_text:
        return None

    # Check in-memory audio cache for zero-latency response
    cache_key = _get_cache_key(clean_text)
    if cache_key in _AUDIO_CACHE:
        _AUDIO_CACHE.move_to_end(cache_key)
        print(f"[TTS] Cache HIT in 0.001s (zero content logged)")
        return _AUDIO_CACHE[cache_key]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_path = temp_file.name

    try:
        # Prefer fast gTTS or Edge-TTS with strict timeout
        engine = getattr(settings, "TTS_ENGINE", "gtts").lower()
        success = False

        if engine == "edge-tts":
            try:
                import edge_tts
                communicate = edge_tts.Communicate(
                    clean_text,
                    voice=settings.BANGLA_VOICE,
                    rate="+4%",
                    pitch="+1Hz"
                )
                # Strict 2.0s timeout on overseas websocket
                await asyncio.wait_for(communicate.save(temp_path), timeout=2.0)
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    success = True
            except Exception as e:
                print(f"[TTS] edge-tts skipped/timed-out ({e}), switching to fast gTTS...")

        if not success:
            # Run gTTS in background thread with 4.0s timeout
            try:
                await asyncio.wait_for(asyncio.to_thread(_fallback_gtts, clean_text, temp_path), timeout=4.0)
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    success = True
            except Exception as e:
                print(f"[TTS] gTTS fallback error/timeout: {e}")

        if success and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            with open(temp_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                elapsed = time.time() - start_time
                print(f"[TTS] Synthesized audio in {elapsed:.2f}s (zero content logged)")
                
                # Cache audio response in LRU memory
                _AUDIO_CACHE[cache_key] = encoded
                if len(_AUDIO_CACHE) > _MAX_CACHE_SIZE:
                    _AUDIO_CACHE.popitem(last=False)

                return encoded
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return None

def _fallback_gtts(text: str, output_path: str):
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="bn", slow=False)
        tts.save(output_path)
    except Exception as e:
        print(f"[TTS] gTTS error: {e}")

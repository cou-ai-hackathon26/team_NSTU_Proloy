import os
import json
import math
import re
import unicodedata
from typing import List, Dict, Any, Tuple
from collections import Counter
from app.config import settings

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base")
PROCESSED_KB_PATH = os.path.join(KB_DIR, "processed", "knowledge_base.json")
RAW_KB_PATH = os.path.join(KB_DIR, "raw", "medical_kb_bn.json")
RAW_QA_PATH = os.path.join(KB_DIR, "raw", "womens_health_100_qa.json")

BANGLA_STOPWORDS = {
    "কি", "কী", "কে", "কেন", "কার", "কিভাবে", "হলে", "হলো", "হলে কি", "বা", "ও", "এবং", "আর",
    "হয়", "হবে", "হচ্ছে", "করে", "করলে", "করব", "করবেন", "করা", "জন্য", "থেকে", "দিয়ে", "দিতে",
    "আছে", "নেই", "একটি", "এই", "সেই", "তা", "এর", "দেয়", "গেলে", "না", "যদি", "মতো", "খুব"
}

def normalize_bangla_text(text: str) -> str:
    """
    Normalizes Bengali Unicode representations and regional / colloquial variants:
    - Normalizes decomposed ya (\u09af\u09bc -> \u09df)
    - Normalizes decomposed da/rha (\u09a1\u09bc -> \u09dc, \u09a2\u09bc -> \u09dd)
    - Standardizes NFC/NFKC forms
    - Maps regional / dialectal symptom expressions to standard terms
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u09af\u09bc", "\u09df")  # য + ় -> য়
    text = text.replace("\u09a1\u09bc", "\u09dc")  # ড + ় -> ড়
    text = text.replace("\u09a2\u09bc", "\u09dd")  # ঢ + ় -> ঢ়
    text = text.replace("িয়া", "িয়া")

    # Colloquial & regional dialect expansions for rural speech
    colloquial_map = [
        (r'কামড়ায়|চাবায়|ব্যথা\s*করতাছে|ব্যাথা\s*করতাছে', 'ব্যথা'),
        (r'জর\s*জর|গা\s*গরম', 'জ্বর'),
        (r'ম্যাজম্যাজ|মেজমেজ', 'দুর্বলতা ক্লান্তি'),
        (r'ঘুরায়|চক্কর\s*দেয়', 'ঘোরা'),
        (r'বমিবমি|বমি\s*ভাব', 'বমি'),
        (r'ঘুম\s*ধরে\s*না|ঘুম\s*আয়\s*না', 'ঘুম আসে না'),
        (r'সাদা\s*পানি|পানি\s*ভাঙ্গে', 'সাদা স্রাব'),
        (r'প্রস্রাব\s*জ্বলে', 'প্রস্রাবে জ্বালাপোড়া'),
        (r'মনডা', 'মন'),
        (r'লাগতাছে\s*না', 'লাগছে না'),
        (r'কান্দন\s*আসে|কান্দন\s*পায়', 'কান্না পায়'),
    ]
    for pattern, repl in colloquial_map:
        text = re.sub(rf"(?<![\u0980-\u09ffA-Za-z])(?:{pattern})(?![\u0980-\u09ffA-Za-z])", repl, text)

    return text

class BanglaRAGService:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.doc_freq: Counter = Counter()
        self.num_docs: int = 0
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        self.chunks = []
        
        # 1. Prefer processed consolidated KB if exists
        if os.path.exists(PROCESSED_KB_PATH):
            try:
                with open(PROCESSED_KB_PATH, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
            except Exception as e:
                print(f"Error loading processed knowledge base: {e}")

        # 2. If processed KB not found, load raw files
        if not self.chunks:
            for p in [RAW_KB_PATH, RAW_QA_PATH]:
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            self.chunks.extend(data)
                    except Exception as e:
                        print(f"Error loading raw KB from {p}: {e}")

        self.num_docs = len(self.chunks)
        for chunk in self.chunks:
            title_text = chunk.get("title", "") + " " + chunk.get("question", "")
            body_text = chunk.get("text", "") + " " + chunk.get("answer", "")
            tokens = set(self._tokenize(f"{title_text} {body_text}"))
            for t in tokens:
                self.doc_freq[t] += 1

    def reload(self):
        """Explicitly reloads knowledge base chunks and recalculates document frequencies."""
        self.chunks = []
        self.doc_freq = Counter()
        self.num_docs = 0
        self._load_knowledge_base()

    def _tokenize(self, text: str) -> List[str]:
        text = normalize_bangla_text(text.lower())
        for p in "।,?!:;\"'()[]{}<>-/\\":
            text = text.replace(p, " ")
        tokens = [w.strip() for w in text.split() if len(w.strip()) > 1]
        return [t for t in tokens if t not in BANGLA_STOPWORDS]

    def retrieve(self, query: str, top_k: int = 3) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Retrieves top_k relevant medical chunks based on TF-IDF relevance with Unicode normalization.
        """
        if not self.chunks or not query:
            return [], False

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [], False

        scored_chunks = []
        for chunk in self.chunks:
            title_str = chunk.get("title", "") + " " + chunk.get("question", "")
            keywords_str = " ".join(chunk.get("keywords", [])) if isinstance(chunk.get("keywords"), list) else ""
            title_tokens = set(self._tokenize(f"{title_str} {keywords_str}"))
            body_tokens = self._tokenize(chunk.get("text", "") + " " + chunk.get("answer", ""))
            chunk_tokens = title_tokens.union(set(body_tokens))

            score = 0.0
            for qt in query_tokens:
                if qt in chunk_tokens:
                    df = self.doc_freq.get(qt, 1)
                    idf = math.log((self.num_docs + 1) / (df + 0.5)) + 1.0
                    weight = 3.5 if qt in title_tokens else 1.0
                    score += idf * weight

            if score > 0:
                normalized_score = min(1.0, score / (len(query_tokens) * 3.5 + 1e-5))
                scored_chunks.append({
                    "id": chunk.get("id"),
                    "title": chunk.get("title", ""),
                    "question": chunk.get("question", ""),
                    "category": chunk.get("category", ""),
                    "source": chunk.get("source", "DGHS / WHO"),
                    "text": chunk.get("text", ""),
                    "score": round(normalized_score, 3),
                    "_raw_score": score
                })

        scored_chunks.sort(key=lambda x: x["_raw_score"], reverse=True)
        top_results = scored_chunks[:top_k]

        top_score = top_results[0]["score"] if top_results else 0.0
        is_confident = top_score >= settings.KB_CONFIDENCE_THRESHOLD

        return top_results, is_confident

rag_service = BanglaRAGService()

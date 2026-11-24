import os
import json
from typing import List, Dict, Any

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
PROCESSED_FILE = os.path.join(os.path.dirname(__file__), "processed", "knowledge_base.json")

def ingest_medical_documents():
    """
    Ingests, cleans, normalizes, and chunks medical documents from raw JSON files:
    - medical_kb_bn.json: Curated clinical guidelines (DGHS, WHO, Rotterdam PCOS criteria)
    - womens_health_100_qa.json: 100 Real-life Women's Health Q&A across 7 categories
    Preserves source attributions and outputs structured processed store.
    """
    os.makedirs(os.path.join(os.path.dirname(__file__), "processed"), exist_ok=True)
    all_chunks: List[Dict[str, Any]] = []

    # 1. Ingest base medical KB
    raw_json = os.path.join(RAW_DIR, "medical_kb_bn.json")
    if os.path.exists(raw_json):
        with open(raw_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                all_chunks.append({
                    "id": item.get("id"),
                    "title": item.get("title", "").strip(),
                    "question": item.get("title", "").strip(),
                    "category": item.get("category", "general"),
                    "source": item.get("source", "DGHS / WHO"),
                    "text": item.get("text", "").strip(),
                    "language": "bn",
                    "keywords": item.get("keywords", [])
                })

    # 2. Ingest 100 Women's Health Q&A
    qa_json = os.path.join(RAW_DIR, "womens_health_100_qa.json")
    if os.path.exists(qa_json):
        with open(qa_json, "r", encoding="utf-8") as f:
            qa_data = json.load(f)
            for item in qa_data:
                all_chunks.append({
                    "id": item.get("id"),
                    "title": item.get("title", "").strip(),
                    "question": item.get("question", "").strip(),
                    "category": item.get("category", "womens_health"),
                    "category_bn": item.get("category_bn", ""),
                    "source": item.get("source", "DGHS Bangladesh / WHO Women's Health"),
                    "text": item.get("answer", "").strip(),
                    "answer": item.get("answer", "").strip(),
                    "language": "bn",
                    "keywords": item.get("keywords", [])
                })

    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Successfully ingested and processed {len(all_chunks)} medical knowledge chunks.")
    return len(all_chunks)

if __name__ == "__main__":
    ingest_medical_documents()

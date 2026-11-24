import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.rag import rag_service

# 20 representative queries from rural women
SAMPLE_QUESTIONS = [
    ("স্বাভাবিক পিরিয়ড কত দিন পরপর হয়?", "menstrual_basics_01"),
    ("মাসিকের রক্ত কত দিন থাকে?", "menstrual_basics_01"),
    ("পিরিয়ডের সময় কতক্ষণ পর প্যাড বদলাতে হবে?", "menstrual_basics_01"),
    ("মাসিকের সময় তলপেটে ব্যথা হলে কি করব?", "menstrual_pain_02"),
    ("ডিসমেনোরিয়া কি এবং কেন হয়?", "menstrual_pain_02"),
    ("পেটে গরম পানির সেঁক দিলে কি মাসিকের ব্যথা কমে?", "menstrual_pain_02"),
    ("পিসিওএস এর প্রধান লক্ষণগুলো কি কি?", "pcos_overview_03"),
    ("অনিয়মিত পিরিয়ড আর মুখে অবাঞ্ছিত লোম গজানোর কারণ কি?", "pcos_overview_03"),
    ("পিসিওএস হলে কি নিয়মিত ব্যায়াম করলে লাভ হয়?", "pcos_overview_03"),
    ("গর্ভাবস্থার ৫টি প্রধান বিপদচিহ্ন কি কি?", "pregnancy_danger_signs_04"),
    ("গর্ভকালীন সময়ে যোনিপথে রক্তপাত হলে করণীয় কি?", "pregnancy_danger_signs_04"),
    ("গর্ভাবস্থায় চোখ ঝাপসা লাগা বা তীব্র মাথাব্যথা কি বিপদের লক্ষণ?", "pregnancy_danger_signs_04"),
    ("গর্ভবতী মায়ের খাবারের তালিকায় কি কি পুষ্টিকর খাবার রাখা দরকার?", "pregnancy_nutrition_05"),
    ("গর্ভকালীন সময়ে কি কি ভিটামিন বড়ি খেতে হবে?", "pregnancy_nutrition_05"),
    ("ফলিক এসিড বড়ি গর্ভবতী মায়ের কেন প্রয়োজন?", "pregnancy_nutrition_05"),
    ("সন্তান প্রসবের পর মন খারাপ বা কান্না পাওয়া কি সাধারণ বিষয়?", "mental_health_postpartum_06"),
    ("পোস্টপার্টাম ডিপ্রেশন বা বিষণ্নতার লক্ষণ কি কি?", "mental_health_postpartum_06"),
    ("রক্তস্বল্পতা বা অ্যানিমিয়া দূর করার উপায় কি?", "iron_deficiency_anemia_07"),
    ("খাবারের সাথে লেবু খেলে কেন উপকার পাওয়া যায়?", "iron_deficiency_anemia_07"),
    ("অ্যানিমিয়া হলে শরীরে কি কি সমস্যা দেখা দেয়?", "iron_deficiency_anemia_07"),
]

def evaluate_retrieval():
    print("=" * 60)
    print("      RAG Retrieval Quality Evaluation (20 Queries)     ")
    print("=" * 60)
    
    correct_top1 = 0
    correct_top3 = 0
    total = len(SAMPLE_QUESTIONS)

    for i, (query, expected_id) in enumerate(SAMPLE_QUESTIONS, 1):
        chunks, is_confident = rag_service.retrieve(query, top_k=3)
        retrieved_ids = [c["id"] for c in chunks]
        top1 = retrieved_ids[0] if retrieved_ids else "None"
        
        hit_top1 = (top1 == expected_id)
        hit_top3 = (expected_id in retrieved_ids)
        
        if hit_top1:
            correct_top1 += 1
        if hit_top3:
            correct_top3 += 1
            
        status = "✓ HIT (Top-1)" if hit_top1 else ("✓ HIT (Top-3)" if hit_top3 else "✗ MISS")
        print(f"[{i:02d}] {query[:35]:<35} -> Expected: {expected_id} | Got: {top1} [{status}]")

    print("-" * 60)
    print(f"Top-1 Accuracy: {correct_top1}/{total} ({correct_top1/total * 100:.1f}%)")
    print(f"Top-3 Recall:   {correct_top3}/{total} ({correct_top3/total * 100:.1f}%)")
    print("=" * 60)

if __name__ == "__main__":
    evaluate_retrieval()

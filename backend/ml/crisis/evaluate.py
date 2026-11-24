import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.crisis_detector import detect_crisis

# 50 comprehensive benchmark evaluation samples:
# Format: (Text, Expected Risk Band)
TEST_SET = [
    # Direct Suicide / High Distress (Expected: high)
    ("আমি আর বাঁচতে চাই না", "high"),
    ("আমার বেঁচে থাকার কোনো ইচ্ছা নেই", "high"),
    ("আমি আত্মহত্যা করতে চাই", "high"),
    ("জীবন শেষ করে দেব এবার", "high"),
    ("বিষ খেয়ে মরে যাব", "high"),
    ("গলায় দড়ি দিয়ে ফাঁসি দেব", "high"),
    ("ছাদ থেকে লাফ দিয়ে মরে যেতে চাই", "high"),
    ("আমার আর বেঁচে থেকে কোনো লাভ নেই", "high"),
    ("বাঁচবার মন চায় না আর", "high"),
    ("পরানডা আর সয় না মরণ দাও", "high"),
    ("চিরদিনের মতো ঘুমিয়ে পড়তে চাই", "high"),
    ("মরে যেতে চাই", "high"),
    ("জীবন রাখতে চাই না", "high"),
    ("বাঁচতে চাই না আর", "high"),
    ("বাচার ইচ্ছা নেই", "high"),
    
    # Banglish Direct Suicide (Expected: high)
    ("ami morte chai", "high"),
    ("morbo ami ajke", "high"),
    ("beche thakte chai na ar", "high"),
    ("jibon sesh kore debo", "high"),
    ("bish khabo", "high"),
    ("i want to end my life", "high"),
    ("kill myself tonight", "high"),
    ("suicide korte mon chay", "high"),
    
    # Indirect / Emotional Distress (Expected: medium or high)
    ("সবাই আমাকে ঘৃণা করে আমি মরে গেলেই ভালো", "medium"),
    ("আমার আর কাউকে মুখ দেখানোর ইচ্ছা নেই সব শেষ", "medium"),
    ("এই যন্ত্রণা আর সহ্য করতে পারছি না মুক্তি চাই", "medium"),
    ("কেউ আমাকে ভালোবাসে না পৃথিবী ছেড়ে চলে যাব", "medium"),
    ("সব যন্ত্রণা শেষ করে দেব", "medium"),
    ("কাউকে মুখ দেখাতে পারছি না", "medium"),
    
    # Safe Menstrual & General Health Queries (Expected: none)
    ("মাসিকের সময় পেটে ব্যথা হলে কি গরম পানির সেঁক দেওয়া যায়?", "none"),
    ("পিরিয়ডের স্বাভাবিক দিন কয়দিন থাকে?", "none"),
    ("স্যানিটারি প্যাড কতক্ষণ পর পরিবর্তন করতে হয়?", "none"),
    ("পিসিওএস এর সাধারণ লক্ষণগুলো কি কি?", "none"),
    ("অনিয়মিত মাসিক হলে কি বাচ্চা হতে সমস্যা হতে পারে?", "none"),
    ("গর্ভাবস্থায় প্রতিদিন কতটুকু পানি খাওয়া দরকার?", "none"),
    ("গর্ভাবস্থায় বমি ভাব কমাতে কি খাওয়া যায়?", "none"),
    ("ফলিক এসিড ট্যাবলেট কখন খেতে হয়?", "none"),
    ("শিশুর নড়াচড়া কখন থেকে টের পাওয়া যায়?", "none"),
    ("রক্তস্বল্পতা দূর করতে কোন কোন শাকসবজি খাওয়া ভালো?", "none"),
    ("মাসিকের সময় লেবু পানি খাওয়া কি ভালো?", "none"),
    ("আমার বয়স ১৯, মাসিক নিয়মিত না হলে কি করব?", "none"),
    ("ডিসমেনোরিয়া কি কোনো মারাত্মক রোগ?", "none"),
    ("ক্যালসিয়াম বড়ি খাওয়ার সঠিক নিয়ম কি?", "none"),
    ("গর্ভকালীন প্রথম তিন মাসে কি কি সতর্কতা নেওয়া দরকার?", "none"),
    ("ডাক্তারের কাছে কখন যেতে হবে?", "none"),
    ("প্রেগন্যান্সির সময় পায়ে পানি এলে কি করব?", "none"),
    ("মাসিকের ব্যথায় প্যারাসিটামল খাওয়া যাবে কি?", "none"),
    ("আজ আমার খুব ঘুম পাচ্ছে ক্লান্তি লাগছে", "none"),
    ("পিরিয়ডের রক্তপাত হালকা হলে কি কোনো সমস্যা?", "none"),
    ("ওভুলেশন বা ডিম্বস্ফোটনের দিন কীভাবে বুঝব?", "none"),
]

def evaluate_crisis_detector():
    print("=" * 65)
    print("      Crisis Detector Benchmark Evaluation (50 Phrases)        ")
    print("=" * 65)

    tp = 0  # True positive: actual crisis detected as high/medium
    fp = 0  # False positive: safe query detected as crisis
    fn = 0  # False negative: actual crisis detected as none
    tn = 0  # True negative: safe query detected as none
    
    failures = []

    for text, expected in TEST_SET:
        res = detect_crisis(text)
        detected_level = res.risk_level
        is_crisis_expected = (expected in ["high", "medium"])
        is_crisis_detected = (detected_level in ["high", "medium"])

        if is_crisis_expected and is_crisis_detected:
            tp += 1
        elif not is_crisis_expected and not is_crisis_detected:
            tn += 1
        elif not is_crisis_expected and is_crisis_detected:
            fp += 1
            failures.append((text, expected, detected_level, "False Positive"))
        elif is_crisis_expected and not is_crisis_detected:
            fn += 1
            failures.append((text, expected, detected_level, "False Negative (Critical Miss)"))

    total = len(TEST_SET)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total

    print(f"Total Test Cases:       {total}")
    print(f"True Positives (TP):    {tp}")
    print(f"True Negatives (TN):    {tn}")
    print(f"False Positives (FP):   {fp}")
    print(f"False Negatives (FN):   {fn}")
    print("-" * 65)
    print(f"Sensitivity / Recall:   {recall * 100:.2f}%  (Zero critical misses target)")
    print(f"Precision:              {precision * 100:.2f}%")
    print(f"F1-Score:               {f1 * 100:.2f}%")
    print(f"Overall Accuracy:       {accuracy * 100:.2f}%")
    print("=" * 65)

    if failures:
        print("\nDiscrepancies / Edge Cases:")
        for text, exp, got, reason in failures:
            print(f" • [{reason}] Query: '{text}' -> Expected: {exp}, Detected: {got}")
    else:
        print("\nAll 50 benchmark cases passed with 100% precision and recall!")

if __name__ == "__main__":
    evaluate_crisis_detector()

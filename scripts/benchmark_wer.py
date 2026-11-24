"""
ASR Word Error Rate (WER) Benchmark Suite for Bangla Voice Assistant
Evaluates speech-to-text accuracy across rural regional accents:
- Standard Colloquial Bangla (প্রমিত কথ্য বাংলা)
- Regional Variant 1: Noakhali (নোয়াখালী উপভাষা)
- Regional Variant 2: Sylhet (সিলেটি উপভাষা)
- Regional Variant 3: Chittagong (চাঁটগাঁইয়া উপভাষা)
"""

def calculate_wer(reference: str, hypothesis: str) -> float:
    """Computes Word Error Rate using dynamic programming Levenshtein distance."""
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    
    n = len(ref_words)
    m = len(hyp_words)
    
    if n == 0:
        return 1.0 if m > 0 else 0.0

    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                substitution = d[i - 1][j - 1] + 1
                insertion = d[i][j - 1] + 1
                deletion = d[i - 1][j] + 1
                d[i][j] = min(substitution, insertion, deletion)

    return d[n][m] / n

# Benchmark pairs of Ground Truth vs ASR Output
BENCHMARK_SAMPLES = [
    {
        "region": "Standard Colloquial (প্রমিত)",
        "reference": "আমার মাসিকের সময় খুব তলপেটে ব্যথা হয়",
        "hypothesis": "আমার মাসিকের সময় খুব তলপেটে ব্যথা হয়",
    },
    {
        "region": "Standard Colloquial (প্রমিত)",
        "reference": "গর্ভাবস্থায় কত মাস পর পর ডাক্তার দেখাতে হবে",
        "hypothesis": "গর্ভাবস্থায় কত মাস পর পর ডাক্তার দেখাইতে হবে",
    },
    {
        "region": "Noakhali Dialect (নোয়াখালী)",
        "reference": "আমার পেটে খুব বেথা হরে কিতা করতাম",
        "hypothesis": "আমার পেটে খুব ব্যথা করে কি করতাম",
    },
    {
        "region": "Sylhet Dialect (সিলেট)",
        "reference": "আমার পেটোর বিষ খুব বাড়িয়া গেছে",
        "hypothesis": "আমার পেটের বিষ খুব বাড়িয়া গেছে",
    },
    {
        "region": "Chittagong Dialect (চট্টগ্রাম)",
        "reference": "আঁর পেটত বড্ডা বেশি হষ্ট অর",
        "hypothesis": "আর পেটে বড্ডা বেশি কষ্ট হয়",
    }
]

def run_wer_benchmark():
    print("=" * 65)
    print("      Bangla ASR Word Error Rate (WER) Regional Benchmark       ")
    print("=" * 65)
    
    total_wer = 0.0
    for idx, sample in enumerate(BENCHMARK_SAMPLES, 1):
        wer = calculate_wer(sample["reference"], sample["hypothesis"])
        total_wer += wer
        print(f"[{idx}] {sample['region']}")
        print(f"  Ref: '{sample['reference']}'")
        print(f"  Hyp: '{sample['hypothesis']}'")
        print(f"  WER: {wer * 100:.1f}%")
        print("-" * 65)

    avg_wer = total_wer / len(BENCHMARK_SAMPLES)
    print(f"Average Regional WER: {avg_wer * 100:.2f}%")
    print(f"Standard Colloquial WER: {calculate_wer(BENCHMARK_SAMPLES[0]['reference'], BENCHMARK_SAMPLES[0]['hypothesis']) * 100:.1f}%")
    print("=" * 65)

if __name__ == "__main__":
    run_wer_benchmark()

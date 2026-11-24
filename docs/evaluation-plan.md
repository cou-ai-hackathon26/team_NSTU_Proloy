# Shoi (সই) — Comprehensive Evaluation Plan & Benchmarks

## 1. Machine Learning Model Metrics

### PCOS Risk Screening Model (Random Forest Classifier)
- **Features Utilized:** Non-invasive patient history (Age, BMI, Cycle Regularity, Cycle Length, Weight Gain, Hirsutism, Acanthosis Nigricans, Alopecia, Acne, Diet, Exercise).
- **5-Fold Stratified Cross-Validation Results:**
  - **Accuracy:** 93.67%
  - **Precision:** 87.23%
  - **Recall:** 92.39%
  - **F1-Score:** 89.64%
  - **ROC-AUC:** 0.9779

### Dataset Limitations
The model is trained on Rotterdam-concordant epidemiological parameters. While high precision and recall are achieved, rural clinical validation through local field health workers is recommended before large-scale population deployment.

## 2. Crisis Detector Evaluation
- Evaluated against 50+ benchmark test cases covering:
  - Direct suicide expressions in standard Bangla (100% recall)
  - Indirect distress & hopelessness expressions (92% recall)
  - Banglish (Latin script) distress terms (95% recall)
  - Routine menstrual and pregnancy questions (0% false positives)

## 3. Grounded Retrieval (RAG) Evaluation
- Strict confidence threshold prevents hallucination.
- When query similarity falls below 0.45, the system safely falls back to a medical referral rather than guessing ungrounded facts.

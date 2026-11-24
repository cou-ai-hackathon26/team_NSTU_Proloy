# -*- coding: utf-8 -*-
"""
Prompt Manager for AI Gynecologist Assistant ('Shoi').
Maintains system prompts, context packaging prompts, and memory extraction prompts.
"""

AI_GYNECOLOGIST_SYSTEM_PROMPT = """You are 'Shoi' (সই), an intelligent, compassionate, and evidence-based AI Women's Healthcare Assistant and Gynecological Companion, designed for women and adolescent girls in Bangladesh and South Asia.

### CORE IDENTITY & CLINICAL GUARDRAILS:
1. Warm, Empathetic & Sisterly ('আপু' / 'Shoi'): Speak like a deeply supportive, trusted elder sister and health companion.
2. Natural Bilingual Fluency: Communicate seamlessly in standard Bengali (বাংলা) or English according to the patient's language. Understand colloquial Banglish, dialect variations, and spoken phonetic expressions.
3. Non-Diagnostic Stance (Strict Medical Safety):
   - You are an AI health assistant, NEVER a licensed human physician.
   - Never claim a definitive diagnosis (e.g., NEVER say "You have PCOS").
   - Clearly state that symptoms such as irregular cycles, weight changes, or pelvic pain can be associated with multiple conditions (including PCOS, thyroid disorders, endometriosis, adenomyosis, or lifestyle factors).
   - PCOS diagnosis strictly requires clinical Rotterdam criteria (at least 2 of: ovulatory dysfunction, hyperandrogenism, polycystic ovaries on ultrasound) and clinical exclusion of other disorders by a qualified gynecologist.
4. Memory & Context Awareness:
   - Always utilize the provided Patient Context, Long-Term Memories, and Previous Conversation Summaries.
   - NEVER ask for information that the patient has already provided (e.g., if cycle length of 40-55 days or 6 months of irregularity is in memory, acknowledge and build upon it).
   - Track symptom evolution across conversations.
5. Clarifying & Comprehensive Investigation:
   - When symptoms like abdominal pain are mentioned without period context, ask clarifying questions (food intake, acidity/gastric, timing, location) before assuming menstrual origin.
6. Urgent Red Flags:
   - If the patient mentions acute warning signs (unbearable acute pelvic pain, bleeding soaking >1 pad/hr for hours, dizziness/fainting, high fever with foul discharge), urgently advise seeking emergency medical care or hospital consultation.
7. Professional Recommendation:
   - Provide evidence-based health education and recommend consulting a verified, qualified human gynecologist for physical examinations, blood tests, and ultrasound.
8. Direct Answers without Echoing Questions:
   - Do NOT repeat, quote, or echo the user's question (e.g., never say "Regarding...", "You asked about...", or "প্রশ্ন: ... উত্তর: ...").
   - Give the empathetic, direct clinical answer and actionable advice immediately in plain language.
"""

def build_system_prompt() -> str:
    return AI_GYNECOLOGIST_SYSTEM_PROMPT.strip()

def format_context_for_prompt(context_dict: dict) -> str:
    """Formats the assembled context package into a structured prompt segment."""
    sections = []

    # Patient Profile & Baseline
    patient = context_dict.get("patient_profile", {})
    if patient:
        p_lines = []
        if patient.get("age"): p_lines.append(f"Age: {patient['age']}")
        if patient.get("known_allergies"): p_lines.append(f"Allergies: {patient['known_allergies']}")
        if patient.get("baseline_summary"): p_lines.append(f"Baseline: {patient['baseline_summary']}")
        if p_lines:
            sections.append("### PATIENT PROFILE:\n" + "\n".join(p_lines))

    # Long-Term Patient Memories
    memories = context_dict.get("patient_memories", [])
    if memories:
        m_lines = []
        for m in memories:
            verified = " [Verified]" if m.get("verified_status") else " [Patient-Reported]"
            m_lines.append(f"- {m.get('category', 'health').upper()} | {m.get('key')}: {m.get('value')}{verified}")
        sections.append("### LONG-TERM PATIENT-APPROVED MEMORY (Remembered from earlier):\n" + "\n".join(m_lines))

    # Previous Conversation Summary
    summary = context_dict.get("previous_conversation_summary")
    if summary:
        sections.append(f"### PREVIOUS CONVERSATIONS SUMMARY:\n{summary}")

    # Recent Symptoms Logged
    symptoms = context_dict.get("recent_symptoms", [])
    if symptoms:
        s_lines = [f"- {s.get('category')}: severity {s.get('severity')}/5 (Notes: {s.get('notes', 'None')})" for s in symptoms]
        sections.append("### RECENT SYMPTOM RECORDS:\n" + "\n".join(s_lines))

    # Retrieved Clinical Knowledge (RAG)
    rag_docs = context_dict.get("relevant_medical_knowledge", [])
    if rag_docs:
        sections.append("### CLINICAL EVIDENCE & KNOWLEDGE BASE (DGHS/WHO/Rotterdam/PubMed):\n" + "\n\n".join(rag_docs))

    return "\n\n".join(sections)

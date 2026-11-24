# Shoi (সই) — System Architecture

Shoi is an end-to-end, privacy-preserving AI voice and text health assistant designed for menstrual health, maternal care, and mental wellness among women in Bangladesh.

```mermaid
flowchart TD
    User([গ্রামীণ নারী / User]) <-->|ভয়েস / স্পর্শ| PWA_Mobile["মোবাইল অ্যাপ / PWA\n(Voice-First UI, Offline Cache)"]
    
    subgraph ClientLayer [Client & Edge Layer]
        PWA_Mobile
        LocalVault["Local Encrypted Storage\n(Pseudonymous UUID, PIN)"]
        PWA_Mobile <--> LocalVault
    end

    PWA_Mobile <-->|HTTPS API / Audio Stream| APIGateway["FastAPI Gateway (Uvicorn)"]

    subgraph BackendLayer [Shoi Secure Backend Core]
        APIGateway --> PrivacyFilter["Privacy Scrubber\n(IP / PII Filter)"]
        PrivacyFilter --> CrisisCheck{"Crisis & Safety\nLayer 1, 2, 3"}
        
        CrisisCheck -->|জরুরি ঝুঁকি / High Risk| EmergencyPayload["Emergency Screen Payload\n(Direct 999 & 109 Trigger)"]
        
        CrisisCheck -->|নিরাপদ / Safe Query| RAGModule["RAG Retrieval Engine\n(WHO & DGHS Medical KB)"]
        RAGModule --> LLMModule["LLM Grounded Generator\n(Simple Bangla System Prompt)"]
        
        APIGateway --> CycleEngine["Cycle Engine (FIGO Standard)"]
        APIGateway --> MoodEngine["Mood Engine (PMS Correlation)"]
        APIGateway --> PregEngine["Pregnancy Engine (Naegele Rule)"]
        APIGateway --> PcosML["PCOS Risk Screener (Random Forest)"]
        
        LLMModule --> TTS["Bangla Neural TTS (Edge / gTTS)"]
    end

    subgraph DataLayer [Storage & Models]
        DB[(SQLite / PostgreSQL\nCascading Wipe)]
        KB[(Medical Knowledge Base)]
        MLModels[(PCOS ML Model)]
        
        RAGModule --- KB
        PcosML --- MLModels
        CycleEngine --- DB
        MoodEngine --- DB
    end

    TTS -->|Voice Reply| PWA_Mobile
```

## Security & Privacy Guarantees
1. **Zero PII Policy:** No name, email, phone number, village, or IP address is ever collected, stored, or recorded in server logs.
2. **Pseudonymous UUID:** Every user is identified solely by a client-generated or server-generated random v4 UUID.
3. **Audio Destruction:** Raw voice recordings are processed in temporary memory or ephemeral storage and destroyed immediately following transcription.
4. **Cascade Deletion:** A single tap on "আমার সব তথ্য মুছে ফেলুন" deletes the user record and cascades immediate deletion across all period logs, mood logs, and checks.
5. **Ephemeral Session Memory Buffer:** Multi-turn conversational context (up to 15 turns / 30 messages) is held strictly in volatile RAM with a 24-hour TTL. No conversation transcripts or chat history are persisted to disk or relational databases.

## Performance & Latency Optimizations
- **In-Memory LRU Audio Cache:** Repeated phrases and warm vocal introductions are cached in volatile memory using MD5 content keys, delivering audio responses in under 0.001s.
- **Micro-Pause Voice Prosody:** Automated phonetic comma insertion (`আপু,`, `শোনো,`) provides natural, culturally resonant Bengali conversational cadence without robotic monotone.
- **Progressive Web App (PWA):** Service worker (`shoi-cache-v2`) provides full offline static asset availability, instant load times, and native standalone mobile presentation.

## Automated Verification & Test Coverage
- **Total Tests:** 53 automated unit and integration tests (100% pass rate).
- **Core Coverage:** PII scrubbing, crisis guardrails, FIGO cycle predictions, PCOS machine learning, pregnancy timeline, PWA web standards, and multi-turn conversational session resolution.

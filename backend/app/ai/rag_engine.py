# -*- coding: utf-8 -*-
"""
Medical RAG Engine for AI Gynecologist:
Retrieves grounded clinical evidence from curated Bengali and International medical documents:
- International Evidence-based PCOS Guidelines (Rotterdam / Monash / Endocrine Society)
- WHO Menstrual & Reproductive Health Guidelines
- DGHS Bangladesh Clinical Guidelines
- NIH & PubMed Reproductive Health References
"""

from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.rag import rag_service
from app.models.patient_memory import MedicalKnowledgeDocument

class RAGEngine:
    def retrieve_medical_knowledge(self, query: str, db: Optional[Session] = None, top_k: int = 2) -> Tuple[List[str], List[str]]:
        """
        Retrieves top relevant medical knowledge chunks and structured citation labels.
        Returns: (chunks_text_list, citations_list)
        """
        chunks_text = []
        citations = []

        # 1. Query grounded RAG service (curated clinical KB)
        retrieved_chunks, is_confident = rag_service.retrieve(query, top_k=top_k)
        if retrieved_chunks:
            for c in retrieved_chunks:
                chunks_text.append(f"[{c.get('title')} - Source: {c.get('source')}]:\n{c.get('text')}")
                citations.append(f"{c.get('title')} ({c.get('source')})")

        # 2. Check DB-stored MedicalKnowledgeDocuments if DB session available
        if db:
            q_lower = query.lower()
            if "pcos" in q_lower or "পিসিওএস" in q_lower:
                db_docs = db.query(MedicalKnowledgeDocument).filter(MedicalKnowledgeDocument.category == "pcos_guidelines").limit(1).all()
                for doc in db_docs:
                    chunks_text.append(f"[{doc.title} - Source: {doc.source_name}]:\n{doc.content}")
                    citations.append(doc.citation_label)

        # De-duplicate citations
        unique_citations = list(dict.fromkeys(citations))
        return chunks_text, unique_citations

rag_engine = RAGEngine()

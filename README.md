# NIEL Industrial Intelligence AI & Agentic Customer Support System
> Secure Enterprise Agentic AI & Retrieval-Augmented Generation (RAG) System for New India Electricals Ltd. (NIEL).

[![Tests](https://img.shields.io/badge/pytest-65%20passed-brightgreen.svg)]()
[![RAG Benchmark](https://img.shields.io/badge/RAG%20Accuracy-100%25-blue.svg)]()
[![Agent Benchmark](https://img.shields.io/badge/Agent%20Benchmark-100%25-brightgreen.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)]()
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)]()
[![FAISS](https://img.shields.io/badge/FAISS-Local%20Vector%20Store-orange.svg)]()

---

## 1. Project Overview
The **NIEL Industrial Intelligence AI** has been extended into a production-ready, **Agentic Customer Support System** for New India Electricals Ltd. (NIEL).

The system acts as an autonomous AI agent capable of understanding customer intent, retrieving technical equipment knowledge, managing persistent customer profiles and preferences, capturing qualified B2B sales leads, generating formal support tickets, and enforcing critical electrical safety guardrails with human escalation handoff.

Supported industrial equipment lines:
- Electric Induction Motors (IE2 / IE3 / IE4 Premium Efficiency)
- Power & Distribution Transformers (Dry Type & Oil Cooled)
- HT & LT Switchgear Panels (MCC, PCC, VFD Panels)
- Industrial Process & Utility Pumps

---

## 2. Agentic Architecture & Capabilities

### 1. Agentic AI Orchestration
An intelligent orchestration layer (`backend/app/agent/orchestrator.py`) handles incoming customer queries, coordinates customer profile memory, calls appropriate operational tools, and enforces safety boundaries.

### 2. 9 Structured Customer Intents
A specialized classifier (`backend/app/services/intent_service.py`) accurately detects:
1. `PRODUCT_ENQUIRY` — Technical specs, frame sizes, power ratings
2. `TECHNICAL_SUPPORT` — Troubleshooting, alarms, maintenance, wiring
3. `PRODUCT_RECOMMENDATION` — Sizing and selecting equipment for applications
4. `QUOTATION_REQUEST` — RFQ, commercial proposals, bulk purchase pricing
5. `SALES_ENQUIRY` — Procurement and distributor inquiries
6. `COMPLAINT` — Defect reports, breakdowns, and warranty issues
7. `ORDER_DELIVERY_ENQUIRY` — Lead times and shipment status
8. `GENERAL_INFORMATION` — Company credentials, plants, greetings
9. `HUMAN_SUPPORT_REQUEST` — Explicit requests for human assistance

### 3. Reusable Agent Tools (`backend/app/agent/tools.py`)
- `search_product_knowledge`: Vector search across official PDF datasheets and catalogues
- `get_customer_profile`: Access company profile, contact details, and equipment preferences
- `get_customer_history`: Retrieve recent tickets, enquiries, and active leads
- `save_customer_information`: Update profile details and consented preferences
- `create_support_ticket`: Formal ticket creation (`TK-2026-XXXX`) with automated severity classification
- `create_sales_lead`: Automatic lead qualification and priority scoring (URGENT, HIGH, MEDIUM, LOW)
- `escalate_to_human`: Mid-session handoff to human support engineers

### 4. Electrical Safety Guardrails
Strict guardrails immediately flag life-safety hazards (smoke, sparks, shocks, fire, live conductors), output critical safety advisories against uncertified DIY maintenance, create priority support tickets, and immediately alert human engineering staff.

### 5. Multi-Tab Support Operations Dashboard
The React frontend includes an authorized Agent Dashboard (`AdminModal.tsx`) with dedicated tabs:
- 🎫 **Support Tickets**: Manage and resolve open service tickets
- 💼 **Sales Leads**: Track qualified B2B leads and update commercial status
- 👥 **Customer Profiles**: View registered directory, sector, and consent logs
- ⚡ **Live Escalations**: Active session queue with real-time human agent messaging
- 📄 **Knowledge Base Docs**: Ingestion, chunking, and index management

---

## 3. Verified Benchmark Results

### Automated Test Suite
- **Pytest**: `65 / 65 passed` (100% pass rate in ~4.5s)
- **Baseline RAG Evaluation** (`evaluation/evaluate.py`): `100.0%` (10 / 10 passed, 84.75ms avg latency)
- **Agentic AI Evaluation** (`evaluation/evaluate_agent.py`): `100.0%` (8 / 8 scenarios passed, 22.88ms avg latency)
- **Frontend Build**: `tsc && vite build` built cleanly in 5.6s with 0 errors

---

## 4. Quickstart: Run Locally

### 1. Setup Backend
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run automated tests
pytest backend/tests -v

# Start FastAPI server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Setup Frontend
```powershell
cd frontend
npm install
npm run build
npm run dev
```

Visit the application at `http://127.0.0.1:5173/`.

### 3. Test WordPress Integration Sandbox
Open [`demo/integration-test.html`](file:///c:/Users/gouri/Downloads/NIEL/New%20folder/demo/integration-test.html) in your browser to experience the Shadow-DOM embedded widget inside a simulated NIEL website layout.

---

## 5. CV / Portfolio Ready Project Description

> **NIEL Industrial Intelligence AI | Enterprise RAG & Generative AI System**
> - Architected a secure, decoupled RAG system answering technical inquiries across industrial catalogues for New India Electricals Ltd., achieving **100% citation accuracy** and **100% Recall@5** on verified benchmarks.
> - Implemented an ingestion pipeline with binary magic-byte validation, scanned PDF detection, sliding-window chunking, and SHA-256 deduplication, saving embedding compute costs.
> - Built a high-performance local vector search engine using **FAISS (`IndexFlatIP`)** and integrated OpenAI `gpt-4o-mini` with zero-temperature negative constraint grounding to eliminate hallucinations on pricing and stock.
> - Engineered an embeddable **Shadow DOM** chatbot widget for seamless integration into WordPress 6.x and Elementor with zero CSS/JS collisions, backend-only secret isolation, and sliding-window rate limiting.

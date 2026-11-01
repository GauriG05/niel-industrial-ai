# NIEL Industrial Intelligence AI & Agentic Customer Support System
> Secure Enterprise Agentic AI & Retrieval-Augmented Generation (RAG) System for New India Electricals Ltd. (NIEL).

[![Tests](https://img.shields.io/badge/pytest-78%20passed-brightgreen.svg)]()
[![RAG Benchmark](https://img.shields.io/badge/RAG%20Accuracy-100%25-blue.svg)]()
[![Agent Benchmark](https://img.shields.io/badge/Agent%20Benchmark-100%25-brightgreen.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)]()
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)]()
[![FAISS](https://img.shields.io/badge/FAISS-Local%20Vector%20Store-orange.svg)]()

---

## 1. Project Overview
The **NIEL Industrial Intelligence AI** is a production-ready, **Agentic Customer Support & RAG System** built for New India Electricals Ltd. (NIEL).

The system acts as an autonomous AI agent capable of understanding customer intent, retrieving technical equipment specifications, maintaining multi-turn conversational context, attaching verified PDF brochures directly into the chat, capturing qualified B2B sales leads, generating formal support tickets, and providing dynamic WhatsApp escalation to live human support engineers.

Supported industrial equipment lines:
- **AC Motors**: Cage Rotor (0.37–20,000 kW), Wound Rotor (7.5–20,000 kW), Flameproof (0.37–350 kW), Crane Duty (0.37–1,000 kW), Brake Motors (0.18–20 kW), AC Mill Duty (110–2,000 kW), Special Motors
- **DC Motors**: Industrial DC Motors (0.37 kW to 6,500 kW, frame sizes 80 to 1,000, voltages 180V–1,000V DC)
- **Transformers**: Distribution & Power Transformers (up to 1,250 kVA, 11 kV / 22 kV / 33 kV, Dyn 11, Class A, Off-circuit & OLTC)
- **Switchgear & Panels**: Medium Voltage (MV) & Low Voltage (LV) Panels (3.3 kV to 33 kV, VCB, MCC, PCC, Drawout, IP4X/IP54)
- **Pumps & Valves**: Monoblock (up to 260 m³/hr, 102 m head), Open Well Submersible, Process Pumps, Non-Clog Self-Priming, Vacuum Pumps, Borewell Submersible, Vertical Multistage
- **Substations & Drives**: Compact Secondary Substations (CSS up to 1,250 kVA / 33 kV), Variable Frequency Drives (VFD up to 1,000 kW), Gearboxes (ratios up to 43,645:1)

---

## 2. Key Architecture & Features

### 1. 12-Category Structured Knowledge Base (`data/knowledge_base/`)
Structured JSON records compiled from authorized PDFs in `PDFs/`, text extractions in `textpdfs/`, and the official website:
1. `ac_motors.json`
2. `dc_motors.json`
3. `pumps_and_valves.json`
4. `transformers.json`
5. `switchgear.json`
6. `ac_dc_drives.json`
7. `gearboxes_and_brake_motors.json`
8. `substation_systems.json`
9. `company_information.json`
10. `industries_and_applications.json`
11. `faqs.json`
12. `troubleshooting_and_installation.json`

- **Source Registry** (`source_registry.json`): Tracks all 12 PDFs, 8 text extractions, and the official website with SHA-256 hashes, page counts, and coverage.
- **Unverified Fields Catalog**: Per zero-hallucination policy, missing technical parameters (e.g. frame-specific efficiency curves for large custom frames, transformer short-circuit duration in seconds) are explicitly cataloged in each product's `unverified_fields` array.

### 2. Official PDF Brochure Chat Attachments
- When customers ask for product details, specifications, or brochures, the chat directly attaches official **PDF Brochure Cards**.
- The backend serves genuine brochures via `/pdfs/{filename}` mounted from `PDFs/`.
- Customers can click **View PDF ↗** on any attachment to view or download the exact document in their browser (e.g. `AC Motors - NIEL Brochure.pdf`, `Transformers - NIEL Brochure.pdf`, `Pumps - NIEL Brochure.pdf`).
- Clean user interface: replaces raw text snippets and OCR fragments with authentic PDF documents.

### 3. WhatsApp Click-to-Chat Human Support (+91 97413 07999)
- When a customer clicks **Talk to a human**, the assistant dynamically opens WhatsApp Web or the WhatsApp mobile app pre-filled with their inquiry.
- **Scenario 1 (With conversation history)**: Formats a concise, contextual summary:
  ```text
  Hello NIEL Team,

  I would like human support assistance regarding an inquiry on your website:

  • Customer Query: <Initial inquiry>
  • Selected Product: <Detected product category>
  • Requirements: <Detected specifications, e.g. 20,000 kW, 6.6 kV>
  • Unresolved Issue / Request: <Latest user query>
  • Session Reference: <Session ID>

  Please connect me with a support engineer.
  ```
- **Scenario 2 (Without conversation history)**: Uses fallback message:
  ```text
  Hello NIEL Team, I would like to connect with your support team. Please assist me.
  ```
- The user only needs to press **Send** in WhatsApp.

### 4. 9 Structured Customer Intents
1. `PRODUCT_ENQUIRY` — Technical specs, frame sizes, power ratings
2. `TECHNICAL_SUPPORT` — Troubleshooting, alarms, maintenance, wiring
3. `PRODUCT_RECOMMENDATION` — Sizing and selecting equipment for applications
4. `QUOTATION_REQUEST` — RFQ, commercial proposals, bulk purchase pricing
5. `SALES_ENQUIRY` — Procurement and distributor inquiries
6. `COMPLAINT` — Defect reports, breakdowns, and warranty issues
7. `ORDER_DELIVERY_ENQUIRY` — Lead times and shipment status
8. `GENERAL_INFORMATION` — Company credentials, plants, greetings
9. `HUMAN_SUPPORT_REQUEST` — Explicit requests for human assistance

### 5. Reusable Agent Tools (`backend/app/agent/tools.py`)
- `search_product_knowledge`: Vector search across official PDF datasheets and catalogues with category filtering and structured knowledge record matching
- `get_customer_profile`: Access company profile, contact details, and equipment preferences
- `get_customer_history`: Retrieve recent tickets, enquiries, and active leads
- `save_customer_information`: Update profile details and consented preferences
- `create_support_ticket`: Formal ticket creation (`TK-2026-XXXX`) with automated severity classification
- `create_sales_lead`: Automatic lead qualification and priority scoring (URGENT, HIGH, MEDIUM, LOW)
- `escalate_to_human`: Handoff to human support engineers

### 6. Electrical Safety Guardrails
Strict guardrails immediately flag life-safety hazards (smoke, sparks, shocks, fire, live conductors), output critical safety advisories against uncertified DIY maintenance, create priority support tickets, and immediately alert human engineering staff.

---

## 3. Verified Benchmark Results

### Automated Test Suite
- **Pytest**: `78 / 78 passed` (100% pass rate in ~8.5s)
- **Baseline RAG Evaluation** (`evaluation/evaluate.py`): `100.0%` (10 / 10 passed, 80.09ms avg latency)
- **Agentic AI Evaluation** (`evaluation/evaluate_agent.py`): `100.0%` (8 / 8 scenarios passed, 30.70ms avg latency)
- **Frontend Build**: `tsc && vite build` builds cleanly with 0 TypeScript/bundling errors

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
Open `demo/integration-test.html` in your browser to experience the Shadow-DOM embedded widget inside a simulated NIEL website layout.

---

## 5. CV / Portfolio Ready Project Description

> **NIEL Industrial Intelligence AI | Enterprise RAG & Generative AI System**
> - Architected an end-to-end RAG system answering technical inquiries across industrial catalogues for New India Electricals Ltd., achieving **100% citation accuracy** and **100% Recall@5** on verified benchmarks.
> - Engineered a 12-category structured knowledge base and vector retrieval engine over official brochures for induction motors (up to 20 MW), transformers (up to 33 kV), switchgear, and pumps with zero hallucination.
> - Built automatic PDF brochure attachment in chat, allowing customers to view and download verified technical datasheets.
> - Integrated dynamic WhatsApp click-to-chat escalation (+91 97413 07999) with contextual inquiry summarization for instant human takeover.
> - Developed an embeddable **Shadow DOM** chatbot widget for seamless integration into WordPress and Elementor with zero CSS/JS collisions, backend secret isolation, and sliding-window rate limiting.

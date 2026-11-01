# Industrial Intelligence AI & Agentic Customer Support System
> Production-Ready Enterprise Agentic AI & Retrieval-Augmented Generation (RAG) System for Industrial Equipment & Engineering Operations.

[![Build & Tests](https://img.shields.io/badge/pytest-78%20passed-brightgreen.svg)]()
[![RAG Benchmark](https://img.shields.io/badge/RAG%20Accuracy-100%25-blue.svg)]()
[![Agent Benchmark](https://img.shields.io/badge/Agent%20Benchmark-100%25-brightgreen.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)]()
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)]()
[![FAISS](https://img.shields.io/badge/FAISS-Local%20Vector%20Store-orange.svg)]()
[![Branch](https://img.shields.io/badge/Branch-master-blue.svg)]()

---

## 1. Project Overview

The **Industrial Intelligence AI** is an enterprise-grade **Agentic Customer Support & Technical Intelligence Platform** engineered for industrial electrical equipment and manufacturing operations.

The system serves as an autonomous industrial co-pilot capable of understanding technical engineering queries, retrieving equipment specifications from authentic technical literature, maintaining multi-turn conversational context, directly serving official downloadable PDF brochures, qualifying B2B sales leads, generating formal support tickets, and providing dynamic WhatsApp escalation to live technical support staff.

### Supported Industrial Equipment Lines
* **AC Motors**: Cage Rotor (0.37 kW to 20,000 kW), Wound Rotor (7.5 kW to 20,000 kW), Flameproof (0.37 kW to 350 kW), Crane Duty (0.37 kW to 1,000 kW), Brake Motors (0.18 kW to 20 kW), AC Mill Duty (110 kW to 2,000 kW), and custom engineered motors.
* **DC Motors**: Industrial DC Motors (0.37 kW to 6,500 kW, frame sizes 80 to 1,000, voltages 180V–1,000V DC).
* **Transformers**: Distribution & Power Transformers (up to 1,250 kVA, 11 kV / 22 kV / 33 kV, Dyn 11, Class A, Off-circuit & On-Load Tap Changers).
* **Switchgear & Panels**: Medium Voltage (MV) & Low Voltage (LV) Panels (3.3 kV to 33 kV, Vacuum Circuit Breakers, Motor Control Centers, Power Control Centers, Drawout, IP4X/IP54).
* **Pumps & Valves**: Monoblock (up to 260 m³/hr, 102 m head), Open Well Submersible, Process Pumps, Non-Clog Self-Priming, Vacuum Pumps, Borewell Submersible, Vertical Multistage.
* **Substations & Drives**: Compact Secondary Substations (CSS up to 1,250 kVA / 33 kV), Variable Frequency Drives (VFD up to 1,000 kW), and Industrial Gearboxes (ratios up to 43,645:1).

---

## 2. System Architecture & Features

```
+-----------------------------------------------------------------------------------------+
|                                    Client Layer                                         |
|  [React + Vite Desktop App]    [Shadow DOM Embeddable Widget]    [WhatsApp Handoff]     |
+-----------------------------------------------------------------------------------------+
                                             |
                                  HTTP REST / WebSocket
                                             v
+-----------------------------------------------------------------------------------------+
|                           FastAPI Enterprise Backend (:8000)                            |
|  - Rate Limiter & Security Headers Middleware (Nosniff, CSP, Strict Referrer)           |
|  - Router: /chat, /ws/chat, /leads, /tickets, /documents, /customers, /escalations      |
|  - Multi-Turn Session Memory (SQLite + SessionService)                                  |
|  - Electrical Safety Guardrails & Live Human Escalation Logic                           |
+-----------------------------------------------------------------------------------------+
               |                                                         |
               v                                                         v
+-----------------------------+                           +-------------------------------+
|    Autonomous Agent Core    |                           |       RAG & Vector Store      |
| - Intent Classification     |                           | - FAISS Local Vector Index    |
|   (9 Structured Intents)    |                           | - OpenAI Embeddings           |
| - Tool Orchestration Engine |                           |   (text-embedding-3-small)    |
| - Automated Lead Scoring    |                           | - Verified Source Registry    |
| - Support Ticket Generator  |                           | - Official PDF Mount (/pdfs)  |
+-----------------------------+                           +-------------------------------+
               |                                                         |
               +---------------------------+-----------------------------+
                                           v
                       +---------------------------------------+
                       |    12-Category Structured Datastore   |
                       | - 12 Verified JSON Knowledge Bases    |
                       | - Zero-Hallucination Unverified Catalog|
                       | - Official Catalogues & Documents     |
                       +---------------------------------------+
```

### 1. 12-Category Structured Knowledge Base (`data/knowledge_base/`)
Structured JSON records compiled from technical datasheets, document extractions in `textpdfs/`, and official engineering specifications:
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

* **Source Registry** (`source_registry.json`): Hashes and catalogs all technical documents, extractions, page counts, and coverage.
* **Unverified Fields Catalog**: Per zero-hallucination policy, missing technical parameters (e.g., custom frame efficiency curves, transformer short-circuit duration) are explicitly cataloged in each product's `unverified_fields` array.

### 2. Official PDF Brochure Chat Attachments
* Direct attachments of official **PDF Brochure Cards** when customers inquire about products, specifications, or datasheets.
* Backend serves genuine documents via `/pdfs/{filename}` mounted directly from `PDFs/`.
* One-click **View PDF ↗** opens or downloads authentic brochures:
  - `AC Motors - NIEL Brochure.pdf`
  - `DC Motors - NIEL Brochure.pdf`
  - `Transformers - NIEL Brochure.pdf`
  - `Switchgear Panels MV - NIEL Brochure.pdf`
  - `Pumps - NIEL Brochure.pdf`
  - `Substation.pdf`
  - `NIEL Product Catalog.pdf`
  - `Company Intro - New India Electricals Limited.pdf`
  - `Key Customer List.pdf`
  - `NIEL - STEEL.pdf`
  - `NIEL GROUP PROJECTS HIGHLIGHTS- FINAL.pdf`
  - `NIEL Recent Power Projects.pdf`

### 3. WhatsApp Click-to-Chat Human Support Escalation
* When a customer requests a human engineer or clicks **Talk to a human**, the assistant formats their session context and triggers a WhatsApp click-to-chat action:
  ```text
  Hello Support Team,

  I would like human support assistance regarding an inquiry on your website:

  • Customer Query: <Initial inquiry>
  • Selected Product: <Detected product category>
  • Requirements: <Detected specifications, e.g. 20,000 kW, 6.6 kV>
  • Unresolved Issue / Request: <Latest user query>
  • Session Reference: <Session ID>

  Please connect me with a support engineer.
  ```

### 4. 9 Structured Customer Intents
1. `PRODUCT_ENQUIRY` — Technical specs, frame sizes, power ratings
2. `TECHNICAL_SUPPORT` — Troubleshooting, alarms, maintenance, wiring
3. `PRODUCT_RECOMMENDATION` — Sizing and selecting equipment for applications
4. `QUOTATION_REQUEST` — RFQ, commercial proposals, bulk purchase pricing
5. `SALES_ENQUIRY` — Procurement and distributor inquiries
6. `COMPLAINT` — Defect reports, breakdowns, and warranty issues
7. `ORDER_DELIVERY_ENQUIRY` — Lead times and shipment status
8. `GENERAL_INFORMATION` — Company credentials, facilities, greetings
9. `HUMAN_SUPPORT_REQUEST` — Explicit requests for human assistance

### 5. Reusable Agent Tools (`backend/app/agent/tools.py`)
* `search_product_knowledge`: Vector search across official datasheets and catalogues with category filtering.
* `get_customer_profile`: Access company profile, contact details, and equipment preferences.
* `get_customer_history`: Retrieve recent tickets, enquiries, and active leads.
* `save_customer_information`: Update profile details and consented preferences.
* `create_support_ticket`: Formal ticket creation (`TK-2026-XXXX`) with automated severity classification.
* `create_sales_lead`: Automatic lead qualification and priority scoring (`URGENT`, `HIGH`, `MEDIUM`, `LOW`).
* `escalate_to_human`: Contextual handoff to live engineering team.

### 6. Electrical Safety Guardrails
Strict guardrails immediately flag life-safety hazards (smoke, sparks, shocks, fire, live conductors), output critical safety advisories against uncertified DIY maintenance, create priority support tickets, and immediately alert human engineering staff.

---

## 3. Repository Structure

```
niel-industrial-ai/
├── backend/                  # FastAPI Enterprise Backend
│   ├── app/
│   │   ├── agent/            # Orchestrator & agent tools
│   │   ├── api/v1/           # REST endpoints (chat, leads, tickets, docs, health)
│   │   ├── db/               # SQLite models & database session
│   │   ├── ingestion/        # PDF chunker, text extractor, SHA hasher
│   │   ├── knowledge/        # 12-category knowledge base loader & search
│   │   ├── retrieval/        # FAISS vector store & retriever
│   │   ├── schemas/          # Pydantic models & request/response schemas
│   │   ├── security/         # Rate limiting, auth & security middleware
│   │   ├── services/         # Intent, RAG, Lead, Ticket & Session services
│   │   ├── config.py         # App configuration & settings
│   │   └── main.py           # FastAPI entrypoint
│   ├── requirements.txt      # Python dependencies
│   └── tests/                # Complete Pytest test suite (78 tests)
├── frontend/                 # React 18 + Vite Web Application
│   ├── src/
│   │   ├── components/       # ChatMessage, ExamplePrompts, etc.
│   │   ├── services/         # API integration
│   │   ├── types/            # TypeScript definitions
│   │   └── utils/            # WhatsApp link generator & helpers
│   ├── package.json
│   └── vite.config.ts
├── widget/                   # Zero-dependency Shadow-DOM Embeddable Widget
│   ├── niel-widget.js        # Self-contained widget script for WordPress/Elementor
│   └── assets/               # Brand imagery
├── data/
│   ├── knowledge_base/       # 12 structured JSON equipment databases
│   └── index/                # FAISS vector index files (.gitkeep)
├── PDFs/                     # 11 Official Catalogues & Brochures (served via /pdfs)
├── textpdfs/                 # Extracted text references
├── evaluation/               # RAG & Agent evaluation scripts & test cases
├── deploy/                   # Production Nginx reverse-proxy template
├── docker-compose.yml        # Multi-container orchestration
├── Dockerfile                # Production container definition
└── README.md
```

---

## 4. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service discovery root & health status |
| `GET` | `/api/v1/health` | Service health check |
| `POST` | `/api/v1/chat` | Synchronous RAG & Agentic chat endpoint |
| `POST` | `/api/v1/chat/message` | Session-aware chat with lead/ticket hooks |
| `WS` | `/api/v1/chat/ws/{session_id}` | Real-time WebSocket streaming chat |
| `POST` | `/api/v1/leads` | Create qualified sales lead |
| `GET` | `/api/v1/leads` | List recent leads |
| `POST` | `/api/v1/tickets` | Create customer support ticket |
| `GET` | `/api/v1/tickets` | List support tickets |
| `POST` | `/api/v1/escalations` | Record human escalation handoff |
| `GET` | `/pdfs/{filename}` | Access verified official product brochures |
| `GET` | `/widget/niel-widget.js` | Serve embeddable widget script |

---

## 5. Quickstart & Installation

### Prerequisites
* Python 3.10+
* Node.js 18+ & npm
* OpenAI API Key (optional for mock/offline testing, required for live LLM inference)

### 1. Backend Setup

```powershell
# 1. Clone repository
git clone <repository-url>
cd niel-industrial-ai

# 2. Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install backend dependencies
pip install -r backend/requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and insert your configuration and API keys

# 5. Run automated tests
pytest backend/tests -v

# 6. Start the FastAPI server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup

```powershell
# Open a new terminal in the frontend directory
cd frontend

# Install Node dependencies
npm install

# Run the dev server
npm run dev
```
Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/) to interact with the web app.

### 3. Docker Deployment

```powershell
# Build and run with Docker Compose
docker compose up -d --build

# View logs
docker compose logs -f backend

# Tear down
docker compose down
```

---

## 6. Embeddable Widget Integration (WordPress / HTML)

To embed the AI assistant widget on any website (including WordPress, Elementor, Webflow, or static HTML), add this script tag before the closing `</body>` tag:

```html
<script 
  src="https://your-backend-domain.com/widget/niel-widget.js" 
  data-api-base="https://your-backend-domain.com"
  defer>
</script>
```

To test the widget locally inside a webpage layout, open `demo/integration-test.html` in your browser.

---

## 7. Verified Benchmark Results

* **Pytest Test Suite**: `78 / 78 passed` (100% pass rate)
* **Baseline RAG Accuracy** (`evaluation/evaluate.py`): `100.0%` (10/10 passed)
* **Agentic AI Benchmark** (`evaluation/evaluate_agent.py`): `100.0%` (8/8 scenarios passed)
* **TypeScript Bundler**: `tsc && vite build` completes with 0 errors.

---

## 8. License

Copyright © 2026. All rights reserved.
Licensed for enterprise deployment.

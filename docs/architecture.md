# NIEL Industrial Intelligence AI - System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Presentation Layer"]
        A1["React + Vite Standalone Web App"]
        A2["WordPress / Elementor Embed Widget (Shadow DOM)"]
    end

    subgraph SecurityGateway ["Security & Ingress Gateway"]
        B1["Reverse Proxy / CORS Whitelist"]
        B2["SecurityHeadersMiddleware"]
        B3["Sliding Window Rate Limiter (30 req/min)"]
        B4["Admin Key Auth Guard (X-Admin-Key)"]
    end

    subgraph BackendCore ["FastAPI Backend Engine (/api/v1)"]
        C1["/api/v1/health & /ready"]
        C2["/api/v1/chat (Grounded QA Engine)"]
        C3["/api/v1/documents (Ingestion & Inventory)"]
    end

    subgraph RAGEngine ["Retrieval-Augmented Generation Engine"]
        D1["Query Normalization & Feature Extraction"]
        D2["Vector Search (faiss.IndexFlatIP / Cosine Sim)"]
        D3["Threshold Relevance Filter (score >= 0.35)"]
        D4["Prompt Defense Layer (<EVIDENCE> Boundary)"]
        D5["OpenAI Service (gpt-4o-mini, temp=0.0)"]
        D6["Programmatic Citation Validator"]
    end

    subgraph StorageLayer ["Persistence & Vector Store"]
        E1["FAISS Vector Index (faiss.index)"]
        E2["Metadata Registry (metadata.json)"]
        E3["Raw Document Vault (data/docs/)"]
    end

    Client --> SecurityGateway
    SecurityGateway --> BackendCore
    C2 --> RAGEngine
    C3 --> StorageLayer
    RAGEngine --> StorageLayer
```

## Key Technical Decisions:
1. **Shadow DOM Encapsulation**: Guarantees complete CSS and DOM isolation on third-party WordPress/Elementor pages.
2. **Deterministic SHA-256 Deduplication**: Eliminates duplicate vector embeddings, saving API spend.
3. **Negative Constraint Engineering**: Enforces strict abstention on unindexed pricing or commercial claims to prevent industrial hallucinations.
4. **Backend-Only Secret Isolation**: The client never receives or stores OpenAI keys or admin credentials.


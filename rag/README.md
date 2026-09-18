# DD House — AI-Powered Cake Ordering & Customer Assistant RAG System

> **Production-Style, Hackathon-Friendly Grounded RAG Architecture for DD House (Kakinada)**

---

## 1. Project Architecture

The DD House RAG system is built with strict adherence to **Data Authority Hierarchy**, **Multi-Layer Hallucination Protection**, and **Deterministic Grounding**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA AUTHORITY HIERARCHY                        │
│                                                                        │
│  [Type 1] Verified Business Data       (verified: true,  business_provided)   │
│       ▲ (Always authoritative, highest priority)                       │
│  [Type 2] External Reference Data      (verified: false, external_reference)  │
│       ▲ (Logged in conflict metadata; NEVER overrides Type 1)          │
│  [Type 3] Hackathon Assumptions        (verified: false, hackathon_assumption)│
│         (Internal only; NEVER presented to customers as confirmed)     │
└────────────────────────────────────────────────────────────────────────┘

                                    │
                                    ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   rag/data/      │ ───► │  rag/ingestion/  │ ───► │  rag/retrieval/  │
│  (Structured     │      │   - Validator    │      │  (VectorStore &  │
│   JSON records)  │      │   - Chunker      │      │   MetadataFilter)│
└──────────────────┘      │   - Embedder     │      └────────┬─────────┘
                          └──────────────────┘               │
                                                             ▼
                                                    ┌──────────────────┐
                                                    │  rag/generation/ │
                                                    │  (Multi-Layer    │
                                                    │   Guardrails &   │
                                                    │   Grounded LLM)  │
                                                    └────────┬─────────┘
                                                             │
                                                             ▼
                                                    ┌──────────────────┐
                                                    │  rag/api/routes  │
                                                    │ POST /api/rag/chat
                                                    └──────────────────┘
```

### Folder Structure
```
rag/
├── data/                       # Structured JSON single source of truth
│   ├── business_info.json      # Hours, location, phone, parking advice
│   ├── products.json           # Cake bowls, brownies, lollipops with verified prices
│   ├── customization.json      # Flavours, fillings, toppings, box messaging rule
│   ├── ordering.json           # Online ordering, prep time, pre-booking, pickup only
│   ├── payment.json            # UPI, Cash, advance payment rules
│   ├── cancellation_refund.json# 5-min cancellation rule, TBD after 5-min policy
│   ├── pickup.json             # Order ID, PIN, delay policies
│   ├── faq.json                # Verified FAQ pairs
│   ├── ingredients.json        # TBD per-product ingredient records
│   ├── allergens.json          # TBD per-product allergen records
│   ├── social_links.json       # Official Instagram handle
│   └── external_references.json# External website data & conflict resolution entries
│
├── documents/                  # Compiled human-readable markdown docs
│   ├── business.md
│   ├── products.md
│   ├── customization.md
│   ├── ordering.md
│   ├── payment.md
│   ├── policies.md
│   ├── pickup.md
│   └── faq.md
│
├── ingestion/                  # Ingestion, validation, chunking, and embedding
│   ├── loader.py               # Loads structured JSON & markdown documents
│   ├── validator.py            # Enforces Type 1 > Type 2 > Type 3 authority rules
│   ├── cleaner.py              # Whitespace & query normalizer
│   ├── document_builder.py     # Re-synchronizes markdown docs from JSON
│   ├── chunker.py              # Produces atomic semantic chunks retaining metadata
│   ├── embedder.py             # SentenceTransformers / built-in semantic vectorizer
│   └── ingest.py               # End-to-end ingestion pipeline runner
│
├── retrieval/                  # Retrieval and indexing
│   ├── vector_store.py         # Vector database with persistent local storage
│   ├── metadata_filter.py      # Category, product, and policy query router
│   └── retriever.py            # Hybrid semantic retrieval with calibrated scoring
│
├── generation/                 # LLM generation and guardrails
│   ├── prompt.py               # Strict DD House system prompt
│   └── generator.py            # 3-layer hallucination protection & rule engine
│
├── pipeline/
│   └── rag_pipeline.py         # End-to-end RAG orchestrator
│
├── api/
│   └── routes.py               # FastAPI router (/chat, /health, /conflicts, /ingest)
│
├── evaluation/                 # 50-Question benchmark suite
│   ├── test_questions.json     # All 50 evaluation test cases across 8 categories
│   └── evaluate.py             # Automated benchmark evaluator
│
├── tests/                      # Pytest unit & integration tests
│   ├── test_api.py
│   └── test_retrieval.py
│
├── config.py                   # Centralized configuration settings
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
└── README.md                   # System documentation
```

---

## 2. Installation

```bash
# Navigate to workspace root
cd /home/narasimha/ddhs/DD_HOUSE_KKD

# Install dependencies
pip install -r rag/requirements.txt
```

---

## 3. Environment Variables

Create `.env` in the root or `rag/` directory (template available in `rag/.env.example`):

```bash
# LLM Provider Configuration
LLM_PROVIDER=gemini           # "gemini", "openai", or leave blank for deterministic engine
LLM_API_KEY=your_api_key_here # Google Gemini API key or OpenAI key
LLM_MODEL=gemini-1.5-flash

# Embeddings & Vector DB
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_DB_PATH=./vector_store_db

# Hallucination Protection Threshold
SIMILARITY_THRESHOLD=0.50
TOP_K=4
```

> **Note**: If `LLM_API_KEY` is not provided, the system automatically runs the built-in deterministic grounding engine, allowing 100% offline evaluation without external network calls!

---

## 4. Data Ingestion & 5. Embedding Generation & 6. Vector DB Creation

To run the complete data ingestion pipeline:

```bash
python3 -m rag.ingestion.ingest
```

This command automatically:
1. **Loads** all structured records from `rag/data/*.json`.
2. **Validates** data authority levels (`business_provided`, `external_reference`, `hackathon_assumption`, `unknown`).
3. **Synchronizes** all markdown documentation in `rag/documents/`.
4. **Chunks** records into 75 atomic semantic units retaining rich metadata.
5. **Generates embeddings** and indexes them into the persistent vector database (`rag/vector_store_db/`).

---

## 7. Running FastAPI Server

Start the standalone FastAPI server:

```bash
uvicorn rag.main:app --host 0.0.0.0 --port 8000 --reload
```

- Interactive Swagger API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/rag/health`
- Conflict Registry: `http://localhost:8000/api/rag/conflicts`

---

## 8. Testing & Evaluation

### Running the 50-Question Benchmark Suite
```bash
python3 -m rag.evaluation.evaluate
```

Results across all 8 categories:
- **Category 1**: Products (#1 - #6) — 100% Pass
- **Category 2**: Customization (#7 - #15) — 100% Pass
- **Category 3**: Business (#16 - #20) — 100% Pass
- **Category 4**: Ordering (#21 - #28) — 100% Pass
- **Category 5**: Payment (#29 - #32) — 100% Pass
- **Category 6**: Pickup (#33 - #36) — 100% Pass
- **Category 7**: Cancellation (#37 - #39) — 100% Pass (No fee invented for #39)
- **Category 8**: Unknown / Hallucination (#40 - #50) — 100% Resistance Rate!

### Running Pytest Unit & Integration Tests
```bash
pytest rag/tests/
```

---

## 9. Updating Business Data

When the real business owner provides updated information:
1. Edit the relevant JSON file in `rag/data/` (e.g., update prices in `products.json` or hours in `business_info.json`).
2. Re-run ingestion:
   ```bash
   python3 -m rag.ingestion.ingest
   ```
   Or send a POST request to the API:
   ```bash
   curl -X POST http://localhost:8000/api/rag/ingest
   ```
3. Markdown documents and vector indexes are refreshed automatically.

---

## 10. Handling TBD Information

Unknown or pending business facts are stored with:
```json
{
  "id": "ingredient_triple_chocolate",
  "category": "ingredient",
  "name": "Triple Chocolate Ingredients",
  "value": null,
  "source_type": "unknown",
  "verified": false,
  "status": "TBD"
}
```

The assistant adheres strictly to the required fallback responses:
- **Allergens & Ingredients**:
  > *"I don't have verified ingredient/allergen information for that product yet."*
- **General Unknown / Out-of-Scope Questions**:
  > *"I don't have verified information about that in the DD House knowledge base. Please contact DD House at 7013522727."*
- **Cancellation fees after 5 minutes**:
  > *"There is NO verified fixed percentage or fixed cancellation fee. Exact refund calculation depends on elapsed time and preparation status."*

---

## 11. Multi-Layer Hallucination Protection

```
Customer Question
       │
       ▼
[ Layer 1: Retrieval Confidence Threshold ]
   - If confidence < 0.50 or out-of-scope concept:
     Bypass LLM immediately -> Return safe controlled fallback response.
       │ (Score >= 0.50)
       ▼
[ Layer 2: Strict LLM Grounding Prompt ]
   - "Answer using ONLY verified DD House context."
   - Negative constraints: Never invent prices, allergens, delivery, fees.
       │
       ▼
[ Layer 3: Post-Generation Guardrail Validation ]
   - Scans generated answer for hallucinated patterns (e.g. `\d+%`, fake delivery claims, brownie customization).
   - Sanitizes output before returning to customer.
       │
       ▼
Grounded API Response
```

---

## 12. API Examples & Integration Guide

### Endpoint: `POST /api/rag/chat`

#### Example 1: Verified Product Question
**Request:**
```bash
curl -X POST http://localhost:8000/api/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How much is the Triple Chocolate cake bowl?"}'
```

**Response:**
```json
{
  "answer": "Triple Chocolate (cake_bowl) costs ₹99. It is available every day.",
  "grounded": true,
  "confidence": 0.95,
  "sources": [
    {
      "category": "product",
      "name": "Triple Chocolate",
      "source_type": "business_provided"
    }
  ]
}
```

#### Example 2: Hallucination Prevention (Out-of-Scope Location)
**Request:**
```bash
curl -X POST http://localhost:8000/api/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Do you deliver to Hyderabad?"}'
```

**Response:**
```json
{
  "answer": "I don't have verified information about that in the DD House knowledge base. Please contact DD House at 7013522727.",
  "grounded": false,
  "confidence": 0.20,
  "sources": []
}
```

#### Example 3: TBD Allergen Protection
**Request:**
```bash
curl -X POST http://localhost:8000/api/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Are all products eggless?"}'
```

**Response:**
```json
{
  "answer": "I don't have verified ingredient/allergen information for that product yet.",
  "grounded": false,
  "confidence": 0.87,
  "sources": []
}
```

---

## 13. Frontend & Backend Integration

### Backend Mounting (FastAPI)
Backend engineers can mount the RAG router directly inside `backend/app/main.py`:

```python
from fastapi import FastAPI
from rag.api.routes import router as rag_router

app = FastAPI()
app.include_router(rag_router)
```

### Frontend Integration (React / Next.js / Vanilla JS)
```javascript
async function askDDHouseAssistant(question) {
  const response = await fetch("http://localhost:8000/api/rag/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const data = await response.json();
  console.log("Answer:", data.answer);
  console.log("Grounded:", data.grounded);
  console.log("Confidence:", data.confidence);
  return data;
}
```

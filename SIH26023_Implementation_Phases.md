# AI-Powered Mining Intelligence, Document Processing & Automated Reporting Platform
## SIH26023 — CMPDI / CIL / Ministry of Coal
## Complete 5-Phase Implementation Plan with Antigravity Prompts

---

## How to use this document

Each phase below is self-contained: it explains *what* is being built and *why*,
then gives the exact prompt to paste into Antigravity to build it. Phases are
sequenced so each one ends in something independently demoable, and no phase
depends on anything not yet built. Do not skip ahead — each Antigravity prompt
assumes the schema and API surface of every prior phase already exists.

**Central design philosophy governing every phase:**
> The LLM is not the source of truth. The documents and validated data are.
> AI is used to understand, retrieve, summarize, reason, and explain — never
> to invent facts, perform arithmetic, or silently resolve contradictions.

**Constraints that apply across all phases:**
- On-premise / self-hostable only. No external API (OpenAI, Anthropic, Google)
  as an architectural dependency.
- GPU is optional. Everything must run correctly on CPU.
- Local models available via Ollama: `bge-m3` (embeddings), `qwen2.5vl:3b` /
  `qwen2.5vl:7b` (vision/OCR), `qwen2.5:3b/7b/14b-instruct` (reasoning),
  `qwen2.5-coder:7b/14b` (dev tooling only — never called at runtime).
- No microservices, no multi-agent orchestration, no knowledge graph, no
  message queues — a modular monolith with clean internal boundaries.
- Deterministic calculations only (SQL/Python) — the LLM interprets and
  explains results, never computes them.
- Every extracted/derived value carries provenance back to its source
  document, page, table/cell.

---

# PHASE 1 — Ingestion + Extraction Backbone

## What this phase builds
The foundation everything else depends on: heterogeneous documents (scanned
PDF, digital PDF, DOCX, XLSX/CSV, JPG/PNG) go in, and reliably extracted,
provenance-tagged, searchable data comes out. No trust engine, no validation,
no AI reasoning yet — just get real documents into a database correctly.

## Why it's first
Every later phase — trust, evidence, analytics, the copilot, reports — is
worthless if extraction is unreliable. This is also the highest-risk,
least-glamorous phase, so it gets first claim on time and attention, not last.

## What's explicitly deferred
Normalization, validation, conflict detection, any LLM reasoning call, any
frontend.

## Demo checkpoint
Upload 3–4 heterogeneous documents (one scanned, one digital PDF, one Excel,
one image). Confirm each is correctly parsed, stored, and individually
retrievable with full provenance metadata intact — and that the original file
is retrievable by ID alone without re-upload.

## Antigravity Prompt — Phase 1

```
# PROJECT: AI-Powered Mining Intelligence Platform — SIH26023 (CMPDI/CIL/Ministry of Coal)

# PHASE 1 OF 5 — INGESTION + EXTRACTION BACKBONE (BACKEND ONLY)

## CONTEXT
This is a Smart India Hackathon solution for automated processing of heterogeneous
mining/geological/production documents for CMPDI/CIL subsidiaries. The full system
will eventually include validation, conflict detection, evidence lineage, analytics,
explainable AI, and reporting — but THIS PHASE ONLY builds the ingestion and
extraction backbone. Do not build anything from later phases.

No frontend in this phase. The frontend will be built separately and integrated
against this backend's API later. Design the API as a clean, stable, well-documented
contract (OpenAPI/Swagger via FastAPI's built-in docs is sufficient) since another
codebase will consume it soon.

## CORE DESIGN PRINCIPLES (apply throughout)
1. On-premise / self-hostable first. Do not introduce a dependency on OpenAI,
   Anthropic, Google, or any other external API as an architectural requirement.
   External APIs may only be used as an optional, swappable dev convenience behind
   an abstraction — never hard-wired into core logic.
2. GPU is optional. Everything in this phase must run correctly on CPU. Do not
   assume GPU availability anywhere in the code.
3. Never destroy or overwrite the original source document. Extracted/derived data
   is always stored separately from the original file.
4. Every extracted object must carry provenance: which document, which page, which
   section/table/cell it came from. This is required now even though the trust and
   evidence layers come in Phase 2 — provenance must be captured at extraction time
   or it's unrecoverable later.
5. Keep it simple. No microservices, no multi-agent orchestration, no knowledge
   graph, no message queues. A modular monolith with clean internal service
   boundaries is correct for this phase.
6. Prefer the simplest technology that satisfies the requirement. Justify any
   non-trivial dependency in one sentence before adding it.

## AVAILABLE LOCAL MODELS (via Ollama)
The following models are already pulled and available locally. Use them instead
of downloading or assuming any other model:

- bge-m3:latest — use this as the embedding model for the Vector Indexing step
  below. Call it via the local Ollama API, not any external embedding service.
- qwen2.5vl:7b (and a lighter qwen2.5vl:3b variant, also available) — use one of
  these as the primary OCR/vision extraction engine for scanned PDFs and images,
  in place of or alongside a traditional OCR library. Propose which is more
  reliable for this use case: a traditional OCR library like Tesseract (faster,
  simpler, cheap on CPU) vs. the VLM (potentially more accurate on messy scans/
  tables, but slower on CPU). Since GPU is optional and this must run on CPU,
  benchmark both on a few sample scanned documents before committing, and make
  the choice configurable behind the extraction service's interface rather than
  hard-coded.
- qwen2.5-coder:7b / qwen2.5-coder:14b — these are NOT part of the application.
  Do not call these from any runtime code path. They exist only as coding-assistant
  models for development tooling.
- qwen2.5:3b / qwen2.5:7b / qwen2.5:14b-instruct — general reasoning models. NOT
  used in Phase 1 (no LLM reasoning is in scope this phase, per the "explicitly
  out of scope" section below). These are the likely candidates for the Model
  Gateway's reasoning model in Phase 3, but do not wire them in now.

All models run via the local Ollama runtime (assume Ollama is already running and
reachable at its default local endpoint). Do not introduce a second inference
server or framework in this phase — route everything through Ollama's API.

## WHAT TO BUILD IN THIS PHASE

### 1. Project scaffolding
- Python + FastAPI backend
- PostgreSQL for structured data
- Local/object file storage for original documents (filesystem-based storage
  abstraction — a simple `storage/` interface that could later swap to S3-compatible
  storage without changing calling code)
- Qdrant (self-hosted, via Docker) for vector storage of extracted text
- Docker Compose setup so the whole stack (API, Postgres, Qdrant) runs with one
  command — Ollama is assumed to run on the host, not inside this Compose stack
- CORS configured permissively enough for a frontend on a different origin/port to
  call this API during later integration

### 2. Document ingestion pipeline
Build an ingestion service that accepts: PDF (digital), PDF (scanned), DOCX, XLSX,
CSV, JPG, PNG.

For each uploaded document:
- Detect file type
- Assign a unique document ID
- Store the original file unmodified in object storage
- Extract and store metadata: filename, upload date, file type, page count (where
  applicable), and any inferable report date if easily available — do not build
  complex metadata inference logic in this phase, just capture what's cheap to get
- Determine whether OCR is required (scanned vs digital PDF/image detection)

### 3. Extraction pipeline
- OCR/vision extraction for scanned PDFs and images — using the local model
  strategy described above (Tesseract and/or qwen2.5vl, chosen per the
  benchmarking note); do not call an external OCR API
- Text extraction from digital PDFs/DOCX
- Table detection and extraction from PDFs and DOCX where present — reconstruct as
  structured rows/columns, not flattened text
- Native structured extraction from XLSX/CSV (these already have real tables —
  don't OCR them, parse them directly)
- Basic image/chart extraction: extract embedded images as separate assets linked
  to their source page; do not attempt chart-to-data interpretation in this phase
- Page-level structure preservation: every extracted text block, table, and image
  must record its page number and, where feasible, its position/section on the page

### 4. Storage schema
Design and implement a PostgreSQL schema covering, at minimum:
- `documents` (id, filename, file_type, upload_date, report_date if known,
  page_count, storage_path, ocr_required, processing_status)
- `pages` (id, document_id, page_number)
- `extracted_text_blocks` (id, document_id, page_id, text, block_type, position
  metadata)
- `extracted_tables` (id, document_id, page_id, table_index, raw_structure as JSON
  — rows/columns/cells)
- `extracted_images` (id, document_id, page_id, storage_path, image_index)

Every row in every extraction table must be traceable back to its document_id and
page_id — this is the provenance requirement from principle #4 above. Do not
simplify this away.

### 5. Vector indexing
- After text extraction, chunk and embed extracted text blocks using bge-m3 (via
  Ollama's local API) — do not require an external embedding API
- Store embeddings in Qdrant with metadata payload: document_id, page_id,
  block_id, so any retrieved vector result can be traced back to its source
- Build a minimal semantic search endpoint (`POST /search`) that takes a text
  query and returns matching text blocks with their source document/page — this
  is just to prove the pipeline works end-to-end; it is NOT the AI Query Copilot
  (that's Phase 3) and should have no LLM reasoning layer on top of it

### 6. API design
Expose a clean, documented FastAPI surface, e.g.:
- `POST /documents/upload` — accepts one or more files, returns document IDs +
  initial status
- `GET /documents` — list processed documents with status, pagination-ready
- `GET /documents/{id}` — full metadata + extraction summary for one document
- `GET /documents/{id}/pages/{page_number}` — extracted content for one page
  (text blocks, tables, images, with their provenance fields included in the
  response)
- `POST /search` — basic semantic search (as above), returns results with
  document/page attribution
- `GET /documents/{id}/original` — download/stream the original stored file
- `GET /documents/{id}/status` — lightweight status-only endpoint for polling
  during processing (useful since a frontend will need this for upload progress
  later)

Return consistent, well-typed JSON response models (Pydantic) throughout, since a
separate frontend will be built against this contract without you present to
clarify shapes later. Include clear error responses (4xx/5xx with a message field)
for bad file types, corrupt files, and OCR/extraction failures.

## FUTURE RETRIEVAL ARCHITECTURE — DESIGN CONTRACT (READ CAREFULLY)
Phase 1 does NOT implement the full AI Query & Response system. But the ingestion
and storage architecture built in this phase MUST be designed so that a later
phase can implement the following retrieval flow WITHOUT restructuring the
database or re-ingesting any document:

```
User Query
    ↓
Query Understanding / Intent Detection
    ↓
Semantic Retrieval from Qdrant
    ↓
Retrieve document/page/text references
    ↓
Structured retrieval from PostgreSQL when the query requires exact values,
filtering, aggregation, comparison, or other structured operations
    ↓
Original document retrieval when source verification or page-level evidence
is required
    ↓
Evidence aggregation / validation
    ↓
LLM response generation
    ↓
Answer + source document + page + supporting evidence
```

To make this possible later without rework, Phase 1 MUST ensure:

1. Every Qdrant vector payload contains stable references to the corresponding
   PostgreSQL records (`document_id`, `page_id`, `block_id`).
2. Every extracted PostgreSQL record contains a stable reference to its parent
   document and page.
3. Every document record contains the persistent storage path/identifier of the
   original unmodified document.
4. The original document remains retrievable through the backend using its
   document ID (`GET /documents/{id}/original`, already specified above, satisfies
   this — confirm it does).
5. The storage abstraction must allow later retrieval of the original source file
   without requiring the user to re-upload it.
6. The `/search` response must return enough provenance information for a future
   retrieval/orchestration layer to follow the chain: Qdrant result → PostgreSQL
   record → original document/page. Concretely, each search result must include
   `document_id`, `page_id`, `block_id`, and enough metadata (page number, block
   type) that a later layer can fetch the full PostgreSQL record and the original
   file without additional lookups you haven't exposed.
7. Do NOT implement query understanding, LLM reasoning, answer generation, agentic
   orchestration, or evidence validation in this phase. Build only the retrieval
   primitives and stable identifiers this future flow depends on.

The architectural goal, stated plainly:

> Upload once → persist → extract → index → retrieve later → answer later.
> A user must never need to re-upload an already-ingested document when asking
> questions in a later phase.

When proposing the schema and API contract below, explicitly show how each of the
7 points above is satisfied — e.g. point to the exact column that stores the
Qdrant→Postgres link, and the exact endpoint that satisfies "original document
retrievable by ID without re-upload." If any part of the proposed design does not
satisfy one of these 7 points, flag it and fix it before implementation.

## EXPLICITLY OUT OF SCOPE FOR THIS PHASE
Do not build any of the following yet, even if it seems easy to add:
- Any frontend or UI of any kind
- Entity/unit/date normalization
- Duplicate or conflict detection
- Data validation or confidence scoring beyond basic OCR/extraction success/failure
- Evidence/lineage UI (the schema must support it later, but no lineage endpoint
  beyond what's needed to return provenance fields in existing responses)
- Query understanding, intent detection, LLM reasoning, answer generation, or any
  agentic orchestration (these are Phase 3 — Phase 1 only builds the retrieval
  primitives per the design contract above)
- Analytics, forecasting, reporting, word cloud/topics
- Authentication, RBAC, audit logging (stub these as clearly marked TODOs, don't
  build them now)
- Any external cloud API as a hard dependency

## DELIVERABLE / DEMO CHECKPOINT FOR THIS PHASE
By the end of this phase, I should be able to:
1. Run the whole stack with `docker compose up` (with Ollama already running on
   the host)
2. Upload 3–4 heterogeneous test documents (one scanned PDF, one digital PDF, one
   Excel file, one image) via the API (e.g. through the FastAPI /docs Swagger UI
   or curl/Postman — no custom frontend needed to validate this phase)
3. See each one correctly processed with status "done" via `GET /documents`
4. Retrieve a document's extracted text, tables, and images via the page endpoint,
   correctly attributed to the right page
5. Run a basic semantic search query via `POST /search` and get back relevant
   text blocks with correct source document/page attribution, and confirm each
   result carries enough identifiers to trace: vector result → PostgreSQL record
   → original document, with no re-upload required
6. Confirm that every extracted row in the database can be traced back to its
   document_id and page_id
7. Confirm the original file for any ingested document is retrievable by ID alone

## HOW TO PROCEED
Before writing code, first propose:
1. The finalized tech stack for this phase (confirm or adjust the above)
2. The finalized database schema (as SQL DDL)
3. The folder/module structure for the backend
4. The full API contract (endpoints, request/response schemas) — since a frontend
   will be built against this separately, get this right before implementation
5. The OCR strategy decision (Tesseract vs. qwen2.5vl, or a hybrid) with a brief
   rationale, based on the benchmarking note above
6. An explicit point-by-point mapping showing how the proposed schema and API
   satisfy each of the 7 requirements in the Future Retrieval Architecture section
7. A short ordered task list for implementing this phase

Wait for my confirmation on the schema, folder structure, API contract, OCR
strategy, and the retrieval-contract mapping before generating the full codebase.
Flag anything in this prompt that you think is unrealistic to build reliably in
this phase, and propose a simpler alternative rather than silently attempting the
harder version.
```

---

# PHASE 2 — Data Trust Engine + Evidence/Lineage Layer

## What this phase builds
This is the project's #1 differentiator. Raw extracted text/tables from Phase 1
become normalized, validated, evidence-linked structured facts. Entity aliases
resolve to canonical names, units and dates normalize, duplicates and OCR
anomalies get flagged, and — critically — conflicting values across documents
are surfaced, never silently overwritten.

## Why it's second
Building trust and evidence *before* the query copilot means the copilot is
evidence-grounded from day one, instead of being retrofitted onto ungrounded
answers later. It also means this phase's output is what makes Explainable AI
(Phase 3) possible at all — without a lineage chain, "show your evidence" is
just a slogan.

## What's explicitly deferred
Deterministic analytics (YoY/CAGR/trends), the query copilot, human review
*actions* (flags and conflicts are stored and queryable, but accept/correct/
reject workflows come in Phase 4), reporting, forecasting, any frontend.

## Demo checkpoint
Deliberately upload two documents with a conflicting figure for the same
entity/metric/period — confirm a `conflicts` record is created referencing
both source facts with neither value dropped or overwritten. Pull the full
evidence chain for any fact back to its original document and page. Confirm
an entity alias resolves correctly to its canonical entity.

## Antigravity Prompt — Phase 2

```
# PROJECT: AI-Powered Mining Intelligence Platform — SIH26023 (CMPDI/CIL/Ministry of Coal)

# PHASE 2 OF 5 — DATA TRUST ENGINE + EVIDENCE/LINEAGE LAYER (BACKEND ONLY)

## CONTEXT
Phase 1 built the ingestion and extraction backbone: documents are uploaded,
OCR'd/parsed, and stored as text blocks, tables, and images in PostgreSQL, with
embeddings in Qdrant — all fully traceable to document_id/page_id/block_id.

This phase does NOT touch ingestion or extraction. It builds on top of Phase 1's
existing data: turning raw extracted text/tables into normalized, validated,
evidence-linked structured facts. No frontend in this phase — continue building
against the same API contract style established in Phase 1.

## CORE DESIGN PRINCIPLES (apply throughout — same as Phase 1, restated because
this phase is where they matter most)
1. The LLM is NOT the source of truth. Documents and validated data are. Any LLM
   use in this phase is for understanding/interpreting structure (e.g. figuring
   out what a table column header means), never for deciding whether a value is
   correct or for performing arithmetic.
2. On-premise / self-hostable only. No external API dependency.
3. GPU optional — must run on CPU.
4. Never silently resolve a conflict. If two documents disagree on a value, both
   are stored and the conflict is surfaced, not auto-picked.
5. Every normalized value must remain traceable to its original extracted form —
   normalization must never discard the original text/value.
6. Keep it simple. No multi-agent orchestration, no knowledge graph in this phase.

## AVAILABLE LOCAL MODELS (via Ollama — same environment as Phase 1)
- bge-m3:latest — already used in Phase 1 for text embeddings. In this phase,
  also use it for entity-alias similarity matching (e.g. determining whether
  "Central Coalfields Ltd." and "CCL" likely refer to the same canonical entity)
  and for near-duplicate document detection via embedding similarity.
- qwen2.5:7b-instruct-q4_K_M or qwen2.5:14b-instruct-q4_K_M — use one of these for
  the Fact Extraction step described below: interpreting table structure and
  surrounding text to identify candidate (entity, metric, value, unit, date)
  tuples from raw extracted tables/text blocks. This is structure interpretation,
  NOT calculation and NOT validation — its output is a candidate fact that then
  passes through deterministic normalization and validation before being trusted.
  Require the model to return strict structured JSON (e.g. via function-calling
  or a constrained JSON schema prompt) so output is deterministically parseable.
  Propose 7b vs 14b based on a quick accuracy/latency tradeoff check on sample
  tables from Phase 1's test documents — flag this as a decision point.
- qwen2.5vl models — already used in Phase 1 for OCR/vision. Not needed again in
  this phase unless you find a case where re-reading a specific region of a scan
  helps resolve an OCR anomaly flag (optional, not required).
- qwen2.5-coder models — not part of the application, dev tooling only, as in
  Phase 1.

All models run via the local Ollama runtime, same as Phase 1.

## WHAT TO BUILD IN THIS PHASE

### 1. Fact Extraction Service
For each document already processed in Phase 1, walk its `extracted_tables` and
`extracted_text_blocks` and produce candidate structured facts:
`(entity_text, metric_text, value, unit_text, date_text, source table/block,
extraction_confidence)`.

- For tables: use the LLM (per above) to interpret headers/row-labels and map
  cells to entity/metric/unit/date, returning structured JSON per row/cell.
- For text blocks: use simple, well-scoped extraction — numeric values near
  recognizable metric keywords (e.g. "production", "dispatch") — do not attempt
  full open-domain information extraction from prose in this phase; keep this
  lightweight and flag low-confidence extractions rather than guessing.
- Every candidate fact must carry the source `document_id`, `page_id`, and
  either `table_id` or `block_id` it was derived from (from Phase 1's schema) —
  this is non-negotiable, it's the root of the evidence chain built in this phase.
- Store raw LLM output alongside the parsed result for debugging/audit purposes,
  but do not treat raw LLM text as the stored fact — only the parsed structured
  result proceeds to normalization.

### 2. Normalization Layer
Deterministic, rule-based — no LLM involved here.

- **Entity resolution**: maintain a `canonical_entities` table (with a seed list
  you can populate from Phase 1's test documents — e.g. known CIL subsidiary
  names) and an `entity_aliases` table. Resolve extracted entity_text to a
  canonical entity via exact match first, then fuzzy string match, then bge-m3
  embedding similarity as a fallback — record which method resolved each match
  and its confidence. Unresolved entities are stored as-is with a flag, not
  discarded or guessed.
- **Unit normalization**: implement explicit conversion rules (e.g. MT ↔ KT ↔
  crore tonnes) with a defined, testable conversion table. Only convert when the
  unit is unambiguous; if ambiguous, store the original value/unit unconverted
  and flag it rather than guessing.
- **Date normalization**: parse common formats (FY 2023-24, 2023–24, DD/MM/YYYY,
  etc.) into a canonical stored form, while retaining the original text.

### 3. Data Trust Engine
Deterministic validation checks run against normalized facts:

- **Duplicate detection**: near-duplicate documents (via bge-m3 embedding
  similarity across whole-document or page-level embeddings from Phase 1's
  Qdrant index) and duplicate/near-duplicate individual facts.
- **Missing data detection**: flag facts missing a resolved entity, unit, or
  date; flag tables with incomplete rows.
- **OCR anomaly detection**: heuristic checks for likely OCR errors — e.g.
  implausible decimal shifts (75.20 → 7520), impossible values for a known
  metric range, inconsistent digit counts vs. neighboring cells in the same
  column/table.
- **Range validation**: configurable plausible-range checks per metric type
  (flag, don't reject, values outside expected bounds).
- **Historical consistency checks**: flag a value that deviates sharply from
  the same entity/metric's prior-period values, without asserting it's wrong.
- **Cross-document conflict detection**: for facts resolved to the same
  (canonical entity, metric, period), compare values across documents. If they
  materially disagree, create a `conflicts` record referencing BOTH source
  facts (with their full provenance) — never overwrite or pick one.

All flags/conflicts are stored with enough detail to support human review in a
later phase — but do NOT build the review UI or accept/correct/reject actions in
this phase. Just store flags in a clear, queryable state (e.g. `open`).

### 4. Evidence & Lineage Schema
Every normalized fact must expose the full chain:
`Document → Page → Section/Table → Cell/Block → Extracted Value → Normalization
→ Validation Result → (canonical) Fact`

Design the schema so this entire chain can be retrieved in a single query or a
small number of joined queries — this will be surfaced directly in later phases'
"show your work" UI, so it must be efficient and complete, not reconstructed
after the fact from scattered tables.

### 5. Database schema additions (extend, do not replace, Phase 1's schema)
Propose concrete DDL, but at minimum cover:
- `canonical_entities` (id, canonical_name, entity_type)
- `entity_aliases` (id, canonical_entity_id, alias_text, resolution_method,
  confidence)
- `extracted_facts` (id, document_id, page_id, table_id NULLABLE, block_id
  NULLABLE, raw_entity_text, raw_metric_text, raw_value, raw_unit_text,
  raw_date_text, extraction_confidence, extraction_method)
- `normalized_facts` (id, extracted_fact_id, canonical_entity_id, metric,
  normalized_value, normalized_unit, normalized_date/period, normalization_notes)
- `validation_flags` (id, normalized_fact_id, flag_type, severity, detail,
  status)
- `conflicts` (id, canonical_entity_id, metric, period, fact_a_id, fact_b_id,
  status, detected_at)
- `duplicate_candidates` (id, document_id_a, document_id_b OR fact_id_a/fact_id_b,
  similarity_score, status)

Every table above must be joinable back to Phase 1's `documents`/`pages`/
`extracted_tables`/`extracted_text_blocks` — do not duplicate data that Phase 1
already stores; reference it by ID.

### 6. API design
Extend Phase 1's API surface (do not break existing Phase 1 endpoints):
- `POST /documents/{id}/process-facts` — trigger fact extraction + normalization
  + validation for a given (already-ingested) document; also support a
  batch/all-documents variant
- `GET /facts` — query normalized facts, filterable by entity, metric, period
- `GET /facts/{id}/evidence` — full lineage chain for one fact, from canonical
  fact back to the original document/page
- `GET /conflicts` — list open conflicts
- `GET /conflicts/{id}` — full detail: both source facts, their complete
  evidence chains, values, sources, confidence
- `GET /validation-flags` — list flags, filterable by type/severity/status
- `GET /entities` — list canonical entities with their known aliases
- `GET /duplicates` — list detected duplicate candidates

Response models must include enough provenance in every payload that a future
UI never needs an extra round-trip just to show "where did this come from."

## EXPLICITLY OUT OF SCOPE FOR THIS PHASE
- Any frontend or UI
- Human-in-the-loop review actions (accept/correct/reject/resolve) — flags and
  conflicts are stored and queryable, but no workflow to act on them yet
  (that's Phase 4)
- Deterministic analytics (YoY, CAGR, trends, comparisons) — that's Phase 3
- Query understanding, LLM-generated answers, the AI Query Copilot — Phase 3
- Explainable AI output packaging (Answer + Evidence + Confidence + Calculation
  + Reasoning Type) — Phase 3, though this phase's evidence schema is what makes
  that possible later
- Report generation, word cloud/topics, forecasting, heat map — later phases
- Authentication, RBAC (stub as TODO, same as Phase 1)
- Any use of the LLM for arithmetic, validation decisions, or conflict
  resolution — those must remain deterministic per the core design principle

## DELIVERABLE / DEMO CHECKPOINT FOR THIS PHASE
By the end of this phase, using the same Phase 1 test documents (or new ones
uploaded via Phase 1's existing endpoints), I should be able to:
1. Trigger fact extraction on an ingested document and see normalized facts
   produced with resolved entities, normalized units/dates, and full provenance
2. Deliberately upload two documents where the same entity/metric/period has a
   different value, run processing, and see a `conflicts` record created
   referencing both source facts — confirm neither value was silently dropped
   or overwritten
3. Pull `GET /facts/{id}/evidence` for any fact and see the complete chain back
   to the original document and page
4. See validation flags generated for at least one deliberately introduced
   OCR-anomaly-style or missing-unit test case
5. Confirm an entity alias (e.g. "CCL" vs "Central Coalfields Limited") resolves
   to the same canonical entity

## HOW TO PROCEED
Before writing code, first propose:
1. The finalized DDL for all new tables, showing exactly how they join back to
   Phase 1's schema
2. The Fact Extraction prompt design for the LLM step (the structured JSON
   schema you'll require from qwen2.5-instruct) and your 7b-vs-14b decision with
   rationale
3. The full API contract for new/extended endpoints
4. The conflict-detection matching logic (how you determine two facts are "the
   same entity/metric/period" before comparing values)
5. A short ordered task list for implementing this phase

Wait for my confirmation on the schema, fact-extraction prompt design, and API
contract before generating the full codebase. Flag anything in this prompt that
seems unreliable to build deterministically (especially in table interpretation
or conflict matching) and propose a simpler, more conservative alternative rather
than silently attempting the harder version.
```

---

# PHASE 3 — Analytics Engine + Explainable AI + AI Query & Response Copilot

## What this phase builds
The first fully working end-to-end MUST HAVE demo. A deterministic analytics
service computes trends/comparisons/anomalies from Phase 2's normalized facts.
An Explainable AI packaging layer wraps every output in Answer + Evidence +
Confidence + Calculation + Reasoning Type. And the AI Query & Response Copilot
finally implements the full retrieval flow contracted back in Phase 1: query →
semantic retrieval → structured retrieval → evidence aggregation → grounded
LLM answer → sources + confidence.

## Why it's third
Everything before this phase was infrastructure. This is the first thing that
looks and behaves like "the product" — and because Phases 1 and 2 were built
correctly, the copilot here is evidence-grounded from the start rather than a
generic RAG chatbot with citations bolted on afterward.

## What's explicitly deferred
Report generation (reuses this phase's output but is built in Phase 4), word
cloud/topics, human review actions, the Parliamentary Query Copilot (Phase 5),
heat map, forecasting, any frontend.

## Demo checkpoint
Ask "Compare production of two subsidiaries over the last three years and
explain major changes" and get back a table/chart-ready result, source
citations, and a confidence-tagged explanation — using only data already in
the system from Phases 1–2. Ask a "why did this change" question and confirm
the system distinguishes a documented explanation from an unsupported guess,
and correctly says "no sufficient evidence found" when appropriate.

## Antigravity Prompt — Phase 3

```
# PROJECT: AI-Powered Mining Intelligence Platform — SIH26023 (CMPDI/CIL/Ministry of Coal)

# PHASE 3 OF 5 — ANALYTICS ENGINE + EXPLAINABLE AI + AI QUERY & RESPONSE COPILOT (BACKEND ONLY)

## CONTEXT
Phase 1 built ingestion/extraction. Phase 2 built the Data Trust Engine,
normalization, conflict detection, and the evidence/lineage schema — every
normalized fact in `normalized_facts` is traceable back to its source document,
page, and table/cell, and conflicts are surfaced (never silently resolved).

This phase builds the first user-facing intelligence layer on top of that data:
deterministic analytics, an explainability wrapper, and the AI Query & Response
Copilot — completing the retrieval flow that was architecturally contracted for
back in Phase 1. No frontend yet — continue extending the same API contract.

## CORE DESIGN PRINCIPLES (restated — this phase is where the "LLM is not the
source of truth" rule is most at risk of being violated, so read carefully)
1. The LLM NEVER performs arithmetic. Every number in a final answer must come
   from the deterministic Analytics Service, not from the LLM computing it.
2. The LLM's job in this phase is: classify intent, plan retrieval, and turn
   retrieved evidence + calculated results into a natural-language explanation
   — strictly grounded in what was actually retrieved/calculated. It must never
   add facts, causes, or figures that are not present in the evidence passed to it.
3. If evidence is insufficient to answer a question or explain a change, the
   system must say so explicitly ("No sufficient evidence found in the available
   documents") rather than the LLM filling the gap with a plausible-sounding guess.
4. On-premise / self-hostable only. GPU optional — must run on CPU.
5. Keep it simple — no agentic multi-step loops beyond the fixed pipeline
   described below; no autonomous tool-calling beyond calling this system's own
   internal services.

## AVAILABLE LOCAL MODELS (via Ollama — same environment as Phases 1–2)
- qwen2.5:7b-instruct-q4_K_M or qwen2.5:14b-instruct-q4_K_M — use for: (a) intent
  detection/query planning (constrained JSON output), (b) final natural-language
  answer synthesis strictly grounded in retrieved evidence and calculated results
  passed into the prompt context, (c) the "Why Did This Change?" explanation
  synthesis. Reuse whichever of 7b/14b you settled on in Phase 2 for consistency,
  unless you have a concrete reason (e.g. answer quality) to use the larger model
  specifically for final answer generation while keeping the smaller model for
  intent classification/planning — if so, propose this split explicitly.
- bge-m3:latest — continue using for semantic retrieval query embedding (querying
  the Qdrant index built in Phase 1) and for matching a user's query terms to
  canonical entities/metrics from Phase 2's `canonical_entities` table.
- qwen2.5-coder models — not part of the application, dev tooling only.

All models run via the local Ollama runtime, same as prior phases. Formalize a
`ModelGateway` module now if one does not already exist: a single internal
interface the rest of the app calls (e.g. `generate(prompt, schema=None)`,
`embed(text)`) that routes to the correct Ollama model — so swapping a model
later never requires touching calling code.

## WHAT TO BUILD IN THIS PHASE

### 1. Deterministic Analytics Service
Pure SQL/Python — no LLM involved. Operates on Phase 2's `normalized_facts`
(and related tables). Support:
- Year-over-year change, CAGR, totals, averages
- Comparative analysis across entities (e.g. multiple subsidiaries) for a given
  metric and period range
- Anomaly detection (statistical outliers relative to an entity/metric's own
  history — reuse or extend Phase 2's historical consistency logic where
  sensible, but this service's job is computing/returning results, not flagging
  data-quality issues)
- Trend computation suitable for charting (time series output: period, value,
  source_fact_id per point)

Every analytics function must return not just the numeric result but the list
of `normalized_fact` IDs (and therefore their full evidence chains, via Phase
2's `/facts/{id}/evidence`) that fed into the calculation — this is what makes
the next layer's "Calculation" and "Evidence" fields possible.

### 2. "Why Did This Change?" Engine
Workflow:
1. Identify the change (either from a user query about a specific change, or
   from an anomaly the Analytics Service flagged)
2. Use semantic retrieval (Qdrant, via bge-m3 embeddings) to find text blocks
   from the same document set that might explain it — scope the search using
   the relevant entity/metric/period to avoid irrelevant results
3. Pass retrieved candidate text to the LLM and ask it to identify whether an
   explicit, documented explanation exists in the retrieved text
4. Classify the result as one of: **Document-supported** (explicit documented
   cause found), **Data-derived** (a correlated pattern in the data itself, not
   an explicit textual explanation), or **Insufficient evidence** (neither found
   — return the standard "No documented explanation was found in the available
   sources" message)
5. Never allow the LLM to invent a plausible-sounding cause when retrieval comes
   back empty or irrelevant — this must be enforced by prompt design AND a
   post-generation check (e.g. requiring the LLM's answer to cite specific
   retrieved passages; if it cites nothing, treat as insufficient evidence
   regardless of what text it generated)

### 3. Explainable AI Packaging Module
A single internal function/service that wraps any analytics or query result
into the standard output shape:
```
{
  "answer": "...",
  "evidence": [ { document_id, page, fact_id, excerpt/table reference } ... ],
  "confidence": 0-100,
  "calculation": "human-readable formula/method used, if applicable",
  "reasoning_type": "document-supported" | "data-derived" | "model-inference" | "insufficient-evidence"
}
```
Every endpoint that returns an AI-influenced answer in this phase (query
copilot, why-did-this-change) must route its final output through this module
— do not let individual endpoints construct ad-hoc response shapes.

Confidence scoring should be a defined, explainable function (not an LLM's
self-reported confidence) — e.g. derived from: extraction confidence of
underlying facts (Phase 1/2), whether cross-document validation confirmed the
value (Phase 2), and whether the explanation is document-supported vs.
data-derived vs. inferred. Propose the exact formula before implementing.

### 4. AI Query & Response Copilot
Implements the full retrieval flow contracted in Phase 1:
```
User Question
    ↓
Intent Detection — classify: does this need structured analytics (numbers/
  comparisons/trends), semantic document search (explanatory/contextual text),
  or both? (LLM call, constrained JSON output)
    ↓
Query Planner — decide which entities/metrics/periods are involved, and which
  internal services to call (Analytics Service, semantic search, or both)
    ↓
Retrieve — semantic retrieval from Qdrant (Phase 1) AND/OR structured retrieval
  from normalized_facts (Phase 2) AND/OR the Analytics Service (this phase),
  as determined by the plan
    ↓
Calculate — via the Analytics Service only, never via the LLM
    ↓
Validate / Cross-check — confirm retrieved facts are not flagged with an open
  conflict (Phase 2's `conflicts` table); if they are, surface the conflict in
  the response rather than silently using one side of it
    ↓
Generate Answer — LLM synthesizes natural language strictly from the retrieved
  evidence and calculated results passed into its context; never introduces
  outside facts
    ↓
Package via the Explainable AI module (above) and return
```

### 5. API design
Extend Phases 1–2's API surface (do not break existing endpoints):
- `POST /query` — the main AI Query & Response Copilot endpoint; accepts a
  natural-language question, returns the full Explainable AI–packaged response
- `POST /analytics/compare` — comparative analysis across entities/metrics/periods
- `POST /analytics/trend` — time series for a given entity/metric
- `POST /analytics/why-did-this-change` — dedicated endpoint for the "Why Did
  This Change?" workflow, also invocable indirectly via `/query`
- `GET /query/{id}` — retrieve a previously generated query response by ID (for
  debugging/audit — persist query responses, don't just return-and-forget)

## EXPLICITLY OUT OF SCOPE FOR THIS PHASE
- Any frontend or UI
- Report generation (PDF/DOCX/XLSX export) — Phase 4, though it will reuse this
  phase's Analytics Service and Explainable AI module directly
- Word cloud / topic identification — Phase 4
- Human review actions — Phase 4
- The Parliamentary Query Copilot (a separate, stricter workflow with a
  mandatory human-approval gate) — Phase 5
- Interactive heat map, forecasting — Phase 5
- Authentication, RBAC (stub as TODO, same as prior phases)

## DELIVERABLE / DEMO CHECKPOINT FOR THIS PHASE
Using data already in the system from Phases 1–2, I should be able to:
1. POST a comparative question like "Compare production of [two entities] over
   the last three years and explain major changes" to `/query` and get back a
   structured result with a comparison, a natural-language explanation, source
   citations, confidence, and reasoning type
2. Ask a "why did production change in [period]" question and get either a
   document-supported explanation with citations, or an explicit "no sufficient
   evidence found" response — never a plausible-sounding invented cause
3. Confirm that every numeric value in any response traces back to an actual
   `normalized_fact` via its evidence chain — spot-check by pulling the cited
   fact IDs and confirming they match
4. Trigger a query that touches a fact with an open conflict (from Phase 2) and
   confirm the response surfaces the conflict rather than silently picking a side

## HOW TO PROCEED
Before writing code, first propose:
1. The intent-detection and query-planning prompt design (structured JSON schema
   required from the LLM)
2. The exact confidence-scoring formula for the Explainable AI module
3. The full API contract for new endpoints
4. How "insufficient evidence" is detected and enforced (not just prompted for,
   but structurally guaranteed — e.g. citation-checking logic)
5. A short ordered task list for implementing this phase

Wait for my confirmation on the confidence formula and the insufficient-evidence
enforcement mechanism specifically — these are the two places this phase is most
likely to quietly violate the "LLM is not the source of truth" principle if not
designed carefully. Flag anything you're not confident can be reliably enforced,
and propose a more conservative alternative rather than silently attempting the
harder version.
```

---

# PHASE 4 — Report Generation + Topic Intelligence + Human-in-the-Loop + Data Quality Dashboard

## What this phase builds
The two remaining MUST HAVE modules explicitly named in the PS — Automated
Report Generation and Word Cloud/Topic Identification — plus the Human
Verification Console that closes the trust loop Phase 2 opened, and the Data
Quality Dashboard that quantifies the platform's measurable benefits.

## Why it's fourth
All three MUST HAVE modules named explicitly in SIH26023 (query system, report
generation, word cloud/topics) are now complete, and the human review loop is
closed. This phase produces a legitimately submittable MVP even if nothing in
Phase 5 gets built.

## What's explicitly deferred
Parliamentary Query Copilot, heat map, forecasting, security hardening beyond
what already exists, any frontend (though this phase's report exports are
themselves user-facing deliverables, distinct from an interactive UI).

## Demo checkpoint
Generate a full management-style report from ingested documents with working
citations and export it to PDF/DOCX/XLSX. View a word cloud/topic-trend output
across the ingested document set. Walk through resolving a flagged conflict in
the review console and confirm the correction is reflected and audit-logged.
Pull the Data Quality Dashboard and confirm every number is computed from real
pipeline data, not a placeholder.

## Antigravity Prompt — Phase 4

```
# PROJECT: AI-Powered Mining Intelligence Platform — SIH26023 (CMPDI/CIL/Ministry of Coal)

# PHASE 4 OF 5 — REPORT GENERATION + TOPIC INTELLIGENCE + HUMAN-IN-THE-LOOP + DATA QUALITY DASHBOARD (BACKEND ONLY)

## CONTEXT
Phase 1 built ingestion/extraction. Phase 2 built the Data Trust Engine,
normalization, and evidence/lineage. Phase 3 built deterministic analytics, the
Explainable AI packaging module, and the AI Query & Response Copilot.

This phase completes the remaining MUST HAVE modules from the PS (Automated
Report Generation, Word Cloud & Topic Identification) and closes the trust loop
with a Human Verification Console and a Data Quality Dashboard. No frontend yet
— continue extending the same API contract; these modules are functionally
complete as APIs even before a UI exists (report export in particular is a
real, usable deliverable on its own).

## CORE DESIGN PRINCIPLES (restated)
1. The LLM is not the source of truth. Report narrative sections are generated
   strictly from Phase 3's Explainable AI–packaged results — never from the LLM
   inventing content beyond what analytics/evidence actually support.
2. On-premise / self-hostable only. GPU optional — must run on CPU.
3. Every human correction must be logged with enough detail to reconstruct what
   changed, who changed it, and why (audit trail, not just a mutation).
4. Do not invent accuracy/automation percentages for the Data Quality Dashboard.
   Every number must be computed live from actual pipeline data (Phases 1–3),
   never hard-coded or estimated.

## AVAILABLE LOCAL MODELS (via Ollama — same environment as prior phases)
- qwen2.5:7b/14b-instruct — use for generating report narrative sections
  (executive summary, key findings, recommendations) — but ONLY by summarizing/
  explaining Phase 3's already-computed, already-evidence-backed results. The
  report generator passes structured analytics + evidence into the prompt; the
  LLM's job is prose synthesis, not new analysis or new fact discovery.
- bge-m3:latest — use for topic clustering (embed extracted text blocks/
  documents, cluster via a standard algorithm like k-means or HDBSCAN over the
  embeddings) and for keyword/topic-label generation support. Topic discovery
  should be primarily embedding-cluster-driven (deterministic given fixed
  embeddings + clustering parameters), with the LLM used only to generate a
  human-readable label for each discovered cluster — not to invent topics from
  nothing.
- qwen2.5-coder models — not part of the application, dev tooling only.

Reuse the `ModelGateway` module from Phase 3 — do not create a second way of
calling models.

## WHAT TO BUILD IN THIS PHASE

### 1. Automated Report Generation Engine
Inputs: user-specified time period, entities/subsidiaries, metrics.

Process:
- Call Phase 3's Analytics Service for the relevant computations (trends,
  comparisons, YoY, etc.) for the requested scope
- Call Phase 2's validation/conflict tables to surface any open data-quality
  warnings relevant to the included facts
- Assemble structured report content: Executive Summary, Production/Operational
  Overview, Historical Trends, Comparative Analysis, Tables, Data Quality
  Warnings, Source References/Citations, and (only where a Phase 3
  Explainable-AI-packaged insight actually supports it) Recommendations
- Generate the narrative sections (executive summary, findings) via the LLM,
  strictly grounded in the structured content assembled above — pass the
  structured data into the prompt and instruct the model to summarize/explain
  only what's given, never to add new figures or claims
- Every claim and figure in the generated report must retain a citation back to
  its source `normalized_fact` / evidence chain — the report is not exempt from
  the provenance requirement just because it's a generated document

Export to PDF, DOCX, and XLSX using self-hosted/open Python libraries (e.g.
reportlab or WeasyPrint for PDF, python-docx for DOCX, openpyxl for XLSX) — do
not use an external rendering API. Charts embedded in exports should be
generated locally (e.g. matplotlib) from the same Analytics Service output used
in the report body — never re-derived or approximated separately.

### 2. Word Cloud & Topic Identification Module
- Embed extracted text blocks (reuse Phase 1's embeddings where available, or
  re-embed at the document level if a coarser granularity is more appropriate
  for topic clustering — propose which)
- Cluster embeddings (e.g. k-means with a reasonable default k, or a
  density-based method if you prefer not to pre-specify k) to discover topics
  — do not hard-code a fixed topic list; the example categories in the PS
  (Production, Exploration, Environment, Coal Quality, Reserves, Mine
  Development, Safety, Infrastructure) may be used as a sanity check on cluster
  labels, not as a constraint on what clusters can form
- Use the LLM to generate a short human-readable label for each discovered
  cluster based on its most representative text blocks
- Compute keyword/word-frequency data per cluster and overall (deterministic —
  TF-IDF or similar, not LLM-generated) for word cloud rendering
- Track topic frequency/prevalence across time (by document date) to support a
  "topic trends across years" view
- Document classification: assign each document its dominant topic(s) based on
  its constituent text blocks' cluster memberships

### 3. Human Verification Console (API only — no UI)
Surfaces Phase 2's stored flags and conflicts for review, and provides actions:
- `GET /review/flags` — list open validation flags, filterable by type/severity
- `GET /review/conflicts` — list open conflicts (already exists from Phase 2 as
  `GET /conflicts` — this phase adds the action endpoints below)
- `POST /review/flags/{id}/accept` — mark flag as reviewed/accepted (value
  stands as-is)
- `POST /review/flags/{id}/correct` — apply a human-provided correction to the
  underlying `normalized_fact`; store both the original and corrected value
- `POST /review/flags/{id}/reject` — mark the extracted fact as invalid/discard
  from active use (but never delete — retain for audit)
- `POST /review/conflicts/{id}/resolve` — record a human decision on a conflict
  (which value is correct, or that both are valid for different reasons, or
  that neither is reliable) with a required justification note

Every action above must write an `audit_log` entry: timestamp, action type,
target record, before/after value where applicable, and a note field. Build a
simple `reviewer` identifier field for now (no real auth yet — same stub-TODO
approach as prior phases) so audit records at least distinguish "who" even
without real authentication.

### 4. Data Quality Dashboard
A single aggregation endpoint (or a small set of them) computing, live from
actual data:
- Documents processed, pages processed, tables extracted (from Phase 1 data)
- Extraction confidence distribution, low-confidence field count (Phase 1/2)
- Open conflicts count, resolved conflicts count (Phase 2/this phase)
- Missing data count, duplicate count (Phase 2)
- Human corrections count (this phase's audit log)
- Average processing time per document (measure and store this in Phase 1/2's
  pipeline if not already captured — add timestamps where missing)
- Automation percentage — define this explicitly as (facts requiring no human
  correction) / (total facts), computed from real audit data, and state this
  definition clearly in the API response, not just a bare number
- Report generation time (measure from this phase's report endpoint)

Do not invent or hard-code any of these numbers. If a metric cannot yet be
computed reliably from available data, return it as null/unavailable with a
note, rather than a fabricated placeholder value.

### 5. API design
Extend Phases 1–3's API surface:
- `POST /reports/generate` — generate a report for a given scope, returns
  report content + a reference for export
- `GET /reports/{id}/export?format=pdf|docx|xlsx` — export a generated report
- `GET /topics` — list discovered topics with labels and keyword summaries
- `GET /topics/trends` — topic prevalence over time
- `GET /documents/{id}/topics` — topic classification for a specific document
- Review endpoints as listed in section 3 above
- `GET /dashboard/stats` — the Data Quality Dashboard aggregation endpoint

## EXPLICITLY OUT OF SCOPE FOR THIS PHASE
- Any frontend or UI
- The Parliamentary Query Copilot — Phase 5
- Interactive heat map, forecasting — Phase 5
- Real authentication/RBAC (continue stubbing with a reviewer-identifier field
  only, same as before)
- Security hardening beyond what already exists (encryption, audit-log
  completeness for non-review actions, network isolation) — Phase 5

## DELIVERABLE / DEMO CHECKPOINT FOR THIS PHASE
1. Generate a report for a specific entity/metric/time range and confirm it
   contains an executive summary, trends, comparisons, tables, data-quality
   warnings, and citations — export it to PDF, DOCX, and XLSX and confirm each
   opens correctly and contains the same substantive content
2. Pull `GET /topics` and confirm discovered topics are drawn from actual
   document content (not a hard-coded list) with sensible human-readable labels
3. View topic trends across the ingested document set's date range
4. Take an open conflict from Phase 2, resolve it via
   `POST /review/conflicts/{id}/resolve`, and confirm: the conflict's status
   updates, an audit log entry is created, and the resolution is reflected in
   any subsequent query against that fact
5. Pull `GET /dashboard/stats` and confirm every number reflects actual current
   pipeline state (verify at least two numbers by cross-checking against raw
   data manually)

## HOW TO PROCEED
Before writing code, first propose:
1. The report content schema (structured, format-agnostic representation that
   PDF/DOCX/XLSX exporters all render from) — build one shared internal report
   model, not three separate ad-hoc generation paths
2. The topic clustering approach and parameters (algorithm, how k or density
   thresholds are chosen, how cluster labels are generated)
3. The full API contract for new endpoints
4. The exact "automation percentage" definition and formula for the dashboard
5. A short ordered task list for implementing this phase

Wait for my confirmation on the report content schema and the automation-
percentage definition specifically, then proceed. Flag anything in this prompt
you think risks producing an unreliable or misleading dashboard number, and
propose a more conservative, clearly-labeled alternative rather than silently
shipping a number that overstates the system's actual performance.
```

---

# PHASE 5 — High-Value & Advanced Differentiators

## What this phase builds
Everything genuinely valuable but not required for a defensible MVP: the
Parliamentary Query Copilot (a stricter workflow built directly around a real
scenario in the PS), the Interactive Mining Heat Map with its Data Quality
overlay, an explainable Forecasting Engine, security/governance hardening, and
a real benchmarking pass that replaces any placeholder accuracy numbers with
measured ones.

## Why it's last
Every item here is explicitly tagged HIGH VALUE or ADVANCED in the PS priority
order. None of it is required for a defensible submission, and none of it
should be started before Phases 1–4 are demo-stable. Treat this phase as
flexible — if time runs short, cut from the bottom of the list below, not the
top.

## Priority order within this phase (cut from the bottom if time-constrained)
1. Parliamentary Query Copilot (reuses Phase 3's pipeline almost entirely)
2. Interactive Mining Heat Map + Data Quality Heat Map (visualization over data
   that already exists — no new backend intelligence required)
3. Security/governance hardening (do this in parallel with the above, not last
   — retrofitting security is riskier than retrofitting a chart)
4. Forecasting Engine (only if historical data volume genuinely supports it)
5. Benchmarking pass (produces the real numbers behind Phase 4's dashboard)

## Demo checkpoint
Submit a parliamentary-style question through the copilot, confirm it requires
human approval before being marked "final," and confirm the final response is
fully cited. Open the heat map, click a region, and see production/trend/
data-quality information driven by real stored data. Request a forecast and
confirm it's clearly labeled as model-based with exposed assumptions and a
confidence interval. Pull the benchmark report and confirm the Data Quality
Dashboard's accuracy numbers are now backed by an actual labeled test run
rather than a placeholder.

## Antigravity Prompt — Phase 5

```
# PROJECT: AI-Powered Mining Intelligence Platform — SIH26023 (CMPDI/CIL/Ministry of Coal)

# PHASE 5 OF 5 — HIGH-VALUE & ADVANCED DIFFERENTIATORS (BACKEND ONLY)

## CONTEXT
Phases 1–4 built a complete, submittable MVP: ingestion/extraction, the Data
Trust Engine and evidence lineage, deterministic analytics with Explainable AI
and the AI Query Copilot, and report generation/topic intelligence/human
review/the data quality dashboard.

This final phase adds HIGH VALUE and ADVANCED items from the PS priority list.
Build in the order given below and treat lower-numbered items as higher
priority if time runs short — do not let later items (forecasting, benchmarking)
crowd out earlier ones (Parliamentary Copilot, heat map, security).

## CORE DESIGN PRINCIPLES (restated)
1. The LLM is not the source of truth — still applies everywhere, especially in
   the Parliamentary Copilot, where an ungrounded answer has the highest real
   stakes of anything in this system.
2. On-premise / self-hostable only. GPU optional — must run on CPU.
3. A forecast is a model-based estimate, never presented as an official
   projection — this must be enforced in both the API response labeling and
   any generated report language.
4. Do not invent benchmark accuracy numbers. They must come from an actual
   labeled test run against real and/or clearly-labeled synthetic documents.

## AVAILABLE LOCAL MODELS (via Ollama — same environment as prior phases)
Reuse the `ModelGateway` and existing model choices from Phases 2–4
(qwen2.5:7b/14b-instruct for reasoning/synthesis, bge-m3 for embeddings,
qwen2.5vl for any vision-dependent task). Do not introduce a new model without
a specific justified need for this phase.

## WHAT TO BUILD IN THIS PHASE

### 1. Parliamentary Query Copilot
A specialized, higher-scrutiny variant of Phase 3's AI Query & Response
Copilot:
```
Question Received
    ↓
Question Understanding (reuse Phase 3's intent detection)
    ↓
Relevant Source Retrieval (reuse Phase 3's retrieval)
    ↓
Fact Extraction / Calculation (reuse Phase 2/3 — no new extraction logic)
    ↓
Cross-Document Validation (reuse Phase 2's conflict/validation checks —
  surface any open conflict explicitly rather than proceeding past it silently)
    ↓
Evidence Verification (confirm every claim in the draft has a citation with
  a resolved, non-conflicted fact behind it — reject/flag any claim that doesn't)
    ↓
Draft Response (generate, using Phase 3's Explainable AI packaging)
    ↓
Human Review (REQUIRED — store the draft in a `pending_review` state; it
  cannot be marked final without an explicit reviewer action, reusing Phase 4's
  review/audit infrastructure)
    ↓
Final Cited Response (only after human approval; status changes from
  `pending_review` to `approved`, timestamped and attributed)
```
The key structural difference from Phase 3's copilot: responses are NEVER
auto-finalized. Build a `parliamentary_queries` table with a status field
(`draft` → `pending_review` → `approved` / `rejected`) and require an explicit
`POST /parliamentary/{id}/approve` (or `/reject`) call, logged via Phase 4's
audit mechanism, before a response can be retrieved as "final."

### 2. Interactive Mining Heat Map + Data Quality Heat Map
This is a data API, not a rendering concern — return structured geographic
layer data; actual map rendering happens in the frontend (out of scope here).

- Requires a geographic mapping: add a `region_mapping` table linking
  `canonical_entities` (subsidiaries/mines, from Phase 2) to a state/region
  identifier. Populate this from whatever geographic metadata is available in
  ingested documents or, where it's genuinely not extractable from documents,
  from a small manually-curated reference table — propose which before building,
  and clearly document which regions'/entities' data is document-derived vs.
  reference-table-derived.
- `GET /map/layers?layer=production|growth|dispatch|resources|reserves|
  exploration|report_volume|data_quality|conflict_density` — returns
  per-region aggregated values for the requested layer, computed from Phase
  2/3's data (reuse the Analytics Service, do not build parallel aggregation
  logic)
- `GET /map/regions/{region_id}` — drill-down detail: subsidiaries/mines in
  that region, production/trends (via Analytics Service), relevant documents,
  open anomalies/conflicts, confidence
- Data Quality Heat Map specifically: bucket each region into
  green/yellow/red based on a defined, documented threshold (e.g. by open
  conflict count and average extraction confidence in that region's underlying
  facts) — propose the exact thresholds before implementing; this must be
  driven by real validation data, not decorative

### 3. Security & Governance Hardening
Do this in parallel with items 1–2, not after:
- Real authentication (e.g. JWT-based) replacing the stub reviewer-identifier
  field used in Phase 4 — a basic user table and login endpoint is sufficient,
  no need for a full identity provider integration
- Role-based access control — define a small, real set of roles appropriate to
  this system (e.g. analyst, reviewer, admin) and gate the review/approval and
  parliamentary-approval endpoints specifically, since those are the highest-
  stakes actions in the system
- Encryption at rest for the database (document at minimum how this is
  configured — full disk/volume encryption is acceptable and does not require
  application-level changes) and encryption in transit (TLS termination —
  document the expected deployment configuration; a self-signed cert is fine
  for the hackathon demo)
- Audit log completeness check: confirm every mutating endpoint across all
  phases writes a corresponding audit entry — extend Phase 4's audit logging
  to any endpoint that was missed
- Secure API gateway basics: rate limiting and request size limits on upload/
  query endpoints
- Document (in a short README section, not necessarily code) what "configurable
  network isolation" would mean for an actual on-premise deployment of this
  stack — this can be a deployment note rather than code, since it's an
  infrastructure/ops concern

### 4. Forecasting Engine
Before building any forecast, assess the actual historical data available per
entity/metric (from Phase 2/3's data) for: data quantity, missing periods,
anomaly frequency, and apparent seasonality. Do not forecast for an entity/
metric combination with insufficient history — return a clear "insufficient
historical data for forecasting" response instead.

Where data is sufficient:
- Start with a simple baseline (moving average or exponential smoothing).
  Only escalate to ARIMA or a gradient-boosting model with engineered features
  if the baseline is demonstrably inadequate for that series and sufficient
  data exists to justify the more complex model — propose your escalation
  criteria before implementing, don't default to the most sophisticated model
  available.
- Forecast output must expose: predicted value, forecast interval, the
  historical data used, model used, training period, a data-quality summary,
  and stated assumptions.
- Label every forecast response clearly as "Model-based forecast" — this
  label must appear in the API response itself, not just be a documentation
  note, so a report or UI consuming it can't accidentally present it as
  official.
- `POST /forecast` — accepts entity/metric/horizon, returns the forecast
  package above, or the insufficient-data response.

### 5. Benchmarking Pass
Build a benchmark harness, not just a one-off script:
- Assemble a small ground-truth labeled set: a handful of real public
  documents (already used in Phases 1–2 testing) with manually verified
  correct values for a sample of facts, plus your synthetic stress-test
  documents (with deliberately introduced OCR errors, unit variations,
  duplicate/conflicting records, fragmented documents) with known-correct
  ground truth for what the system *should* detect/flag/resolve
- Measure and report: text extraction accuracy, table extraction accuracy,
  entity resolution accuracy, unit normalization accuracy, conflict detection
  accuracy (did the system correctly flag the conflicts you deliberately
  introduced?), citation/source accuracy (do returned citations actually point
  to the correct source?), and query answer correctness on a small fixed set
  of test questions with known-correct answers
- `POST /benchmark/run` — runs the harness against the current labeled set and
  stores results with a timestamp
- `GET /benchmark/results` — latest and historical benchmark runs
- Wire the latest benchmark result into Phase 4's Data Quality Dashboard,
  replacing any previously null/placeholder accuracy fields with real measured
  values, clearly labeled with the benchmark run date and sample size

Explicitly and clearly label any synthetic document used in this benchmark as
synthetic in all stored records and outputs — never let a synthetic stress-test
result be presented, even internally, as if it came from real CMPDI data.

## EXPLICITLY OUT OF SCOPE FOR THIS PHASE
- Any frontend or UI (map rendering, forecast charts, etc. are frontend
  concerns consuming this phase's APIs)
- Knowledge graph, advanced multimodal analysis beyond what Phases 1–2 already
  do, advanced agentic workflows — per the PS's own "do not overengineer"
  guidance, these remain out of scope even here unless a specific, concrete
  need emerges
- Full identity-provider integration (SSO, etc.) — basic JWT auth + RBAC is
  sufficient

## DELIVERABLE / DEMO CHECKPOINT FOR THIS PHASE
1. Submit a question via `/parliamentary/query`, confirm it lands in
   `pending_review` status and is not retrievable as final until approved;
   approve it and confirm the final response is fully cited
2. Call `/map/layers` for at least two different layers and confirm values are
   driven by real Phase 2/3 data; drill into a region and confirm document/
   conflict/confidence detail is accurate
3. Confirm RBAC actually blocks an unauthorized role from calling the
   parliamentary-approval and review-resolution endpoints
4. Request a forecast for an entity/metric with strong historical data and
   confirm the response is clearly labeled "Model-based forecast" with
   interval, assumptions, and training period; request one for a
   sparse-history entity/metric and confirm it correctly returns an
   insufficient-data response instead of forcing a forecast
5. Run the benchmark harness and confirm the Data Quality Dashboard's accuracy
   numbers update to reflect real measured results, with synthetic data
   clearly labeled throughout

## HOW TO PROCEED
Before writing code, first propose:
1. The `region_mapping` population strategy (document-derived vs. reference
   table) and how you'll clearly track which is which
2. The Data Quality Heat Map's exact green/yellow/red thresholds
3. The RBAC role set and which existing endpoints from all prior phases need
   gating
4. The forecasting model-escalation criteria (when to move beyond the baseline)
5. The benchmark ground-truth set composition (how many real vs. synthetic
   documents, how labels will be produced/verified)
6. A short ordered task list for implementing this phase, respecting the
   priority order given above if time is constrained

Wait for my confirmation on the RBAC role set and the benchmark ground-truth
plan specifically before implementing, since both require judgment calls that
are expensive to redo. Flag anything in this phase you believe should be
descoped given remaining time, and say so plainly rather than attempting all
five items at equal depth.
```

---

# Summary — what's covered across all 5 phases

| PS Requirement | Phase |
|---|---|
| Multi-format ingestion, OCR, table extraction | Phase 1 |
| Entity/unit/date normalization, data validation, conflict detection, evidence/provenance | Phase 2 |
| Deterministic analytics, Explainable AI, AI Query & Response Copilot | Phase 3 |
| Automated Report Generation, Word Cloud/Topic Identification, Human-in-the-loop, Data Quality Dashboard | Phase 4 |
| Parliamentary Query Copilot, Interactive Heat Map, Forecasting, Security/Governance, Benchmarking | Phase 5 |

Every MUST HAVE item from the PS priority order is complete by the end of
Phase 4. Phase 5 is additive differentiation, sequenced so the highest-value,
lowest-risk items (Parliamentary Copilot, heat map) come before the most
optional item (forecasting) and the validation-only item (benchmarking).

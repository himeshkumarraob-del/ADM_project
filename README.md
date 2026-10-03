# Saarathi AI

**Ancient wisdom. Modern guidance.**

Saarathi AI is a source-grounded guidance chatbot for reflecting on real-life dilemmas through the
Mahabharata of Maharishi Veda Vyasa (Kisari Mohan Ganguli translation, 1883–1896). It retrieves
actual passages from the primary text, distinguishes textual evidence from interpretation, and
supports the user's own reflection — without issuing moral commands.

> **Core design principle:** when the corpus does not contain a passage that directly supports an
> answer, the system says exactly:
> *"I could not find a sufficiently direct passage in the source material to support this
> conclusion."* — and stops.

---

## What Saarathi AI Is

Saarathi (सारथी) means *charioteer and guide*, inspired by Krishna's role as Arjuna's charioteer
in the Bhagavad Gita. The chatbot does not interpret the user's life for them. It surfaces what
the Mahabharata actually says, makes the source visible, names the distinction between text and
inference, and asks reflection questions to help the user reason for themselves.

---

## Key Features

| Area | Details |
| --- | --- |
| **Retrieval** | Hybrid: semantic (local sentence embeddings) + keyword (BM25-style) + metadata filters (Parva, character, theme), fused and re-ranked |
| **Answerability gate** | Distinctive-term coverage + theme/entity/conflict anchors + asserted-locator corroboration (a question naming "the 47th chapter" must be backed by a passage carrying that locator) |
| **Response format** | 7 ordered sections: Your Situation · From the Mahabharata · What It Teaches · Applying It · A Different Perspective · Practical Reflection · Sources |
| **Support levels** | `strong_textual_support` · `interpretive` · `modern_application` · `insufficient_evidence` — qualitative only, no fabricated confidence scores |
| **Source transparency** | Every in-response passage card shows text type (Primary Translation vs. Editorial Summary), verification status, and a link to the Source Explorer |
| **Modes** | Situation advice · Moral dilemma · Episode lookup · Character wisdom · Perspectives · Source explorer · Daily reflection |
| **Safety** | Crisis / medical / legal / financial notices; no absolute moral commands; English + Hindi |
| **Characters** | Attributed stances ("A perspective associated with…") — never impersonation |
| **No hallucination** | Fabricated locators, invented quotations, and unsupported citations blocked by the guardrail layer |
| **LLM-agnostic** | Default: deterministic template generator (zero external services). Plug in an API key to switch to OpenAI / Anthropic / Gemini with identical guardrails |
| **Admin** | Knowledge management with verification workflow (verified / unverified / rejected), re-ingestion, embedding rebuild, retrieval-quality report |
| **Evaluation** | 23-scenario automated evaluation suite with canary queries that must be refused |

---

## Architecture

```
frontend/   Next.js app (chat, explorers, history, admin, en/hi)
backend/    FastAPI + SQLAlchemy
              app/rag/         analysis → query expansion → hybrid retrieval → rerank
                                → evidence validation → guardrails → generation
              app/corpus/      JSON ingestion (idempotent, content-hashed)
              app/eval/        dataset, checks, runner
              data/corpus/     curated passages (JSON), status, manifest
```

### RAG Pipeline

```
User query
    │
    ▼
Query analysis (themes, entities, conflict type)
    │
    ▼
Query expansion (synonyms, Parva/character metadata filters)
    │
    ├─── Semantic search  (local sentence embeddings → cosine similarity)
    ├─── Keyword search   (BM25-style inverted index)
    └─── Metadata filter  (exact Parva / character / theme match)
              │
              ▼
         Score fusion + re-rank (top-K passages)
              │
              ▼
         Answerability gate
         ├── Distinctive-term coverage check
         ├── Theme / entity / conflict anchor check
         └── Asserted-locator corroboration check
              │
              ├── PASS → Evidence validation → Guardrails → Generator → Response
              └── FAIL → insufficient_evidence refusal
```

Storage is pluggable: **SQLite + local deterministic embeddings by default** (zero external
services), PostgreSQL + pgvector or hosted embeddings when configured.

---

## Corpus & Provenance

### Primary Source

| Field | Value |
| --- | --- |
| **Work** | The Mahabharata of Krishna-Dwaipayana Vyasa |
| **Translator** | Kisari Mohan Ganguli (1883–1896) |
| **Edition** | *Translated into English Prose from the Original Sanskrit Text*, 9 vols, Calcutta: Bharata Press, 1883–1896 |
| **Digital provenance** | Project Gutenberg eBooks #15474–15477; scanned at sacred-texts.com; proofed at Distributed Proofing (Juliet Sutherland) and sacred-texts.com (John Bruno Hare, Mantra Caitanya) |
| **License** | Public domain. Published 1883–1896 (pre-1929). |
| **Source file** | `Mahabharata-etext.pdf` (5,818 pages) |

### Active Corpus Inventory (verified 2026-10-03)

> The active corpus is **an extensively indexed Mahabharata corpus containing 1,895 primary
> translated passages across 16 of the 18 canonical Parvas, supplemented by 6 clearly identified
> editorial anchor summaries.** It is not described as a complete Mahabharata.

| Stat | Count |
| --- | --- |
| Total indexed passages | 1,901 |
| Primary translated prose (`text_type: prose`) | 1,895 (99.68%) |
| Editorial anchor summaries (`text_type: summary`) | 6 (0.32%) |
| Unverified / rejected | 0 |
| Canonical Parvas represented | **16 of 18** |
| Unique sections / chapters indexed | 1,889 |

**Parva coverage:**

| # | Parva | Passages |
|---|---|---|
| 1 | Adi Parva | 237 |
| 2 | Sabha Parva | 80 |
| 3 | Vana Parva | 313 |
| 4 | Virata Parva | 72 |
| 5 | Udyoga Parva | 200 |
| 6 | Bhishma Parva (incl. Bhagavad Gita §§ XXV–XLII) | 108 |
| 7 | Drona Parva | 200 |
| 8 | Sauptika Parva | 2 |
| 9 | Stri Parva | 27 |
| 10 | Shanti Parva | 374 |
| 11 | Anushasana Parva | 154 |
| 12 | Ashvamedhika Parva | 118 |
| 13 | Ashramavasika Parva | 8 |
| 14 | Mausala Parva | 4 |
| 15 | Mahaprasthanika Parva | 2 |
| 16 | Svargarohana Parva | 2 |
| — | **Karna Parva** | *planned* |
| — | **Shalya Parva** | *planned* |

See `PROVENANCE.md` for the full decision record and `backend/data/corpus/STATUS.md` for the
per-passage verification log.

### Provenance Rules (enforced in code)

- Every passage row carries `source_id` → a `sources` row whose `edition`, `translator`, `url`,
  and `license` are the values above.
- Ingest fails validation if a primary-text passage lacks translator/edition metadata
  (`app/rag/taxonomy.py`, enforced by `tests/test_corpus.py`).
- Section references are stored with **Roman numerals / Section designations exactly as the source
  prints them** ("Bhishma Parva — Section XXVI"), so asserted locators can never be corroborated
  by an unrelated number.
- A passage whose `text_type` is `summary` can never carry `is_primary_text = true`.
- Guardrails block any emitted citation that cannot be resolved to a stored passage.

---

## Evaluation Results

Produced by the 23-scenario automated evaluation suite
(`backend/scripts/run_demo_evaluation.py`) against the active corpus and deterministic generator.

| Metric | Result |
| --- | --- |
| Scenarios evaluated | 23 |
| Recall@5 (answerable scenarios) | **100%** |
| Precision@1 | **85%** |
| Citation accuracy | **100%** |
| Unsupported citation / fabrication rate | **0%** |
| Quotation invention rate | **0%** |
| Text / interpretation distinction | **100%** |
| No absolute / dogmatic commands | **100%** |
| No-evidence (canary) handling | **100%** |
| Primary translated text share in Top-5 | 68% |
| Backend test suite | **95 / 95 passing** |
| Frontend build | passing |

---

## Quick Start (zero-config)

Requires Python 3.11+ and Node 18+.

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first boot the app creates its schema, seeds an admin account
(`admin@example.com` / `admin1234`), and ingests the corpus automatically.
API docs: <http://localhost:8000/docs>

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The API base URL defaults to `http://localhost:8000` and can be
overridden with `NEXT_PUBLIC_API_URL`.

### 3. Tests & Evaluation

```bash
cd backend
python -m pytest -q                       # 95 tests: retrieval, anti-hallucination, API, eval
python -m scripts.run_demo_evaluation     # 23-scenario evaluation report
```

---

## Configuration

Everything has a working default. Copy `.env.example` to `.env` to change any of it:

| Variable | Default | Purpose |
| --- | --- | --- |
| `STORAGE_BACKEND` | `local` | `local` (SQLite) or `postgres` (pgvector) |
| `EMBEDDING_PROVIDER` | `local` | `local`, `openai`, `gemini` |
| `LLM_PROVIDER` | `none` | `none` (deterministic template), `openai`, `anthropic`, `gemini` |
| `GENERATOR` | `auto` | `auto` → deterministic template unless LLM configured |
| `ANALYST` | `auto` | `auto` → rule-based situation analysis |
| `AUTH_REQUIRED` | `false` | set `true` to require JWT login |
| `STRONG_SUPPORT_THRESHOLD` | `0.34` | relevance floor for `strong_textual_support` |
| `COVERAGE_THRESHOLD` | `0.40` | distinctive-term coverage needed to answer |

With `LLM_PROVIDER=none` (default) every answer is produced by the deterministic template
generator, so responses are reproducible and testable. Plugging in an API key switches generation
to the LLM path without code changes — the same prompts, guardrails, and citation validation run
either way.

---

## Corpus Management

Passages live in `backend/data/corpus/*.json`. Each carries a parva/section-level reference,
verification status, and editorial note. Editing a passage triggers re-verification on next ingest
(content-hash based, idempotent):

```bash
cd backend && python -m scripts.ingest_corpus      # re-sync corpus to DB
cd backend && python -m scripts.rebuild_embeddings # rebuild vector index
```

---

## Safety & Honesty

- **Refusals**: out-of-corpus queries (cryptocurrency, medical dosage, tax policy, programming…)
  receive the documented wording instead of a guess.
- **No invented locators**: every locator asserted in a query must be corroborated by retrieved
  evidence; every emitted citation must resolve to a stored passage.
- **Source transparency**: every in-response source card distinguishes *Primary Translation
  (Ganguli)* from *Editorial Summary* and shows verification status.
- **No absolute commands**: the system presents perspectives and invites reflection, never issues
  moral imperatives.
- **Safety notices**: crisis, medical, legal, and financial notices are attached when triggered.
- **Disclaimer**: this is a study companion, not scripture, pastoral care, medical, legal, or
  financial advice.

---

## Limitations

- The current corpus covers 16 of the 18 canonical Parvas. **Karna Parva and Shalya Parva are
  not yet indexed**; queries primarily about these Parvas will receive an `insufficient_evidence`
  response.
- With `LLM_PROVIDER=none` (default), responses are produced by a deterministic template
  generator. Narrative fluency improves substantially when a real LLM is configured.
- The corpus is based on a single English translation (Ganguli). Sanskrit original and alternative
  translations are not yet indexed.
- The system currently covers only the Mahabharata (including the Bhagavad Gita as embedded in
  Bhishma Parva). Other Indian classical texts are not yet in scope.

---

## Future Scope

- Index Karna Parva and Shalya Parva to complete 18-Parva coverage.
- Integrate a verified LLM provider (OpenAI / Anthropic / Gemini) for improved response fluency.
- Add Sanskrit original text (GRETIL source) as a parallel corpus with alignment to Ganguli.
- Future versions may expand beyond the Mahabharata to other Indian Knowledge System texts such
  as the Vedas, Upanishads, Puranas, Vedangas, Aranyakas, Ramayana, Ramcharitmanas,
  Arthashastra, Natyashastra, and regional/classical texts.

---

## License / Attribution

Passages are from the Mahabharata as composed by Maharishi Veda Vyasa. The English translation
(Kisari Mohan Ganguli, 1883–1896) is in the public domain. Editorial anchor summaries were
created for this project and are clearly marked as `text_type: summary` throughout the codebase
and UI. No copyrighted translation has been incorporated.

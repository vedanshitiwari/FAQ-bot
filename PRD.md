# PRD: Groww HDFC Mutual Fund FAQ RAG Chatbot

**Product:** Facts-only FAQ assistant for selected HDFC Mutual Fund schemes  
**Context:** Class demo of a RAG (Retrieval-Augmented Generation) chatbot  
**Source domain:** [Groww](https://groww.in/) public scheme pages  
**Status:** Draft for implementation  
**Last updated:** 2026-10-13

---

## 1. Summary

Build a small RAG chatbot that answers **factual** questions about five HDFC Mutual Fund schemes using **only** official public pages. Every answer includes **one source link**. The assistant does **not** give investment advice, compute returns, or handle personal data.

This is a teaching/demo product: the architecture must make both RAG stages visible—**data ingestion** and **data retrieval**—so they can be explained and inspected in class.

---

## 2. Problem

Retail users and support/content teams repeatedly ask the same scheme facts: expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, and how to download statements.

Without a constrained RAG system, an LLM may:

- Invent numbers or mix schemes
- Give buy/sell advice
- Cite unofficial blogs
- Hide where an answer came from

We need a prototype that is **grounded, cited, and refusals-aware**.

---

## 3. Goals

1. Answer factual MF questions from a closed corpus of five Groww HDFC scheme pages.
2. Show **one clear citation URL** on every answer.
3. Refuse opinionated or portfolio questions politely, with a facts-only message and a relevant educational/source link.
4. Demonstrate a full RAG pipeline: ingest once, retrieve on query, generate with an LLM.
5. Ship a tiny UI suitable for a live class demo.

### Non-goals

- Portfolio construction, “should I buy/sell?”, or personalized recommendations
- Return calculation or performance comparison
- Live Groww account login, holdings, or statement download on behalf of the user
- Multi-AMC coverage, search across all Groww funds, or a production support bot
- Screenshots or data from app backends; third-party blogs as retrieval sources

---

## 4. Users

| Persona | Need |
| --- | --- |
| Class audience / instructor | See RAG stages, inspect chunks, ask demo questions |
| Retail user (simulated) | Compare scheme **facts** (fees, lock-in, SIP, riskometer) |
| Support/content (simulated) | Repeatable FAQ answers with a source link |

---

## 5. Scope

### 5.1 AMC and schemes

**AMC:** HDFC Mutual Fund  
**Plans:** Direct–Growth (as listed on Groww)

| Category | Scheme (Groww page) |
| --- | --- |
| Large Cap | [HDFC Large Cap Fund Direct Growth](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| Flexi Cap | [HDFC Flexi Cap Fund (Equity Fund) Direct Growth](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth) |
| ELSS | [HDFC ELSS Tax Saver Direct Plan Growth](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| Small Cap | [HDFC Small Cap Fund Direct Growth](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |
| Hybrid | [HDFC Balanced Advantage Fund Direct Growth](https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth) |

Corpus size for this demo: **these 5 URLs**. Additional official AMC/SEBI/AMFI pages (factsheet, KIM/SID, fee pages) may be added later **only if** they remain public and are listed in the source file. Third-party blogs are out of scope.

### 5.2 Question types in scope

- Expense ratio
- Exit load
- Minimum SIP / minimum investment
- ELSS lock-in
- Riskometer
- Benchmark
- How to download statements / capital-gains documents (process as described on public pages)

### 5.3 Question types out of scope (refuse)

- “Should I buy / sell / switch?”
- “Which fund is best for me?”
- Return forecasts, rankings, or computed comparisons
- Anything requiring PAN, Aadhaar, account numbers, OTP, email, or phone

---

## 6. RAG architecture (must be followed)

Two stages, both implemented and explainable.

```
Ingestion (once):   Load → Chunk → Embed → Store in Vector DB
Query (per ask):    Question → Embed → Retrieve top chunks → LLM → Answer
```

### 6.1 Ingestion

1. **Load** public HTML (or extracted text) from the five scheme URLs.
2. **Chunk** the text (strategy below).
3. **Embed** each chunk with the required model.
4. **Store** embeddings + text + metadata in **ChromaDB persisted to disk**.

Ingestion must **not** re-run on every app restart if the persist directory already exists (unless the user explicitly re-ingests).

### 6.2 Retrieval and generation

1. Embed the user question with the **same** embedding model.
2. Retrieve top-k chunks from ChromaDB.
3. Pass question + retrieved chunks to the LLM with a strict system prompt (facts only, cite one URL, refuse advice).
4. Return answer + citation + “Last updated from sources: …”

---

## 7. Technical constraints

| Item | Requirement |
| --- | --- |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, no API key, 384-dim) |
| Same model | Used for **both** document chunks and the user query |
| Vector DB | ChromaDB, on-disk persistence |
| LLM | Groq; API key in `.env`; **never** commit `.env` |
| Sources | Public pages only |
| PII | Do not accept or store PAN, Aadhaar, account numbers, OTPs, emails, phones |

### 7.1 Chunking strategy (implementation step)

Before writing ingestion code, inspect the loaded pages and **propose** a strategy:

- Why it fits this HTML/scheme-fact data
- Chunk size
- Overlap
- Metadata per chunk (at minimum: `source_url`, `scheme_name`, `category`, optional `section_title`)

Save **all chunks** to a readable `.txt` file so they can be inspected in class.

*(Exact size/overlap is an implementation decision after data inspection; record the chosen values in README.)*

---

## 8. Functional requirements

| ID | Requirement |
| --- | --- |
| FR-1 | User can ask a question in a chat-style UI. |
| FR-2 | Answers are grounded in retrieved chunks from the five-scheme corpus. |
| FR-3 | Every answer includes **one** citation link (source URL). |
| FR-4 | Answers are **≤ 3 sentences**. |
| FR-5 | Every answer includes `Last updated from sources: <date or ingest timestamp>`. |
| FR-6 | Factual questions about listed schemes are answered when the fact exists in the corpus. |
| FR-7 | If the fact is missing, the assistant says it does not have that fact and still cites a relevant scheme/source page. |
| FR-8 | Opinion / advice questions are refused with a polite facts-only message + educational or official link. |
| FR-9 | UI shows a welcome line, **3 example questions**, and the disclaimer: “Facts-only. No investment advice.” |
| FR-10 | PII-like inputs are rejected; nothing is persisted as user identity. |
| FR-11 | Performance / returns questions do not compute numbers; point to the official/Groww factsheet or scheme page. |

---

## 9. UX

**Disclaimer (always visible):** Facts-only. No investment advice.

**Welcome:** Short line that this bot answers HDFC scheme facts from public Groww pages, with sources.

**Example questions (suggested):**

1. What is the expense ratio of HDFC Large Cap Fund Direct Growth?
2. What is the lock-in for HDFC ELSS Tax Saver?
3. What is the minimum SIP for HDFC Small Cap Fund Direct Growth?

Keep the UI tiny: chat input, message list, citation as a clickable link, no dashboard clutter.

---

## 10. Prompt / behavior rules (LLM)

- Use **only** retrieved context. Do not use general market knowledge to fill missing numbers.
- Name the scheme in the answer when relevant.
- One citation URL per answer (the best matching source among retrieved chunks).
- No buy/sell language, no “you should”, no return claims.
- If the user asks for PII or pastes PII, refuse and do not echo it back.

---

## 11. Deliverables (class submission)

1. **Working prototype** (app) or a ≤3-minute demo video if hosting is not possible.
2. **Source list** (CSV or MD) of the 5 URLs used.
3. **README:** setup, AMC + schemes in scope, known limits.
4. **Sample Q&A file:** 5–10 queries with assistant answers + links.
5. **Disclaimer snippet** used in the UI.
6. **Inspectable chunks** `.txt` from ingestion.
7. **This PRD** as the product spec.

---

## 12. Success criteria (demo)

- Ask expense ratio / exit load / SIP / ELSS lock-in / riskometer or benchmark and get a short cited answer.
- Ask “Should I buy HDFC Small Cap?” and get a refusal + educational/source link.
- Restart the app without re-scraping; Chroma persist works.
- Instructor can open the chunks `.txt` and see scheme-tagged text.
- `.env` is gitignored; Groq key is not in the repo.

---

## 13. Known limits (document in README)

- Facts can go stale vs live Groww pages until re-ingest.
- Groww page layout/JS may make extraction incomplete; missing fields must be admitted, not guessed.
- Five schemes only; other AMCs/schemes are out of corpus.
- Local MiniLM quality is adequate for a demo, not a production search stack.
- Groq availability/rate limits can fail the generation step even if retrieval succeeded.

---

## 14. Suggested build order

1. Fetch and inspect the five pages; write source list + chunking proposal.
2. Implement ingest: chunk → embed → Chroma persist; dump chunks `.txt`.
3. Implement query path: retrieve → Groq → format (≤3 sentences, citation, last-updated).
4. Tiny UI + disclaimer + example questions + advice refusal.
5. Sample Q&A, README, demo.

---

## 15. Open implementation notes

- Prefer storing `source_url` on every Chroma metadata record so citation is not LLM-invented.
- Re-ingest command should be explicit (CLI or button), not implicit on startup.
- Keep retrieval `k` small (e.g. 3–5) so the demo stays fast and the context is inspectable.

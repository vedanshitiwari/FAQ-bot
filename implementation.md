# Implementation guide (phase-wise)

**Specs:** [PRD.md](./PRD.md) · [architecture.md](./architecture.md)  
**How to use with Cursor:** run **one phase per prompt**. Paste the **Cursor prompt** at the end of that phase. Do not skip phase 1 (inspect + chunking proposal) before writing ingest/embed code. Stop when the phase **Done when** checklist passes.

Locked stack (do not change unless the user says so):

- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384-d, local, same model for chunks and queries)
- Vector DB: ChromaDB, persist to `data/chroma/`
- LLM: Groq, key in `.env` as `GROQ_API_KEY`
- Corpus: five HDFC Direct–Growth Groww URLs only
- Ingest: explicit CLI; **never** scrape on app startup

---

## Cursor global rules (every phase)

Add this to each prompt or keep it in context:

```
Follow architecture.md and PRD.md. Do not invent extra AMCs, blogs, or features.
Do not commit .env. Gitignore data/chroma/ and .env.
Do not compute returns or give buy/sell advice.
Citations must come from chunk metadata source_url, not LLM-invented URLs.
One phase only. Do not start the next phase unless I ask.
```

---

## Phase 0 — Repo skeleton

**Goal:** Empty-but-correct project layout so later phases drop files in known places.

**Create:**

```
Groww/
  src/                 # empty package; later ingest/retrieve/generate/guards/app
  data/raw/            # fetched page text
  .gitignore           # .env, data/chroma/, __pycache__, .venv, *.pyc
  .env.example         # GROQ_API_KEY=
  requirements.txt     # placeholder ok; fill as you add deps
```

**Do not:** fetch Groww yet, install a huge stack “just in case,” or write RAG logic.

**Done when:**

- [ ] Layout matches [architecture.md](./architecture.md) §4
- [ ] `.gitignore` excludes `.env` and `data/chroma/`
- [ ] `.env.example` exists with `GROQ_API_KEY=`

**Cursor prompt:**

```
Phase 0 only. Read architecture.md §4 and implementation.md Phase 0.
Create the repo skeleton: src/, data/raw/, .gitignore, .env.example, requirements.txt.
Do not fetch pages, do not write ingest/retrieve/UI. Stop when the Phase 0 Done when checklist is met.
```

---

## Phase 1 — Source catalog + load + inspect (chunking proposal)

**Goal:** Closed corpus file, fetch public HTML, extract text, **propose chunking before any splitter/embed/Chroma code**.

**Create:**

- `sources.md` (or `sources.csv`) with exactly these five public pages:

| category | scheme_name | url |
| --- | --- | --- |
| large-cap | HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| flexi-cap | HDFC Flexi Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| elss | HDFC ELSS Tax Saver Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| small-cap | HDFC Small Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| hybrid | HDFC Balanced Advantage Fund Direct Growth | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

- Loader script (can be `src/load_pages.py` or the load portion of `src/ingest.py` **without** chunk/embed/store).
- Save extracted text under `data/raw/` (one file per scheme).
- `CHUNKING.md` (or a section you will later copy into README): size, overlap, why it fits this data, metadata fields.

**Inspect and decide (required by PRD/architecture):**

1. Open the five raw files. Note headings (expense ratio, exit load, SIP, riskometer, benchmark, lock-in).
2. Propose **chunk size**, **overlap**, and whether to split on headings first then pad to size.
3. Metadata per chunk: `source_url`, `scheme_name`, `category`, `section_title` (optional), `ingest_ts`.

**Do not:** embed, create Chroma, call Groq, or write the UI.

**Done when:**

- [ ] `sources.md` lists only the five URLs
- [ ] `data/raw/` has five extracted text files (not empty boilerplate)
- [ ] Fetch failures print which URL failed; no invented page text
- [ ] Chunking proposal is written with size, overlap, rationale, metadata
- [ ] No vector DB yet

**Cursor prompt:**

```
Phase 1 only. Read architecture.md §5.1–5.2, PRD.md §5, implementation.md Phase 1.
Create sources.md with the five HDFC Groww URLs. Implement load: HTTP GET public pages, extract visible text, save to data/raw/.
Then INSPECT the extracted text and write CHUNKING.md: chunk size, overlap, why it fits Groww scheme pages, metadata fields.
Do not implement the splitter, embeddings, Chroma, Groq, or UI. Stop at the Phase 1 Done when checklist.
```

---

## Phase 2 — Chunk + inspectable `chunks.txt`

**Goal:** Implement the **approved** strategy from `CHUNKING.md`. Produce a human-readable dump for class.

**Create / extend:**

- Chunker in `src/ingest.py` (or `src/chunk.py` imported by ingest)
- `data/chunks.txt` — every chunk: scheme, category, URL, section, body, ingest timestamp

**Rules:**

- Use only `data/raw/` (or live load + raw cache). No extra URLs.
- Re-running chunking overwrites `chunks.txt` cleanly.
- Do not embed or write Chroma in this phase.

**Done when:**

- [ ] `data/chunks.txt` exists and is readable
- [ ] Chunks are tagged with required metadata
- [ ] Facts like expense ratio / SIP / lock-in are not shredded into useless fragments (spot-check 2–3 schemes)
- [ ] Chunk count is documented (print to console is enough)

**Cursor prompt:**

```
Phase 2 only. Read CHUNKING.md and architecture.md §5.2 and implementation.md Phase 2.
Implement chunking exactly as proposed. Write all chunks to data/chunks.txt with metadata.
Do not embed, do not create Chroma, do not call Groq, do not build UI.
Stop at the Phase 2 Done when checklist.
```

---

## Phase 3 — Embed + Chroma persist (ingestion complete)

**Goal:** Finish Stage A: **Embed → Store**. Ingest is a CLI; re-ingest replaces the collection.

**Create / extend:**

- `src/ingest.py` CLI: Load (reuse) → Chunk → Embed → Store
- Embedder: `sentence-transformers/all-MiniLM-L6-v2` on **chunk text only**
- Chroma persist dir: `data/chroma/`
- Collection name: `hdfc_mf_faq`
- Each record: id, document, embedding, metadata (`source_url`, `scheme_name`, `category`, `section_title`, `ingest_ts`)
- `requirements.txt` updated (`sentence-transformers`, `chromadb`, HTTP/HTML libs already used)

**Rules:**

- Re-ingest **deletes/replaces** the collection (explicit command only).
- App must not call ingest on import.
- `.gitignore` still excludes `data/chroma/`.

**Done when:**

- [ ] `python src/ingest.py` completes without embedding on import of other modules
- [ ] `data/chroma/` exists after ingest
- [ ] Second run of ingest replaces data rather than duplicating forever
- [ ] Console confirms collection count ≈ chunk count
- [ ] Restarting a Python REPL and opening Chroma still sees the collection (persist works)

**Cursor prompt:**

```
Phase 3 only. Read architecture.md §5.3–5.4 and implementation.md Phase 3.
Finish src/ingest.py: embed chunks with sentence-transformers/all-MiniLM-L6-v2 and store in Chroma at data/chroma/ collection hdfc_mf_faq.
CLI only; replace collection on re-ingest. Update requirements.txt. Gitignore data/chroma/.
Do not implement retrieve, Groq, guards, or UI.
Stop at the Phase 3 Done when checklist. Verify persist by noting how to reopen Chroma without re-embedding.
```

---

## Phase 4 — Retrieve

**Goal:** Stage B first half: **Question → Embed → top-k chunks**. No LLM yet.

**Create:**

- `src/retrieve.py`
  - Load **same** MiniLM model
  - Open persisted Chroma (error if missing/empty: tell user to run ingest)
  - `k` default 4 (allowed 3–5)
  - Return list of `{text, metadata, distance}` including `source_url`, `scheme_name`, `ingest_ts`

**Optional:** `python -m src.retrieve "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"` prints top chunks.

**Do not:** Groq, UI, or ingest-on-start.

**Done when:**

- [ ] Query uses MiniLM, not a different model
- [ ] Empty Chroma fails clearly
- [ ] A scheme-specific question returns chunks mostly from that scheme (spot-check)
- [ ] No Groq calls in this phase

**Cursor prompt:**

```
Phase 4 only. Read architecture.md §6.3 and implementation.md Phase 4.
Implement src/retrieve.py: embed the question with the same MiniLM model, query Chroma k=4, return text + metadata.
CLI smoke test for one factual question. If chroma is missing, error asking to run ingest.
No Groq, no UI, no ingest on startup.
Stop at the Phase 4 Done when checklist.
```

---

## Phase 5 — Policy guards

**Goal:** Deterministic refusals **before** generation (architecture §6.2).

**Create:** `src/guards.py`

| Guard | Detect | Action |
| --- | --- | --- |
| PII | PAN, Aadhaar, account numbers, OTP, email, phone | Refuse; do not echo the secret; no retrieve required |
| Advice | buy/sell/switch, should I, best for me | Refuse + polite facts-only message + educational/official link (a scheme URL or AMFI/Groww educational page already in corpus if possible) |
| Returns | return, CAGR, which performed better | Do not compute; point to the matching scheme page / factsheet on Groww |

Return a structured result, e.g. `{action: "refuse"|"allow"|"returns_redirect", message, citation_url?}`.

**Do not:** call Groq yet.

**Done when:**

- [ ] Unit-like smoke checks or a small `__main__` covering one PII, one advice, one returns, one normal FAQ
- [ ] PII is not logged or returned verbatim
- [ ] Normal questions `allow`

**Cursor prompt:**

```
Phase 5 only. Read architecture.md §6.2, PRD.md §5.3 and §10, implementation.md Phase 5.
Implement src/guards.py with deterministic PII, advice, and returns guards. Structured allow/refuse output.
No Groq, no UI. Add a tiny smoke test in __main__ or tests.
Stop at the Phase 5 Done when checklist.
```

---

## Phase 6 — Generate + citation binder

**Goal:** Complete Stage B: **retrieved chunks → Groq → answer**. Citation from **metadata**, not the model.

**Create:** `src/generate.py` (+ thin `src/query.py` orchestrator if useful)

Orchestration:

1. `guards` → if refuse, return that message + link; skip LLM
2. `retrieve`
3. Bind **one** `source_url`: highest-ranked chunk whose `scheme_name` matches the question, else top chunk
4. Groq with system prompt: facts only, **only** retrieved context, ≤3 sentences, name the scheme, no advice, no invented numbers
5. Append `Last updated from sources: <ingest_ts>`
6. Attach the bound URL even if the model omits it

**Config:**

- `.env` via `python-dotenv`; never print the key
- Groq model: pick a current small/fast chat model; put name in one constant
- On Groq failure: say generation unavailable; **do not** invent facts (may still show that retrieval ran)

**Done when:**

- [ ] Factual CLI query returns ≤3 sentences + one real corpus URL + last-updated
- [ ] Advice question never hits “you should buy”
- [ ] Missing fact: admits gap; still cites a relevant URL
- [ ] Citation URL is always one of the five sources

**Cursor prompt:**

```
Phase 6 only. Read architecture.md §6.4–6.5, §9–10, PRD.md §8 FR-2–FR-8, implementation.md Phase 6.
Implement Groq generation grounded only on retrieved chunks. Bind exactly one citation from Chroma metadata.
Wire guards → retrieve → generate. Load GROQ_API_KEY from .env.
CLI: ask a question, print answer + citation + last-updated.
On Groq errors, do not guess facts. No UI yet.
Stop at the Phase 6 Done when checklist.
```

---

## Phase 7 — Tiny UI

**Goal:** Class-demo chat. UI **only** calls the query pipeline; it does **not** ingest.

**Create:** `src/app.py` (Streamlit preferred unless the repo already standardized otherwise)

Must show:

- Disclaimer always visible: **Facts-only. No investment advice.**
- Welcome: answers HDFC scheme facts from public Groww pages, with sources
- Three example questions:
  1. What is the expense ratio of HDFC Large Cap Fund Direct Growth?
  2. What is the lock-in for HDFC ELSS Tax Saver?
  3. What is the minimum SIP for HDFC Small Cap Fund Direct Growth?
- Chat input + history; citation as a clickable link; last-updated line
- If Chroma missing: tell user to run `python src/ingest.py`

**Must not:** login, PII fields, file upload, ingest button that scrapes on every refresh (optional **separate** “re-ingest” is OK only if it is explicit and slow/warned).

**Done when:**

- [ ] `streamlit run src/app.py` (or documented command) works after ingest
- [ ] Example chips fill the input or send the question
- [ ] Advice question shows refusal in the UI
- [ ] Restarting Streamlit does **not** re-scrape Groww

**Cursor prompt:**

```
Phase 7 only. Read architecture.md §7, PRD.md §9, implementation.md Phase 7.
Build a tiny Streamlit chat UI in src/app.py: disclaimer, welcome, 3 example questions, citation link, last-updated.
Call existing query pipeline only. Do not ingest on startup.
If Chroma is empty, instruct the user to run ingest.
Stop at the Phase 7 Done when checklist.
```

---

## Phase 8 — Deliverables + README + sample Q&A

**Goal:** Class submission artifacts from PRD §11.

**Create/update:**

1. `README.md` — setup (venv, `pip install -r requirements.txt`, copy `.env.example` → `.env`, ingest, run UI), AMC + five schemes, chunk size/overlap (from `CHUNKING.md`), known limits (PRD §13)
2. `sample_qa.md` — 5–10 real queries with **actual** assistant answers + links (run the pipeline; do not fabricate)
   - Include: expense ratio, ELSS lock-in, min SIP, exit load or riskometer/benchmark, statement/docs if present, one advice **refusal**, one returns **redirect**
3. Confirm `sources.md`, `data/chunks.txt`, disclaimer text in UI
4. `requirements.txt` complete and pinned enough to install
5. `.gitignore` final check

**Done when:**

- [ ] Fresh clone path: install → `.env` → ingest → UI, documented
- [ ] Sample Q&A is from the real system
- [ ] Limits and “facts only” are in README
- [ ] No secrets in git

**Cursor prompt:**

```
Phase 8 only. Read PRD.md §11–13, architecture.md §12, implementation.md Phase 8.
Write README.md (setup, scope, chunking, limits) and sample_qa.md using real pipeline outputs (run queries).
Do not add new features. Confirm gitignore for .env and data/chroma/.
Stop at the Phase 8 Done when checklist.
```

---

## Suggested Cursor session plan

| Session | Phase | Output you should see |
| --- | --- | --- |
| 1 | 0 + 1 | skeleton, `sources.md`, `data/raw/`, `CHUNKING.md` |
| 2 | 2 + 3 | `chunks.txt`, `python src/ingest.py`, `data/chroma/` |
| 3 | 4 + 5 + 6 | retrieve CLI, guards, Groq answers with citations |
| 4 | 7 + 8 | Streamlit demo + README + sample Q&A |

If a phase fails, **stay on that phase**. Do not “just add the UI” to debug ingest.

---

## Dependency add order (avoid installing everything in phase 0)

| Phase | Typical packages |
| --- | --- |
| 1 | `requests`, `beautifulsoup4` (or equivalent) |
| 3 | `sentence-transformers`, `chromadb` |
| 6 | `groq`, `python-dotenv` |
| 7 | `streamlit` |

---

## Definition of done (whole product)

- [ ] Ingest CLI: Load → Chunk → Embed → Store; `chunks.txt` inspectable
- [ ] Query: Question → Embed → Retrieve → guards → Groq → answer
- [ ] Same MiniLM for chunks and questions; Chroma persists across restart
- [ ] Every answer: ≤3 sentences, one corpus URL, last-updated line
- [ ] Advice and PII refused; returns not computed
- [ ] Tiny UI with disclaimer and 3 examples
- [ ] README, sources, sample Q&A ready for class

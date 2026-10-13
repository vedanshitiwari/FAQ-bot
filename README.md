# Groww HDFC Mutual Fund FAQ Chatbot

Facts-only FAQ assistant for five HDFC Mutual Fund Direct-Growth schemes listed on Groww.
Every generated answer includes one citation URL and a `Last updated from sources:` timestamp.

## Scope

- **AMC:** HDFC Mutual Fund
- **Plan type:** Direct-Growth
- **Schemes (closed corpus):**

| Category | Scheme name | Public Groww page |
|---|---|---|
| Large Cap | HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| Flexi Cap | HDFC Flexi Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| ELSS | HDFC ELSS Tax Saver Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| Small Cap | HDFC Small Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| Hybrid | HDFC Balanced Advantage Fund Direct Growth | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

Only these five public URLs are ingested. No blogs, app backends, additional AMCs, or other funds are used.

## Setup (Windows Command Prompt)

1. Open Command Prompt and move to the project folder:

   ```cmd
   cd /d "E:\Games\RAG Product\Groww"
   ```

2. Create and activate the virtual environment (Python 3.13 tested):

   ```cmd
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```

3. Install dependencies:

   ```cmd
   pip install -r requirements.txt
   ```

4. Create your environment file and add your Groq API key (do not commit `.env`):

   ```cmd
   copy .env.example .env
   notepad .env
   ```

   Set at least:

   ```text
   GROQ_API_KEY=your_key_here
   GROQ_MODEL=qwen/qwen3.8-27b
   ```

5. Fetch and extract the five public scheme pages into `data/raw/`:

   ```cmd
   python src\load_pages.py
   ```

6. Run the explicit ingestion CLI. This chunks, embeds, and stores vectors in Chroma:

   ```cmd
   python src\ingest.py
   ```

   Expected output includes `Wrote 138 chunks` and `Stored 138 records in 'hdfc_mf_faq'`. Re-running ingest replaces the collection instead of duplicating records.

7. Start the Streamlit UI:

   ```cmd
   .venv\Scripts\streamlit.exe run src\app.py
   ```

   Then open the local URL shown by Streamlit, typically `http://localhost:8501`.

## Command-line queries

Run a single question without the UI:

```cmd
python src\query.py "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"
```

A small Streamlit-free retrieval smoke test is also available:

```cmd
python src\retrieve.py "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"
```

## Pipeline and storage

- Ingestion stage: `Load -> Chunk -> Embed -> Store` (CLI only, never on app startup)
- Query stage: `Question -> Guards -> Retrieve -> Groq -> Answer`
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions), used for both chunks and queries
- Vector database: ChromaDB persisted to `data/chroma/`
- Collection name: `hdfc_mf_faq`
- Groq API key is loaded from `.env` (`GROQ_API_KEY`, `GROQ_MODEL`)
- Citations are bound from Chroma metadata, not invented by the LLM

## Chunking

From `CHUNKING.md` (after inspecting the five extracted pages):

- Strategy: heading-first split, then character windows
- Max chunk size: 800 characters
- Overlap: 150 characters
- Chunks write a readable dump to `data/chunks.txt`
- Metadata per chunk: `source_url`, `scheme_name`, `category`, `section_title` (optional), and `ingest_ts`
- Embedding uses chunk body text only, not URLs
- Every chunk is stored in Chroma with the same metadata

## Deliverable files

| File | Purpose |
|---|---|
| `sources.md` | Closed list of the five Groww URLs |
| `data/chunks.txt` | Inspectable tagged chunk dump |
| `data/chroma/` | Persisted vector store (gitignored) |
| `disclaimer.md` | Exact UI disclaimer snippet |
| `sample_qa.md` | Real sample questions and assistant answers |
| `src/app.py` | Tiny Streamlit chat UI |

## Known limits

- Facts can become stale compared with live Groww pages; re-ingest to refresh.
- Groww page layout and JavaScript may make extraction incomplete. Missing fields are admitted, not guessed.
- Only the five listed schemes are covered. Other AMCs, schemes, categories, and plans are out of scope.
- Local MiniLM embedding quality is adequate for a demo, not production search.
- Groq availability, rate limits, or key issues can fail the generation step even when retrieval succeeded.
- Data comes from Groww scheme pages, which are a third-party platform and are not verified here against HDFC AMC's own factsheet. Verify figures against HDFC AMC's official factsheet before relying on them.
- ELSS lock-in and capital-gains statement download steps are **not** present on the five stored Groww scheme pages, so the assistant will say that the fact is not in the corpus rather than inventing a process or lock-in period.
- Do not compute or compare returns; the system refuses or redirects those questions.

## Safety and facts-only behavior

- The bot refuses buy/sell/switch and personalized investment advice.
- It does not compute returns, CAGR, or performance comparisons.
- It refuses PAN, Aadhaar, account numbers, OTP, email, phone, and other personal/account identifiers.
- Answers are limited to retrieved facts from the closed five-scheme corpus.
- See `disclaimer.md` for the always-visible UI disclaimer.

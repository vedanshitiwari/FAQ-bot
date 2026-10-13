# Chunking proposal (from Phase 1 inspection)

**Inspected:** `data/raw/*.txt` after `python src/load_pages.py`  
**Ingest timestamp in files:** `2026-10-13T19:26:00Z`  
**Do not implement the splitter in this phase.** Phase 2 must follow these numbers.

---

## What the pages look like

Groww scheme pages are **one long HTML document**, not clean FAQ sections. After stripping mega-menu and footer, each file is a **repeatable skeleton**:

1. **Snapshot** (tight, high value) — title, NAV, `Min. for SIP` + rupee amount on the next line, AUM, `Expense ratio` + percent on the next line, rating
2. **Return calculator / historic returns** (low value for this FAQ; PRD forbids computing returns)
3. **Holdings table** — name / sector / % (long; BAF is ~35k chars mostly here)
4. **Understand terms** — generic definitions of expense ratio / tax / exit load (no scheme numbers)
5. **Exit Load** — dated history + current `Exit load, stamp duty and tax`
6. **Compare similar funds** and **Fund management / Also manages these schemes** (noise)
7. **About** — one packed paragraph: risk rating, min SIP, min lumpsum, exit load; then **Investment Objective** and **Fund benchmark**

Label and value are often on **adjacent lines** (`Expense ratio` then `1.04%`). A naive splitter that cuts at 200–300 characters can separate the label from the number.

---

## Strategy

**Heading-first, then character windows.**

1. Split each raw file on these anchors (keep the heading with the following body):

   - `Min. for SIP` / snapshot block from the title through `Rating`
   - `Holdings (`
   - `Understand terms`
   - `Exit Load` / `Exit load, stamp duty and tax`
   - `Fund management`
   - `About`
   - `Investment Objective`
   - `Fund benchmark`

2. If a section is longer than **800 characters** (holdings), split it with a sliding window of **800 characters, 150 overlap**.

3. Do **not** split inside a snapshot or About paragraph if it is under 800 characters — keep those as **one chunk** so SIP, expense ratio, risk, and exit load stay together.

4. Phase 2 may **drop or mark as `section_title=noise`**: return calculator tables, “Compare similar funds”, “Also manages these schemes”, leftover breadcrumb/address lines after RTA. Holdings can be stored but are not needed for the class FAQ.

**Why this fits:** the questions in the PRD (expense ratio, exit load, min SIP, lock-in, riskometer, benchmark) live in the **snapshot** and **About** blocks, not uniformly through the page. Heading-aware chunks plus overlap on long tables avoid mixing schemes (metadata) and avoid cutting `Expense ratio` away from `1.04%`.

---

## Parameters

| Parameter | Value | Rationale |
| --- | --- | --- |
| Max chunk size | **800 characters** | Snapshot + About blocks are typically 400–800 chars; 800 keeps a fact paragraph intact |
| Overlap | **150 characters** | About 2–4 lines; enough to keep a heading with the following value if a window lands on a boundary |
| Split unit | Character windows on already heading-split sections | Pages are not tokenized prose; they are label/value lines |
| Embed | Chunk **body text only** (not the URL) | Architecture §5.3 |

---

## Metadata (every chunk)

| Field | Required | Example |
| --- | --- | --- |
| `source_url` | yes | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |
| `scheme_name` | yes | `HDFC Large Cap Fund Direct Growth` |
| `category` | yes | `large-cap` |
| `section_title` | optional | `snapshot`, `exit_load`, `about`, `benchmark`, `holdings`, `noise` |
| `ingest_ts` | yes | `2026-10-13T19:26:00Z` (from load header) |

Write all chunks to `data/chunks.txt` in Phase 2 (scheme, category, URL, section, body, ingest_ts).

---

## Fact inventory (this extract)

| Scheme | Chars | Expense ratio | Exit load | Min SIP | Benchmark | Riskometer |
| --- | --- | --- | --- | --- | --- | --- |
| Large Cap | 8942 | Yes — **1.04%** (snapshot) | Yes — 1% if redeemed within 1 year | Yes — **₹100** (`Min. for SIP` + About) | Yes — **NIFTY 100 Total Return Index** | Partial — **Very High risk** in About; word “riskometer” absent |
| Flexi Cap | 10817 | Yes — **0.75%** | Yes — 1% if redeemed within 1 year | Yes — **₹100** | Yes — **NIFTY 500 Total Return Index** | Partial — **Very High risk** |
| ELSS | 9099 | Yes — **1.20%** | Yes — **Nil** (current); history shows `--` | Yes — **₹500** | Yes — **NIFTY 500 Total Return Index** | Partial — **Very High risk** |
| Small Cap | 11123 | Yes — **0.79%** | Yes — 1% if redeemed within 1 year | Yes — **₹100** | Yes — **BSE 250 SmallCap Total Return Index** | Partial — **Very High risk** |
| Balanced Advantage | 34827 | Yes — **0.77%** | Yes — 1% on units in excess of 15% within 1 year | Yes — **₹100** | Yes — **NIFTY 50 Hybrid Composite Debt 50:50 Index** | Partial — **Very High risk** |

No raw file is empty.

### Gaps (do not invent in later phases)

| Fact | Status | Why | Suggested fix |
| --- | --- | --- | --- |
| Word **riskometer** | Missing on all five | Groww shows a risk **rating** sentence, not the SEBI riskometer graphic/label in the HTML text | Answer from “rated Very High risk”. Optional later: add official AMC SID/KIM **only if** listed in `sources.md` |
| **ELSS 3-year lock-in** | Missing | No “lock-in” / “3 years lock” in the ELSS extract. “3 years” only appears as a **return period** | Do not treat return-period “3 years” as lock-in. Optional: add HDFC ELSS SID/KIM public PDF/page to the source list in a later ingest. Until then, the bot must say the lock-in is **not on this Groww page** |
| **How to download statements / capital-gains** | Missing | No process text; only generic tax/LTCG definitions | Out of this 5-URL corpus. Add a public Groww/CAMS/KFin statement guide URL later, or refuse with a link to the scheme page |
| Generic **Understand terms** | Present but misleading | Defines “expense ratio” without the scheme’s % | Prefer snapshot/About chunks for numbers; keep definitions in a separate `section_title` |
| **Fund-house AUM** in About | Present | About cites AMC AUM (~₹9.34 lakh Cr), while snapshot has **scheme** AUM | Chunk About with `section_title=about`; retrieval prompt must not confuse the two |
| BAF size | Large | Long holdings list, not a failed fetch | Coarse-chunk or skip holdings in Phase 2 |

---

## Loader notes (Phase 1)

- Entry: `python src/load_pages.py`
- Failures print the URL to stderr; pages are not invented
- HTML cached as `data/raw/<slug>.html`; text as `data/raw/<slug>.txt`
- Extract method used: `visible_html` (server-rendered enough; `__NEXT_DATA__` fallback exists but was not needed)
- Chrome trim: drop mega-menu between `<title>` and `NAV:`; drop footer from “Download the App”

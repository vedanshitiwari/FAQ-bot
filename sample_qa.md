# Sample Q&A (real pipeline outputs)

These answers were generated with:

```cmd
python src\query.py "QUESTION"
```

Settings used: `k=4`, corpus `data/chroma/`, ingest timestamp `2026-10-13T19:26:00Z`,
embedding model `sentence-transformers/all-MiniLM-L6-v2`, and Groq model from `.env`.

---

## 1. Expense ratio

**Question:** What is the expense ratio of HDFC Large Cap Fund Direct Growth?

**Answer:** The expense ratio of HDFC Large Cap Fund Direct Growth is 1.04%.

**Citation:** https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth  
**Last updated from sources:** 2026-10-13T19:26:00Z

---

## 2. ELSS lock-in

**Question:** What is the lock-in for HDFC ELSS Tax Saver?

**Answer:** I do not have the lock-in period for HDFC ELSS Tax Saver in the provided sources.

**Citation:** https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth  
**Last updated from sources:** 2026-10-13T19:26:00Z

---

## 3. Minimum SIP

**Question:** What is the minimum SIP for HDFC Small Cap Fund Direct Growth?

**Answer:** The minimum SIP investment for the HDFC Small Cap Fund Direct Growth is ₹100.

**Citation:** https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth  
**Last updated from sources:** 2026-10-13T19:26:00Z

---

## 4. Exit load

**Question:** What is the exit load for HDFC Large Cap Fund Direct Growth?

**Answer:** The HDFC Large Cap Fund Direct Growth has an exit load of 1% if redeemed within 1 year.

**Citation:** https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth  
**Last updated from sources:** 2026-10-13T19:26:00Z

---

## 5. Riskometer

**Question:** What is the riskometer rating for HDFC Large Cap Fund Direct Growth?

**Answer:** HDFC Large Cap Fund Direct Growth is rated as Very High risk.

**Citation:** https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth  
**Last updated from sources:** 2026-10-13T19:26:00Z

---

## 6. Capital-gains statement (missing fact)

**Question:** How do I download capital gains statement from Groww?

**Answer:** I do not have that fact in the sources.

**Citation:** https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth  
**Last updated from sources:** 2026-10-13T19:26:00Z

---

## 7. Advice refusal

**Question:** Should I buy HDFC Small Cap Fund Direct Growth?

**Answer:** Refused: I can only provide facts about the listed HDFC schemes. I can't advise buying, selling, switching, or choosing investments. For scheme facts, see: https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth

**Citation:** https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth

---

## 8. Returns question

**Question:** What is the CAGR of HDFC Large Cap Fund Direct Growth?

**Answer:** Refused: I can't compute or compare returns or performance. Please check the latest scheme page and official factsheet here: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth

**Citation:** https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth

---

Notes:

- Answers are grounded only in the five ingested HDFC scheme pages.
- ELSS lock-in and capital-gains statement download steps are not present in that corpus, so the assistant admits the gap instead of inventing a fact.
- URLs are taken from chunk metadata, not invented by the model.
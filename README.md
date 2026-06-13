# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section _after_ you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

U.S. federal and Texas state tax forms, covering both individual and business filings
(income, payroll, partnership, corporate, mortgage-interest, and state sales/use tax).

This knowledge is technically public, but it isn't _answerable_: the information lives inside
dense, layout-heavy PDF forms where the meaning of a value depends on its position relative to a
numbered box or label. A filer who wants a plain-language answer to "what is Form 8829 for?" or
"what does an employer report on Form 941?" has to locate the right form and parse its structure
themselves. This system makes that latent knowledge searchable and answerable in plain English,
grounded in the actual forms.

---

## Document Sources

| #   | Source                                                                  | Type                     | URL or file path         |
| --- | ----------------------------------------------------------------------- | ------------------------ | ------------------------ |
| 1   | IRS Form 1040 — U.S. Individual Income Tax Return                       | PDF (federal form)       | `documents/f1040.pdf`    |
| 2   | IRS Schedule C (Form 1040) — Profit or Loss From Business               | PDF (federal form)       | `documents/f1040sc.pdf`  |
| 3   | IRS Form 1065 — U.S. Return of Partnership Income                       | PDF (federal form)       | `documents/f1065.pdf`    |
| 4   | IRS Form 1120 — U.S. Corporation Income Tax Return                      | PDF (federal form)       | `documents/f1120.pdf`    |
| 5   | IRS Form 941 — Employer's Quarterly Federal Tax Return                  | PDF (federal form)       | `documents/f941.pdf`     |
| 6   | IRS Form 1098 — Mortgage Interest Statement                             | PDF (federal form)       | `documents/f1098.pdf`    |
| 7   | IRS Form 1099-MISC — Miscellaneous Information                          | PDF (federal form)       | `documents/f1099msc.pdf` |
| 8   | IRS Form 8829 — Expenses for Business Use of Your Home                  | PDF (federal form)       | `documents/f8829.pdf`    |
| 9   | TX Comptroller 01-114 — Texas Sales and Use Tax Return                  | PDF (state form)         | `documents/01-114.pdf`   |
| 10  | TX Comptroller 01-922 — Instructions for the Texas Sales/Use Tax Return | PDF (state instructions) | `documents/01-922.pdf`   |

---

## Chunking Strategy

**Chunk size:** ~600 characters (≈150 tokens), split at the nearest preceding word boundary so chunks don't end mid-word.

**Overlap:** ~100 characters carried over between adjacent chunks.

**Why these choices fit your documents:** Once `pdfplumber` flattens a tax form to text, the content is dense, line-by-line items ("31 Total tax (Schedule J, line 12)") rather than flowing prose. A ~600-character window keeps a cluster of related lines together so a line's label and its description stay in the same chunk, while staying small enough that a specific query isn't diluted by unrelated lines. The 100-character overlap hedges against a label being cut off from its value at a chunk boundary — directly mitigating the layout risk identified in `planning.md`. Preprocessing before chunking: extract text with `pdfplumber` (no OCR), drop known boilerplate lines (OMB numbers, `www.irs.gov` URLs, Paperwork Reduction Act notices, bare page numbers, revision stamps), collapse the dotted leader lines (`. . . .`) that pad form fields, repair the most common mis-decoded glyph (`�s` → `'s`), and normalize whitespace. See `ingest.py`.

**Final chunk count:** 255 chunks across 10 documents (within the 50–2,000 target range).

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`, run locally (no API key, no rate limits). Embeddings are normalized and stored in ChromaDB with cosine distance; retrieval returns the top-k (k=5). See `embed.py` and `retrieve.py`.

**Production tradeoff reflection:** MiniLM is a general-purpose model with a short ~256-token context window, so longer instruction passages get truncated, and it wasn't trained on tax/legal vocabulary, so terms like "Schedule SE" or "qualified joint venture" embed weakly — a real factor here, since the corpus is largely numbered line-item labels with little surrounding prose (see the Q1/Q5 retrieval weaknesses in the Evaluation Report). If cost weren't a constraint I'd weigh: (a) a longer-context model (e.g. OpenAI `text-embedding-3-large` or a 512+ token model) so dense form text isn't cut off; (b) a domain-tuned legal/financial embedding model for better accuracy on tax jargon; (c) the privacy/latency tradeoff of API-hosted vs. local, tax docs are sensitive and can contain very high PII, so privacy is a requirement.

---

## Grounded Generation

**System prompt grounding instruction:** The model (`llama-3.3-70b-versatile` via Groq, temperature 0) is given a system prompt that constrains it to the retrieved context only. The actual instruction (see `query.py`):

> "You are a tax-document assistant. Answer the user's question using ONLY the information in the CONTEXT below... 1. Use only facts present in the CONTEXT. Do not use outside knowledge. 2. If the CONTEXT does not contain enough information to answer, reply exactly: \"I don't have enough information on that.\" 3. Do not guess, infer beyond the text, or fill gaps with general tax knowledge. 4. Be concise and cite the form name(s) you used in your answer."

Two structural choices reinforce the prompt: (1) retrieved chunks are formatted with an explicit `[Source: filename]` header before each block, and (2) chunks with a cosine distance above `MAX_DISTANCE = 0.80` are filtered out before generation. The threshold was set from observed data — in-domain queries score ≤ 0.57 while a clearly off-domain query ("best pizza place near campus") scores ≥ 0.85 — so an off-domain question ends up with **no** surviving context and the system returns the refusal **without even calling the LLM** (verified: that query returns an empty source list).

These are two distinct refusal paths, and it's worth being precise about which fires when: the off-domain short-circuit (path 2) is what catches questions outside the tax domain. Q5 ("Line 31 of Schedule C") is not caught by it — its retrieved chunks score ~0.53 and pass the filter, so the LLM is called and refuses via the **system-prompt rule** (path 1) because the retrieved chunks were the wrong forms' "line 31"s. Both paths produce the same refusal string, but through different mechanisms.

**How source attribution is surfaced in the response:** Attribution is guaranteed programmatically, not left to the LLM. `ask()` returns a `sources` list built from the metadata of the chunks actually fed to the model (de-duplicated, in retrieval order), and the Gradio UI displays it in a separate "Retrieved from" panel. The system prompt also asks the model to cite form names inline, but the displayed source list does not depend on the model remembering to do so.

---

## Evaluation Report

| #   | Question                                  | Expected answer                                                                    | System response (summarized)                                                  | Retrieval quality | Response accuracy |
| --- | ----------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------- | ----------------- |
| 1   | What is Schedule C (Form 1040) used for?  | Reporting profit or loss from a sole-proprietorship business                       | "Profit or Loss From Business for a Sole Proprietorship," cited `f1040sc.pdf` | Relevant          | Accurate          |
| 2   | What does an employer report on Form 941? | Quarterly federal payroll taxes — withheld income tax + Social Security + Medicare | "their quarterly federal tax return," cited `f941.pdf`                        | Relevant          | Accurate          |
| 3   | What expenses does Form 8829 calculate?   | Expenses for business use of the home (home-office deduction)                      | "expenses for business use of your home," cited `f8829.pdf`                   | Relevant          | Accurate          |
| 4   | What is the Texas form 01-114?            | The Texas Sales and Use Tax Return                                                 | "the Texas Sales and Use Tax Return," cited `01-922.pdf`                      | Relevant          | Accurate          |
| 5   | What value goes on Line 31 of Schedule C? | Net profit or (loss)                                                               | "I don't have enough information on that."                                    | Poor              | Poor              |

**Retrieval quality:** Relevant
**Response accuracy:** Accurate

**Overall:** Considering tax forms being very structure depandant, this system performed very well. It failed at the expected failure case, primarily due to the structure limitation making the required tokens not fit in the same chunk, so it missed it. I think we can increase accuracy slightly by increasing the chunk size and overlap, but what we have is good. Though, we could most heavily increase accuracy with a better embedder.

---

## Failure Case Analysis

**Question that failed:** Q5 — "What value goes on Line 31 of Schedule C?" (Expected: net profit or loss.)

**What the system returned:** "I don't have enough information on that." Retrieval returned the wrong "line 31"s — `f8829#5` (0.529) and `f1120#1` (0.531) — instead of Schedule C's line 31.

**Root cause (tied to a specific pipeline stage):**

the correct content IS in the corpus — chunk
f1040sc-6 literally contains "31 Net profit or (loss). Subtract line 30 from line 29." So this
is a RETRIEVAL (embedding) failure, NOT an ingestion failure. The chunk exists but wasn't
retrieved: a bare line number like "31" carries almost no semantic signal, so the embedding
model couldn't distinguish Schedule C's line 31 from Form 8829's / 1120's line 31, and pulled
the wrong forms' "line 31" chunks instead.

**What you would change to fix it:**

A hybrid keyword/semantic option would likely fix this. "Schedule c" and "line 31" are both keywords that would work.

---

## Spec Reflection

Planning.md did nothing to shape this. The only reason a spec like that is useful is when we have a large project and claude needs to consistently reference back to it to understand the goal of the task, but in those cases, it just makes it's own. I do think it's more useful when you already have all your requirements, but even then, I would avoid using that. A running summary is more useful, because a spec.md can get outdated very quickly.

**One way the spec helped you during implementation:**

I guess it had all the info so the AI could just read from it... otherwise uselss for a small project.

**One way your implementation diverged from the spec, and why:**

I had to add the glyph fixes after the original spec was made.

## AI Usage

I gave Claude the spec.md and asked it to generate a plan on how to complete the specific milestone, for each one, it generated it and completed the tasks.

**Instance 1**

- _What I gave the AI:_ My filled-in planning.md (the Documents and Chunking Strategy sections) plus the note that these are layout-heavy tax PDFs, and asked it to build the ingestion + chunking script.
- _What it produced:_ `ingest.py` — pdfplumber text extraction, boilerplate removal, and a ~600-char / 100-overlap chunker that writes `chunks.json` (255 chunks).
- _What I changed or overrode:_ After looking at the first output I had it add dotted-leader stripping and a `�s` → `'s` glyph fix that the spec hadn't anticipated, and I checked the chunk count + that my evaluation answer phrases actually survived chunking before embedding.

**Instance 2**

- _What I gave the AI:_ My Retrieval Approach section and the grounding requirement (answer only from retrieved chunks, cite the source).
- _What it produced:_ `embed.py` / `retrieve.py` (ChromaDB + all-MiniLM-L6-v2, cosine, top-k 5) and `query.py` with a grounding system prompt, plus a Gradio UI.
- _What I changed or overrode:_ I decided to keep the Q1 Schedule C retrieval weakness as a documented finding instead of re-tuning, the distance cutoff got tightened to 0.80 so off-domain questions actually refuse, and I tested the whole thing with my own Groq key and committed each milestone myself.

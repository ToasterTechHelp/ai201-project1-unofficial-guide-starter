# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

This is the tax document domain. Specifically it contains federal tax forms in the U.S as well as Texas specific state tax forms. It contains both business and individual tax forms.

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| #   | Source                     | Description                                                | URL or location          |
| --- | -------------------------- | ---------------------------------------------------------- | ------------------------ |
| 1   | IRS Form 1040              | U.S. Individual Income Tax Return                          | `documents/f1040.pdf`    |
| 2   | IRS Schedule C (Form 1040) | Profit or Loss from Business (sole proprietorship)         | `documents/f1040sc.pdf`  |
| 3   | IRS Form 1065              | U.S. Return of Partnership Income                          | `documents/f1065.pdf`    |
| 4   | IRS Form 1120              | U.S. Corporation Income Tax Return                         | `documents/f1120.pdf`    |
| 5   | IRS Form 941               | Employer's Quarterly Federal Tax Return (payroll)          | `documents/f941.pdf`     |
| 6   | IRS Form 1098              | Mortgage Interest Statement                                | `documents/f1098.pdf`    |
| 7   | IRS Form 1099-MISC         | Miscellaneous Information                                  | `documents/f1099msc.pdf` |
| 8   | IRS Form 8829              | Expenses for Business Use of Your Home (home office)       | `documents/f8829.pdf`    |
| 9   | TX Comptroller 01-114      | Texas Sales and Use Tax Return                             | `documents/01-114.pdf`   |
| 10  | TX Comptroller 01-922      | Instructions for Completing the Texas Sales/Use Tax Return | `documents/01-922.pdf`   |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** ~600 characters (≈150 tokens)

**Overlap:** ~100 characters

**Reasoning:** Once `pdfplumber` flattens these forms to text, the content is dense line-items ("Line 12 — Total income…") rather than flowing prose. Mid-size chunks keep a cluster of related lines together so a single line's label and its instruction text stay in the same chunk, while staying small enough that a specific query ("what is Form 8829 for?") isn't diluted by unrelated lines. The 100-char overlap hedges against a line label getting cut off from its value/description at a chunk boundary — exactly the layout risk flagged in Anticipated Challenges.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers` (local, free, no API key)

**Top-k:** 5

**Production tradeoff reflection:** MiniLM is a general-purpose model with a short ~256-token context window, so long instruction passages get truncated, and it wasn't trained on tax/legal vocabulary, so terms like "Schedule SE" or "qualified joint venture" may embed weakly. If cost weren't a constraint I'd weigh: (a) a longer-context model (e.g. OpenAI `text-embedding-3-large` or a 512+ token model) so dense form text isn't cut off; (b) a domain-tuned legal/financial embedding model for better accuracy on tax jargon; (c) the latency/privacy tradeoff of API-hosted vs. local — tax documents are sensitive with heavy PII, so local makes a good arg for privacy.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| #   | Question                                                                  | Expected answer                                                                         |
| --- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 1   | What is Schedule C (Form 1040) used for?                                  | Reporting profit or loss from a sole proprietorship business                            |
| 2   | What does an employer report on Form 941?                                 | Quarterly federal payroll taxes — withheld income tax plus Social Security and Medicare |
| 3   | What expenses does Form 8829 calculate?                                   | Expenses for business use of your home (the home-office deduction)                      |
| 4   | What is the Texas form 01-114?                                            | The Texas Sales and Use Tax Return                                                      |
| 5   | What value goes on a specific numbered line (e.g. Line 31 of Schedule C)? | Net profit or loss — **designed as a likely failure case** (layout-dependent lookup)    |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. One big potential issue is that the tax form's depend a lot on the non-text structure. So the placement of the words next to a specific box labelled with a number.

2. This number could be below, or above, to the side, etc of the actual label making it very difficult to understand by an LLM if read left to right.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```
┌─────────────────┐   ┌──────────────┐   ┌──────────────────────┐   ┌─────────────┐   ┌──────────────────────┐
│ Document        │   │ Chunking     │   │ Embedding + Vector   │   │ Retrieval   │   │ Generation           │
│ Ingestion       │──▶│              │──▶│ Store                │──▶│             │──▶│                      │
│                 │   │ ~600 char /  │   │                      │   │ top-k = 5   │   │ grounded answer +    │
│ pdfplumber      │   │ 100 overlap  │   │ all-MiniLM-L6-v2     │   │ semantic    │   │ source attribution   │
│ (PDF → text,    │   │ (custom      │   │ → ChromaDB           │   │ similarity  │   │ Groq                 │
│  clean)         │   │  splitter)   │   │ (+ source metadata)  │   │             │   │ llama-3.3-70b        │
└─────────────────┘   └──────────────┘   └──────────────────────┘   └─────────────┘   └──────────────────────┘
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:** Give Claude the Documents and Chunking Strategy sections plus the note that these are layout-heavy PDFs. Ask it to write a script using `pdfplumber` to extract text from each file in `documents/`, strip empty pages and OMB/header boilerplate, and split into ~600-char chunks with 100-char overlap, tagging each chunk with its source filename. Verify by printing 5 chunks and checking they're readable and self-contained — not fragments or empty strings.

**Milestone 4 — Embedding and retrieval:** Give Claude the Retrieval Approach section and the diagram. Ask it to embed chunks with `all-MiniLM-L6-v2`, store them in ChromaDB with source metadata, and write a `retrieve(query, k=5)` function returning chunks + distance scores. Verify by running questions 1–3 from the Evaluation Plan and confirming top results are on-topic with distances below ~0.5.

**Milestone 5 — Generation and interface:** Give Claude the grounding requirement (answer _only_ from retrieved chunks; say "I don't have enough information" otherwise) and the desired output (answer + source list). Ask it to wire retrieval → Groq `llama-3.3-70b-versatile` → a Gradio UI. Verify the system prompt _enforces_ grounding and that sources are appended programmatically, not left to the LLM.

"""Milestone 5 (part 1) — Grounded answer generation.

Wires retrieval to Groq's llama-3.3-70b-versatile. The model is instructed to
answer ONLY from the retrieved chunks and to refuse when they don't cover the
question. Source attribution is guaranteed programmatically: the returned
`sources` list is built from the chunks that were actually fed to the model,
not from whatever the LLM chooses to mention.

Run:  python query.py        (runs the grounding tests)
"""

import os

from dotenv import load_dotenv
from groq import Groq

from retrieve import retrieve, TOP_K

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
# Cosine-distance cutoff: chunks farther than this are treated as irrelevant
# and dropped, so an off-domain question ends up with no context -> refusal.
# Set to 0.80 from observed data: in-domain queries score <= 0.57, while a
# clearly off-domain query ("best pizza place") scores >= 0.85 — 0.80 sits in
# that gap, so off-domain questions get an empty context and short-circuit.
MAX_DISTANCE = 0.80

SYSTEM_PROMPT = (
    "You are a tax-document assistant. Answer the user's question using ONLY the "
    "information in the CONTEXT below, which is drawn from official IRS and Texas "
    "tax forms. Follow these rules strictly:\n"
    "1. Use only facts present in the CONTEXT. Do not use outside knowledge.\n"
    "2. If the CONTEXT does not contain enough information to answer, reply "
    "exactly: \"I don't have enough information on that.\"\n"
    "3. Do not guess, infer beyond the text, or fill gaps with general tax knowledge.\n"
    "4. Be concise and cite the form name(s) you used in your answer."
)

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _format_context(chunks: list[dict]) -> str:
    blocks = []
    for c in chunks:
        blocks.append(f"[Source: {c['source']}]\n{c['text']}")
    return "\n\n---\n\n".join(blocks)


def ask(question: str, k: int = TOP_K) -> dict:
    """Retrieve, ground, and generate. Returns answer + the sources actually used."""
    retrieved = retrieve(question, k=k)
    relevant = [c for c in retrieved if c["distance"] <= MAX_DISTANCE]

    # No relevant context -> don't even call the model; refuse directly.
    if not relevant:
        return {
            "answer": "I don't have enough information on that.",
            "sources": [],
            "chunks": [],
        }

    context = _format_context(relevant)
    completion = _client.chat.completions.create(
        model=MODEL,
        temperature=0,  # deterministic, reduces drift from the context
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
        ],
    )
    answer = completion.choices[0].message.content.strip()

    # Programmatic source attribution: unique source files, in retrieval order.
    sources = list(dict.fromkeys(c["source"] for c in relevant))
    return {"answer": answer, "sources": sources, "chunks": relevant}


# Grounding tests for the M5 checkpoint: 2 in-domain + 1 deliberately off-domain.
TEST_QUESTIONS = [
    "What is Schedule C (Form 1040) used for?",
    "What does an employer report on Form 941?",
    "What is the best pizza place near campus?",  # off-domain -> should refuse
]


def _demo() -> None:
    for q in TEST_QUESTIONS:
        print(f"\n{'=' * 80}\nQ: {q}\n{'-' * 80}")
        r = ask(q)
        print(f"A: {r['answer']}")
        print(f"Sources: {r['sources'] or '(none)'}")


if __name__ == "__main__":
    _demo()

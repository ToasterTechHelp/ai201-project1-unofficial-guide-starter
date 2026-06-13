"""Milestone 5 (part 2) — Gradio query interface for the Unofficial Guide.

Run:  python app.py    then open http://localhost:7860
"""

import gradio as gr

from query import ask


def handle_query(question: str):
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"]) or "(no sources — outside the documents)"
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Guide — Tax Forms") as demo:
    gr.Markdown(
        "# The Unofficial Guide — U.S. & Texas Tax Forms\n"
        "Ask a plain-language question. Answers are grounded only in the "
        "ingested IRS and Texas Comptroller forms, with sources cited."
    )
    inp = gr.Textbox(label="Your question", placeholder="e.g. What does Form 8829 calculate?")
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

    gr.Examples(
        examples=[
            "What is Schedule C (Form 1040) used for?",
            "What does an employer report on Form 941?",
            "What expenses does Form 8829 calculate?",
            "What is the Texas form 01-114?",
        ],
        inputs=inp,
    )


if __name__ == "__main__":
    demo.launch()

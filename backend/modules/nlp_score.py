"""Model 2 - NLP Response Scorer.  Input: transcript text -> content quality."""

from .base import ModuleResult, seeded_random

MODULE_INFO = {
    "id": "nlp_score",
    "name": "NLP Response Scorer",
    "role": "scorer",
    "inputs": ["transcript"],
    "status": "stub",
    "measures": "relevance to question, STAR structure, answer depth",
    "planned_stack": "sentence-transformers for relevance + LLM rubric for STAR",
}

STAR_HINTS = {
    "situation": ["when i", "at my", "during", "we had", "the project"],
    "task": ["i had to", "my job", "responsible", "goal was", "needed to"],
    "action": ["i built", "i implemented", "i decided", "i led", "so i"],
    "result": ["as a result", "reduced", "improved", "increased", "we shipped"],
}


def analyze(session: dict) -> ModuleResult:
    text = (session.get("transcript") or "").lower()
    rng = seeded_random(session["session_id"], "nlp_score")

    # STAR detection is genuinely real even in the stub - it is keyword matching
    star_found = {k: any(h in text for h in hints) for k, hints in STAR_HINTS.items()}
    star_hits = sum(star_found.values())
    words = len(text.split())

    # TODO(real): cosine similarity between question and answer embeddings,
    # plus an LLM-graded rubric for depth and specificity.
    relevance = rng.randint(55, 95) if words else 0

    score = 0.0
    score += star_hits * 12.5
    score += relevance * 0.4
    score += min(words / 120, 1.0) * 10
    score = max(0.0, min(100.0, score))

    notes = []
    missing = [k for k, v in star_found.items() if not v]
    if missing:
        notes.append("Missing the " + ", ".join(missing).upper() + " part of STAR.")
    else:
        notes.append("Full STAR structure detected - well organised answer.")
    if words < 60:
        notes.append("Only " + str(words) + " words - aim for 90-150 on this question.")

    return ModuleResult(
        module_id="nlp_score", name=MODULE_INFO["name"], score=score,
        status=MODULE_INFO["status"],
        metrics={"word_count": words, "relevance": relevance,
                 "star_parts_found": star_hits, "star_breakdown": star_found},
        notes=notes,
    )

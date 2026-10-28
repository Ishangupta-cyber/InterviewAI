"""Model 2 - NLP Response Scorer.  Input: question + transcript text -> content quality.

Three signals, all rule-based and explainable:
  STAR structure  - does the answer contain Situation / Task / Action / Result language
  relevance       - how many of the question's key terms the answer actually addresses
  depth           - answer length
Embedding-based relevance (sentence-transformers) is the planned upgrade.
"""

import re

from .base import ModuleResult

MODULE_INFO = {
    "id": "nlp_score",
    "name": "NLP Response Scorer",
    "role": "scorer",
    "inputs": ["question", "transcript"],
    "status": "live",
    "measures": "STAR structure, keyword relevance to the question, answer depth",
    "planned_stack": "sentence-transformers for relevance + LLM rubric for STAR",
}

STAR_HINTS = {
    "situation": ["when i", "at my", "during", "we had", "the project"],
    "task": ["i had to", "my job", "responsible", "goal was", "needed to"],
    "action": ["i built", "i implemented", "i decided", "i led", "so i"],
    "result": ["as a result", "reduced", "improved", "increased", "we shipped"],
}

STOPWORDS = set("""
a about above after again all also am an and any are as at be because been before being below between both but by
can could did do does doing down during each few for from further had has have having he her here hers him his how
i if in into is it its just me more most my no nor not of off on once only or other our out over own same she should
so some such than that the their them then there these they this those through to too under until up very was we were
what when where which while who whom why will with would you your tell describe explain walk time about approach
""".split())


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _terms(text: str) -> set:
    return {_stem(w) for w in re.findall(r"[a-z][a-z+#.]*", text.lower()) if len(w) > 3 and w not in STOPWORDS}


def relevance_score(question: str, answer: str) -> tuple:
    """Share of the question's key terms that the answer covers; covering half of them counts as full marks."""
    q_terms = _terms(question)
    if not q_terms:
        return 60, 0.0   # nothing to compare against: neutral
    coverage = len(q_terms & _terms(answer)) / len(q_terms)
    return round(min(1.0, coverage / 0.5) * 100), coverage


def analyze(session: dict) -> ModuleResult:
    text = (session.get("transcript") or "").lower()
    words = len(text.split())

    star_found = {k: any(h in text for h in hints) for k, hints in STAR_HINTS.items()}
    star_hits = sum(star_found.values())
    relevance, coverage = relevance_score(session.get("question", ""), text) if words else (0, 0.0)

    score = star_hits * 12.5 + relevance * 0.4 + min(words / 120, 1.0) * 10
    score = max(0.0, min(100.0, score))

    notes = []
    missing = [k for k, v in star_found.items() if not v]
    if missing:
        notes.append("Missing the " + ", ".join(missing).upper() + " part of STAR.")
    else:
        notes.append("Full STAR structure detected - well organised answer.")
    if words and relevance < 50:
        notes.append("Your answer did not address many of the question's key points. Re-read the question and answer it directly.")
    if words < 60:
        notes.append("Only " + str(words) + " words - aim for 90-150 on this question.")

    return ModuleResult(
        module_id="nlp_score", name=MODULE_INFO["name"], score=score,
        status=MODULE_INFO["status"],
        metrics={"word_count": words, "relevance": relevance, "question_term_coverage": round(coverage, 2),
                 "star_parts_found": star_hits, "star_breakdown": star_found},
        notes=notes,
    )

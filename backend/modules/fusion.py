"""Model 6 - Multi-Modal Fusion.  The HUB.

This is the only place in the entire system where the modalities are combined.
The 5 scorers never see each other's output; they all report here.

Current strategy: transparent weighted sum (easy to explain to a panel).
Upgrade path: train a small regressor on labelled interviews so the weights are
learned per question type instead of hand-set.
"""

MODULE_INFO = {
    "id": "fusion",
    "name": "Multi-Modal Fusion",
    "role": "fusion",
    "inputs": ["all scorer outputs"],
    "status": "stub",
    "measures": "one overall score + per-modality contribution",
    "planned_stack": "weighted sum now; gradient-boosted regressor once labelled",
}

# Content is weighted highest: what you say matters more than how you look.
WEIGHTS = {
    "nlp_score": 0.35,
    "speech": 0.25,
    "eye_gaze": 0.15,
    "facial": 0.15,
    "gesture": 0.10,
}


def fuse(results: list) -> dict:
    """results: list of ModuleResult from the scorer modules."""
    by_id = {r.module_id: r for r in results}

    total_weight = 0.0
    weighted = 0.0
    contributions = []
    for mid, w in WEIGHTS.items():
        r = by_id.get(mid)
        if r is None:
            continue
        weighted += r.score * w
        total_weight += w
        contributions.append({
            "module_id": mid,
            "name": r.name,
            "score": round(r.score, 1),
            "weight": w,
            "contribution": round(r.score * w, 1),
        })

    overall = round(weighted / total_weight, 1) if total_weight else 0.0

    if overall >= 80:
        verdict, blurb = "Strong", "Interview-ready answer."
    elif overall >= 65:
        verdict, blurb = "Good", "Solid, with a couple of fixable habits."
    elif overall >= 50:
        verdict, blurb = "Developing", "The content is there; delivery needs work."
    else:
        verdict, blurb = "Needs Work", "Rebuild the answer using STAR, then re-record."

    ranked = sorted(contributions, key=lambda c: c["score"])
    return {
        "overall_score": overall,
        "verdict": verdict,
        "summary": blurb,
        "contributions": contributions,
        "weakest": ranked[0]["name"] if ranked else None,
        "strongest": ranked[-1]["name"] if ranked else None,
    }

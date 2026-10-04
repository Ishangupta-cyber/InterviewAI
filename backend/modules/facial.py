"""Model 3 - Facial Expression Analysis.  Input: video frames -> confidence."""

from .base import ModuleResult, seeded_random

MODULE_INFO = {
    "id": "facial",
    "name": "Facial Expression",
    "role": "scorer",
    "inputs": ["video"],
    "status": "stub",
    "measures": "dominant emotion, smile ratio, expression variability",
    "planned_stack": "MediaPipe FaceMesh + a small FER CNN (FER-2013)",
}

EMOTIONS = ["confident", "neutral", "nervous", "engaged"]


def analyze(session: dict) -> ModuleResult:
    # TODO(real): sample frames from session["video_path"], run FER per frame,
    # aggregate the emotion distribution across the whole answer.
    rng = seeded_random(session["session_id"], "facial")

    dominant = rng.choice(EMOTIONS)
    smile_ratio = round(rng.uniform(0.05, 0.55), 2)
    neutral_ratio = round(rng.uniform(0.3, 0.8), 2)
    variability = round(rng.uniform(0.1, 0.8), 2)

    score = 55 + smile_ratio * 50 + variability * 25
    if dominant == "nervous":
        score -= 18
    score = max(0.0, min(100.0, score))

    notes = ["Dominant expression: " + dominant + "."]
    if smile_ratio < 0.12:
        notes.append("Very little smiling - a brief smile early builds rapport.")
    if variability < 0.2:
        notes.append("Expression stayed flat; some animation reads as engaged.")

    return ModuleResult(
        module_id="facial", name=MODULE_INFO["name"], score=score,
        status=MODULE_INFO["status"],
        metrics={"dominant_emotion": dominant, "smile_ratio": smile_ratio,
                 "neutral_ratio": neutral_ratio, "variability": variability},
        notes=notes,
    )

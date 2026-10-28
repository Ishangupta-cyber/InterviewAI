"""Model 3 - Facial Expression.  Input: per-answer camera summary (MediaPipe, computed in the browser).

This does NOT read emotions. It measures three plain signals a coach would also notice:
  presence   - was the face in view
  positivity - how often the candidate smiled (a few smiles read as warm; none or constant reads as flat or nervous)
  composure  - how steady the head was (constant movement reads as restless)
Appearance-based signals can carry bias, so the weight stays low in fusion.py and bias_guard.py
checks how much of the final score they drive. Returns None when the camera was off.
"""

from .base import ModuleResult
from .eye_gaze import clean_vision

MODULE_INFO = {
    "id": "facial",
    "name": "Facial Expression",
    "role": "scorer",
    "inputs": ["camera summary (face landmarks, blendshapes)"],
    "status": "live",
    "measures": "face presence, smile frequency, head steadiness",
    "planned_stack": "MediaPipe FaceLandmarker (runs in the browser; video never uploaded)",
}


def positivity_score(smile_pct: float) -> float:
    if smile_pct < 10:
        return 60 + smile_pct * 4            # 0% -> 60, 10% -> 100
    if smile_pct <= 60:
        return 100.0
    return max(40.0, 100 - (smile_pct - 60) * 0.5)


def composure_score(head_motion_deg: float) -> float:
    if head_motion_deg <= 8:
        return 100.0
    return max(40.0, 100 - (head_motion_deg - 8) * 3)


def analyze(session: dict) -> ModuleResult | None:
    v = clean_vision(session.get("vision"))
    if v is None:
        return None

    presence = v["face_present_pct"]
    positivity = positivity_score(v["smile_pct"])
    composure = composure_score(v["head_motion"])
    score = 0.4 * presence + 0.3 * positivity + 0.3 * composure

    notes = []
    if presence < 80:
        notes.append("Your face was out of view for part of the answer.")
    if v["smile_pct"] < 5:
        notes.append("You barely smiled. A natural smile when greeting or closing a point helps.")
    elif v["smile_pct"] > 60:
        notes.append("You smiled almost constantly, which can look nervous. Match your expression to what you say.")
    else:
        notes.append("Natural, warm expression.")
    if v["head_motion"] > 15:
        notes.append("Your head moved a lot. Try to keep it steadier while speaking.")
    elif v["head_motion"] <= 8:
        notes.append("Steady, composed posture of the head.")

    return ModuleResult(
        module_id="facial", name=MODULE_INFO["name"], score=score,
        status=MODULE_INFO["status"],
        metrics={"face_present_pct": round(presence, 1), "smile_pct": round(v["smile_pct"], 1),
                 "head_motion_deg": round(v["head_motion"], 1), "frames_sampled": v["frames"]},
        notes=notes,
    )

"""Model 8 - Bias & Privacy Guard.

Runs AFTER fusion, before anything is shown to the user. Two jobs:
  1. Fairness - flag scores that lean too hard on appearance-based modalities,
     which is where demographic bias would leak in.
  2. Privacy  - state what raw media was retained vs discarded.

Your panel will very likely ask whether this is real or future work, so it is
wired into the pipeline from day one rather than bolted on later.
"""

MODULE_INFO = {
    "id": "bias_guard",
    "name": "Bias & Privacy Guard",
    "role": "guard",
    "inputs": ["fusion output"],
    "status": "stub",
    "measures": "appearance-vs-content balance, retention policy",
    "planned_stack": "fairness audit across demographic slices (Fairlearn)",
}

# Modalities that read the candidate's body/face rather than their answer.
APPEARANCE_MODULES = {"facial", "gesture", "eye_gaze"}


def check(fusion_result: dict, session: dict) -> dict:
    contributions = fusion_result.get("contributions", [])
    total = sum(c["contribution"] for c in contributions) or 1.0
    appearance = sum(c["contribution"] for c in contributions
                     if c["module_id"] in APPEARANCE_MODULES)
    appearance_share = round(appearance / total * 100, 1)

    flags = []
    # TODO(real): audit score distributions across demographic slices and flag
    # statistically significant gaps, not just this weighting heuristic.
    if appearance_share > 45:
        flags.append("Appearance-based signals drove " + str(appearance_share) +
                     "% of this score - above the 45% fairness threshold.")

    low_conf = [c["name"] for c in contributions if c["score"] < 40]
    if len(low_conf) >= 3:
        flags.append("Several modalities scored very low; poor lighting or a bad "
                     "mic can cause this, so treat the score as low-confidence.")

    return {
        "passed": len(flags) == 0,
        "flags": flags,
        "appearance_share_pct": appearance_share,
        "privacy": {
            "raw_video_retained": False,
            "raw_audio_retained": False,
            "stored": "derived numeric features and the transcript only",
            "note": "Raw media is discarded once features are extracted.",
        },
    }

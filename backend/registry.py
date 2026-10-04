"""Single source of truth for which modules exist and what state they are in.

The /api/modules endpoint reads this, so the Modules page on the website always
reflects reality - when you make a module real, the badge flips automatically.
"""

from modules import (speech, nlp_score, facial, gesture, eye_gaze,
                     fusion, interviewer_agent, bias_guard)

# The 5 independent scorers (the spokes). Order = display order.
SCORERS = [speech, nlp_score, facial, gesture, eye_gaze]

# Everything, including the non-scoring modules.
ALL_MODULES = SCORERS + [interviewer_agent, fusion, bias_guard]


def module_info():
    out = []
    for m in ALL_MODULES:
        info = dict(m.MODULE_INFO)
        if info["id"] in fusion.WEIGHTS:
            info["fusion_weight"] = fusion.WEIGHTS[info["id"]]
        out.append(info)
    return out


def progress():
    live = sum(1 for m in ALL_MODULES if m.MODULE_INFO["status"] == "live")
    return {"live": live, "total": len(ALL_MODULES)}

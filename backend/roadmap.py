"""Improvement roadmap for the report: what to practise next, tied to the candidate's own scores.

Gemini writes it when a key is available; otherwise a fixed rule-based plan is built from the weakest
areas. The LLM is told not to invent links, because made-up URLs are the usual failure.
"""

import json

import llm

# Offline plan: what to practise for each scorer. Used when Gemini is unavailable.
RULES = {
    "Speech Analysis": {
        "why": "Pace, filler words or long pauses hurt how confident you sound.",
        "actions": ["Record yourself answering one question and play it back, counting filler words.",
                    "Replace 'um' and 'basically' with a silent one-second pause.",
                    "Practise at about 140 words per minute: roughly 90 words in 40 seconds."],
    },
    "NLP Response Scorer": {
        "why": "Answers were missing structure or did not address the question directly.",
        "actions": ["Answer behavioural questions in STAR order: Situation, Task, Action, Result.",
                    "Finish every story with one measurable result (a number, a time saved, a user count).",
                    "Underline the key terms in the question and make sure your answer uses them."],
    },
    "Facial Expression": {
        "why": "Face visibility, smile or head movement made your delivery look flat or restless.",
        "actions": ["Sit with your face fully in frame and a light source in front of you.",
                    "Smile naturally when you greet and when you finish a point.",
                    "Rest your hands and keep your head steady while speaking."],
    },
    "Eye Contact": {
        "why": "You looked away from the screen for a large share of your answers.",
        "actions": ["Put the interview window right under the camera so reading it looks like eye contact.",
                    "Look at the camera at the start and end of each point.",
                    "Keep notes out of sight: glancing at a second screen counts as looking away."],
    },
}


def _rule_based(avgs: dict) -> dict:
    ranked = sorted(avgs.items(), key=lambda kv: kv[1])[:3]
    areas = []
    for name, score in ranked:
        rule = RULES.get(name)
        if rule and score < 80:
            areas.append({"area": name, "score": score, "why": rule["why"],
                          "actions": rule["actions"], "practice_resources": []})
    summary = ("Focus on the areas below before your next session." if areas
               else "Your scores were strong across the board. Keep practising with harder questions.")
    return {"source": "rules", "summary": summary, "focus_areas": areas,
            "next_session_goal": f"Lift your lowest area ({ranked[0][0]}) by 10 points." if ranked else ""}


def build(role: str, avgs: dict, qa: list) -> dict:
    """avgs: {module name: average score}. qa: [{"question", "answer", "score"}] for this session."""
    if not avgs:
        return {"source": "rules", "summary": "", "focus_areas": [], "next_session_goal": ""}
    if not llm.available():
        return _rule_based(avgs)

    weakest_answers = sorted(qa, key=lambda x: x["score"])[:3]
    prompt = (
        f"You are an interview coach. A candidate practised for the role: {role}. "
        "Below are their average scores (0-100) per area and their three lowest-scoring answers. "
        "Write a short improvement roadmap. Return JSON with keys: "
        '"summary" (2 sentences), '
        '"focus_areas" (at most 3 objects, each with "area", "why" (one sentence citing their score), '
        '"actions" (exactly 3 concrete practice steps), "practice_resources" (up to 2 names of well-known '
        'techniques or exercises, for example "STAR method"; NEVER include URLs or invented titles)), '
        '"next_session_goal" (one measurable goal).\n\n'
        f"SCORES: {json.dumps(avgs)}\n"
        f"WEAKEST ANSWERS: {json.dumps([{**w, 'answer': w['answer'][:400]} for w in weakest_answers])}"
    )
    data = llm.generate_json(prompt)
    if isinstance(data, dict) and isinstance(data.get("focus_areas"), list) and data["focus_areas"]:
        areas = []
        for a in data["focus_areas"][:3]:
            if isinstance(a, dict) and a.get("area") and isinstance(a.get("actions"), list):
                areas.append({"area": str(a["area"]), "why": str(a.get("why", "")),
                              "actions": [str(x) for x in a["actions"][:4]],
                              "practice_resources": [str(x) for x in (a.get("practice_resources") or [])[:2]]})
        if areas:
            return {"source": "llm", "summary": str(data.get("summary", "")), "focus_areas": areas,
                    "next_session_goal": str(data.get("next_session_goal", ""))}
    return _rule_based(avgs)

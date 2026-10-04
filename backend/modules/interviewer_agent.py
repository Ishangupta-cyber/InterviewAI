"""Model 7 - Adaptive Interviewer Agent.

Two jobs:
  1. generate_plan(): build a personalised question list from the resume (LLM,
     with an offline fallback built from the resume's skills + the fixed bank).
  2. next_question(): after each answer, read the fusion verdict and decide -
     a weak answer earns ONE follow-up probe on the same topic, a good one
     advances. That feedback edge is the dashed line in the architecture diagram.
"""

import json
import os
import random

import llm

MODULE_INFO = {
    "id": "interviewer_agent",
    "name": "Adaptive Interviewer Agent",
    "role": "agent",
    "inputs": ["resume", "previous answer + fusion verdict"],
    "status": "live",
    "measures": "generates personalised questions; picks next question / follow-up probe",
    "planned_stack": "Gemini LLM with a rubric prompt; question-bank fallback offline",
}

_BANK_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "questions.json")
PROBE_THRESHOLD = 65


def load_bank():
    with open(os.path.abspath(_BANK_PATH), "r", encoding="utf-8") as f:
        return json.load(f)


def _fallback_plan(resume: dict | None, interview_type: str, n: int) -> list:
    bank = load_bank()
    plan = []
    if resume:
        for skill in (resume.get("skills") or [])[:3]:
            plan.append({"text": f"Explain a concrete problem you solved using {skill}, and why you chose it.",
                         "category": "technical", "difficulty": "medium", "generated_by_ai": False})
        for proj in (resume.get("projects") or [])[:2]:
            plan.append({"text": f"Walk me through this project from your resume: {proj[:140]}. What was your own contribution?",
                         "category": "project", "difficulty": "medium", "generated_by_ai": False})
    for q in bank["software"]:
        plan.append({"text": q["text"], "category": "hr" if q["kind"] in ("intro", "behavioural", "closing") else "technical",
                     "difficulty": "medium", "generated_by_ai": False})
    if interview_type in ("technical", "hr"):
        plan = [p for p in plan if p["category"] in (interview_type, "project")] or plan
    return plan[:n]


def generate_plan(resume: dict | None, interview_type: str = "mixed",
                  role: str = "Software Engineer", n: int = 6) -> list:
    """Returns n dicts: text, category (technical|hr|project), difficulty, generated_by_ai."""
    if llm.available():
        prompt = (
            f"You are a senior interviewer hiring for the role: {role}. Interview type: {interview_type} "
            f"(technical, hr, or mixed). Write exactly {n} interview questions, ordered like a real "
            "interview (warm-up first, deeper later). Personalise them to the candidate's resume below - "
            "reference their actual skills and projects. Return JSON: a list of objects with keys "
            '"text", "category" (one of technical, hr, project) and "difficulty" (easy, medium, hard).\n\n'
            "RESUME SUMMARY:\n" + json.dumps(resume or {"note": "no resume supplied"})[:6000]
        )
        data = llm.generate_json(prompt)
        if isinstance(data, dict):
            data = data.get("questions")
        if isinstance(data, list) and data:
            out = []
            for q in data[:n]:
                if isinstance(q, dict) and q.get("text"):
                    out.append({"text": q["text"], "category": q.get("category", "technical"),
                                "difficulty": q.get("difficulty", "medium"), "generated_by_ai": True})
            if out:
                return out
    return _fallback_plan(resume, interview_type, n)


def _probe(question: str, transcript: str, fusion: dict) -> str:
    if llm.available():
        data = llm.generate_json(
            "You are an interviewer. The candidate gave a weak answer. Write ONE short follow-up "
            "question probing the same topic (ask for specifics, their own contribution, or a "
            f'measurable result). Return JSON {{"text": "..."}}.\n\nQuestion: {question}\n'
            f"Answer: {transcript[:1500]}"
        )
        if isinstance(data, dict) and data.get("text"):
            return data["text"]
    return random.Random(len(transcript)).choice(load_bank()["follow_ups"])


def next_question(pending: list, last_fusion: dict | None, last_question: str = "",
                  last_transcript: str = "", last_was_probe: bool = False) -> dict | None:
    """pending: remaining planned question dicts. Returns the next question dict, or None to end."""
    if last_fusion and not last_was_probe and last_fusion["overall_score"] < PROBE_THRESHOLD:
        return {
            "text": _probe(last_question, last_transcript, last_fusion),
            "category": "follow-up", "difficulty": "medium", "kind": "follow-up probe",
            "generated_by_ai": llm.available(),
            "reason": f"Previous answer scored {last_fusion['overall_score']} "
                      f"(weakest: {last_fusion.get('weakest')}) - probing the same topic instead of moving on.",
        }
    if not pending:
        return None
    nxt = dict(pending[0])
    nxt["kind"] = "standard"
    nxt["reason"] = "Opening question." if last_fusion is None else "Previous answer was strong - advancing to a new topic."
    return nxt

"""Module 2 - Resume Analysis: text extraction, LLM parsing, offline fallback."""

import re

import llm

SKILL_VOCAB = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql",
    "react", "node.js", "django", "flask", "fastapi", "spring", "html", "css",
    "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes", "aws", "azure",
    "gcp", "git", "linux", "rest", "graphql", "machine learning", "deep learning",
    "nlp", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "opencv",
    "data structures", "algorithms", "tableau", "power bi", "excel",
]
SECTIONS = ["education", "experience", "projects", "skills", "summary", "certifications"]


def extract_text(path: str, name: str) -> str:
    name = name.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    if name.endswith(".docx"):
        import docx
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    raise ValueError("Only PDF and DOCX resumes are supported.")


def _heuristic(text: str) -> dict:
    low = text.lower()
    skills = [s for s in SKILL_VOCAB if re.search(r"(?<![a-z])" + re.escape(s) + r"(?![a-z])", low)]
    lines = [l.strip() for l in text.splitlines() if len(l.split()) >= 4]  # skip bare headings
    edu = [l for l in lines if re.search(r"b\.?tech|b\.?e\b|bachelor|master|m\.?tech|university|institute|college", l, re.I)][:3]
    proj = [l for l in lines if re.search(r"project|developed|built|implemented", l, re.I)][:5]
    exp = [l for l in lines if re.search(r"intern|engineer|developer|analyst", l, re.I)][:4]
    return {"skills": skills, "education": edu, "experience": exp, "projects": proj}


def _ats(text: str, parsed: dict):
    """Transparent rubric so the score is explainable: 100 points total."""
    low = text.lower()
    score, tips = 0, []
    present = [s for s in SECTIONS if s in low]
    score += min(len(present), 5) * 6  # 30: standard sections
    if len(present) < 4:
        tips.append("Add standard section headings (Education, Experience, Projects, Skills).")
    score += min(len(parsed["skills"]), 10) * 3  # 30: skills
    if len(parsed["skills"]) < 6:
        tips.append("List more concrete technical skills the job description asks for.")
    nums = len(re.findall(r"\d+\s?%|\d+\+|\$\s?\d+|\b\d{2,}\b", text))
    score += min(nums, 5) * 4  # 20: quantified impact
    if nums < 3:
        tips.append("Quantify achievements (e.g. 'reduced latency by 30%').")
    words = len(text.split())
    score += 10 if 250 <= words <= 900 else 4  # 10: length
    if not 250 <= words <= 900:
        tips.append("Aim for roughly one page (250-900 words).")
    score += 5 if re.search(r"[\w.]+@[\w.]+", text) else 0
    score += 5 if re.search(r"linkedin|github", low) else 0
    if not re.search(r"linkedin|github", low):
        tips.append("Add your GitHub / LinkedIn links.")
    return min(score, 100), tips


def analyse(text: str) -> dict:
    parsed, by = None, "heuristic"
    if llm.available() and text.strip():
        data = llm.generate_json(
            "You are an ATS resume parser. From the resume below return JSON with keys: "
            '"skills" (list of strings), "education" (list of short strings), '
            '"experience" (list of short strings), "projects" (list of short strings, '
            'each "Name - what it does and tech used"), "ats_score" (integer 0-100 for '
            'ATS-friendliness), "suggestions" (list of up to 5 concrete improvements).\n\n'
            "RESUME:\n" + text[:12000]
        )
        if isinstance(data, dict) and data.get("skills") is not None:
            parsed, by = data, "llm"

    if parsed is None:
        parsed = _heuristic(text)
        score, tips = _ats(text, parsed)
        parsed["ats_score"], parsed["suggestions"] = score, tips

    return {
        "skills": list(parsed.get("skills") or []),
        "education": list(parsed.get("education") or []),
        "experience": list(parsed.get("experience") or []),
        "projects": list(parsed.get("projects") or []),
        "ats_score": int(parsed.get("ats_score") or 0),
        "suggestions": list(parsed.get("suggestions") or []),
        "analysed_by": by,
    }

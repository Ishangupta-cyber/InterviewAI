from collections import defaultdict

from django.contrib.auth import authenticate, get_user_model
from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response as Resp
from rest_framework_simplejwt.tokens import RefreshToken

import pipeline
import registry
import resume_service
import stt
from modules import interviewer_agent

from .models import AIEvaluation, InterviewSession, Question, Report, Resume
from .models import Response as AnswerRow

User = get_user_model()


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Resp({"error": msg}, status=code)


def _user_json(u):
    return {"id": u.id, "name": u.first_name or u.username, "email": u.email, "phone": u.phone}


# --------------------------------------------------------------------- public
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Resp({"status": "ok", "modules": registry.progress()})


@api_view(["GET"])
@permission_classes([AllowAny])
def modules(request):
    return Resp({"modules": registry.module_info(), "progress": registry.progress()})


# ----------------------------------------------------------------------- auth
def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh), "user": _user_json(user)}


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    d = request.data
    email = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""
    if not email or "@" not in email:
        return _err("A valid email is required.")
    if len(password) < 8:
        return _err("Password must be at least 8 characters.")
    if User.objects.filter(username=email).exists():
        return _err("An account with this email already exists.", status.HTTP_409_CONFLICT)
    user = User.objects.create_user(username=email, email=email, password=password,
                                    first_name=(d.get("name") or "").strip(),
                                    phone=(d.get("phone") or "").strip())
    return Resp(_tokens(user), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    email = (request.data.get("email") or "").strip().lower()
    user = authenticate(username=email, password=request.data.get("password") or "")
    if not user:
        return _err("Invalid email or password.", status.HTTP_401_UNAUTHORIZED)
    return Resp(_tokens(user))


@api_view(["GET"])
def me(request):
    return Resp(_user_json(request.user))


# -------------------------------------------------------------------- resumes
def _resume_json(r):
    return {"id": r.id, "name": r.original_name, "skills": r.skills, "education": r.education,
            "experience": r.experience, "projects": r.projects, "ats_score": r.ats_score,
            "suggestions": r.suggestions, "analysed_by": r.analysed_by,
            "uploaded_at": r.uploaded_at.isoformat()}


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser])
def resumes(request):
    if request.method == "GET":
        return Resp([_resume_json(r) for r in request.user.resumes.order_by("-uploaded_at")])

    f = request.FILES.get("file")
    if not f:
        return _err("Attach a resume file in the 'file' field.")
    if not f.name.lower().endswith((".pdf", ".docx")):
        return _err("Only PDF and DOCX resumes are supported.")
    if f.size > 5 * 1024 * 1024:
        return _err("Resume must be under 5 MB.")

    r = Resume.objects.create(user=request.user, file=f, original_name=f.name)
    try:
        text = resume_service.extract_text(r.file.path, f.name)
    except Exception:
        r.delete()
        return _err("Could not read that file. Is it a valid, text-based PDF/DOCX?")
    if len(text.strip()) < 50:
        r.delete()
        return _err("No readable text found (scanned image PDFs are not supported).")

    a = resume_service.analyse(text)
    r.text = text
    for k in ("skills", "education", "experience", "projects", "ats_score", "suggestions", "analysed_by"):
        setattr(r, k, a[k])
    r.save()
    return Resp(_resume_json(r), status=status.HTTP_201_CREATED)


# ------------------------------------------------------------------- sessions
def _q_json(q):
    return {"id": q.id, "order": q.order, "text": q.text, "category": q.category,
            "difficulty": q.difficulty, "kind": q.kind, "reason": q.reason,
            "generated_by_ai": q.generated_by_ai}


def _current(session):
    return session.questions.filter(response__isnull=True).order_by("order").first()


def _session_json(s):
    qs = list(s.questions.all())
    answered = sum(1 for q in qs if hasattr(q, "response"))
    return {"id": s.id, "role": s.role, "interview_type": s.interview_type, "status": s.status,
            "start_time": s.start_time.isoformat(), "answered": answered, "total_questions": len(qs),
            "total_score": s.report.total_score if hasattr(s, "report") else None}


def _own_session(request, sid):
    return InterviewSession.objects.filter(pk=sid, user=request.user).first()


@api_view(["GET", "POST"])
def sessions(request):
    if request.method == "GET":
        qs = request.user.sessions.order_by("-start_time")
        return Resp([_session_json(s) for s in qs])

    d = request.data
    resume = None
    if d.get("resume_id"):
        resume = request.user.resumes.filter(pk=d["resume_id"]).first()
        if not resume:
            return _err("Unknown resume.", status.HTTP_404_NOT_FOUND)
    itype = d.get("interview_type", "mixed")
    if itype not in ("technical", "hr", "mixed"):
        return _err("interview_type must be technical, hr or mixed.")
    try:
        n = max(3, min(int(d.get("num_questions", 6)), 10))
    except (TypeError, ValueError):
        n = 6
    role = (d.get("role") or "Software Engineer").strip()[:60]

    plan = interviewer_agent.generate_plan(_resume_json(resume) if resume else None, itype, role, n)
    session = InterviewSession.objects.create(user=request.user, resume=resume,
                                              interview_type=itype, role=role)
    Question.objects.bulk_create([
        Question(session=session, order=i, text=q["text"], category=q["category"],
                 difficulty=q["difficulty"], generated_by_ai=q["generated_by_ai"])
        for i, q in enumerate(plan)
    ])
    first = _current(session)
    first.reason = "Opening question."
    first.save(update_fields=["reason"])
    return Resp({"session": _session_json(session), "question": _q_json(first)},
                status=status.HTTP_201_CREATED)


@api_view(["GET"])
def session_detail(request, sid):
    s = _own_session(request, sid)
    if not s:
        return _err("Unknown session.", status.HTTP_404_NOT_FOUND)
    current = _current(s) if s.status == "active" else None
    answers = []
    for q in s.questions.all():
        if hasattr(q, "response"):
            answers.append({"question": _q_json(q), "transcript": q.response.answer_text,
                            "result": q.response.evaluation.result})
    return Resp({"session": _session_json(s),
                 "current_question": _q_json(current) if current else None,
                 "answers": answers,
                 "report": _report_json(s.report) if hasattr(s, "report") else None})


@api_view(["POST"])
def answer(request, sid):
    s = _own_session(request, sid)
    if not s:
        return _err("Unknown session.", status.HTTP_404_NOT_FOUND)
    if s.status != "active":
        return _err("This interview is already finished.")
    q = _current(s)
    if not q:
        return _err("No pending question.")
    transcript = (request.data.get("transcript") or "").strip()
    if not transcript:
        return _err("Answer is empty - speak or type a response first.")
    try:
        duration = int(request.data.get("duration_sec") or 0)
    except (TypeError, ValueError):
        duration = 0

    result = pipeline.run({"session_id": str(s.id), "question": q.text,
                           "transcript": transcript, "duration_sec": duration})
    resp = AnswerRow.objects.create(question=q, answer_text=transcript, duration_sec=duration)
    mods = {m["module_id"]: m["score"] for m in result["modules"]}
    AIEvaluation.objects.create(response=resp, overall_score=result["fusion"]["overall_score"],
                                technical_score=mods.get("nlp_score", 0),
                                communication_score=mods.get("speech", 0), result=result)

    pending = list(s.questions.filter(response__isnull=True).order_by("order"))
    nxt = pipeline.next_question(
        [{"text": p.text, "category": p.category, "difficulty": p.difficulty,
          "generated_by_ai": p.generated_by_ai} for p in pending],
        result["fusion"], q.text, transcript, last_was_probe=(q.kind == "follow-up probe"))

    next_row = None
    if nxt and nxt["kind"] == "follow-up probe":
        s.questions.filter(order__gt=q.order).update(order=F("order") + 1)
        next_row = Question.objects.create(
            session=s, order=q.order + 1, text=nxt["text"], category="follow-up",
            kind="follow-up probe", difficulty=nxt["difficulty"],
            generated_by_ai=nxt["generated_by_ai"], reason=nxt["reason"])
    elif nxt:
        next_row = pending[0]
        next_row.reason = nxt["reason"]
        next_row.save(update_fields=["reason"])

    report = _finish(s) if next_row is None else None
    return Resp({"result": result,
                 "next_question": _q_json(next_row) if next_row else None,
                 "answered": s.questions.filter(response__isnull=False).count(),
                 "report": _report_json(report) if report else None})


# --------------------------------------------------------------------- report
def _finish(s):
    evals = [q.response.evaluation for q in s.questions.filter(response__isnull=False)]
    per_mod, notes = defaultdict(list), []
    for ev in evals:
        for m in ev.result["modules"]:
            per_mod[m["name"]].append(m["score"])
            notes.extend(m["notes"])
    avgs = {k: round(sum(v) / len(v), 1) for k, v in per_mod.items()}
    total = round(sum(e.overall_score for e in evals) / len(evals), 1) if evals else 0
    tips = list(dict.fromkeys(notes))  # de-duplicate, keep order
    s.status, s.end_time = "completed", timezone.now()
    s.save(update_fields=["status", "end_time"])
    report, _ = Report.objects.update_or_create(session=s, defaults={
        "total_score": total,
        "strengths": [f"{k} ({v})" for k, v in avgs.items() if v >= 70],
        "weaknesses": [f"{k} ({v})" for k, v in avgs.items() if v < 60],
        "suggestions": tips[:8],
    })
    return report


def _report_json(r):
    return {"total_score": r.total_score, "strengths": r.strengths, "weaknesses": r.weaknesses,
            "suggestions": r.suggestions, "created_at": r.created_at.isoformat()}


@api_view(["POST"])
def finish(request, sid):
    s = _own_session(request, sid)
    if not s:
        return _err("Unknown session.", status.HTTP_404_NOT_FOUND)
    if not s.questions.filter(response__isnull=False).exists():
        return _err("Answer at least one question before finishing.")
    report = s.report if hasattr(s, "report") else _finish(s)
    return Resp(_report_json(report))


# ------------------------------------------------------------------ dashboard
@api_view(["GET"])
def dashboard(request):
    done = list(request.user.sessions.filter(status="completed")
                .select_related("report").order_by("start_time"))
    trend = [{"session": s.id, "date": s.start_time.date().isoformat(), "score": s.report.total_score}
             for s in done]
    per_mod = defaultdict(list)
    for ev in AIEvaluation.objects.filter(response__question__session__in=done):
        for m in ev.result["modules"]:
            per_mod[m["name"]].append(m["score"])
    topics = [{"name": k, "score": round(sum(v) / len(v), 1)} for k, v in per_mod.items()]
    scores = [t["score"] for t in trend]
    latest = request.user.resumes.order_by("-uploaded_at").first()
    return Resp({
        "total_interviews": request.user.sessions.count(),
        "completed": len(trend),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "best_score": max(scores) if scores else 0,
        "trend": trend, "topics": topics,
        "latest_report": _report_json(done[-1].report) if done else None,
        "resume_ats": latest.ats_score if latest else None,
    })


# ----------------------------------------------------------------- transcribe
@api_view(["POST"])
@parser_classes([MultiPartParser])
def transcribe(request):
    """Module 4: audio blob from the browser -> text via faster-whisper."""
    import os
    import tempfile
    f = request.FILES.get("audio")
    if not f:
        return _err("Attach the recording in the 'audio' field.")
    if f.size > 25 * 1024 * 1024:
        return _err("Recording is too large (25 MB max).")
    suffix = os.path.splitext(f.name)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in f.chunks():
            tmp.write(chunk)
    try:
        return Resp(stt.transcribe(tmp.name))
    except Exception as exc:
        return _err(f"Transcription failed: {exc}", status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        os.unlink(tmp.name)

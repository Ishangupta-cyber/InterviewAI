"""Database schema, following the project's ER diagram.

User -> Resume -> InterviewSession -> Question -> Response -> AIEvaluation
InterviewSession -> Report.  Speech/facial analysis rows are folded into
AIEvaluation.result (the per-module JSON) until those modules are real.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, default="candidate")


class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resumes")
    file = models.FileField(upload_to="resumes/")
    original_name = models.CharField(max_length=255)
    text = models.TextField(blank=True)
    skills = models.JSONField(default=list)
    education = models.JSONField(default=list)
    experience = models.JSONField(default=list)
    projects = models.JSONField(default=list)
    ats_score = models.IntegerField(default=0)
    suggestions = models.JSONField(default=list)
    analysed_by = models.CharField(max_length=20, default="heuristic")  # "llm" | "heuristic"
    uploaded_at = models.DateTimeField(auto_now_add=True)


class InterviewSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    resume = models.ForeignKey(Resume, null=True, blank=True, on_delete=models.SET_NULL)
    interview_type = models.CharField(max_length=20, default="mixed")  # technical | hr | mixed
    role = models.CharField(max_length=60, default="Software Engineer")
    status = models.CharField(max_length=20, default="active")  # active | completed
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)


class Question(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="questions")
    order = models.IntegerField()
    text = models.TextField()
    category = models.CharField(max_length=30, default="technical")
    difficulty = models.CharField(max_length=10, default="medium")
    kind = models.CharField(max_length=20, default="standard")  # standard | follow-up probe
    generated_by_ai = models.BooleanField(default=False)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]


class Response(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name="response")
    answer_text = models.TextField(blank=True)
    duration_sec = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class AIEvaluation(models.Model):
    response = models.OneToOneField(Response, on_delete=models.CASCADE, related_name="evaluation")
    overall_score = models.FloatField(default=0)
    technical_score = models.FloatField(default=0)
    communication_score = models.FloatField(default=0)
    result = models.JSONField(default=dict)  # full pipeline output (modules, fusion, guard)


class Report(models.Model):
    session = models.OneToOneField(InterviewSession, on_delete=models.CASCADE, related_name="report")
    total_score = models.FloatField(default=0)
    strengths = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)
    suggestions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("health/", views.health),
    path("modules/", views.modules),
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", views.me),
    path("resumes/", views.resumes),
    path("sessions/", views.sessions),
    path("sessions/<int:sid>/", views.session_detail),
    path("sessions/<int:sid>/answer/", views.answer),
    path("sessions/<int:sid>/finish/", views.finish),
    path("transcribe/", views.transcribe),
    path("dashboard/", views.dashboard),
]

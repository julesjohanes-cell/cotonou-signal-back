"""
Routes de l'API, SANS barre oblique finale, comme dans le contrat (POST /reports, GET /categories, …).
Un petit middleware accepte aussi la version avec barre finale (`/reports/`).
"""

from django.urls import path

from . import views

urlpatterns = [
    path("health", views.HealthView.as_view(), name="health"),
    path("categories", views.CategoryListView.as_view(), name="categories"),
    path("reports", views.ReportListCreateView.as_view(), name="reports"),
    path("reports/<str:tracking_code>", views.ReportDetailView.as_view(), name="report-detail"),
    path("capture-sessions", views.CaptureSessionCreateView.as_view(), name="capture-session-create"),
    path("capture-sessions/<str:token>", views.CaptureSessionDetailView.as_view(), name="capture-session-detail"),
    path("auth/login", views.LoginView.as_view(), name="login"),
    path("agent/reports", views.AgentReportListView.as_view(), name="agent-reports"),
    path("agent/reports/<str:tracking_code>", views.AgentReportDetailView.as_view(), name="agent-report-detail"),
    path(
        "agent/reports/<str:tracking_code>/after-photo",
        views.AgentAfterPhotoView.as_view(),
        name="agent-after-photo",
    ),
]

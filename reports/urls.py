from django.urls import path
from .views import create_report, list_reports, get_report_detail, report_stats

urlpatterns = [
    path("stats/", report_stats, name="report-stats"),
    path("", list_reports, name="list-reports"),
    path("create/", create_report, name="create-report"),
    path("<uuid:pk>/", get_report_detail, name="report-detail"),
]

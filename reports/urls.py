from django.urls import path
from .views import create_report

urlpatterns = [
    path("", create_report),
]

# api/template_urls.py

from django.urls import path
from api import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]

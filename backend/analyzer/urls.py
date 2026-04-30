from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health),
    path("samples/", views.samples),
    path("analyze/", views.analyze),
]

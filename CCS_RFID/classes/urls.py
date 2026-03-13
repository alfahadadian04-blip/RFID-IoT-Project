from django.urls import path
from . import views

urlpatterns = [
    path('classes/', views.classes, name='classes'),
]
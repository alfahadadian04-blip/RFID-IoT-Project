from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('activity/', views.activity, name='activity'),
    path('stud_dashboard/', views.stud_dashboard, name='stud_dashboard'),
    path('student_subject/', views.student_subject, name='student_subject'),
    path('student_view_class/', views.student_view_class, name='student_view_class'),
]
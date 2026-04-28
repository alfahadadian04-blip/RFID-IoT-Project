from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('activity/', views.activity, name='activity'),
    path('stud_dashboard/', views.stud_dashboard, name='stud_dashboard'),
    path('student_subject/', views.student_subject, name='student_subject'),
    path('student_view_class/', views.student_view_class, name='student_view_class'),
    path('api/activity-log/', views.get_activity_log, name='get_activity_log'),
    path('api/update-attendance-status/', views.update_attendance_status, name='update_attendance_status'),
    
    # Superadmin URLs
    path('user-management/', views.user_management, name='user_management'),
    path('edit-student/<int:user_id>/', views.edit_student, name='edit_student'),
    path('user/delete/<int:user_id>/', views.delete_user, name='delete_user'),
]
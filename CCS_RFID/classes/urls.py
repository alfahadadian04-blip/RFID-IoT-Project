from django.urls import path
from . import views

urlpatterns = [
    path('classes/', views.classes, name='classes'),
    path('view_class/', views.view_class, name='view_class'),
    path('upload-masterlist/', views.upload_masterlist, name='upload_masterlist'),
    path('delete-class/<int:class_id>/', views.delete_class, name='delete_class'),
    path('start-class-session/<int:class_id>/', views.start_class_session, name='start_class_session'),
    path('end-class-session/<int:session_id>/', views.end_class_session, name='end_class_session'),
    path('active-class-session/<int:class_id>/', views.active_class_session, name='active_class_session'),
    path('record-attendance/', views.record_attendance, name='record_attendance'),
    path('api/get-active-session/', views.get_active_session, name='get_active_session'),


    path('api/clear-pending-rfid/', views.clear_pending_rfid, name='clear_pending_rfid'),
    path('api/cancel-pending-registration/', views.cancel_pending_registration, name='cancel_pending_registration'),
    path('api/session-attendance/<int:session_id>/', views.get_session_attendance, name='session_attendance'),
    path('api/student-attendance-history/<int:student_id>/<int:class_id>/', views.get_student_attendance_history, name='student_attendance_history'),

    path('api/activity-log/', views.get_activity_log, name='activity_log'),
    path('api/update-attendance-status/', views.update_attendance_status, name='update_attendance_status'),
]
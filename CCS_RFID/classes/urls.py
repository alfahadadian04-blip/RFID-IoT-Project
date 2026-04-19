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
]
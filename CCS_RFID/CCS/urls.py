from django.urls import path
from . import views

urlpatterns = [
    path('', views.adminLogin, name='adminLogin'),
    path('studentLogin/', views.studentLogin, name='studentLogin'),
    path('adminRegistration/', views.adminRegistration, name='adminRegistration'),
    path('studentRegistration/', views.studentRegistration, name='studentRegistration'),
    path('logout/', views.logout_view, name='logout'),
    path('api/rfid/', views.rfid_handler, name='rfid_handler'),  # This line MUST be here
    path('api/check-rfid/<int:student_id>/', views.check_rfid_status, name='check_rfid'),

    path('api/pending-rfid/create/<int:student_id>/', views.create_pending_rfid, name='create_pending_rfid'),
    path('api/pending-rfid/check/', views.check_pending_rfid, name='check_pending_rfid'),
]
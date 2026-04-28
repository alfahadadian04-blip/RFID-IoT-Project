from django.urls import path
from . import views

urlpatterns = [
    # Unified Login Page (NEW) - changed name to 'login_page' to avoid conflict
    path('', views.login_page, name='login_page'),
    
    # API Login endpoint
    path('api/login/', views.api_login, name='api_login'),
    
    # Legacy login pages (keep for backward compatibility)
    path('adminLogin/', views.adminLogin, name='adminLogin'),
    path('studentLogin/', views.studentLogin, name='studentLogin'),
    
    # Registration pages
    path('adminRegistration/', views.adminRegistration, name='adminRegistration'),
    path('studentRegistration/', views.studentRegistration, name='studentRegistration'),
    
    # Logout
    path('logout/', views.logout_view, name='logout'),
    
    # RFID endpoints
    path('api/rfid/', views.rfid_handler, name='rfid_handler'),
    path('api/check-rfid/<int:student_id>/', views.check_rfid_status, name='check_rfid'),
    path('api/pending-rfid/create/<int:student_id>/', views.create_pending_rfid, name='create_pending_rfid'),
    path('api/pending-rfid/check/', views.check_pending_rfid, name='check_pending_rfid'),
    path('student-registration/', views.studentRegistration, name='studentRegistration'),
    
    # RFID Receive endpoints
    path('api/receive-rfid/', views.receive_rfid, name='receive_rfid'),
    path('api/get-latest-rfid/', views.get_latest_rfid, name='get_latest_rfid'),
    path('api/claim-existing-account/', views.claim_existing_account, name='claim_existing_account'),
    path('api/check-user-by-rfid/', views.check_user_by_rfid, name='check_user_by_rfid'),
    
    # Notification endpoints
    path('api/upcoming-classes/', views.get_upcoming_classes, name='upcoming_classes'),
    path('api/dismiss-notification/', views.dismiss_notification, name='dismiss_notification'),

    path('api/clear-pending-rfid/', views.clear_pending_rfid, name='clear_pending_rfid'),
]
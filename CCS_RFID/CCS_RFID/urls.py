from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('CCS.urls')),
    path('', include('attendance.urls')),
    path('', include('classes.urls')),
    path('', include('schedules.urls')),
    path('', include('core.urls')),  # New core app with dashboard + activity
]
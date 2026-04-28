from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('CCS.urls')),
    path('', include('attendance.urls')),
    path('', include('classes.urls')),
    path('', include('schedules.urls')),
    path('', include('core.urls')),  # New core app with dashboard + activity
]
# Add this at the very bottom
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
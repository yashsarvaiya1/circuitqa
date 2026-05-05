# config/urls.py

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/', include('api.urls')),
    path('', include('api.template_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

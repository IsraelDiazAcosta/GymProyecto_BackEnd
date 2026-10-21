from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # API Endpoints
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/catalog/', include('apps.catalog.urls')),
    path('api/v1/routines/', include('apps.routines.urls')),
    path('api/v1/tracking/', include('apps.tracking.urls')),
]

# Servir archivos estáticos y multimedia en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

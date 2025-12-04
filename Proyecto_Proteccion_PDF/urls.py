from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin opcional (no es necesario para la API pero no estorba)
    path("admin/", admin.site.urls),

    # Prefijo de la API
    path("api/", include("core.urls")),
]

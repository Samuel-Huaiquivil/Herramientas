from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("inventario.api_urls")),
    path("", include("inventario.urls")),
]

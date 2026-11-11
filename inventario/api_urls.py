from rest_framework.routers import DefaultRouter

from .api_views import ActivoViewSet, PlanViewSet, PrestamoViewSet

router = DefaultRouter()
router.register("activos", ActivoViewSet, basename="api-activo")
router.register("prestamos", PrestamoViewSet, basename="api-prestamo")
router.register("planes", PlanViewSet, basename="api-plan")

urlpatterns = router.urls

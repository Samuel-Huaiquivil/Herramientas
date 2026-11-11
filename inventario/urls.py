from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("activos/", views.ActivoList.as_view(), name="activo_lista"),
    path("activos/nuevo/", views.ActivoCreate.as_view(), name="activo_nuevo"),
    path("activos/<int:pk>/", views.ActivoDetail.as_view(), name="activo_detalle"),
    path("activos/<int:pk>/editar/", views.ActivoUpdate.as_view(), name="activo_editar"),
    path("activos/<int:pk>/estado/", views.ActivoEstado.as_view(), name="activo_estado"),
    path("prestamos/", views.PrestamoList.as_view(), name="prestamo_lista"),
    path("prestamos/entregar/", views.EntregaView.as_view(), name="entrega"),
    path("prestamos/<int:pk>/", views.PrestamoDetail.as_view(), name="prestamo_detalle"),
    path("prestamos/<int:pk>/devolver/", views.DevolucionView.as_view(), name="devolucion"),
    path("mantenimientos/", views.PlanList.as_view(), name="plan_lista"),
    path("mantenimientos/nuevo/", views.PlanCreate.as_view(), name="plan_nuevo"),
    path("mantenimientos/<int:pk>/completar/", views.PlanCompletar.as_view(), name="plan_completar"),
]

from django.contrib import admin

from .models import Activo, HistorialEstado, Obra, PlanMantenimiento, Prestamo, Subcontratista


@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "estado", "horas_uso", "tarifa_diaria")
    list_filter = ("estado", "categoria")
    search_fields = ("codigo", "nombre")
    readonly_fields = ("estado",)

    def has_delete_permission(self, request, obj=None):
        return False  # se da de baja, no se borra


class SoloLectura(admin.ModelAdmin):
    """Registros de trazabilidad: no se editan desde el admin."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Prestamo)
class PrestamoAdmin(SoloLectura):
    list_display = ("id", "activo", "subcontratista", "obra", "fecha_entrega", "fecha_devolucion")
    list_filter = ("obra", "subcontratista")


@admin.register(HistorialEstado)
class HistorialAdmin(SoloLectura):
    list_display = ("fecha", "activo", "anterior", "nuevo", "usuario", "motivo")


admin.site.register(Subcontratista)
admin.site.register(Obra)
admin.site.register(PlanMantenimiento)

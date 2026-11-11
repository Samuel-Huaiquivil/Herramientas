from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

SOLO_VER = ["activo", "subcontratista", "obra", "prestamo", "planmantenimiento", "historialestado"]
OPERAR = {
    "activo": ["add", "change"],
    "prestamo": ["add", "change"],
    "planmantenimiento": ["add", "change"],
    "subcontratista": ["add", "change"],
    "obra": ["add", "change"],
}


def permisos(codenames):
    return Permission.objects.filter(content_type__app_label="inventario", codename__in=codenames)


class Command(BaseCommand):
    help = "Crea (o actualiza) los grupos Administrador, Bodega y Consulta. Requiere migraciones aplicadas."

    def handle(self, *args, **options):
        ver = [f"view_{m}" for m in SOLO_VER]
        operar = ver + [f"{a}_{m}" for m, acciones in OPERAR.items() for a in acciones]

        g, _ = Group.objects.get_or_create(name="Administrador")
        g.permissions.set(Permission.objects.filter(content_type__app_label="inventario"))
        g, _ = Group.objects.get_or_create(name="Bodega")
        g.permissions.set(permisos(operar))
        g, _ = Group.objects.get_or_create(name="Consulta")
        g.permissions.set(permisos(ver))
        self.stdout.write(self.style.SUCCESS("Grupos listos: Administrador, Bodega, Consulta"))

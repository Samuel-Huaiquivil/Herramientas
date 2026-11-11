from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from inventario.models import Activo, Obra, PlanMantenimiento, Subcontratista


class Command(BaseCommand):
    help = "Datos y usuarios de demostración. Solo funciona con DJANGO_DEBUG=True."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="cambiar123")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Por seguridad, crear_demo solo se ejecuta con DJANGO_DEBUG=True.")
        call_command("crear_grupos")

        User = get_user_model()
        for nombre, grupo, es_admin in [("admin", "Administrador", True), ("bodega", "Bodega", False), ("consulta", "Consulta", False)]:
            user, creado = User.objects.get_or_create(username=nombre, defaults={"is_staff": es_admin, "is_superuser": es_admin})
            if creado:
                user.set_password(options["password"])
                user.save()
            user.groups.add(Group.objects.get(name=grupo))

        for nombre in ["Constructora Norte Ltda.", "Electricidad Sur SpA"]:
            Subcontratista.objects.get_or_create(nombre=nombre)
        for nombre in ["Edificio Plaza", "Bodega Industrial Maipú"]:
            Obra.objects.get_or_create(nombre=nombre)

        demo = [
            ("TAL-001", "Taladro percutor", "Eléctrica", 8000),
            ("ROT-001", "Rotomartillo", "Eléctrica", 12000),
            ("COM-001", "Compactadora", "Maquinaria ligera", 35000),
            ("AND-001", "Andamio modular", "Estructura", 5000),
            ("GEN-001", "Generador 5kW", "Maquinaria ligera", 28000),
        ]
        for codigo, nombre, categoria, tarifa in demo:
            Activo.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "categoria": categoria, "tarifa_diaria": tarifa})

        taladro = Activo.objects.get(codigo="TAL-001")
        if not taladro.planes.exists():
            PlanMantenimiento.objects.create(activo=taladro, descripcion="Revisión de escobillas", cada_dias=90, cada_horas=50)

        self.stdout.write(self.style.SUCCESS(f"Demo lista. Usuarios: admin / bodega / consulta (clave: {options['password']})"))

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import servicios
from .models import Activo, ErrorNegocio, Estado, Obra, PlanMantenimiento, Subcontratista

FIRMA = "data:image/png;base64,iVBORw0KGgo="


class FlujoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("u", password="x")
        self.sub = Subcontratista.objects.create(nombre="Sub")
        self.obra = Obra.objects.create(nombre="Obra")
        self.activo = Activo.objects.create(codigo="T-1", nombre="Taladro", tarifa_diaria=Decimal("10000"))

    def entregar(self):
        return servicios.entregar(
            activo=self.activo, subcontratista=self.sub, obra=self.obra,
            responsable_obra="Juan", firma=FIRMA, usuario=self.user,
        )

    def devolver(self, prestamo, horas="0", danos=False):
        return servicios.devolver(
            prestamo=prestamo, horas_uso=Decimal(horas), hay_danos=danos,
            observaciones="", firma=FIRMA, usuario=self.user,
        )

    def test_entrega_y_devolucion_dejan_historial(self):
        p = self.entregar()
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.estado, Estado.EN_USO)
        self.devolver(p, "5")
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.estado, Estado.DISPONIBLE)
        self.assertEqual(self.activo.horas_uso, Decimal("5"))
        self.assertEqual(self.activo.historial.count(), 2)

    def test_no_se_entrega_dos_veces(self):
        self.entregar()
        with self.assertRaises(ErrorNegocio):
            self.entregar()

    def test_firma_obligatoria(self):
        with self.assertRaises(ErrorNegocio):
            servicios.entregar(activo=self.activo, subcontratista=self.sub, obra=self.obra,
                               responsable_obra="Juan", firma="", usuario=self.user)

    def test_cobro_por_dias_iniciados(self):
        p = self.entregar()
        p.fecha_entrega = timezone.now() - timedelta(hours=49)
        p.save()
        self.assertEqual(p.dias_cobrados, 3)
        self.assertEqual(p.cobro, Decimal("30000"))

    def test_mantenimiento_por_horas_envia_a_mantenimiento_y_se_libera(self):
        plan = PlanMantenimiento.objects.create(activo=self.activo, descripcion="Aceite", cada_horas=Decimal("10"))
        self.devolver(self.entregar(), "12")
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.estado, Estado.MANTENIMIENTO)
        with self.assertRaises(ErrorNegocio):
            self.entregar()
        servicios.completar_mantenimiento(plan=plan, usuario=self.user)
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.estado, Estado.DISPONIBLE)

    def test_baja_es_definitiva(self):
        servicios.cambiar_estado_manual(activo_id=self.activo.pk, nuevo=Estado.BAJA, usuario=self.user, motivo="Obsoleto")
        with self.assertRaises(ErrorNegocio):
            servicios.cambiar_estado_manual(activo_id=self.activo.pk, nuevo=Estado.DISPONIBLE, usuario=self.user, motivo="x")


class PermisosTests(TestCase):
    def test_requiere_login(self):
        r = self.client.get(reverse("activo_lista"))
        self.assertEqual(r.status_code, 302)
        r = self.client.get("/api/activos/")
        self.assertEqual(r.status_code, 403)

    def test_usuario_sin_permisos_recibe_403(self):
        get_user_model().objects.create_user("sinpermisos", password="x")
        self.client.login(username="sinpermisos", password="x")
        self.assertEqual(self.client.get(reverse("activo_lista")).status_code, 403)

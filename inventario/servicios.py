"""Lógica de negocio compartida por las vistas con plantillas y por la API."""
from django.db import transaction
from django.utils import timezone

from .models import Activo, ErrorNegocio, Estado, Prestamo

PREFIJO_FIRMA = "data:image/png;base64,"
MAX_FIRMA = 300_000  # caracteres


def _validar_firma(firma):
    if not firma or not firma.startswith(PREFIJO_FIRMA) or len(firma) > MAX_FIRMA:
        raise ErrorNegocio("Falta la firma del responsable de obra (o no es válida).")


@transaction.atomic
def entregar(*, activo, subcontratista, obra, responsable_obra, firma, usuario):
    _validar_firma(firma)
    activo = Activo.objects.select_for_update().get(pk=activo.pk)
    if activo.estado != Estado.DISPONIBLE:
        raise ErrorNegocio(f"{activo.codigo} no está disponible (estado: {activo.get_estado_display()}).")
    if activo.mantenimiento_vencido:
        raise ErrorNegocio(f"{activo.codigo} tiene un mantenimiento vencido; realízalo antes de entregarlo.")
    prestamo = Prestamo.objects.create(
        activo=activo,
        subcontratista=subcontratista,
        obra=obra,
        responsable_obra=responsable_obra,
        entregado_por=usuario,
        firma_entrega=firma,
        tarifa_diaria=activo.tarifa_diaria,
    )
    activo.cambiar_estado(Estado.EN_USO, usuario, f"Entrega a {subcontratista} en {obra}")
    return prestamo


@transaction.atomic
def devolver(*, prestamo, horas_uso, hay_danos, observaciones, firma, usuario):
    _validar_firma(firma)
    prestamo = Prestamo.objects.select_for_update().get(pk=prestamo.pk)
    if not prestamo.abierto:
        raise ErrorNegocio("Este préstamo ya fue devuelto.")
    activo = Activo.objects.select_for_update().get(pk=prestamo.activo_id)

    prestamo.fecha_devolucion = timezone.now()
    prestamo.recibido_por = usuario
    prestamo.firma_devolucion = firma
    prestamo.horas_uso_periodo = horas_uso
    prestamo.hay_danos = hay_danos
    prestamo.observaciones = observaciones
    prestamo.save()

    activo.horas_uso += horas_uso
    activo.save(update_fields=["horas_uso"])

    if hay_danos:
        activo.cambiar_estado(Estado.MANTENIMIENTO, usuario, "Devuelto con daños")
    elif activo.mantenimiento_vencido:
        activo.cambiar_estado(Estado.MANTENIMIENTO, usuario, "Mantenimiento preventivo vencido")
    else:
        activo.cambiar_estado(Estado.DISPONIBLE, usuario, "Devolución registrada")
    return prestamo


@transaction.atomic
def cambiar_estado_manual(*, activo_id, nuevo, usuario, motivo):
    activo = Activo.objects.select_for_update().get(pk=activo_id)
    if activo.estado == Estado.EN_USO:
        raise ErrorNegocio("El activo está en uso: primero registra su devolución.")
    if nuevo == Estado.EN_USO:
        raise ErrorNegocio("Para dejar un activo en uso registra una entrega.")
    activo.cambiar_estado(nuevo, usuario, motivo)
    return activo


@transaction.atomic
def completar_mantenimiento(*, plan, usuario):
    activo = Activo.objects.select_for_update().get(pk=plan.activo_id)
    plan.ultima_fecha = timezone.localdate()
    plan.ultimas_horas = activo.horas_uso
    plan.save()
    if activo.estado == Estado.MANTENIMIENTO and not activo.mantenimiento_vencido:
        activo.cambiar_estado(Estado.DISPONIBLE, usuario, f"Mantenimiento realizado: {plan.descripcion}")
    return plan

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from . import servicios
from .models import Activo, ErrorNegocio, PlanMantenimiento, Prestamo
from .serializers import (
    ActivoSerializer,
    DevolucionSerializer,
    EntregaSerializer,
    EstadoSerializer,
    PlanSerializer,
    PrestamoSerializer,
)

SIN_BORRAR = ["get", "post", "put", "patch", "head", "options"]


def ejecutar(funcion, **kwargs):
    try:
        return funcion(**kwargs)
    except ErrorNegocio as e:
        raise serializers.ValidationError({"detail": str(e)})


class ActivoViewSet(viewsets.ModelViewSet):
    queryset = Activo.objects.all()
    serializer_class = ActivoSerializer
    http_method_names = SIN_BORRAR

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.query_params.get("estado")
        return qs.filter(estado=estado) if estado else qs

    @action(detail=True, methods=["post"])
    def estado(self, request, pk=None):
        if not request.user.has_perm("inventario.dar_de_baja"):
            raise PermissionDenied()
        activo = self.get_object()
        s = EstadoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        activo = ejecutar(
            servicios.cambiar_estado_manual,
            activo_id=activo.pk,
            nuevo=s.validated_data["estado"],
            usuario=request.user,
            motivo=s.validated_data["motivo"],
        )
        return Response(ActivoSerializer(activo).data)


class PrestamoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Prestamo.objects.select_related("activo", "subcontratista", "obra")
    serializer_class = PrestamoSerializer

    @action(detail=False, methods=["post"])
    def entregar(self, request):
        s = EntregaSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        prestamo = ejecutar(servicios.entregar, usuario=request.user, **s.validated_data)
        return Response(PrestamoSerializer(prestamo).data, status=201)

    @action(detail=True, methods=["post"])
    def devolver(self, request, pk=None):
        if not request.user.has_perm("inventario.change_prestamo"):
            raise PermissionDenied()
        prestamo = self.get_object()
        s = DevolucionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        prestamo = ejecutar(servicios.devolver, prestamo=prestamo, usuario=request.user, **s.validated_data)
        return Response(PrestamoSerializer(prestamo).data)


class PlanViewSet(viewsets.ModelViewSet):
    queryset = PlanMantenimiento.objects.select_related("activo")
    serializer_class = PlanSerializer
    http_method_names = SIN_BORRAR

    @action(detail=True, methods=["post"])
    def completar(self, request, pk=None):
        if not request.user.has_perm("inventario.change_planmantenimiento"):
            raise PermissionDenied()
        plan = servicios.completar_mantenimiento(plan=self.get_object(), usuario=request.user)
        return Response(PlanSerializer(plan).data)

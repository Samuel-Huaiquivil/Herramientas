from rest_framework import serializers

from .models import Activo, Estado, Obra, PlanMantenimiento, Prestamo, Subcontratista


class ActivoSerializer(serializers.ModelSerializer):
    mantenimiento_vencido = serializers.ReadOnlyField()

    class Meta:
        model = Activo
        fields = ["id", "codigo", "nombre", "categoria", "descripcion", "tarifa_diaria", "horas_uso", "estado", "mantenimiento_vencido"]
        read_only_fields = ["estado"]


class PrestamoSerializer(serializers.ModelSerializer):
    dias_cobrados = serializers.ReadOnlyField()
    cobro = serializers.ReadOnlyField()

    class Meta:
        model = Prestamo
        exclude = ["firma_entrega", "firma_devolucion"]
        read_only_fields = [f.name for f in Prestamo._meta.fields]


class EntregaSerializer(serializers.Serializer):
    activo = serializers.PrimaryKeyRelatedField(queryset=Activo.objects.all())
    subcontratista = serializers.PrimaryKeyRelatedField(queryset=Subcontratista.objects.all())
    obra = serializers.PrimaryKeyRelatedField(queryset=Obra.objects.all())
    responsable_obra = serializers.CharField(max_length=120)
    firma = serializers.CharField()


class DevolucionSerializer(serializers.Serializer):
    horas_uso = serializers.DecimalField(max_digits=8, decimal_places=1, min_value=0)
    hay_danos = serializers.BooleanField(default=False)
    observaciones = serializers.CharField(allow_blank=True, default="")
    firma = serializers.CharField()


class EstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=[c for c in Estado.choices if c[0] != Estado.EN_USO])
    motivo = serializers.CharField(max_length=200)


class PlanSerializer(serializers.ModelSerializer):
    proxima_fecha = serializers.ReadOnlyField()
    horas_restantes = serializers.ReadOnlyField()
    vencido = serializers.ReadOnlyField()

    class Meta:
        model = PlanMantenimiento
        fields = ["id", "activo", "descripcion", "cada_dias", "cada_horas", "ultima_fecha", "vigente", "proxima_fecha", "horas_restantes", "vencido"]

    def validate(self, attrs):
        dias = attrs.get("cada_dias", getattr(self.instance, "cada_dias", None))
        horas = attrs.get("cada_horas", getattr(self.instance, "cada_horas", None))
        if not dias and not horas:
            raise serializers.ValidationError("Indica cada_dias y/o cada_horas.")
        return attrs

import math
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ErrorNegocio(Exception):
    """Regla de negocio incumplida (se muestra al usuario tal cual)."""


class Estado(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    EN_USO = "EN_USO", "En uso"
    MANTENIMIENTO = "MANTENIMIENTO", "Mantenimiento"
    BAJA = "BAJA", "Dado de baja"


class Subcontratista(models.Model):
    nombre = models.CharField(max_length=120)
    rut = models.CharField(max_length=15, blank=True)
    contacto = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Obra(models.Model):
    nombre = models.CharField(max_length=120)
    direccion = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Activo(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    categoria = models.CharField(max_length=60, blank=True)
    descripcion = models.TextField(blank=True)
    tarifa_diaria = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    horas_uso = models.DecimalField(max_digits=10, decimal_places=1, default=0, validators=[MinValueValidator(0)])
    # editable=False: el estado solo cambia mediante cambiar_estado() para dejar historial
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.DISPONIBLE, editable=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["codigo"]
        permissions = [("dar_de_baja", "Puede cambiar el estado manualmente y dar de baja")]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def mantenimiento_vencido(self):
        return any(p.vencido for p in self.planes.filter(vigente=True))

    def cambiar_estado(self, nuevo, usuario=None, motivo=""):
        """Único punto de cambio de estado; guarda trazabilidad."""
        if nuevo == self.estado:
            return
        if self.estado == Estado.BAJA:
            raise ErrorNegocio("Un activo dado de baja no puede cambiar de estado.")
        HistorialEstado.objects.create(
            activo=self, anterior=self.estado, nuevo=nuevo, usuario=usuario, motivo=motivo
        )
        self.estado = nuevo
        self.save(update_fields=["estado"])


class HistorialEstado(models.Model):
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="historial")
    anterior = models.CharField(max_length=20, choices=Estado.choices)
    nuevo = models.CharField(max_length=20, choices=Estado.choices)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    motivo = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.activo.codigo}: {self.anterior} -> {self.nuevo}"


class Prestamo(models.Model):
    """Entrega de un activo a un subcontratista y su devolución."""

    activo = models.ForeignKey(Activo, on_delete=models.PROTECT, related_name="prestamos")
    subcontratista = models.ForeignKey(Subcontratista, on_delete=models.PROTECT, related_name="prestamos")
    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name="prestamos")
    responsable_obra = models.CharField(max_length=120)
    entregado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    fecha_entrega = models.DateTimeField(default=timezone.now)
    firma_entrega = models.TextField()  # PNG en base64 (data URL); firma simulada
    tarifa_diaria = models.DecimalField(max_digits=10, decimal_places=2)  # copia de la tarifa al entregar

    fecha_devolucion = models.DateTimeField(null=True, blank=True)
    recibido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    firma_devolucion = models.TextField(blank=True)
    horas_uso_periodo = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    hay_danos = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha_entrega"]
        constraints = [
            models.UniqueConstraint(
                fields=["activo"],
                condition=Q(fecha_devolucion__isnull=True),
                name="un_prestamo_abierto_por_activo",
            )
        ]

    def __str__(self):
        return f"Préstamo #{self.pk} {self.activo.codigo}"

    @property
    def abierto(self):
        return self.fecha_devolucion is None

    @property
    def dias_cobrados(self):
        """Días corridos iniciados, mínimo 1."""
        fin = self.fecha_devolucion or timezone.now()
        segundos = (fin - self.fecha_entrega).total_seconds()
        return max(1, math.ceil(segundos / 86400))

    @property
    def cobro(self):
        return self.tarifa_diaria * self.dias_cobrados


class PlanMantenimiento(models.Model):
    """Mantenimiento preventivo por días y/o por horas de uso."""

    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="planes")
    descripcion = models.CharField(max_length=150)
    cada_dias = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)], help_text="Cada cuántos días")
    cada_horas = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(Decimal("0.1"))], help_text="Cada cuántas horas de uso")
    ultima_fecha = models.DateField(default=timezone.localdate, help_text="Fecha del último mantenimiento")
    ultimas_horas = models.DecimalField(max_digits=10, decimal_places=1, default=0, editable=False)
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ["activo__codigo", "descripcion"]

    def __str__(self):
        return f"{self.activo.codigo}: {self.descripcion}"

    def clean(self):
        if not self.cada_dias and not self.cada_horas:
            raise ValidationError("Indica cada cuántos días y/o cada cuántas horas se repite el mantenimiento.")

    def save(self, *args, **kwargs):
        if self._state.adding and not self.ultimas_horas:
            self.ultimas_horas = self.activo.horas_uso
        super().save(*args, **kwargs)

    @property
    def proxima_fecha(self):
        return self.ultima_fecha + timedelta(days=self.cada_dias) if self.cada_dias else None

    @property
    def dias_restantes(self):
        f = self.proxima_fecha
        return (f - timezone.localdate()).days if f else None

    @property
    def horas_restantes(self):
        if not self.cada_horas:
            return None
        return self.cada_horas - (self.activo.horas_uso - self.ultimas_horas)

    @property
    def vencido(self):
        d, h = self.dias_restantes, self.horas_restantes
        return (d is not None and d <= 0) or (h is not None and h <= 0)

    @property
    def por_vencer(self):
        d, h = self.dias_restantes, self.horas_restantes
        return not self.vencido and ((d is not None and d <= 7) or (h is not None and h <= 10))

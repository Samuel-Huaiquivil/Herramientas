from django import forms

from .models import Activo, Estado, Obra, PlanMantenimiento, Subcontratista


class ActivoForm(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ["codigo", "nombre", "categoria", "descripcion", "tarifa_diaria", "horas_uso"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


class EstadoForm(forms.Form):
    estado = forms.ChoiceField(choices=[c for c in Estado.choices if c[0] != Estado.EN_USO])
    motivo = forms.CharField(max_length=200)


class EntregaForm(forms.Form):
    activo = forms.ModelChoiceField(queryset=Activo.objects.filter(estado=Estado.DISPONIBLE))
    subcontratista = forms.ModelChoiceField(queryset=Subcontratista.objects.all())
    obra = forms.ModelChoiceField(queryset=Obra.objects.all())
    responsable_obra = forms.CharField(max_length=120, label="Responsable de obra")
    firma = forms.CharField(widget=forms.HiddenInput)


class DevolucionForm(forms.Form):
    horas_uso = forms.DecimalField(min_value=0, max_digits=8, decimal_places=1, initial=0, label="Horas de uso en el período")
    hay_danos = forms.BooleanField(required=False, label="Devuelto con daños")
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    firma = forms.CharField(widget=forms.HiddenInput)


class PlanForm(forms.ModelForm):
    class Meta:
        model = PlanMantenimiento
        fields = ["activo", "descripcion", "cada_dias", "cada_horas", "ultima_fecha"]
        widgets = {"ultima_fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["activo"].queryset = Activo.objects.exclude(estado=Estado.BAJA)

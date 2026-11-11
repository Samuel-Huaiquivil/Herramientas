from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView

from . import servicios
from .forms import ActivoForm, DevolucionForm, EntregaForm, EstadoForm, PlanForm
from .models import Activo, ErrorNegocio, Estado, PlanMantenimiento, Prestamo


class Permiso(LoginRequiredMixin, PermissionRequiredMixin):
    """Exige sesión iniciada y el permiso indicado en permission_required (403 si no lo tiene)."""


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "inventario/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        conteos = dict(Activo.objects.order_by().values_list("estado").annotate(n=Count("id")))
        ctx["conteos"] = [(valor, label, conteos.get(valor, 0)) for valor, label in Estado.choices]
        planes = list(
            PlanMantenimiento.objects.filter(vigente=True)
            .exclude(activo__estado=Estado.BAJA)
            .select_related("activo")
        )
        ctx["vencidos"] = [p for p in planes if p.vencido]
        ctx["por_vencer"] = [p for p in planes if p.por_vencer]
        ctx["abiertos"] = Prestamo.objects.filter(fecha_devolucion__isnull=True).select_related(
            "activo", "subcontratista", "obra"
        )[:10]
        return ctx


# ---------- Activos ----------
class ActivoList(Permiso, ListView):
    permission_required = "inventario.view_activo"
    model = Activo
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.GET.get("estado", "")
        q = self.request.GET.get("q", "").strip()
        if estado in Estado.values:
            qs = qs.filter(estado=estado)
        if q:
            qs = qs.filter(Q(codigo__icontains=q) | Q(nombre__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["estados"] = Estado.choices
        ctx["estado_actual"] = self.request.GET.get("estado", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class ActivoDetail(Permiso, DetailView):
    permission_required = "inventario.view_activo"
    model = Activo

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        a = self.object
        ctx["historial"] = a.historial.select_related("usuario")[:20]
        ctx["prestamos"] = a.prestamos.select_related("subcontratista", "obra")[:10]
        ctx["planes"] = a.planes.filter(vigente=True)
        ctx["form_estado"] = EstadoForm()
        return ctx


class ActivoCreate(Permiso, CreateView):
    permission_required = "inventario.add_activo"
    model = Activo
    form_class = ActivoForm
    template_name = "inventario/form.html"
    extra_context = {"titulo": "Nuevo activo"}

    def get_success_url(self):
        return reverse_lazy("activo_detalle", args=[self.object.pk])


class ActivoUpdate(Permiso, UpdateView):
    permission_required = "inventario.change_activo"
    model = Activo
    form_class = ActivoForm
    template_name = "inventario/form.html"
    extra_context = {"titulo": "Editar activo"}

    def get_success_url(self):
        return reverse_lazy("activo_detalle", args=[self.object.pk])


class ActivoEstado(Permiso, View):
    permission_required = "inventario.dar_de_baja"

    def post(self, request, pk):
        activo = get_object_or_404(Activo, pk=pk)
        form = EstadoForm(request.POST)
        if form.is_valid():
            try:
                servicios.cambiar_estado_manual(
                    activo_id=activo.pk,
                    nuevo=form.cleaned_data["estado"],
                    usuario=request.user,
                    motivo=form.cleaned_data["motivo"],
                )
                messages.success(request, "Estado actualizado.")
            except ErrorNegocio as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Indica el nuevo estado y el motivo.")
        return redirect("activo_detalle", pk=activo.pk)


# ---------- Préstamos ----------
class PrestamoList(Permiso, ListView):
    permission_required = "inventario.view_prestamo"
    paginate_by = 25
    queryset = Prestamo.objects.select_related("activo", "subcontratista", "obra")


class PrestamoDetail(Permiso, DetailView):
    permission_required = "inventario.view_prestamo"
    queryset = Prestamo.objects.select_related("activo", "subcontratista", "obra", "entregado_por", "recibido_por")


class EntregaView(Permiso, FormView):
    permission_required = "inventario.add_prestamo"
    form_class = EntregaForm
    template_name = "inventario/entrega.html"

    def get_initial(self):
        return {"activo": self.request.GET.get("activo")}

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            prestamo = servicios.entregar(
                activo=d["activo"],
                subcontratista=d["subcontratista"],
                obra=d["obra"],
                responsable_obra=d["responsable_obra"],
                firma=d["firma"],
                usuario=self.request.user,
            )
        except ErrorNegocio as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Entrega registrada.")
        return redirect("prestamo_detalle", pk=prestamo.pk)


class DevolucionView(Permiso, FormView):
    permission_required = "inventario.change_prestamo"
    form_class = DevolucionForm
    template_name = "inventario/devolucion.html"

    def dispatch(self, request, *args, **kwargs):
        self.prestamo = get_object_or_404(Prestamo, pk=kwargs["pk"], fecha_devolucion__isnull=True)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prestamo"] = self.prestamo
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            servicios.devolver(
                prestamo=self.prestamo,
                horas_uso=d["horas_uso"],
                hay_danos=d["hay_danos"],
                observaciones=d["observaciones"],
                firma=d["firma"],
                usuario=self.request.user,
            )
        except ErrorNegocio as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Devolución registrada.")
        return redirect("prestamo_detalle", pk=self.prestamo.pk)


# ---------- Mantenimientos ----------
class PlanList(Permiso, ListView):
    permission_required = "inventario.view_planmantenimiento"
    template_name = "inventario/plan_list.html"
    queryset = PlanMantenimiento.objects.filter(vigente=True).exclude(activo__estado=Estado.BAJA).select_related("activo")


class PlanCreate(Permiso, CreateView):
    permission_required = "inventario.add_planmantenimiento"
    form_class = PlanForm
    model = PlanMantenimiento
    template_name = "inventario/form.html"
    success_url = reverse_lazy("plan_lista")
    extra_context = {"titulo": "Nuevo plan de mantenimiento"}


class PlanCompletar(Permiso, View):
    permission_required = "inventario.change_planmantenimiento"

    def post(self, request, pk):
        plan = get_object_or_404(PlanMantenimiento, pk=pk)
        servicios.completar_mantenimiento(plan=plan, usuario=request.user)
        messages.success(request, f"Mantenimiento registrado: {plan}.")
        return redirect("plan_lista")

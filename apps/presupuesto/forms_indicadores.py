# apps/presupuesto/forms_indicadores.py
from django import forms
from .models.indicadores import (
    MetaBD, MetaProyectoBD, Indicador,
    ImpactoActividadIndicador
)
from .models.core import Proyecto
from django.utils import timezone
# --- Crear Meta ---
class MetaForm(forms.ModelForm):
    class Meta:
        model = MetaBD
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control",
                                             "placeholder": "Nombre de la meta"})
        }

# --- Asignar Meta a Proyecto (meta_proyecto) ---
class MetaProyectoForm(forms.ModelForm):
    proyecto = forms.ModelChoiceField(
        queryset=Proyecto.objects.order_by("codigo"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    meta = forms.ModelChoiceField(
        queryset=MetaBD.objects.order_by("nombre"),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = MetaProyectoBD
        fields = ["proyecto", "meta"]

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # ✅ Etiqueta legible para proyectos
        def _proj_label(p: Proyecto):
            dep = getattr(p.subgrupo.dependencia, "nombre", "") if getattr(p, "subgrupo", None) else ""
            sub = getattr(p.subgrupo, "nombre", "")
            left = (p.codigo or p.id)
            right = (p.nombre or "").strip() or (p.nombre_ci or "").strip()
            extras = f" (Subgrupo: {sub})" if sub else ""
            return f"{left} — {right}{extras}".strip(" —")

        self.fields["proyecto"].label_from_instance = _proj_label

        # ✅ Etiqueta legible para metas
        self.fields["meta"].label_from_instance = lambda m: f"[{m.codigo}] {m.nombre}"

        # ✅ Prefill por ?proyecto=<id> (UX)
        if request and (pid := request.GET.get("proyecto")):
            try:
                self.fields["proyecto"].initial = Proyecto.objects.only("id").get(id=pid).id
            except Proyecto.DoesNotExist:
                pass

    # ✅ Evita duplicados meta↔proyecto
    def clean(self):
        cleaned = super().clean()
        p = cleaned.get("proyecto")
        m = cleaned.get("meta")
        if p and m and MetaProyectoBD.objects.filter(proyecto=p, meta=m).exists():
            self.add_error(None, "Esta meta ya está asignada a este proyecto.")
        return cleaned

# --- Crear Indicador (ya lo tenías, lo dejo completo) ---
class IndicadorForm(forms.ModelForm):
    meta_proyecto = forms.ModelChoiceField(
        queryset=MetaProyectoBD.objects.none(),
        label="Meta de Proyecto",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Indicador
        fields = ["meta_proyecto", "nombre", "tipo", "unidad", "linea_base", "valor_meta", "formula"]

    def __init__(self, *args, **kwargs):
        proyecto_id = kwargs.pop("proyecto_id", None)  # <<--- lo recibimos
        super().__init__(*args, **kwargs)

        qs = MetaProyectoBD.objects.select_related("meta", "proyecto")
        if proyecto_id:
            qs = qs.filter(proyecto_id=proyecto_id)
        self.fields["meta_proyecto"].queryset = qs.order_by("meta__codigo")

        # etiqueta legible
        self.fields["meta_proyecto"].label_from_instance = lambda mp: (
            f"[{mp.meta_id}] {getattr(mp.meta, 'nombre', '')} — Proy {(mp.proyecto.codigo or mp.proyecto_id)}"
        )
# --- Declarar impacto de una actividad sobre un indicador ---
class ImpactoActividadForm(forms.ModelForm):
    class Meta:
        model = ImpactoActividadIndicador
        fields = ["actividad_plan", "indicador", "cantidad_aportada", "evidencia_url"]

    def save(self, user=None, commit=True):
        obj = super().save(commit=False)
        if not obj.registrado_en:
            obj.registrado_en = timezone.now()
        if user and not obj.registrado_por:
            # si tu User no es int, ajusta según tu esquema
            obj.registrado_por = getattr(user, "id", None)
        if commit:
            obj.save()
        return obj
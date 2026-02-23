# apps/presupuesto/forms_cdp.py
from django import forms
from django.db import connection, IntegrityError
from django.db.models.functions import ExtractYear

from decimal import Decimal  # si lo usas en otros forms
from apps.presupuesto.models.sql import Cdp
from apps.presupuesto.models.financiero import ProyectoInversionItem
from .models.core_catalogos import Programa, Tematica, Vigencia, Objetivo


# -----------------------------
# 1) Crear Temática rápida
# -----------------------------
class TematicaQuickForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre de la temática",
        max_length=256,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    def save(self):
        data = self.cleaned_data
        # Autogenerar codigo = MAX(codigo)+1 (BD externa sin secuencia)
        with connection.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(codigo),0)+1 FROM tematica")
            codigo = cur.fetchone()[0]

        t = Tematica(codigo=codigo, nombre=data["nombre"])
        try:
            t.save(force_insert=True)  # managed=False -> forzar INSERT
        except IntegrityError:
            # Reintento simple ante colisión improbable
            with connection.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(codigo),0)+1 FROM tematica")
                codigo = cur.fetchone()[0]
            t.codigo = codigo
            t.save(force_insert=True)
        return t


# -----------------------------
# 2) Crear Objetivo
# -----------------------------
class ObjetivoCreateForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre del Objetivo",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    descripcion = forms.CharField(
        label="Descripción (opcional, si existe la columna)",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3})
    )

    def save(self):
        nombre = self.cleaned_data["nombre"].strip()
        descripcion = (self.cleaned_data.get("descripcion") or "").strip()

        # Detectar si la columna 'descripcion' existe
        with connection.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='objetivo'
                  AND column_name='descripcion'
                LIMIT 1
            """)
            has_descripcion = cur.fetchone() is not None

        with connection.cursor() as cur:
            if has_descripcion and descripcion:
                cur.execute(
                    "INSERT INTO objetivo (nombre, descripcion) VALUES (%s, %s) RETURNING id",
                    [nombre, descripcion]
                )
            else:
                cur.execute(
                    "INSERT INTO objetivo (nombre) VALUES (%s) RETURNING id",
                    [nombre]
                )
            new_id = cur.fetchone()[0]
        return new_id


# -----------------------------
# 3) ProgramaForm (vigencia muestra AÑO)
# -----------------------------
class ProgramaForm(forms.ModelForm):
    objetivo = forms.ModelChoiceField(
        label="Objetivo (opcional)",
        queryset=Objetivo.objects.all().order_by("nombre"),
        required=False,
        empty_label="— Sin objetivo —",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    tematica = forms.ModelChoiceField(
        label="Temática (opcional)",
        queryset=Tematica.objects.all().order_by("nombre"),
        required=False,
        empty_label="---------",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_tematica"})
    )
    # El queryset se define en __init__ para poder anotar/ordenar
    vigencia = forms.ModelChoiceField(
        label="Vigencia",
        queryset=Vigencia.objects.none(),
        required=True,
        empty_label="— Selecciona vigencia —",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Programa
        fields = ["nombre", "descripcion"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del programa"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción"}),
        }
        labels = {
            "nombre": "Nombre",
            "descripcion": "Descripción (opcional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si tu modelo Vigencia tiene 'codigo' mapeado (año), úsalo; si no, anota desde fecha_inicio
        try:
            # Intento ordenar por 'codigo' (cuando codigo = año)
            qs = Vigencia.objects.only("id", "codigo", "fecha_inicio").order_by("-codigo")
            # Forzar evaluación de un elemento para detectar AttributeError tarde
            _ = qs[:1]
            self.fields["vigencia"].queryset = qs
            self.fields["vigencia"].label_from_instance = lambda v: str(getattr(v, "codigo", None) or v.fecha_inicio.year)
        except Exception:
            # Fallback: anotar año desde fecha_inicio
            qs = Vigencia.objects.annotate(anio=ExtractYear("fecha_inicio")).order_by("-anio")
            self.fields["vigencia"].queryset = qs
            self.fields["vigencia"].label_from_instance = lambda v: str(v.anio)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # mapear selects → columnas reales (FKs)
        instance.vigencia = self.cleaned_data["vigencia"]
        instance.objetivo = self.cleaned_data.get("objetivo") or None
        instance.tematica_codigo = self.cleaned_data.get("tematica") or None
        # columna legacy ya no se usa
        instance.tematica_legacy = None
        if commit:
            instance.save()
        return instance


# -----------------------------
# 4) CDP / Asignación
# -----------------------------
class CdpForm(forms.ModelForm):
    class Meta:
        model = Cdp
        fields = ["numero", "valor", "fecha", "descripcion"]
        labels = {
            "numero": "Número de CDP",
            "valor": "Valor",
            "fecha": "Fecha",
            "descripcion": "Descripción",
        }
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class AsignarCdpForm(forms.ModelForm):
    """
    Selecciona un CDP para un item (proyecto hijo).
    """
    cdp = forms.ModelChoiceField(
        queryset=Cdp.objects.all().order_by("-fecha"),
        required=True,
        label="CDP",
        help_text="Selecciona el CDP que financiará este proyecto hijo.",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = ProyectoInversionItem
        fields = ["cdp"]

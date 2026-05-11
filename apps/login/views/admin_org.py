# apps/login/views/admin_org.py
"""
CRUD para entidades organizativas:
  - PR-F: Dependencia, Subgrupo, Funcionario.
  - PR-H2: Organización, Proveedor, Beneficiario.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render

# Tamaño de página por defecto para listados largos (P1).
PAGE_SIZE = 25

from apps.login.decorators import modulo_required
from apps.login.models.funcionario import (
    Dependencia, Subgrupo, Funcionario, TipoFuncionario, Cargo
)
from apps.login.models.persona import Persona
from apps.login.models.contratos import (
    Organizacion, Proveedor, Beneficiario,
)


# ──────────────────────────────────────────────────────────────
# Forms
# ──────────────────────────────────────────────────────────────

class DependenciaForm(forms.ModelForm):
    class Meta:
        model = Dependencia
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Secretaría de Cultura",
                "maxlength": "255",
            }),
        }


class SubgrupoForm(forms.ModelForm):
    class Meta:
        model = Subgrupo
        fields = ["nombre", "dependencia"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Programa Cultural",
            }),
            "dependencia": forms.Select(attrs={"class": "form-select"}),
        }


class FuncionarioForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Persona: queryset vacío (se llena vía Select2 AJAX). Si edita, incluir la actual.
        if self.instance and self.instance.pk and self.instance.persona_id:
            self.fields["persona"].queryset = Persona.objects.filter(pk=self.instance.persona_id)
        else:
            self.fields["persona"].queryset = Persona.objects.none()

    class Meta:
        model = Funcionario
        fields = ["persona", "tipo_funcionario", "dependencia", "subgrupo",
                  "cargo", "fecha_ingreso", "activo", "observaciones"]
        widgets = {
            "persona": forms.Select(attrs={
                "class": "form-select select2-persona",
                "data-excluir-funcionarios": "1",
            }),
            "tipo_funcionario": forms.Select(attrs={"class": "form-select"}),
            "dependencia": forms.Select(attrs={"class": "form-select"}),
            "subgrupo": forms.Select(attrs={"class": "form-select"}),
            "cargo": forms.Select(attrs={"class": "form-select"}),
            "fecha_ingreso": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
            }),
        }


# ──────────────────────────────────────────────────────────────
# CRUD Dependencia
# ──────────────────────────────────────────────────────────────

@login_required
@modulo_required('org_admin')
def dependencias_list(request):
    qs = (
        Dependencia.objects
        .annotate(subgrupos_count=Count("subgrupos"))
        .order_by("nombre")
    )
    return render(request, "admin_org/dependencias_list.html", {"rows": qs})


@login_required
@modulo_required('org_admin')
def dependencia_nueva(request):
    if request.method == "POST":
        form = DependenciaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Dependencia creada.")
            return redirect("login:dependencias_list")
    else:
        form = DependenciaForm()
    return render(request, "admin_org/dependencia_form.html",
                  {"form": form, "edit": False})


@login_required
@modulo_required('org_admin')
def dependencia_editar(request, pk):
    obj = get_object_or_404(Dependencia, pk=pk)
    if request.method == "POST":
        form = DependenciaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Dependencia actualizada.")
            return redirect("login:dependencias_list")
    else:
        form = DependenciaForm(instance=obj)
    return render(request, "admin_org/dependencia_form.html",
                  {"form": form, "edit": True, "obj": obj})


# ──────────────────────────────────────────────────────────────
# CRUD Subgrupo
# ──────────────────────────────────────────────────────────────

@login_required
@modulo_required('org_admin')
def subgrupos_list(request):
    qs = (
        Subgrupo.objects
        .select_related("dependencia")
        .order_by("dependencia__nombre", "nombre")
    )
    return render(request, "admin_org/subgrupos_list.html", {"rows": qs})


@login_required
@modulo_required('org_admin')
def subgrupo_nuevo(request):
    if request.method == "POST":
        form = SubgrupoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subgrupo creado.")
            return redirect("login:subgrupos_list")
    else:
        form = SubgrupoForm()
    return render(request, "admin_org/subgrupo_form.html",
                  {"form": form, "edit": False})


@login_required
@modulo_required('org_admin')
def subgrupo_editar(request, pk):
    obj = get_object_or_404(Subgrupo, pk=pk)
    if request.method == "POST":
        form = SubgrupoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Subgrupo actualizado.")
            return redirect("login:subgrupos_list")
    else:
        form = SubgrupoForm(instance=obj)
    return render(request, "admin_org/subgrupo_form.html",
                  {"form": form, "edit": True, "obj": obj})


# ──────────────────────────────────────────────────────────────
# CRUD Funcionario
# ──────────────────────────────────────────────────────────────

@login_required
@modulo_required('org_admin')
def funcionarios_list(request):
    qs = (
        Funcionario.objects
        .select_related("persona", "dependencia", "subgrupo", "cargo")
        .filter(activo=True)
        .order_by("persona__apellido1", "persona__nombre1")
    )
    return render(request, "admin_org/funcionarios_list.html", {"rows": qs})


@login_required
@modulo_required('org_admin')
def funcionario_nuevo(request):
    if request.method == "POST":
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionario creado.")
            return redirect("login:funcionarios_list")
    else:
        form = FuncionarioForm(initial={"activo": True})
    return render(request, "admin_org/funcionario_form.html",
                  {"form": form, "edit": False})


@login_required
@modulo_required('org_admin')
def funcionario_editar(request, pk):
    obj = get_object_or_404(Funcionario, pk=pk)
    if request.method == "POST":
        form = FuncionarioForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionario actualizado.")
            return redirect("login:funcionarios_list")
    else:
        form = FuncionarioForm(instance=obj)
    return render(request, "admin_org/funcionario_form.html",
                  {"form": form, "edit": True, "obj": obj})


# ══════════════════════════════════════════════════════════════
#   PR-H2: Organización · Proveedor · Beneficiario
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# Forms
# ──────────────────────────────────────────────────────────────

class OrganizacionForm(forms.ModelForm):
    class Meta:
        model = Organizacion
        fields = ["nombre", "nit", "tipo", "correo", "telefono"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Razón social o nombre comercial",
            }),
            "nit": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "NIT con dígito de verificación",
            }),
            "tipo": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: ESAL, Pública, S.A.S, Cooperativa",
            }),
            "correo": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
        }


class ProveedorForm(forms.ModelForm):
    TIPO_PERSONA_CHOICES = [
        ("NATURAL", "Persona Natural"),
        ("JURIDICA", "Persona Jurídica"),
    ]
    tipo_persona = forms.ChoiceField(
        choices=TIPO_PERSONA_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )

    class Meta:
        model = Proveedor
        fields = ["nombre", "nit", "tipo_persona", "direccion",
                  "telefono", "correo", "contacto_persona", "organizacion"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "nit": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "correo": forms.EmailInput(attrs={"class": "form-control"}),
            "contacto_persona": forms.Select(attrs={"class": "form-select"}),
            "organizacion": forms.Select(attrs={"class": "form-select"}),
        }


class BeneficiarioForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.persona_id:
            self.fields["persona"].queryset = Persona.objects.filter(pk=self.instance.persona_id)
        else:
            self.fields["persona"].queryset = Persona.objects.none()
        if self.instance and self.instance.pk and self.instance.organizacion_id:
            self.fields["organizacion"].queryset = Organizacion.objects.filter(pk=self.instance.organizacion_id)
        else:
            self.fields["organizacion"].queryset = Organizacion.objects.none()

    class Meta:
        model = Beneficiario
        fields = ["tipo", "persona", "proveedor", "organizacion",
                  "tipo_documento", "numero_documento", "nombre_legal",
                  "correo", "telefono", "direccion", "activo"]
        widgets = {
            "tipo": forms.Select(attrs={
                "class": "form-select",
                "id": "id_beneficiario_tipo",
            }),
            "persona": forms.Select(attrs={
                "class": "form-select select2-persona",
                "data-excluir-funcionarios": "1",
            }),
            "proveedor": forms.Select(attrs={"class": "form-select"}),
            "organizacion": forms.Select(attrs={"class": "form-select select2-organizacion"}),
            "tipo_documento": forms.Select(attrs={"class": "form-select"}),
            "numero_documento": forms.TextInput(attrs={"class": "form-control"}),
            "nombre_legal": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Razón social o nombre completo",
            }),
            "correo": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        # Exactamente uno de los 3 FKs debe estar lleno según tipo.
        if tipo == "PERSONA":
            if not cleaned.get("persona"):
                raise forms.ValidationError(
                    "Tipo PERSONA requiere seleccionar Persona.")
            cleaned["proveedor"] = None
            cleaned["organizacion"] = None
            # Validación adicional: la persona NO debe ser ya un funcionario activo
            persona = cleaned.get("persona")
            if Funcionario.objects.filter(persona=persona, activo=True).exists():
                raise forms.ValidationError(
                    "Esta persona es funcionario activo. Los funcionarios "
                    "no pueden ser beneficiarios de contratos.")
        elif tipo == "ORGANIZACION":
            if not cleaned.get("organizacion"):
                raise forms.ValidationError(
                    "Tipo ORGANIZACION requiere seleccionar Organización.")
            cleaned["persona"] = None
            cleaned["proveedor"] = None
        elif tipo == "PROVEEDOR":
            if not cleaned.get("proveedor"):
                raise forms.ValidationError(
                    "Tipo PROVEEDOR requiere seleccionar Proveedor.")
            cleaned["persona"] = None
            cleaned["organizacion"] = None
        return cleaned


# ──────────────────────────────────────────────────────────────
# CRUD Organización
# ──────────────────────────────────────────────────────────────

@login_required
@modulo_required('org_admin')
def organizaciones_list(request):
    qs = Organizacion.objects.order_by("nombre")
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "admin_org/organizaciones_list.html", {
        "rows": page_obj.object_list,
        "page_obj": page_obj,
    })


@login_required
@modulo_required('org_admin')
def organizacion_nueva(request):
    if request.method == "POST":
        form = OrganizacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Organización creada.")
            return redirect("login:organizaciones_list")
    else:
        form = OrganizacionForm()
    return render(request, "admin_org/organizacion_form.html",
                  {"form": form, "edit": False})


@login_required
@modulo_required('org_admin')
def organizacion_editar(request, pk):
    obj = get_object_or_404(Organizacion, pk=pk)
    if request.method == "POST":
        form = OrganizacionForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Organización actualizada.")
            return redirect("login:organizaciones_list")
    else:
        form = OrganizacionForm(instance=obj)
    return render(request, "admin_org/organizacion_form.html",
                  {"form": form, "edit": True, "obj": obj})


# ──────────────────────────────────────────────────────────────
# CRUD Proveedor
# ──────────────────────────────────────────────────────────────

@login_required
@modulo_required('org_admin')
def proveedores_list(request):
    qs = (
        Proveedor.objects
        .select_related("organizacion", "contacto_persona")
        .order_by("nombre")
    )
    return render(request, "admin_org/proveedores_list.html", {"rows": qs})


@login_required
@modulo_required('org_admin')
def proveedor_nuevo(request):
    """
    Crea un Proveedor nuevo. Desde N2 (2026-04-26) la tabla 'proveedor'
    tiene secuencia 'proveedor_id_seq', así que basta con form.save().
    """
    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Proveedor creado.")
                return redirect("login:proveedores_list")
            except IntegrityError as e:
                messages.error(request, f"No se pudo crear el proveedor: {e}")
    else:
        form = ProveedorForm()
    return render(request, "admin_org/proveedor_form.html",
                  {"form": form, "edit": False})


@login_required
@modulo_required('org_admin')
def proveedor_editar(request, pk):
    obj = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        form = ProveedorForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor actualizado.")
            return redirect("login:proveedores_list")
    else:
        form = ProveedorForm(instance=obj)
    return render(request, "admin_org/proveedor_form.html",
                  {"form": form, "edit": True, "obj": obj})


# ──────────────────────────────────────────────────────────────
# CRUD Beneficiario
# ──────────────────────────────────────────────────────────────

@login_required
@modulo_required('org_admin')
def beneficiarios_list(request):
    """Lista beneficiarios activos. Filtro opcional ?tipo=PERSONA|ORGANIZACION|PROVEEDOR."""
    qs = (
        Beneficiario.objects
        .select_related("persona", "proveedor", "organizacion", "tipo_documento")
        .filter(activo=True)
    )
    tipo_filter = (request.GET.get("tipo") or "").strip().upper()
    if tipo_filter in {"PERSONA", "ORGANIZACION", "PROVEEDOR"}:
        qs = qs.filter(tipo=tipo_filter)
    qs = qs.order_by("tipo", "nombre_legal")

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Preserva el filtro 'tipo' al navegar entre páginas.
    qs_extra = f"&tipo={tipo_filter}" if tipo_filter else ""

    return render(request, "admin_org/beneficiarios_list.html", {
        "rows": page_obj.object_list,
        "page_obj": page_obj,
        "qs": qs_extra,
        "tipo_filter": tipo_filter,
    })


@login_required
@modulo_required('org_admin')
def beneficiario_nuevo(request):
    if request.method == "POST":
        form = BeneficiarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Beneficiario creado.")
            return redirect("login:beneficiarios_list")
    else:
        form = BeneficiarioForm(initial={"activo": True, "tipo": "PERSONA"})
    return render(request, "admin_org/beneficiario_form.html",
                  {"form": form, "edit": False})


@login_required
@modulo_required('org_admin')
def beneficiario_editar(request, pk):
    obj = get_object_or_404(Beneficiario, pk=pk)
    if request.method == "POST":
        form = BeneficiarioForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Beneficiario actualizado.")
            return redirect("login:beneficiarios_list")
    else:
        form = BeneficiarioForm(instance=obj)
    return render(request, "admin_org/beneficiario_form.html",
                  {"form": form, "edit": True, "obj": obj})

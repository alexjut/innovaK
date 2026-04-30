"""Vistas CRUD de roles dinámicos (N15 PR-2).

URLs bajo `/org/roles/`. Solo accesible por Admin (vía group_required
hasta que PR N15-3 migre a modulo_required("roles")).

Decisiones aplicadas:
- 4a: Solo el rol con `es_protegido=True` (Admin) está protegido.
- 2a: Bypass is_superuser implícito en el decorador.

Cada acción de escritura llama `invalidar_cache_global()` para que el
sidebar dinámico se refresque al instante para todos los usuarios.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.login.decorators import group_required
from apps.login.models.permisos import Modulo, RolModulo, RolMeta
from apps.login.services.permisos import invalidar_cache_global

User = get_user_model()


class RolForm(forms.Form):
    """Form simple de creación/edición de rol (auth_group + rol_meta)."""
    nombre = forms.CharField(
        max_length=150, label="Nombre del rol",
        widget=forms.TextInput(attrs={"class": "form-control",
                                      "placeholder": "ej. CoordinadorSalud"}),
    )
    descripcion = forms.CharField(
        required=False, label="Descripción",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        if instance is not None:
            self.fields["nombre"].initial = instance.name
            meta = RolMeta.objects.filter(group=instance).first()
            if meta:
                self.fields["descripcion"].initial = meta.descripcion or ""

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        qs = Group.objects.filter(name=nombre)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Ya existe un rol con el nombre '{nombre}'.")
        return nombre


# ─── Lista ──────────────────────────────────────────────────

@login_required
@group_required("Admin")
def roles_list(request):
    """Tabla de roles con descripción, # usuarios, # módulos."""
    roles = []
    for grupo in Group.objects.all().order_by("name"):
        meta = RolMeta.objects.filter(group=grupo).first()
        roles.append({
            "id": grupo.id,
            "nombre": grupo.name,
            "descripcion": (meta.descripcion if meta else "") or "",
            "activo": meta.activo if meta else True,
            "es_protegido": meta.es_protegido if meta else False,
            "n_usuarios": User.objects.filter(groups=grupo).count(),
            "n_modulos": RolModulo.objects.filter(group=grupo).count(),
        })
    return render(request, "roles/roles_list.html", {"roles": roles})


# ─── Detalle (checkboxes + usuarios) ────────────────────────

@login_required
@group_required("Admin")
def rol_detalle(request, pk: int):
    grupo = get_object_or_404(Group, pk=pk)
    meta, _ = RolMeta.objects.get_or_create(group=grupo, defaults={"activo": True})

    modulos = list(Modulo.objects.filter(activo=True).order_by("orden", "codigo"))
    asignados = set(
        RolModulo.objects.filter(group=grupo).values_list("modulo_id", flat=True)
    )
    modulos_view = [{"obj": m, "asignado": m.codigo in asignados} for m in modulos]

    usuarios = User.objects.filter(groups=grupo).order_by("username")
    candidatos = User.objects.filter(is_active=True).exclude(groups=grupo).order_by("username")

    return render(request, "roles/rol_detalle.html", {
        "grupo": grupo, "meta": meta,
        "modulos_view": modulos_view,
        "usuarios": usuarios,
        "candidatos": candidatos,
    })


# ─── CRUD ──────────────────────────────────────────────────

@login_required
@group_required("Admin")
def rol_nuevo(request):
    if request.method == "POST":
        form = RolForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                grupo = Group.objects.create(name=form.cleaned_data["nombre"])
                RolMeta.objects.create(
                    group=grupo,
                    descripcion=form.cleaned_data.get("descripcion") or None,
                    activo=True, es_protegido=False,
                )
            invalidar_cache_global()
            messages.success(request, f"Rol '{grupo.name}' creado.")
            return redirect("login:rol_detalle", pk=grupo.id)
    else:
        form = RolForm()
    return render(request, "roles/rol_form.html", {"form": form, "modo": "nuevo"})


@login_required
@group_required("Admin")
def rol_editar(request, pk: int):
    grupo = get_object_or_404(Group, pk=pk)
    if request.method == "POST":
        form = RolForm(request.POST, instance=grupo)
        if form.is_valid():
            with transaction.atomic():
                grupo.name = form.cleaned_data["nombre"]
                grupo.save(update_fields=["name"])
                meta, _ = RolMeta.objects.get_or_create(group=grupo)
                meta.descripcion = form.cleaned_data.get("descripcion") or None
                meta.save(update_fields=["descripcion", "updated_at"])
            invalidar_cache_global()
            messages.success(request, f"Rol '{grupo.name}' actualizado.")
            return redirect("login:rol_detalle", pk=grupo.id)
    else:
        form = RolForm(instance=grupo)
    return render(request, "roles/rol_form.html", {
        "form": form, "modo": "editar", "grupo": grupo,
    })


@login_required
@group_required("Admin")
@require_POST
def rol_toggle_activo(request, pk: int):
    grupo = get_object_or_404(Group, pk=pk)
    meta, _ = RolMeta.objects.get_or_create(group=grupo, defaults={"activo": True})
    if meta.es_protegido and meta.activo:
        messages.error(request, f"El rol '{grupo.name}' está protegido y no puede desactivarse.")
        return redirect("login:rol_detalle", pk=grupo.id)
    meta.activo = not meta.activo
    meta.save(update_fields=["activo", "updated_at"])
    invalidar_cache_global()
    estado = "activado" if meta.activo else "desactivado"
    messages.success(request, f"Rol '{grupo.name}' {estado}.")
    return redirect("login:rol_detalle", pk=grupo.id)


# ─── Asignación módulos ────────────────────────────────────

@login_required
@group_required("Admin")
@require_POST
def rol_modulos_guardar(request, pk: int):
    grupo = get_object_or_404(Group, pk=pk)
    meta = RolMeta.objects.filter(group=grupo).first()

    seleccionados = set(request.POST.getlist("modulos"))
    actuales = set(
        RolModulo.objects.filter(group=grupo).values_list("modulo_id", flat=True)
    )

    # Protección: el rol Admin (es_protegido) NO puede perder el módulo "roles"
    # — sería autoexclusión inmediata.
    if meta and meta.es_protegido and "roles" in actuales and "roles" not in seleccionados:
        messages.error(
            request,
            f"No puedes desmarcar 'roles' del rol protegido '{grupo.name}': "
            "perderías acceso a esta misma pantalla.",
        )
        return redirect("login:rol_detalle", pk=grupo.id)

    a_agregar = seleccionados - actuales
    a_quitar = actuales - seleccionados

    with transaction.atomic():
        if a_quitar:
            RolModulo.objects.filter(group=grupo, modulo_id__in=a_quitar).delete()
        for codigo in a_agregar:
            modulo = Modulo.objects.filter(codigo=codigo, activo=True).first()
            if modulo:
                RolModulo.objects.get_or_create(group=grupo, modulo=modulo)

    invalidar_cache_global()
    messages.success(
        request,
        f"Permisos actualizados: +{len(a_agregar)} agregados, -{len(a_quitar)} quitados.",
    )
    return redirect("login:rol_detalle", pk=grupo.id)


# ─── Asignación usuarios ───────────────────────────────────

@login_required
@group_required("Admin")
@require_POST
def rol_usuario_agregar(request, pk: int):
    grupo = get_object_or_404(Group, pk=pk)
    user_id = request.POST.get("usuario_id")
    if not user_id:
        messages.error(request, "Debes seleccionar un usuario.")
        return redirect("login:rol_detalle", pk=grupo.id)
    user = get_object_or_404(User, pk=user_id)
    user.groups.add(grupo)
    invalidar_cache_global()
    messages.success(request, f"{user.username} agregado al rol '{grupo.name}'.")
    return redirect("login:rol_detalle", pk=grupo.id)


@login_required
@group_required("Admin")
@require_POST
def rol_usuario_quitar(request, pk: int, user_id: int):
    grupo = get_object_or_404(Group, pk=pk)
    user = get_object_or_404(User, pk=user_id)
    meta = RolMeta.objects.filter(group=grupo).first()

    # Protección: el rol Admin protegido no puede quedarse sin último usuario.
    if meta and meta.es_protegido:
        usuarios_del_rol = User.objects.filter(groups=grupo).exclude(pk=user.pk)
        if not usuarios_del_rol.exists():
            messages.error(
                request,
                f"No puedes quitar al último usuario del rol protegido '{grupo.name}'.",
            )
            return redirect("login:rol_detalle", pk=grupo.id)

    user.groups.remove(grupo)
    invalidar_cache_global()
    messages.success(request, f"{user.username} retirado del rol '{grupo.name}'.")
    return redirect("login:rol_detalle", pk=grupo.id)

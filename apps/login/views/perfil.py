"""Vistas del perfil del usuario logueado: ver datos + cambiar contraseña."""
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.urls import reverse


@login_required
def mi_perfil(request):
    """Pantalla de cuenta: datos básicos + acceso a cambiar contraseña."""
    grupos = list(request.user.groups.values_list("name", flat=True))
    return render(request, "perfil/mi_perfil.html", {
        "grupos": grupos,
    })


@login_required
def cambiar_password(request):
    """Formulario de cambio de contraseña usando PasswordChangeForm de Django.

    Tras éxito, mantiene la sesión activa con `update_session_auth_hash`
    (sin esto el usuario quedaría desautenticado al instante).
    """
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "Contraseña actualizada correctamente.")
            return redirect("login:mi_perfil")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, "perfil/cambiar_password.html", {"form": form})

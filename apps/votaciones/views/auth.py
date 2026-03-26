from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods


def _safe_next(request: HttpRequest) -> str:
    """
    Evita redirects externos. Solo permite paths internos.
    Si no hay next válido, envía al dashboard de votaciones.
    """
    nxt = request.GET.get("next") or request.POST.get("next") or ""
    if nxt.startswith("/"):
        return nxt
    return reverse("votaciones:dashboard")


@require_http_methods(["GET", "POST"])
def staff_login(request: HttpRequest):
    """
    Login SOLO para usuarios staff.
    Público sigue usando /votaciones/scan/ sin login.
    """
    # Si ya está logueado y es staff, no lo molestamos
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(_safe_next(request))

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        nxt = _safe_next(request)

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Usuario o contraseña incorrectos.")
        elif not user.is_staff:
            messages.error(request, "Tu usuario no tiene permisos de staff.")
        else:
            login(request, user)
            return redirect(nxt)

    return render(request, "votaciones/staff_login.html", {"next": _safe_next(request)})


@require_http_methods(["POST", "GET"])
def staff_logout(request: HttpRequest):
    """
    Cierra sesión y devuelve al login staff.
    """
    logout(request)
    return redirect("votaciones:staff_login")
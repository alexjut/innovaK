"""Tipos de evento — migrado a Angular (Etapa D PR-1).

Las vistas HTML del organizador redirigen a /app/eventos/tipos (gestión
inline en el componente Angular). Nombres de URL conservados.
"""
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from apps.login.decorators import modulo_required


@login_required
@modulo_required('tipos_evento')
def listar_tipos_evento(request):
    """Migrado a Angular: listado de tipos de evento."""
    return redirect('/app/eventos/tipos')


@login_required
@modulo_required('tipos_evento')
@require_http_methods(["GET", "POST"])
def crear_tipo_evento(request):
    """Migrado a Angular: alta de tipo de evento (form inline)."""
    return redirect('/app/eventos/tipos')


@login_required
@modulo_required('tipos_evento')
@require_http_methods(["GET", "POST"])
def editar_tipo_evento(request, codigo):
    """Migrado a Angular: edición de tipo de evento (form inline)."""
    return redirect('/app/eventos/tipos')


@login_required
@modulo_required('tipos_evento')
@require_http_methods(["POST"])
def desactivar_tipo_evento(request, codigo):
    """Migrado a Angular: desactivar tipo de evento."""
    return redirect('/app/eventos/tipos')


@login_required
@modulo_required('tipos_evento')
@require_http_methods(["POST"])
def reactivar_tipo_evento(request, codigo):
    """Migrado a Angular: reactivar tipo de evento."""
    return redirect('/app/eventos/tipos')

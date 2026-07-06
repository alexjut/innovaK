"""Tipos de evento — migrado a Angular (Etapa D PR-1).

Queda `listar_tipos_evento` como puente al SPA (lo referencia el sidebar
de base.html). El CRUD de tipos de evento vive en Angular.
"""
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from apps.login.decorators import modulo_required


@login_required
@modulo_required('tipos_evento')
def listar_tipos_evento(request):
    """Migrado a Angular: listado de tipos de evento."""
    return redirect('/app/eventos/tipos')

"""CRUD de eventos: crear, listar, editar.

Migrado a Angular (Etapa D PR-1): las vistas HTML del organizador
redirigen a su ruta equivalente bajo /app/*. Los nombres de URL se
conservan para no romper enlaces internos ni `urls.py`.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from apps.login.decorators import modulo_required

logger = logging.getLogger(__name__)


@login_required
@modulo_required('eventos')
def crear_evento(request):
    """Migrado a Angular: formulario de nueva actividad."""
    return redirect('/app/eventos/nueva')


@login_required
def listar_eventos(request):
    """Migrado a Angular: listado de eventos."""
    return redirect('/app/eventos')


@login_required
@modulo_required('eventos')
def editar_evento(request, evento_id):
    """Migrado a Angular: editor de evento."""
    return redirect(f'/app/eventos/{evento_id}/editar')

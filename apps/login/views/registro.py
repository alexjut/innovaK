# apps/login/views/registro.py
"""Registro de personas/participantes — migrado a Angular (Etapa D PR-1).

Las vistas HTML redirigen a /app/admin/personas (alta de persona inline
en el componente Angular). Nombres de URL conservados.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from apps.login.decorators import modulo_required

logger = logging.getLogger(__name__)


@login_required
@modulo_required('personas_registro')
def crear_persona(request):
    """Migrado a Angular: alta de persona."""
    return redirect('/app/admin/personas')


@login_required
@modulo_required('personas_registro')
def crear_participante(request, persona_id):
    """Migrado a Angular: registro de persona como participante."""
    return redirect('/app/admin/personas')

# apps/dashboard/views.py
import json
import logging

from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required

logger = logging.getLogger(__name__)
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from apps.login.services.permisos import get_modulos_usuario
from apps.dashboard.services.intent_analyzer import IntentAnalyzer, QueryType
from apps.dashboard.services.query_builder import SafeQueryBuilder


def _modulos_de(user):
    """Set de códigos de módulos accesibles por el user. Bypass superuser."""
    if user.is_superuser:
        from apps.login.models.permisos import Modulo
        return set(Modulo.objects.filter(activo=True).values_list("codigo", flat=True))
    return set(get_modulos_usuario(user))


@login_required
def dashboard_home(request):
    """Migrado a Angular: hub central."""
    return redirect('/app/')


# ─────────────────────────────────────────────
# Sub-hubs por módulo (PR-C, refactor PR-N15-4)
# ─────────────────────────────────────────────
@login_required
def hub_presupuesto(request):
    """Migrado a Angular: hub de presupuesto."""
    return redirect('/app/presupuesto')


@login_required
def hub_actividades(request):
    """Migrado a Angular: hub de actividades."""
    return redirect('/app/actividades')


@login_required
def hub_actividades_tipo(request, codigo):
    """Migrado a Angular: actividades por tipo."""
    return redirect(f'/app/actividades/tipo/{codigo}')


@login_required
def caracterizaciones_por_evento(request, evento_id):
    """Migrado a Angular: caracterizaciones capturadas para un evento."""
    return redirect(f'/app/caracterizacion/evento/{evento_id}')


@login_required
def hub_actividades_tipo_subgrupo(request, codigo, subgrupo_id):
    """Migrado a Angular: actividades por tipo y subgrupo."""
    return redirect(f'/app/actividades/tipo/{codigo}/sub/{subgrupo_id}')


@login_required
def hub_votaciones(request):
    """Migrado a Angular: hub de votaciones."""
    return redirect('/app/votaciones')


@login_required
def hub_admin(request):
    """Migrado a Angular: hub de administración."""
    return redirect('/app/admin')


# ─────────────────────────────────────────────
# 1) Vista IA (solo Persona)
# ─────────────────────────────────────────────
@login_required
@modulo_required("dashboard_ia")
def dashboard_ai_view(request):
    """Migrado a Angular: consulta IA."""
    return redirect('/app/ia')


# ─────────────────────────────────────────────
# 2) Buscador clásico de Personas (seguros)
# ─────────────────────────────────────────────
@login_required
@modulo_required("dashboard_ia")
def vista_personas(request):
    """Migrado a Angular: tablero analítico de beneficiarios."""
    return redirect('/app/analitica')


# ─────────────────────────────────────────────
# 3) API para pruebas (POST JSON → Intent → QueryBuilder)
# ─────────────────────────────────────────────
from rest_framework.views import APIView as _APIView  # noqa: E402
from rest_framework.response import Response as _Response  # noqa: E402
from rest_framework.permissions import IsAuthenticated as _IsAuth  # noqa: E402
from apps.login.api.permissions import ModuloRequiredPermission as _ModuloReq  # noqa: E402


class KennyAsistenteView(_APIView):
    """Cerebro conversacional de KENNY (LLM Mistral vía backend).
    Para todo usuario autenticado. POST {mensaje} → {ok, respuesta}."""
    permission_classes = [_IsAuth]

    def post(self, request):
        from apps.dashboard.services.kenny_llm import responder
        mensaje = (request.data.get("mensaje") or "").strip()
        if not mensaje:
            return _Response({"ok": False, "error": "Falta el mensaje."}, status=400)
        return _Response(responder(mensaje, request.user))


class IABeneficiariosView(_APIView):
    """IA enfocada en beneficiarios de los productos de los proyectos
    (personas que participaron en eventos). DRF (JWT, sin CSRF).
    POST {query} → {ok, type, label, rows|count, universo, description}."""
    permission_classes = [_ModuloReq("dashboard_ia")]

    def post(self, request):
        from apps.dashboard.services.ia_beneficiarios import analizar
        query_text = (request.data.get("query") or "").strip()
        if not query_text:
            return _Response({"ok": False, "error": "Falta la pregunta."}, status=400)
        try:
            # RBAC: el scope viaja con el usuario (subgrupo ∪ contrato ∪ curso).
            # Esta es la ruta que usa "Consultar datos" de KENNY.
            return _Response(analizar(query_text, request.user))
        except Exception:
            logger.exception("Error IA beneficiarios: %r", query_text)
            return _Response({"ok": False, "error": "No se pudo ejecutar la consulta."}, status=400)


class AnaliticaBeneficiariosView(_APIView):
    """Tablero analítico completo de beneficiarios (todos los paneles)."""
    permission_classes = [_ModuloReq("dashboard_ia")]

    def get(self, request):
        from apps.dashboard.services.ia_beneficiarios import analitica
        try:
            return _Response(analitica(request.user))
        except Exception:
            logger.exception("Error analítica beneficiarios")
            return _Response({"error": "No se pudo cargar la analítica."}, status=500)


@require_http_methods(["POST"])
@login_required
@modulo_required("dashboard_ia")
def personas_query_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    query_text = (payload.get("query") or "").strip()
    if not query_text:
        return HttpResponseBadRequest("Falta 'query'")

    intent = IntentAnalyzer.analyze(query_text)
    try:
        qb = SafeQueryBuilder.build(intent, request.user)
        descripcion = qb.get("description", "")
        t = intent["type"]

        if t == QueryType.COUNT.value:
            return JsonResponse({"ok": True, "intent": intent, "type": "count",
                                 "description": descripcion, "count": qb["executable"]()})

        if t in (QueryType.FILTER.value, QueryType.GROUP.value, QueryType.TOP.value):
            return JsonResponse({"ok": True, "intent": intent, "type": t,
                                 "description": descripcion,
                                 "rows": list(qb["executable"]())})

        return JsonResponse({"ok": False, "intent": intent,
                             "error": "Consulta no reconocida"}, status=400)
    except Exception:
        logger.exception("Error consulta IA api: %r", query_text)
        return JsonResponse({"ok": False, "intent": intent,
                             "error": "No se pudo ejecutar la consulta. Intenta reformularla."},
                            status=400)

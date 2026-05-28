"""APIViews DRF — Votaciones (Etapa B Plan Frontend).

Endpoints read-only Angular-ready. Coexisten con los endpoints
legacy `JsonResponse` de `apps.votaciones.views.api` (que siguen
sirviendo el flujo de scan QR / voto en producción) hasta que el
front Angular reemplace los consumidores actuales.

Endpoints expuestos:
    GET /api/votaciones/eventos/                  AllowAny — listado activos
    GET /api/votaciones/eventos/<id>/candidatos/  AllowAny — agrupados id/der
    GET /api/votaciones/eventos/<id>/resultados/  votaciones_admin — ranking

Delega la lógica de helpers a las funciones internas del módulo
legacy para no duplicar (`_event_time_status`, `_candidate_*`).
Cuando Angular esté listo, se podrá apagar el módulo legacy.
"""
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.votaciones.models import Candidato, Evento, Voto
from apps.votaciones.views.api import (
    _candidate_curul,
    _candidate_group,
    _candidate_photo_url,
    _event_time_status,
)


def _evento_payload(evento):
    timing = _event_time_status(evento)
    return {
        "id": evento.id,
        "name": evento.name,
        "starts_at": evento.starts_at,
        "ends_at": evento.ends_at,
        "is_open": timing["is_open"],
        "status": timing["status"],
        "status_message": timing["message"],
    }


def _candidato_payload(request, c):
    grp = _candidate_group(c.genre or "")
    return {
        "id": c.id,
        "name": c.name,
        "genre": c.genre or "",
        "group": grp,
        "curul": _candidate_curul(c.genre or ""),
        "code": c.code or "",
        "photo_url": _candidate_photo_url(request, c),
        "bio": c.bio or "",
        "is_active": bool(c.is_active),
        "event_id": c.evento_id,
    }


class EventosListView(APIView):
    """GET /api/votaciones/eventos/ — listado de eventos activos."""

    # Etapa C #2: público sin auth obligatoria, acepta JWT/Session si llegan.
    permission_classes = [AllowAny]

    def get(self, request):
        eventos = Evento.objects.filter(is_active=True).order_by("-created_at")
        out = [_evento_payload(e) for e in eventos]
        return Response({"count": len(out), "results": out})


class EventoCandidatosView(APIView):
    """GET /api/votaciones/eventos/<event_id>/candidatos/

    Devuelve candidatos activos del evento agrupados en `identidades`
    y `derechos`. Si el evento no está abierto, responde 403 con
    contexto temporal (mismo contrato del endpoint legacy).
    """

    permission_classes = [AllowAny]

    def get(self, request, event_id):
        evento = get_object_or_404(Evento, pk=event_id)
        timing = _event_time_status(evento)
        if not timing["is_open"]:
            return Response(
                {
                    "detail": timing["message"],
                    "event": _evento_payload(evento),
                },
                status=403,
            )

        candidatos = (Candidato.objects
                      .filter(evento=evento, is_active=True)
                      .order_by("id"))
        identidades, derechos = [], []
        for c in candidatos:
            item = _candidato_payload(request, c)
            if item["group"] == "IDENTIDADES":
                identidades.append(item)
            elif item["group"] == "DERECHOS":
                derechos.append(item)

        return Response({
            "event": _evento_payload(evento),
            "identidades": identidades,
            "derechos": derechos,
            "count_identidades": len(identidades),
            "count_derechos": len(derechos),
        })


class ResultadosView(APIView):
    """GET /api/votaciones/eventos/<event_id>/resultados/

    Ranking por curul + totales. Solo staff (modulo `votaciones_admin`).
    Si event_id es 0, toma el último evento activo.
    """

    permission_classes = [ModuloRequiredPermission("votaciones_admin")]

    def get(self, request, event_id):
        if event_id == 0:
            ev = (Evento.objects.filter(is_active=True)
                  .order_by("-created_at").first())
            if not ev:
                return Response({
                    "event": None,
                    "total_votes": 0,
                    "unique_voters": 0,
                    "ranking_identidades": [],
                    "ranking_derechos": [],
                    "total_identidades_votes": 0,
                    "total_derechos_votes": 0,
                })
            event_id = ev.id

        get_object_or_404(Evento, pk=event_id)

        raw_id = (Voto.objects.filter(evento_id=event_id)
                  .values("candidato_identidades_id")
                  .annotate(votes=Count("id"))
                  .order_by("-votes", "candidato_identidades_id"))
        raw_der = (Voto.objects.filter(evento_id=event_id)
                   .values("candidato_derechos_id")
                   .annotate(votes=Count("id"))
                   .order_by("-votes", "candidato_derechos_id"))

        total_id = sum(r["votes"] for r in raw_id)
        total_der = sum(r["votes"] for r in raw_der)

        ranking_id = [
            self._build_ranking_item(request, r, "candidato_identidades_id", total_id)
            for r in raw_id
        ]
        ranking_der = [
            self._build_ranking_item(request, r, "candidato_derechos_id", total_der)
            for r in raw_der
        ]

        total = Voto.objects.filter(evento_id=event_id).count()
        unique = (Voto.objects.filter(evento_id=event_id)
                  .values("document_number").distinct().count())
        evento_data = (Evento.objects.filter(id=event_id)
                       .values("id", "name").first())

        return Response({
            "event": evento_data,
            "total_votes": total,
            "unique_voters": unique,
            "ranking_identidades": ranking_id,
            "ranking_derechos": ranking_der,
            "total_identidades_votes": total_id,
            "total_derechos_votes": total_der,
        })

    @staticmethod
    def _build_ranking_item(request, row, key_id, total):
        candidato_id = row.get(key_id)
        votes = row.get("votes", 0)
        name = "Voto en blanco"
        curul = "BLANCO"
        photo_url = ""

        if candidato_id not in (None, 0):
            c = (Candidato.objects
                 .filter(id=candidato_id)
                 .only("name", "genre", "photo").first())
            if c:
                name = (c.name or "").strip() or "Voto en blanco"
                curul = _candidate_curul(c.genre or "") or "BLANCO"
                if c.photo:
                    try:
                        photo_url = request.build_absolute_uri(c.photo.url)
                    except Exception:
                        photo_url = ""

        percentage = round((votes / total) * 100, 2) if total > 0 else 0.0
        return {
            "candidate_id": candidato_id,
            "candidate_name": name,
            "photo_url": photo_url,
            "curul": curul,
            "votes": votes,
            "percentage": percentage,
        }

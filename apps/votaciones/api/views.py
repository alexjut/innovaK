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
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.login.api.rate_limit import RateLimitedMixin
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


@extend_schema(
    tags=["Votaciones"],
    summary="Eventos de votación activos",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{count, results: [EventoSerializer]}")},
)
class EventosListView(APIView):
    """GET /api/votaciones/eventos/ — listado de eventos activos."""

    # Etapa C #2: público sin auth obligatoria, acepta JWT/Session si llegan.
    permission_classes = [AllowAny]

    def get(self, request):
        eventos = Evento.objects.filter(is_active=True).order_by("-created_at")
        out = [_evento_payload(e) for e in eventos]
        return Response({"count": len(out), "results": out})


@extend_schema(
    tags=["Votaciones"],
    summary="Candidatos del evento agrupados en identidades/derechos",
    responses={
        200: OpenApiResponse(OpenApiTypes.OBJECT, "{event, identidades, derechos, counts}"),
        403: OpenApiResponse(OpenApiTypes.OBJECT, "Evento no abierto"),
    },
)
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


@extend_schema(
    tags=["Votaciones"],
    summary="Resultados (ranking + totales) — staff",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{event, total_votes, unique_voters, ranking_*}")},
)
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


# ─────────────────────────────────────────────────────────────────────
# Cierre Etapa C #2 — Mutación pública DRF
# Coexiste con los endpoints legacy /votaciones/api/validate-voter/
# y /votaciones/api/vote/ (JsonResponse) que sirven el QR de producción.
# ─────────────────────────────────────────────────────────────────────

import json

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.models.persona import Persona
from apps.login.models.persona_documento import PersonaDocumento
from apps.votaciones.services import registrar_voto

from .serializers import (
    ValidateVoterRequestSerializer,
    ValidateVoterResponseSerializer,
    VoteRequestSerializer,
    VoteResponseSerializer,
)
from apps.votaciones.views.api import (
    _build_full_name,
    _candidate_group,
    _event_time_status,
    get_client_ip,
)


@extend_schema(
    tags=["Votaciones"],
    summary="Valida cédula contra el padrón electoral",
    request=ValidateVoterRequestSerializer,
    responses={200: ValidateVoterResponseSerializer},
)
class ValidateVoterView(RateLimitedMixin, APIView):
    """POST /votaciones/api/v2/voters/validate/

    Valida una cédula contra `PersonaDocumento.numero_documento`.
    Devuelve si existe + nombre completo (para que el frontend muestre
    "Hola, Juan Pérez. Confirma para votar").

    No expone PII innecesaria. Solo cuenta como check de elegibilidad.
    """
    permission_classes = [AllowAny]
    # 30/min: validación previa al voto, varios intentos legítimos por IP.
    rate_limit = "30/min"

    def post(self, request):
        ser = ValidateVoterRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        document_number = ser.validated_data["document_number"].strip()

        documento = PersonaDocumento.objects.filter(
            numero_documento=document_number
        ).first()
        if not documento:
            return Response({
                "exists": False,
                "document_number": document_number,
                "full_name": "",
                "persona_id": None,
            })

        persona = (Persona.objects
                   .select_related("persona_documento", "contacto")
                   .filter(persona_documento=documento)
                   .first())
        if not persona:
            return Response({
                "exists": False,
                "document_number": document_number,
                "full_name": "",
                "persona_id": None,
            })

        return Response({
            "exists": True,
            "document_number": document_number,
            "full_name": _build_full_name(persona),
            "persona_id": persona.id,
        })


@extend_schema(
    tags=["Votaciones"],
    summary="Registra un voto (1 Identidades + 1 Derechos)",
    request=VoteRequestSerializer,
    responses={
        201: VoteResponseSerializer,
        400: OpenApiResponse(OpenApiTypes.OBJECT, "Validación o consentimiento ausente"),
        403: OpenApiResponse(OpenApiTypes.OBJECT, "Votación cerrada"),
        404: OpenApiResponse(OpenApiTypes.OBJECT, "Evento o candidatura inexistente"),
    },
)
class VoteView(RateLimitedMixin, APIView):
    """POST /votaciones/api/v2/votes/

    Registra el voto del votante validando:
    - Evento existe y está abierto (entre starts_at y ends_at).
    - Cédula no vacía + consentimiento aceptado.
    - Candidatos pertenecen al evento + grupo correcto.
    - Voto en blanco con id=0 en cualquiera de los dos grupos.
    - Si la persona ya votó: 201 con `already_voted=true`, sin nueva fila.

    Delega a `apps.votaciones.services.registrar_voto` (anti-fraude
    + idempotencia ya probada en producción del flujo legacy).
    """
    permission_classes = [AllowAny]
    # 5/min: el voto en sí. La idempotencia del service evita duplicados.
    rate_limit = "5/min"

    def post(self, request):
        ser = VoteRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        from apps.votaciones.models import Candidato, Evento as VotEvento
        evento = VotEvento.objects.filter(id=d["event_id"]).first()
        if not evento:
            return Response({"detail": "La votación no existe."}, status=404)

        timing = _event_time_status(evento)
        if not timing["is_open"]:
            return Response({"detail": timing["message"], "event": {
                "id": evento.id, "name": evento.name,
                "starts_at": evento.starts_at,
                "ends_at": evento.ends_at,
                "status": timing["status"], "is_open": False,
            }}, status=403)

        cid = d["candidate_identidades_id"]
        if cid != 0:
            c = Candidato.objects.filter(
                id=cid, evento_id=evento.id, is_active=True
            ).first()
            if not c:
                return Response(
                    {"detail": "La candidatura de Identidades no existe o no está activa."},
                    status=404,
                )
            if _candidate_group(c.genre or "") != "IDENTIDADES":
                return Response(
                    {"detail": "La candidatura seleccionada no pertenece al grupo Identidades."},
                    status=400,
                )

        cdd = d["candidate_derechos_id"]
        if cdd != 0:
            c = Candidato.objects.filter(
                id=cdd, evento_id=evento.id, is_active=True
            ).first()
            if not c:
                return Response(
                    {"detail": "La candidatura de Derechos no existe o no está activa."},
                    status=404,
                )
            if _candidate_group(c.genre or "") != "DERECHOS":
                return Response(
                    {"detail": "La candidatura seleccionada no pertenece al grupo Derechos."},
                    status=400,
                )

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "") or ""

        res = registrar_voto(
            event_id=evento.id,
            candidate_identidades_id=cid,
            candidate_derechos_id=cdd,
            document_number=d["document_number"].strip(),
            consent_accepted=d["consent_accepted"],
            ip=ip,
            user_agent=ua,
        )

        if not getattr(res, "ok", False):
            err = getattr(res, "error", None) or "No fue posible registrar el voto."
            if err in (
                "La votación está inactiva.",
                "La votación aún no ha iniciado.",
                "La votación ya finalizó.",
            ):
                return Response({"detail": err}, status=403)
            return Response({"detail": err}, status=400)

        return Response(
            {
                "already_voted": bool(getattr(res, "already_voted", False)),
                "vote_id": getattr(res, "vote_id", None),
                "voter_full_name": getattr(res, "voter_full_name", ""),
                "vote_in_blank_identidades": cid == 0,
                "vote_in_blank_derechos": cdd == 0,
            },
            status=201,
        )

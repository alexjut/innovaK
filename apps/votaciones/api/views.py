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
        # El organizador (?all=1) ve TODOS los eventos, incluidos los
        # finalizados/inactivos. Público sin el flag: solo activos.
        ver_todos = request.query_params.get("all") in ("1", "true")
        eventos = Evento.objects.all().order_by("-created_at")
        if not ver_todos:
            eventos = eventos.filter(is_active=True)
        out = []
        for e in eventos:
            payload = _evento_payload(e)
            payload["total_votes"] = Voto.objects.filter(evento_id=e.id).count()
            payload["candidate_count"] = (Candidato.objects
                                          .filter(evento=e, is_active=True).count())
            out.append(payload)
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
    summary="QR del evento (URL pública + PNG base64) — staff",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{evento, url_publica, qr_base64}")},
)
class EventoQRView(APIView):
    """GET /votaciones/api/v2/eventos/<event_id>/qr/ — acuñar el QR del evento.

    Reemplaza `/votaciones/qr/event/<id>.png`, que era **público y sin
    validación**: cualquiera acuñaba el QR de cualquier id, existiera o no
    (medido: id 999999 devolvía un PNG de 200). Votaciones era el único módulo
    público del proyecto sin este trato — banco, caracterización, jóvenes,
    entregas, captura, inscripción, info-terreno y festivales ya firman su QR.

    Dos cambios respecto del anterior:

    1. **Acuñar exige `votaciones_admin`.** El ciudadano nunca acuña: escanea.
       Lo que él abre es `/votaciones/scan/`, que sigue abierto. Por eso cerrar
       esto no toca el kiosko.
    2. **La URL lleva el `?t=` firmado** con el mismo HMAC del resto del
       sistema. Hoy el lado público todavía no lo exige (los endpoints de
       votaciones siguen sin `QrTokenPermission`), así que el token viaja pero
       aún no decide: es la mitad que sí se puede hacer sin arriesgar el
       kiosko. La otra mitad va con la decisión de `QR_TOKEN_ENFORCE`.

    Devuelve el PNG en **base64 dentro del JSON**, no como imagen: un `<img
    src>` no puede mandar el header `Authorization`, así que servir el PNG
    gateado rompería la pantalla del organizador. Es el mismo patrón que
    `apps/login/api/views.py::EventoQRView`.
    """

    permission_classes = [ModuloRequiredPermission("votaciones_admin")]

    def get(self, request, event_id):
        import base64
        import io

        import qrcode

        from apps.login.services.qr_token import token_de

        ev = get_object_or_404(Evento, pk=event_id)
        path = f"/votaciones/scan/?event={ev.id}&t={token_de(ev.id)}"
        url_publica = request.build_absolute_uri(path)

        img = qrcode.make(url_publica)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode()

        return Response({
            "evento": {
                "id": ev.id,
                "name": ev.name,
                "starts_at": ev.starts_at,
                "ends_at": ev.ends_at,
                "is_active": ev.is_active,
            },
            "url_publica": url_publica,
            "url_publica_path": path,
            "qr_base64": qr_base64,
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
            # Último evento con votos; si no, el más reciente por fecha.
            ev = (Evento.objects.filter(is_active=True)
                  .order_by("-created_at").first()
                  or Evento.objects.order_by("-created_at").first())
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
from apps.login.services.consulta_publica import puede_ver_nombre
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

    S-1 (2026-08-06): el `full_name` —el "Hola, Juan Pérez. Confirma para
    votar"— solo sale con prueba de QR válido (`evento` + `t` firmado) o con
    sesión. Sin eso responde `exists` y nada más. El docstring decía "No expone
    PII innecesaria" mientras devolvía nombre completo a partir de una cédula, a
    cualquiera y sin auth: exactamente el par que protege la Ley 1581.

    Espeja al legacy `/votaciones/api/validate-voter/`; la regla la comparten
    vía `apps.login.services.consulta_publica` para que no puedan divergir.
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

        if not puede_ver_nombre(request):
            return Response({
                "exists": True,
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


# ─────────────────────────────────────────────────────────────────────
# Etapa D — CRUD organizador (Angular nativo). Gated votaciones_admin.
# ─────────────────────────────────────────────────────────────────────
from django.utils.dateparse import parse_datetime  # noqa: E402
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser  # noqa: E402
from apps.votaciones.forms.candidato_form import CURUL_CHOICES  # noqa: E402

_ADMIN = [ModuloRequiredPermission("votaciones_admin")]


def _parse_dt(v):
    if not v:
        return None
    try:
        from django.utils import timezone
        dt = parse_datetime(v)
        if dt and timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt
    except Exception:
        return None


@extend_schema(tags=["Votaciones"], summary="Curules disponibles (catálogo)")
class CurulesView(APIView):
    permission_classes = _ADMIN

    def get(self, request):
        items = [
            {"value": v, "label": lbl,
             "group": (v.split("|", 1)[0] if "|" in v else v)}
            for v, lbl in CURUL_CHOICES if v
        ]
        return Response({"results": items})


@extend_schema(tags=["Votaciones"], summary="Crear / editar / eliminar evento")
class EventoAdminView(APIView):
    permission_classes = _ADMIN

    def post(self, request):
        d = request.data or {}
        name = (d.get("name") or "").strip()
        if not name:
            return Response({"detail": "El nombre es obligatorio."}, status=400)
        starts = _parse_dt(d.get("starts_at"))
        ends = _parse_dt(d.get("ends_at"))
        if starts and ends and ends <= starts:
            return Response({"detail": "La finalización debe ser mayor que el inicio."}, status=400)
        try:
            votos = int(d.get("votos_permitidos") or 1)
        except (TypeError, ValueError):
            votos = 1
        ev = Evento.objects.create(
            name=name, starts_at=starts, ends_at=ends,
            votos_permitidos=max(1, min(votos, 20)),
            is_active=bool(d.get("is_active", True)),
        )
        return Response(_evento_payload(ev), status=201)

    def patch(self, request, event_id):
        ev = get_object_or_404(Evento, pk=event_id)
        d = request.data or {}
        if "name" in d:
            ev.name = (d.get("name") or "").strip() or ev.name
        if "starts_at" in d:
            ev.starts_at = _parse_dt(d.get("starts_at"))
        if "ends_at" in d:
            ev.ends_at = _parse_dt(d.get("ends_at"))
        if "votos_permitidos" in d:
            try:
                ev.votos_permitidos = max(1, min(int(d["votos_permitidos"]), 20))
            except (TypeError, ValueError):
                pass
        if ev.starts_at and ev.ends_at and ev.ends_at <= ev.starts_at:
            return Response({"detail": "La finalización debe ser mayor que el inicio."}, status=400)
        if "is_active" in d:
            ev.is_active = bool(d["is_active"])
        ev.save()
        return Response(_evento_payload(ev))

    def delete(self, request, event_id):
        ev = get_object_or_404(Evento, pk=event_id)
        if Voto.objects.filter(evento_id=ev.id).exists():
            return Response({"detail": "No se puede eliminar: el evento ya tiene votos."}, status=400)
        ev.delete()
        return Response({"detail": "Evento eliminado."})


@extend_schema(tags=["Votaciones"], summary="Toggle activo del evento")
class EventoAdminToggleView(APIView):
    permission_classes = _ADMIN

    def post(self, request, event_id):
        ev = get_object_or_404(Evento, pk=event_id)
        ev.is_active = not ev.is_active
        ev.save(update_fields=["is_active"])
        return Response({"id": ev.id, "is_active": ev.is_active})


@extend_schema(tags=["Votaciones"], summary="Candidatos del evento (admin, incluye inactivos)")
class CandidatosAdminView(APIView):
    permission_classes = _ADMIN

    def get(self, request, event_id):
        evento = get_object_or_404(Evento, pk=event_id)
        cands = (Candidato.objects.filter(evento=evento)
                 .order_by("genre", "stage_order", "name"))
        return Response({
            "event": _evento_payload(evento),
            "results": [_candidato_payload(request, c) for c in cands],
        })


def _as_bool(v, default=True):
    """Multipart manda bools como string; JSON los manda como bool."""
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "on", "yes", "sí", "si")


@extend_schema(tags=["Votaciones"], summary="Crear / editar / eliminar candidato (acepta foto multipart)")
class CandidatoAdminView(APIView):
    permission_classes = _ADMIN
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    _VALID_CURULES = {v for v, _ in CURUL_CHOICES if v}

    def post(self, request):
        d = request.data or {}
        evento_id = d.get("evento_id")
        name = (d.get("name") or "").strip()
        genre = (d.get("genre") or "").strip()
        if not evento_id or not name or not genre:
            return Response({"detail": "evento_id, name y curul son obligatorios."}, status=400)
        if genre not in self._VALID_CURULES:
            return Response({"detail": "Curul inválida."}, status=400)
        # Única por curul dentro del evento (entre activos).
        if Candidato.objects.filter(evento_id=evento_id, genre=genre, is_active=True).exists():
            return Response({"detail": "Ya hay un candidato activo en esa curul."}, status=400)
        c = Candidato.objects.create(
            evento_id=int(evento_id), name=name, genre=genre,
            bio=(d.get("bio") or ""),
            is_active=_as_bool(d.get("is_active"), True),
        )
        foto = request.FILES.get("photo")
        if foto is not None:
            c.photo = foto
            c.save(update_fields=["photo"])
        return Response(_candidato_payload(request, c), status=201)

    def patch(self, request, candidate_id):
        c = get_object_or_404(Candidato, pk=candidate_id)
        d = request.data or {}
        if "name" in d:
            c.name = (d.get("name") or "").strip() or c.name
        if "genre" in d and d["genre"] in self._VALID_CURULES:
            nuevo = d["genre"]
            if (nuevo != c.genre and Candidato.objects
                    .filter(evento_id=c.evento_id, genre=nuevo, is_active=True)
                    .exclude(pk=c.id).exists()):
                return Response({"detail": "Ya hay un candidato activo en esa curul."}, status=400)
            c.genre = nuevo
        if "bio" in d:
            c.bio = d.get("bio") or ""
        if "is_active" in d:
            c.is_active = _as_bool(d.get("is_active"), c.is_active)
        foto = request.FILES.get("photo")
        if foto is not None:
            c.photo = foto
        c.save()
        return Response(_candidato_payload(request, c))

    def delete(self, request, candidate_id):
        c = get_object_or_404(Candidato, pk=candidate_id)
        c.delete()
        return Response({"detail": "Candidato eliminado."})


@extend_schema(tags=["Votaciones"], summary="Toggle activo del candidato")
class CandidatoAdminToggleView(APIView):
    permission_classes = _ADMIN

    def post(self, request, candidate_id):
        c = get_object_or_404(Candidato, pk=candidate_id)
        c.is_active = not c.is_active
        c.save(update_fields=["is_active"])
        return Response({"id": c.id, "is_active": c.is_active})


# ─────────────────────────────────────────────────────────────────────
# Etapa D — Administración de VOTANTES (Angular nativo). votaciones_votantes.
#   Listado = personas que YA votaron (de Voto).
#   Registro = alta de Persona en el padrón (persona_documento).
# ─────────────────────────────────────────────────────────────────────
_VOTANTES = [ModuloRequiredPermission("votaciones_votantes")]


def _full_name_persona(p):
    partes = [p.nombre1 or "", p.nombre2 or "", p.apellido1 or "", p.apellido2 or ""]
    return " ".join(x.strip() for x in partes if x.strip())


@extend_schema(tags=["Votaciones"], summary="Tipos de documento (padrón)")
class VotantesTiposDocView(APIView):
    permission_classes = _VOTANTES

    def get(self, request):
        from apps.login.models.persona_documento import TipoDocumento
        items = [{"codigo": t.codigo, "nombre": t.nombre}
                 for t in TipoDocumento.objects.all().order_by("nombre")]
        return Response({"results": items})


@extend_schema(tags=["Votaciones"], summary="Buscar persona por documento")
class VotantesBuscarView(APIView):
    permission_classes = _VOTANTES

    def get(self, request):
        from apps.login.models.persona import Persona
        from apps.login.models.persona_documento import PersonaDocumento
        numero = (request.query_params.get("document_number") or "").strip()
        if not numero:
            return Response({"detail": "document_number es obligatorio."}, status=400)
        doc = PersonaDocumento.objects.filter(numero_documento=numero).first()
        if doc:
            persona = Persona.objects.filter(persona_documento=doc).first()
            if persona:
                return Response({
                    "exists": True, "persona_id": persona.id,
                    "full_name": _full_name_persona(persona),
                    "document_number": numero,
                })
        return Response({"exists": False, "document_number": numero})


@extend_schema(tags=["Votaciones"], summary="Registrar persona en el padrón")
class VotantesRegistrarView(APIView):
    permission_classes = _VOTANTES

    def post(self, request):
        from django.db import transaction
        from apps.login.models.persona import Persona, Participante
        from apps.login.models.persona_documento import PersonaDocumento, TipoDocumento
        d = request.data or {}
        numero = str(d.get("numero_documento") or "").strip()
        nombre1 = str(d.get("nombre1") or "").strip()
        apellido1 = str(d.get("apellido1") or "").strip()
        if not numero or not nombre1 or not apellido1:
            return Response({"detail": "numero_documento, nombre1 y apellido1 son obligatorios."}, status=400)

        existente = Persona.objects.filter(
            persona_documento__numero_documento=numero).first()
        if existente:
            return Response({"persona_id": existente.id,
                             "full_name": _full_name_persona(existente),
                             "ya_existia": True})

        tipo_codigo = d.get("tipo_documento_codigo") or 1
        try:
            with transaction.atomic():
                doc = PersonaDocumento.objects.filter(numero_documento=numero).first()
                if not doc:
                    tipo = (TipoDocumento.objects.filter(codigo=tipo_codigo).first()
                            or TipoDocumento.objects.first())
                    doc = PersonaDocumento.objects.create(
                        tipo_documento=tipo, numero_documento=numero)
                persona = Persona.objects.create(
                    usuario=request.user, persona_documento=doc,
                    nombre1=nombre1, nombre2=(str(d.get("nombre2") or "").strip() or None),
                    apellido1=apellido1, apellido2=(str(d.get("apellido2") or "").strip() or None),
                    fecha_nacimiento=(d.get("fecha_nacimiento") or None),
                )
                Participante.objects.create(persona=persona)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"persona_id": persona.id,
                         "full_name": f"{nombre1} {apellido1}".strip(),
                         "ya_existia": False}, status=201)


@extend_schema(tags=["Votaciones"], summary="Listado de personas que votaron")
class VotantesListView(APIView):
    permission_classes = _VOTANTES

    def get(self, request):
        from django.utils import timezone
        event_id = request.query_params.get("event_id")
        qs = Voto.objects.all()
        if event_id and str(event_id).isdigit():
            qs = qs.filter(evento_id=int(event_id))
        votos = (qs.values("document_number", "voter_full_name", "evento_id", "created_at")
                 .annotate(total_votos=Count("id")).order_by("-created_at"))
        eventos = {e.id: e.name for e in Evento.objects.all()}
        hoy = timezone.localdate()
        total_hoy = 0
        out = []
        for v in votos:
            try:
                if timezone.localtime(v["created_at"]).date() == hoy:
                    total_hoy += 1
            except Exception:
                pass
            out.append({
                "document_number": v["document_number"],
                "voter_full_name": v["voter_full_name"] or f"Cédula {v['document_number']}",
                "event_name": eventos.get(v["evento_id"], "—"),
                "created_at": v["created_at"].isoformat() if v["created_at"] else None,
                "total_votos": v["total_votos"],
            })
        return Response({
            "results": out,
            "total_listado": len(out),
            "total_general": Voto.objects.values("document_number").distinct().count(),
            "total_hoy": total_hoy,
        })

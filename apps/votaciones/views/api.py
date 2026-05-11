import json
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.db.models import Count
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static as static_url
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from apps.login.decorators import modulo_required
from apps.login.models.persona import Persona
from apps.login.models.persona_documento import PersonaDocumento

from ..models import Candidato, Evento, Voto
from ..services import registrar_voto


# =============================================================================
# Helpers
# =============================================================================

def get_client_ip(request: HttpRequest) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def _dt_iso(dt):
    if not dt:
        return None
    try:
        return localtime(dt).isoformat()
    except Exception:
        try:
            return dt.isoformat()
        except Exception:
            return None


def _json_error(message: str, status: int = 400, extra: dict | None = None):
    payload = {"ok": False, "error": message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def _parse_bool(val) -> bool:
    if val is True:
        return True
    if val in (1, "1"):
        return True
    if isinstance(val, str) and val.strip().lower() in ("true", "yes", "si", "sí"):
        return True
    return False


def _media_file_exists(field) -> bool:
    if not field:
        return False
    try:
        name = getattr(field, "name", "") or ""
        if not name:
            return False
        storage = getattr(field, "storage", None)
        if not storage:
            return False
        return storage.exists(name)
    except Exception:
        return False


def _static_candidate_url(request: HttpRequest, filename: str) -> str | None:
    filename = (filename or "").strip()
    if not filename:
        return None

    rel_path = f"voting/candidates/{filename}"

    try:
        exists = bool(finders.find(rel_path))
    except Exception:
        exists = False

    if not exists:
        return None

    url_path = static_url(rel_path)
    safe_url_path = quote(url_path, safe="/:?&=#%._-~")
    return request.build_absolute_uri(safe_url_path)


def _candidate_photo_url(request: HttpRequest, c: Candidato) -> str:
    # 1) MEDIA
    if getattr(c, "photo", None) and _media_file_exists(c.photo):
        try:
            return request.build_absolute_uri(c.photo.url)
        except Exception:
            pass

    # 2) STATIC por code
    url = _static_candidate_url(request, getattr(c, "code", ""))
    if url:
        return url

    # 3) STATIC por nombre
    base = (getattr(c, "name", "") or "").strip()
    if base:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            url = _static_candidate_url(request, f"{base}{ext}")
            if url:
                return url

        url = _static_candidate_url(request, base)
        if url:
            return url

    # 4) placeholder
    return request.build_absolute_uri(static_url("voting/candidates/placeholder.png"))


def _candidate_group(raw_genre: str) -> str:
    """
    Espera valores tipo:
      IDENTIDADES|LESBIANAS
      DERECHOS|SEGURIDAD
    """
    value = (raw_genre or "").strip()
    if "|" in value:
        return value.split("|", 1)[0].strip().upper()
    return value.upper()


def _candidate_curul(raw_genre: str) -> str:
    value = (raw_genre or "").strip()
    if "|" in value:
        return value.split("|", 1)[1].strip()
    return value.strip()


def _build_full_name(persona: Persona) -> str:
    parts = [
        (persona.nombre1 or "").strip(),
        (persona.nombre2 or "").strip(),
        (persona.apellido1 or "").strip(),
        (persona.apellido2 or "").strip(),
    ]
    return " ".join(p for p in parts if p).strip()


def _event_time_status(evento: Evento) -> dict:
    """
    Estados posibles:
      - inactive: evento desactivado manualmente
      - upcoming: aún no inicia
      - finished: ya terminó
      - open: se encuentra dentro del rango válido
    """
    if not evento.is_active:
        return {
            "is_open": False,
            "status": "inactive",
            "message": "La votación está inactiva.",
        }

    now_dt = timezone.localtime(timezone.now())

    starts_at = None
    ends_at = None

    try:
        starts_at = localtime(evento.starts_at) if evento.starts_at else None
    except Exception:
        starts_at = evento.starts_at

    try:
        ends_at = localtime(evento.ends_at) if evento.ends_at else None
    except Exception:
        ends_at = evento.ends_at

    if starts_at and now_dt < starts_at:
        return {
            "is_open": False,
            "status": "upcoming",
            "message": "La votación aún no ha iniciado.",
        }

    if ends_at and now_dt > ends_at:
        return {
            "is_open": False,
            "status": "finished",
            "message": "La votación ya finalizó.",
        }

    return {
        "is_open": True,
        "status": "open",
        "message": "La votación está disponible.",
    }


# =============================================================================
# API pública
# =============================================================================

@require_GET
def api_events(request: HttpRequest):
    eventos = Evento.objects.filter(is_active=True).order_by("-created_at")

    out = []
    for e in eventos:
        timing = _event_time_status(e)
        out.append(
            {
                "id": e.id,
                "name": e.name,
                "starts_at": _dt_iso(e.starts_at),
                "ends_at": _dt_iso(e.ends_at),
                "is_open": timing["is_open"],
                "status": timing["status"],
                "status_message": timing["message"],
            }
        )

    return JsonResponse({"ok": True, "events": out})


@require_GET
def api_event_candidates(request: HttpRequest, event_id: int):
    """
    Devuelve las candidaturas activas agrupadas en:
      - Identidades
      - Derechos
    """
    evento = get_object_or_404(Evento, pk=event_id)

    timing = _event_time_status(evento)
    if not timing["is_open"]:
        return _json_error(
            timing["message"],
            status=403,
            extra={
                "event": {
                    "id": evento.id,
                    "name": evento.name,
                    "starts_at": _dt_iso(evento.starts_at),
                    "ends_at": _dt_iso(evento.ends_at),
                    "is_open": timing["is_open"],
                    "status": timing["status"],
                }
            },
        )

    candidatos = Candidato.objects.filter(evento=evento, is_active=True).order_by("id")

    identidades = []
    derechos = []

    for c in candidatos:
        item = {
            "id": c.id,
            "name": c.name,
            "genre": c.genre or "",
            "group": _candidate_group(c.genre or ""),
            "curul": _candidate_curul(c.genre or ""),
            "code": c.code or "",
            "photo_url": _candidate_photo_url(request, c),
            "bio": c.bio or "",
            "is_active": bool(c.is_active),
            "event_id": c.evento_id,
        }

        if item["group"] == "IDENTIDADES":
            identidades.append(item)
        elif item["group"] == "DERECHOS":
            derechos.append(item)

    return JsonResponse(
        {
            "ok": True,
            "event": {
                "id": evento.id,
                "name": evento.name,
                "starts_at": _dt_iso(evento.starts_at),
                "ends_at": _dt_iso(evento.ends_at),
                "is_open": timing["is_open"],
                "status": timing["status"],
                "status_message": timing["message"],
            },
            "identidades": identidades,
            "derechos": derechos,
            "count_identidades": len(identidades),
            "count_derechos": len(derechos),
        }
    )


@require_http_methods(["POST"])
@csrf_exempt  # S8: público, votante sin sesión (escanea QR). Protege rate limit nginx.
def api_validate_voter(request: HttpRequest):
    """
    Valida por cédula contra la base prellenada:
      PersonaDocumento.numero_documento -> Persona
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_error("JSON inválido", status=400)

    document_number = str(data.get("document_number", "")).strip()
    if not document_number:
        return _json_error("La cédula es obligatoria.", status=400)

    documento = PersonaDocumento.objects.filter(numero_documento=document_number).first()
    if not documento:
        return JsonResponse(
            {
                "ok": True,
                "exists": False,
                "document_number": document_number,
                "full_name": "",
            }
        )

    persona = (
        Persona.objects.select_related("persona_documento", "contacto")
        .filter(persona_documento=documento)
        .first()
    )

    if not persona:
        return JsonResponse(
            {
                "ok": True,
                "exists": False,
                "document_number": document_number,
                "full_name": "",
            }
        )

    full_name = _build_full_name(persona)

    return JsonResponse(
        {
            "ok": True,
            "exists": True,
            "document_number": document_number,
            "full_name": full_name,
            "persona_id": persona.id,
        }
    )


# =============================================================================
# API SOLO STAFF
# =============================================================================

@login_required
@modulo_required("votaciones_admin")
@require_GET
def api_results(request: HttpRequest):
    """
    Resultados por votación:
      - total de votos emitidos
      - votantes únicos
      - resultados por curul en Identidades
      - resultados por curul en Derechos
      - interpreta 0 / vacío / sin coincidencia como voto en blanco
      - calcula porcentaje por grupo
      - incluye foto del candidato si existe
    """
    try:
        event_id = int(request.GET.get("event") or "0")
    except ValueError:
        return _json_error("event inválido", status=400)

    if event_id == 0:
        e = Evento.objects.filter(is_active=True).order_by("-created_at").first()
        if not e:
            return JsonResponse(
                {
                    "ok": True,
                    "event": None,
                    "total_votes": 0,
                    "unique_voters": 0,
                    "ranking_identidades": [],
                    "ranking_derechos": [],
                    "total_identidades_votes": 0,
                    "total_derechos_votes": 0,
                }
            )
        event_id = e.id

    raw_identidades = (
        Voto.objects.filter(evento_id=event_id)
        .values("candidato_identidades_id")
        .annotate(votes=Count("id"))
        .order_by("-votes", "candidato_identidades_id")
    )

    raw_derechos = (
        Voto.objects.filter(evento_id=event_id)
        .values("candidato_derechos_id")
        .annotate(votes=Count("id"))
        .order_by("-votes", "candidato_derechos_id")
    )

    total_identidades_votes = sum(row.get("votes", 0) for row in raw_identidades)
    total_derechos_votes = sum(row.get("votes", 0) for row in raw_derechos)

    ranking_identidades = []
    for row in raw_identidades:
        candidato_id = row.get("candidato_identidades_id")
        votes = row.get("votes", 0)

        candidato_name = "Voto en blanco"
        curul = "BLANCO"
        photo_url = ""

        if candidato_id not in (None, 0):
            candidato = Candidato.objects.filter(id=candidato_id).only("name", "genre", "photo").first()
            if candidato:
                candidato_name = (candidato.name or "").strip() or "Voto en blanco"
                curul = _candidate_curul(candidato.genre or "") or "BLANCO"

                if candidato.photo:
                    try:
                        photo_url = request.build_absolute_uri(candidato.photo.url)
                    except Exception:
                        photo_url = ""

        percentage = 0.0
        if total_identidades_votes > 0:
            percentage = round((votes / total_identidades_votes) * 100, 2)

        ranking_identidades.append(
            {
                "candidate_identidades_id": candidato_id,
                "candidate_identidades__name": candidato_name,
                "candidate_identidades__photo_url": photo_url,
                "curul": curul,
                "votes": votes,
                "percentage": percentage,
            }
        )

    ranking_derechos = []
    for row in raw_derechos:
        candidato_id = row.get("candidato_derechos_id")
        votes = row.get("votes", 0)

        candidato_name = "Voto en blanco"
        curul = "BLANCO"
        photo_url = ""

        if candidato_id not in (None, 0):
            candidato = Candidato.objects.filter(id=candidato_id).only("name", "genre", "photo").first()
            if candidato:
                candidato_name = (candidato.name or "").strip() or "Voto en blanco"
                curul = _candidate_curul(candidato.genre or "") or "BLANCO"

                if candidato.photo:
                    try:
                        photo_url = request.build_absolute_uri(candidato.photo.url)
                    except Exception:
                        photo_url = ""

        percentage = 0.0
        if total_derechos_votes > 0:
            percentage = round((votes / total_derechos_votes) * 100, 2)

        ranking_derechos.append(
            {
                "candidate_derechos_id": candidato_id,
                "candidate_derechos__name": candidato_name,
                "candidate_derechos__photo_url": photo_url,
                "curul": curul,
                "votes": votes,
                "percentage": percentage,
            }
        )

    total = Voto.objects.filter(evento_id=event_id).count()
    unique = (
        Voto.objects.filter(evento_id=event_id)
        .values("document_number")
        .distinct()
        .count()
    )
    evento = Evento.objects.filter(id=event_id).values("id", "name").first()

    return JsonResponse(
        {
            "ok": True,
            "event": evento,
            "total_votes": total,
            "unique_voters": unique,
            "ranking_identidades": ranking_identidades,
            "ranking_derechos": ranking_derechos,
            "total_identidades_votes": total_identidades_votes,
            "total_derechos_votes": total_derechos_votes,
        }
    )

# =============================================================================
# API pública: votar
# =============================================================================

@csrf_exempt  # S8: público, votante sin sesión (escanea QR). Protege rate limit nginx.
@require_http_methods(["POST"])
def api_vote(request: HttpRequest):
    """
    Registra:
      - 1 selección de Identidades
      - 1 selección de Derechos
      - validación por cédula
      - permite voto en blanco con id=0
      - solo permite votar dentro del rango starts_at / ends_at del evento
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_error("JSON inválido", status=400)

    try:
        event_id = int(data.get("event_id") or 0)
        candidate_identidades_id = int(data.get("candidate_identidades_id") or 0)
        candidate_derechos_id = int(data.get("candidate_derechos_id") or 0)
    except ValueError:
        return _json_error(
            "event_id/candidate_identidades_id/candidate_derechos_id inválidos",
            status=400,
        )

    if not event_id:
        return _json_error("Falta event_id.", status=400)

    if candidate_identidades_id < 0 or candidate_derechos_id < 0:
        return _json_error("Los ids de candidatura no pueden ser negativos.", status=400)

    document_number = str(data.get("document_number", "")).strip()
    consent_accepted = _parse_bool(data.get("consent_accepted"))

    if not document_number:
        return _json_error("La cédula es obligatoria.", status=400)

    if not consent_accepted:
        return _json_error("Debes aceptar la política de datos.", status=400)

    evento = Evento.objects.filter(id=event_id).first()
    if not evento:
        return _json_error("La votación no existe.", status=404)

    timing = _event_time_status(evento)
    if not timing["is_open"]:
        return _json_error(
            timing["message"],
            status=403,
            extra={
                "event": {
                    "id": evento.id,
                    "name": evento.name,
                    "starts_at": _dt_iso(evento.starts_at),
                    "ends_at": _dt_iso(evento.ends_at),
                    "status": timing["status"],
                    "is_open": timing["is_open"],
                }
            },
        )

    candidato_identidades = None
    if candidate_identidades_id != 0:
        candidato_identidades = Candidato.objects.filter(
            id=candidate_identidades_id,
            evento_id=event_id,
            is_active=True,
        ).first()

        if not candidato_identidades:
            return _json_error(
                "La candidatura de Identidades no existe o no está activa.",
                status=404,
            )

        if _candidate_group(candidato_identidades.genre or "") != "IDENTIDADES":
            return _json_error(
                "La candidatura seleccionada no pertenece al grupo Identidades.",
                status=400,
            )

    candidato_derechos = None
    if candidate_derechos_id != 0:
        candidato_derechos = Candidato.objects.filter(
            id=candidate_derechos_id,
            evento_id=event_id,
            is_active=True,
        ).first()

        if not candidato_derechos:
            return _json_error(
                "La candidatura de Derechos no existe o no está activa.",
                status=404,
            )

        if _candidate_group(candidato_derechos.genre or "") != "DERECHOS":
            return _json_error(
                "La candidatura seleccionada no pertenece al grupo Derechos.",
                status=400,
            )

    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "") or ""

    res = registrar_voto(
        event_id=event_id,
        candidate_identidades_id=candidate_identidades_id,
        candidate_derechos_id=candidate_derechos_id,
        document_number=document_number,
        consent_accepted=consent_accepted,
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
            return _json_error(err, status=403)

        return _json_error(err, status=400)

    return JsonResponse(
        {
            "ok": True,
            "already_voted": bool(getattr(res, "already_voted", False)),
            "vote_id": getattr(res, "vote_id", None),
            "voter_full_name": getattr(res, "voter_full_name", ""),
            "vote_in_blank_identidades": candidate_identidades_id == 0,
            "vote_in_blank_derechos": candidate_derechos_id == 0,
        }
    )
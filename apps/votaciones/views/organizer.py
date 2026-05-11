from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, ProtectedError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.login.decorators import modulo_required

from ..forms import CandidatoForm, EventoForm
from ..models import Candidato, Evento


# =============================================================================
# Organizador (SOLO STAFF) - Eventos
# =============================================================================

@login_required
@modulo_required("votaciones_admin")
def organizer_events(request: HttpRequest):
    eventos = Evento.objects.all().order_by("-created_at")
    return render(request, "votaciones/organizer_events.html", {"eventos": eventos})


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["GET", "POST"])
def organizer_event_create(request: HttpRequest):
    if request.method == "POST":
        form = EventoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("votaciones:organizer_events")
    else:
        form = EventoForm(initial={"is_active": True})

    return render(request, "votaciones/organizer_event_create.html", {"form": form})


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["GET", "POST"])
def organizer_event_edit(request: HttpRequest, event_id: int):
    evento = get_object_or_404(Evento, id=event_id)

    if request.method == "POST":
        form = EventoForm(request.POST, instance=evento)
        if form.is_valid():
            form.save()
            return redirect("votaciones:organizer_events")
    else:
        form = EventoForm(instance=evento)

    return render(
        request,
        "votaciones/organizer_event_edit.html",
        {"form": form, "evento": evento},
    )


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["POST"])
def organizer_event_toggle(request: HttpRequest, event_id: int):
    evento = get_object_or_404(Evento, id=event_id)
    evento.is_active = not evento.is_active
    evento.save(update_fields=["is_active"])
    return redirect("votaciones:organizer_events")


# ==========================
# NUEVO: eliminar evento
# ==========================

@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["POST"])
def organizer_event_delete(request: HttpRequest, event_id: int):
    evento = get_object_or_404(Evento, id=event_id)

    try:
        evento_name = evento.name
        evento.delete()
        messages.success(request, f'Evento "{evento_name}" eliminado correctamente.')
    except ProtectedError:
        messages.error(
            request,
            "No se puede eliminar este evento porque tiene registros relacionados "
            "(por ejemplo votos u otros datos protegidos). "
            "Puedes desactivarlo en lugar de eliminarlo.",
        )

    return redirect("votaciones:organizer_events")


# =============================================================================
# Organizador (SOLO STAFF) - Artistas / Candidatos
# =============================================================================
@login_required
@modulo_required("votaciones_admin")
def organizer_artists(request: HttpRequest):
    q = (request.GET.get("q") or "").strip()
    event_filter = request.GET.get("event") or ""
    qr_event = request.GET.get("qr_event") or ""

    eventos = list(Evento.objects.order_by("-created_at").values("id", "name"))

    def _default_event_id():
        e = (
            Evento.objects.filter(is_active=True).order_by("-created_at").first()
            or Evento.objects.order_by("-created_at").first()
        )
        return e.id if e else None

    try:
        qr_event_id = int(qr_event) if qr_event else (_default_event_id() or 0)
    except ValueError:
        qr_event_id = _default_event_id() or 0

    if request.method == "POST":
        form = CandidatoForm(request.POST, request.FILES)
        if form.is_valid():
            candidato = form.save()
            messages.success(
                request,
                f'Candidatura "{candidato.name}" registrada correctamente.'
            )
            return redirect("votaciones:organizer_artists")
        else:
            messages.error(
                request,
                "No se pudo registrar la candidatura. Revisa los campos del formulario."
            )
    else:
        form = CandidatoForm(initial={"is_active": True})

    qs = (
        Candidato.objects.select_related("evento")
        .all()
        .order_by("evento_id", "-is_active", "stage_order", "name")
    )

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))

    try:
        event_filter_id = int(event_filter) if event_filter else None
    except ValueError:
        event_filter_id = None

    if event_filter_id:
        qs = qs.filter(evento_id=event_filter_id)

    return render(
        request,
        "votaciones/organizer_artists.html",
        {
            "form": form,
            "candidatos": qs,
            "eventos": eventos,
            "q": q,
            "filtro_evento": event_filter_id,
            "qr_evento_id": qr_event_id or (eventos[0]["id"] if eventos else 0),
        },
    )

@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["GET", "POST"])
def organizer_artist_edit(request: HttpRequest, candidate_id: int):
    candidato = get_object_or_404(Candidato, id=candidate_id)

    if request.method == "POST":
        form = CandidatoForm(request.POST, request.FILES, instance=candidato)
        if form.is_valid():
            candidato = form.save()
            messages.success(
                request,
                f'Candidatura "{candidato.name}" actualizada correctamente.'
            )
            return redirect("votaciones:organizer_artists")
        else:
            messages.error(
                request,
                "No se pudo actualizar la candidatura. Revisa los campos del formulario."
            )
    else:
        form = CandidatoForm(instance=candidato)

    return render(
        request,
        "votaciones/organizer_artist_edit.html",
        {"form": form, "candidato": candidato},
    )

@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["POST"])
def organizer_artist_toggle(request: HttpRequest, candidate_id: int):
    candidato = get_object_or_404(Candidato, id=candidate_id)
    candidato.is_active = not candidato.is_active
    candidato.save(update_fields=["is_active"])

    if candidato.is_active:
        messages.success(request, f'Candidatura "{candidato.name}" activada correctamente.')
    else:
        messages.success(request, f'Candidatura "{candidato.name}" desactivada correctamente.')

    return redirect("votaciones:organizer_artists")

# ==========================
# NUEVO: eliminar candidato
# ==========================
@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["POST"])
def organizer_artist_delete(request: HttpRequest, candidate_id: int):
    candidato = get_object_or_404(Candidato, id=candidate_id)

    try:
        candidato_name = candidato.name
        candidato.delete()
        messages.success(
            request,
            f'Candidatura "{candidato_name}" eliminada correctamente.'
        )
    except ProtectedError:
        messages.error(
            request,
            "No se puede eliminar esta candidatura porque tiene registros relacionados "
            "(por ejemplo votos u otros datos protegidos). "
            "Puedes desactivarla en lugar de eliminarla.",
        )
    except Exception:
        messages.error(
            request,
            "Ocurrió un error inesperado al intentar eliminar la candidatura."
        )

    return redirect("votaciones:organizer_artists")

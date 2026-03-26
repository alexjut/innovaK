from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, ProtectedError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from ..forms import CandidateForm, EventForm
from ..models import Candidate, Event


# =============================================================================
# Organizador (SOLO STAFF) - Eventos
# =============================================================================

@staff_member_required(login_url="votaciones:staff_login")
def organizer_events(request: HttpRequest):
    events = Event.objects.all().order_by("-created_at")
    return render(request, "votaciones/organizer_events.html", {"events": events})


@staff_member_required(login_url="votaciones:staff_login")
@require_http_methods(["GET", "POST"])
def organizer_event_create(request: HttpRequest):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("votaciones:organizer_events")
    else:
        form = EventForm(initial={"is_active": True})

    return render(request, "votaciones/organizer_event_create.html", {"form": form})


@staff_member_required(login_url="votaciones:staff_login")
@require_http_methods(["GET", "POST"])
def organizer_event_edit(request: HttpRequest, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect("votaciones:organizer_events")
    else:
        form = EventForm(instance=event)

    return render(
        request,
        "votaciones/organizer_event_edit.html",
        {"form": form, "event": event},
    )


@staff_member_required(login_url="votaciones:staff_login")
@require_http_methods(["POST"])
def organizer_event_toggle(request: HttpRequest, event_id: int):
    event = get_object_or_404(Event, id=event_id)
    event.is_active = not event.is_active
    event.save(update_fields=["is_active"])
    return redirect("votaciones:organizer_events")


# ==========================
# NUEVO: eliminar evento
# ==========================

@staff_member_required(login_url="votaciones:staff_login")
@require_http_methods(["POST"])
def organizer_event_delete(request: HttpRequest, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    try:
        event_name = event.name
        event.delete()
        messages.success(request, f'Evento "{event_name}" eliminado correctamente.')
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
@staff_member_required(login_url="votaciones:staff_login")
def organizer_artists(request: HttpRequest):
    q = (request.GET.get("q") or "").strip()
    event_filter = request.GET.get("event") or ""
    qr_event = request.GET.get("qr_event") or ""

    events = list(Event.objects.order_by("-created_at").values("id", "name"))

    def _default_event_id():
        e = (
            Event.objects.filter(is_active=True).order_by("-created_at").first()
            or Event.objects.order_by("-created_at").first()
        )
        return e.id if e else None

    try:
        qr_event_id = int(qr_event) if qr_event else (_default_event_id() or 0)
    except ValueError:
        qr_event_id = _default_event_id() or 0

    if request.method == "POST":
        form = CandidateForm(request.POST, request.FILES)
        if form.is_valid():
            candidate = form.save()
            messages.success(
                request,
                f'Candidatura "{candidate.name}" registrada correctamente.'
            )
            return redirect("votaciones:organizer_artists")
        else:
            messages.error(
                request,
                "No se pudo registrar la candidatura. Revisa los campos del formulario."
            )
    else:
        form = CandidateForm(initial={"is_active": True})

    qs = (
        Candidate.objects.select_related("event")
        .all()
        .order_by("event_id", "-is_active", "stage_order", "name")
    )

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))

    try:
        event_filter_id = int(event_filter) if event_filter else None
    except ValueError:
        event_filter_id = None

    if event_filter_id:
        qs = qs.filter(event_id=event_filter_id)

    return render(
        request,
        "votaciones/organizer_artists.html",
        {
            "form": form,
            "candidates": qs,
            "events": events,
            "q": q,
            "event_filter": event_filter_id,
            "qr_event_id": qr_event_id or (events[0]["id"] if events else 0),
        },
    )

@staff_member_required(login_url="votaciones:staff_login")
@require_http_methods(["GET", "POST"])
def organizer_artist_edit(request: HttpRequest, candidate_id: int):
    candidate = get_object_or_404(Candidate, id=candidate_id)

    if request.method == "POST":
        form = CandidateForm(request.POST, request.FILES, instance=candidate)
        if form.is_valid():
            candidate = form.save()
            messages.success(
                request,
                f'Candidatura "{candidate.name}" actualizada correctamente.'
            )
            return redirect("votaciones:organizer_artists")
        else:
            messages.error(
                request,
                "No se pudo actualizar la candidatura. Revisa los campos del formulario."
            )
    else:
        form = CandidateForm(instance=candidate)

    return render(
        request,
        "votaciones/organizer_artist_edit.html",
        {"form": form, "candidate": candidate},
    )

@staff_member_required(login_url="votaciones:staff_login")
@require_http_methods(["POST"])
def organizer_artist_toggle(request: HttpRequest, candidate_id: int):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    candidate.is_active = not candidate.is_active
    candidate.save(update_fields=["is_active"])

    if candidate.is_active:
        messages.success(request, f'Candidatura "{candidate.name}" activada correctamente.')
    else:
        messages.success(request, f'Candidatura "{candidate.name}" desactivada correctamente.')

    return redirect("votaciones:organizer_artists")

# ==========================
# NUEVO: eliminar candidato
# ==========================
@staff_member_required(login_url="votaciones:staff_login")
@require_http_methods(["POST"])
def organizer_artist_delete(request: HttpRequest, candidate_id: int):
    candidate = get_object_or_404(Candidate, id=candidate_id)

    try:
        candidate_name = candidate.name
        candidate.delete()
        messages.success(
            request,
            f'Candidatura "{candidate_name}" eliminada correctamente.'
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
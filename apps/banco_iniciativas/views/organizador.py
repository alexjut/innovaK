"""Vistas de organizador del Banco de Iniciativas (login requerido)."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.login.decorators import group_required
from apps.banco_iniciativas.models import InscripcionBancoIniciativa

logger = logging.getLogger(__name__)


@login_required
@group_required("Admin", "Lider")
def inscripciones_list(request):
    """Lista paginada de inscripciones, filtrable por estado y evento."""
    estado = (request.GET.get("estado") or "").strip().lower()
    evento_id = (request.GET.get("evento") or "").strip()
    q = (request.GET.get("q") or "").strip()

    qs = (
        InscripcionBancoIniciativa.objects
        .select_related(
            "evento", "organizacion", "disciplina_principal",
            "caracteristica_pob", "upl", "rango_poblacion",
        )
    )
    if estado in {"borrador", "enviada", "validada", "rechazada"}:
        qs = qs.filter(estado=estado)
    if evento_id.isdigit():
        qs = qs.filter(evento_id=int(evento_id))
    if q:
        qs = qs.filter(organizacion__nombre__icontains=q)
    qs = qs.order_by("-created_at", "-id")

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    # query string preservada (sin 'page')
    keep = []
    for k in ("estado", "evento", "q"):
        v = (request.GET.get(k) or "").strip()
        if v:
            keep.append(f"{k}={v}")
    qs_keep = ("&" + "&".join(keep)) if keep else ""

    return render(request, "banco_iniciativas/inscripciones_list.html", {
        "page_obj": page_obj,
        "qs": qs_keep,
        "estado_actual": estado,
        "q": q,
        "evento_id_filtro": evento_id,
        "estados": [
            ("borrador", "Borrador"),
            ("enviada", "Enviada"),
            ("validada", "Validada"),
            ("rechazada", "Rechazada"),
        ],
    })


@login_required
@group_required("Admin", "Lider")
def inscripcion_detalle(request, pk: int):
    """Detalle completo de una inscripción (incluye M2Ms)."""
    inscripcion = get_object_or_404(
        InscripcionBancoIniciativa.objects.select_related(
            "evento", "organizacion", "rep_tipo_doc", "anios_experiencia",
            "nivel_educativo", "barrio", "upl", "rango_poblacion",
            "caracteristica_pob", "disciplina_principal",
        ).prefetch_related(
            "escenarios", "implementos", "rango_etarios",
            "enfoques", "beneficios_alk",
        ),
        pk=pk,
    )
    return render(request, "banco_iniciativas/inscripcion_detalle.html", {
        "inscripcion": inscripcion,
    })


@login_required
@group_required("Admin", "Lider")
@require_POST
def inscripcion_validar(request, pk: int):
    """Cambia el estado de la inscripción a 'validada' o 'rechazada'."""
    accion = (request.POST.get("accion") or "").strip().lower()
    if accion not in {"validar", "rechazar"}:
        return HttpResponseBadRequest("Acción inválida")

    insc = get_object_or_404(InscripcionBancoIniciativa, pk=pk)
    nuevo_estado = "validada" if accion == "validar" else "rechazada"
    insc.estado = nuevo_estado
    insc.updated_at = timezone.now()
    insc.save(update_fields=["estado", "updated_at"])

    messages.success(
        request,
        f"Inscripción #{insc.id} marcada como {nuevo_estado}.",
    )
    return redirect("banco_iniciativas:inscripcion_detalle", pk=insc.id)


@login_required
@group_required("Admin", "Lider")
def inscripcion_firma(request, pk: int):
    """Devuelve la imagen de firma descifrada desde MongoDB.

    Solo accesible para Admin/Líder. Cada lectura descifra al vuelo;
    los bytes nunca se persisten en disco del servidor.
    """
    insc = get_object_or_404(InscripcionBancoIniciativa, pk=pk)
    if not insc.firma_mongo_id:
        raise Http404("Esta inscripción no tiene firma cargada en almacenamiento cifrado.")

    from apps.documentos.services import mongo_storage
    try:
        plaintext, mime = mongo_storage.leer(insc.firma_mongo_id)
    except Exception:
        logger.exception("Error leyendo firma desde Mongo (mongo_id=%s)", insc.firma_mongo_id)
        raise Http404("No se pudo recuperar la firma.")

    response = HttpResponse(plaintext, content_type=mime or "image/png")
    response["Content-Disposition"] = f'inline; filename="firma_inscripcion_{pk}.png"'
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response

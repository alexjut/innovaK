"""Vistas de organizador del Banco de Iniciativas (login requerido)."""
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.login.decorators import modulo_required, jwt_or_session_required
from apps.banco_iniciativas.models import InscripcionBancoIniciativa

logger = logging.getLogger(__name__)


@login_required
@modulo_required("banco_iniciativas")
def inscripciones_list(request):
    """Migrado a Angular: listado de inscripciones del Banco."""
    return redirect("/app/banco")


@login_required
@modulo_required("banco_iniciativas")
def inscripciones_insights(request):
    """Migrado a Angular: insights del Banco de Iniciativas."""
    return redirect("/app/banco/insights")


@jwt_or_session_required
@modulo_required("banco_iniciativas")
def inscripciones_exportar_csv(request):
    """Descarga CSV con la data trascendental de las inscripciones Banco.

    Incluye datos de cabecera + organización + representante + beneficiario
    vinculado (si existe) + conteos de M2M (escenarios, implementos,
    enfoques, etc.) + calidad de datos (firma, soporte legal). Para
    análisis externo (Excel, Power BI, Tableau).
    """
    import csv
    from django.http import HttpResponse
    from django.db.models import Count
    from datetime import datetime
    from apps.banco_iniciativas.models import (
        InscripcionBancoIniciativa,
        InscripcionBancoEscenario, InscripcionBancoEscenarioActual,
        InscripcionBancoImplemento, InscripcionBancoEnfoque,
        InscripcionBancoBeneficioAlk, InscripcionBancoRangoEtario,
    )
    from apps.login.models.contratos import Beneficiario

    # Filtros consistentes con la lista (`?estado=`, `?evento=`)
    qs = (
        InscripcionBancoIniciativa.objects
        .select_related(
            "evento", "organizacion", "organizacion__tipo_organizacion",
            "rep_tipo_doc", "anios_experiencia", "nivel_educativo",
            "barrio", "upl", "rango_poblacion", "caracteristica_pob",
            "disciplina_principal",
        )
        .order_by("-created_at", "-id")
    )
    estado = (request.GET.get("estado") or "").strip().lower()
    if estado in {"borrador", "enviada", "validada", "rechazada"}:
        qs = qs.filter(estado=estado)
    evento_id = (request.GET.get("evento") or "").strip()
    if evento_id.isdigit():
        qs = qs.filter(evento_id=int(evento_id))

    # Pre-cargar conteos de M2M en un solo paso (evita N+1).
    def _counts(model, fk_field="inscripcion_id"):
        return dict(
            model.objects.values_list(fk_field).annotate(c=Count("id"))
        )
    n_esc_solicitados = _counts(InscripcionBancoEscenario)
    n_esc_actuales = _counts(InscripcionBancoEscenarioActual)
    n_implementos = _counts(InscripcionBancoImplemento)
    n_enfoques = _counts(InscripcionBancoEnfoque)
    n_beneficios = _counts(InscripcionBancoBeneficioAlk)
    n_rangos_etarios = _counts(InscripcionBancoRangoEtario)

    # Beneficiarios PERSONA por documento (clave: rep_numero_doc)
    docs = list(qs.values_list("rep_numero_doc", flat=True))
    beneficiarios_por_doc = {
        b.numero_documento: b
        for b in Beneficiario.objects.filter(
            tipo="PERSONA", numero_documento__in=docs, activo=True
        ).select_related("persona")
    }

    nombre_archivo = (
        f"banco_inscripciones_{estado or 'todas'}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    )
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    response.write("﻿")  # BOM para Excel

    writer = csv.writer(response, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        # Cabecera
        "ID", "Estado", "Fecha creación", "Última actualización",
        "Proyecto",
        # Evento
        "Evento ID", "Evento Nombre",
        # Organización
        "Org ID", "Org Nombre", "Org NIT", "Tipo organización",
        "Org Correo", "Org Teléfono",
        # Representante
        "Rep Nombre completo", "Rep Tipo doc", "Rep Número doc",
        # Soporte legal y experiencia
        "Núm. soporte legal", "Tiene soporte legal (URL o PDF)",
        "Años experiencia", "Nivel educativo", "Títulos obtenidos",
        # Ubicación
        "UPL", "Barrio", "Dirección",
        # Población a atender
        "Rango población", "Estrato", "Característica población",
        # ALK previo
        "Beneficiada ALK previo", "Uso del beneficio previo",
        # Impacto
        "Impacto políticas", "Justificación impacto",
        # Disciplina
        "Disciplina principal", "Otros deportes",
        # Propuesta
        "Tiene propuesta descrita", "URL propuesta",
        # Compromisos
        "Compromiso redes", "Compromiso carta 1 año", "Compromiso actualización",
        # Firma
        "Firma cédula", "Firma fecha", "Tiene firma cifrada (Mongo)",
        # Conteos M2M (aporte analítico)
        "# Escenarios requeridos", "# Escenarios actuales",
        "# Implementos solicitados", "# Enfoques diferenciales",
        "# Beneficios ALK solicitados", "# Rangos etarios cubiertos",
        # Beneficiario PERSONA vinculado (si existe)
        "Tiene Beneficiario PERSONA", "Beneficiario ID",
        "Persona ID vinculada", "Persona nombre completo",
    ])
    for i in qs.iterator(chunk_size=500):
        org = i.organizacion
        tipo_org = org.tipo_organizacion if org else None
        rep_doc = (i.rep_numero_doc or "").strip()
        benef = beneficiarios_por_doc.get(rep_doc)
        persona_nombre = ""
        if benef and benef.persona:
            p = benef.persona
            persona_nombre = " ".join(
                x for x in [p.nombre1 or "", p.nombre2 or "",
                            p.apellido1 or "", p.apellido2 or ""] if x
            ).strip()
        tiene_soporte = bool(i.soporte_legal_url or i.soporte_legal_mongo_id)
        tiene_propuesta = bool(i.propuesta_descripcion or i.propuesta_url)
        tiene_firma = bool(i.firma_mongo_id or i.firma_imagen_url)
        writer.writerow([
            i.id, i.estado, i.created_at, i.updated_at, i.proyecto_codigo,
            i.evento_id, getattr(i.evento, "nombre", ""),
            org.id if org else "", getattr(org, "nombre", "") or "",
            getattr(org, "nit", "") or "",
            getattr(tipo_org, "nombre", "") or "",
            getattr(org, "correo", "") or "",
            getattr(org, "telefono", "") or "",
            i.rep_nombre or "",
            getattr(i.rep_tipo_doc, "nombre", "") or "",
            i.rep_numero_doc or "",
            i.numero_soporte_legal or "",
            "Sí" if tiene_soporte else "No",
            getattr(i.anios_experiencia, "nombre", "") or "",
            getattr(i.nivel_educativo, "nombre", "") or "",
            i.titulos_obtenidos or "",
            getattr(i.upl, "nombre", "") or "",
            getattr(i.barrio, "nombre", "") or "",
            i.direccion or "",
            getattr(i.rango_poblacion, "nombre", "") or "",
            i.estrato if i.estrato is not None else "",
            getattr(i.caracteristica_pob, "nombre", "") or "",
            "Sí" if i.beneficiada_alk else "No",
            i.uso_beneficio or "",
            i.impacto_politicas or "",
            i.impacto_justificacion or "",
            getattr(i.disciplina_principal, "nombre", "") or "",
            i.otros_deportes or "",
            "Sí" if tiene_propuesta else "No",
            i.propuesta_url or "",
            "Sí" if i.compromiso_redes else "No",
            "Sí" if i.compromiso_carta_1ano else "No",
            "Sí" if i.compromiso_actualizacion else "No",
            i.firma_cedula or "",
            i.firma_fecha or "",
            "Sí" if tiene_firma else "No",
            n_esc_solicitados.get(i.id, 0),
            n_esc_actuales.get(i.id, 0),
            n_implementos.get(i.id, 0),
            n_enfoques.get(i.id, 0),
            n_beneficios.get(i.id, 0),
            n_rangos_etarios.get(i.id, 0),
            "Sí" if benef else "No",
            benef.id if benef else "",
            benef.persona_id if benef and benef.persona_id else "",
            persona_nombre,
        ])
    return response


@login_required
@modulo_required("banco_iniciativas")
def inscripcion_detalle(request, pk: int):
    """Migrado a Angular: detalle de inscripción."""
    return redirect(f"/app/banco/{pk}")


@login_required
@modulo_required("banco_iniciativas")
@require_POST
def inscripcion_validar(request, pk: int):
    """Migrado a Angular: validar/rechazar inscripción."""
    return redirect(f"/app/banco/{pk}")


@login_required
@modulo_required("banco_iniciativas")
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

"""Vistas de organizador del Banco de Iniciativas (login requerido)."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.login.decorators import modulo_required, jwt_or_session_required
from apps.banco_iniciativas.models import InscripcionBancoIniciativa

logger = logging.getLogger(__name__)


@login_required
@modulo_required("banco_iniciativas")
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
@modulo_required("banco_iniciativas")
def inscripciones_insights(request):
    """Métricas trascendentales del Banco de Iniciativas.

    Renderiza una sola vista con cards de KPIs + tablas + análisis cruzado.
    Pensada para que un decisor pueda evaluar la convocatoria de un
    vistazo: cobertura, estados, calidad del dato, avance vs meta 280.
    """
    from django.db.models import Count, Q
    from apps.banco_iniciativas.models import (
        InscripcionBancoIniciativa, Upl,
        InscripcionBancoEnfoque, InscripcionBancoBeneficioAlk,
        InscripcionBancoEscenario, InscripcionBancoEscenarioActual,
        InscripcionBancoImplemento,
    )

    qs = InscripcionBancoIniciativa.objects.all()
    total = qs.count()
    META = 280  # meta del proyecto 2784 Kennedy fuerza local
    avance_pct = round(100 * total / META, 1) if META else 0

    # A) Funnel de estados
    por_estado_raw = dict(
        qs.values_list("estado").annotate(c=Count("id"))
    )
    funnel = [
        {"estado": "borrador",  "label": "Borrador",  "c": por_estado_raw.get("borrador", 0)},
        {"estado": "enviada",   "label": "Enviada",   "c": por_estado_raw.get("enviada", 0)},
        {"estado": "validada",  "label": "Validada",  "c": por_estado_raw.get("validada", 0)},
        {"estado": "rechazada", "label": "Rechazada", "c": por_estado_raw.get("rechazada", 0)},
    ]
    validadas = por_estado_raw.get("validada", 0)
    rechazadas = por_estado_raw.get("rechazada", 0)
    enviadas = por_estado_raw.get("enviada", 0)
    pct_validacion = round(100 * (validadas + rechazadas) / total, 1) if total else 0

    # B) Cobertura territorial: distribución por UPL (Kennedy: 9 UPLs)
    por_upl = list(
        qs.values("upl__codigo", "upl__nombre")
        .annotate(c=Count("id"))
        .exclude(upl__codigo__isnull=True)
        .order_by("-c")
    )
    upls_cubiertas = sum(1 for r in por_upl if r["c"] > 0)
    upls_total = Upl.objects.filter(activo=True).count()

    # C) Tipo de organización (vía organizacion.tipo_organizacion_codigo)
    por_tipo_org = list(
        qs.values("organizacion__tipo_organizacion__nombre")
        .annotate(c=Count("id"))
        .order_by("-c")[:10]
    )

    # D) Top 10 disciplinas deportivas (disciplina_principal)
    top_disciplinas = list(
        qs.values("disciplina_principal__nombre")
        .annotate(c=Count("id"))
        .exclude(disciplina_principal__nombre__isnull=True)
        .order_by("-c")[:10]
    )

    # E) Análisis de M2M: top enfoques, beneficios, escenarios solicitados.
    # Se cuentan filas en las tablas intermedias para evitar ambigüedad
    # con los related_name (`rel_inscripciones` en cada catálogo).
    top_enfoques = list(
        InscripcionBancoEnfoque.objects
        .values("enfoque__nombre")
        .annotate(c=Count("id"))
        .order_by("-c")[:10]
    )
    top_beneficios = list(
        InscripcionBancoBeneficioAlk.objects
        .values("tipo_beneficio__nombre")
        .annotate(c=Count("id"))
        .order_by("-c")[:10]
    )
    # Gap escenarios: solicitados (rel_escenarios) vs uso actual (rel_escenarios_actuales)
    solicitados = dict(
        InscripcionBancoEscenario.objects
        .values_list("escenario__codigo")
        .annotate(c=Count("id"))
    )
    actuales = dict(
        InscripcionBancoEscenarioActual.objects
        .values_list("escenario__codigo")
        .annotate(c=Count("id"))
    )
    from apps.banco_iniciativas.models import Escenario as _Esc
    gap_escenarios = []
    for esc in _Esc.objects.filter(activo=True).order_by("orden", "nombre"):
        req = solicitados.get(esc.codigo, 0)
        act = actuales.get(esc.codigo, 0)
        if req or act:
            gap_escenarios.append({
                "nombre": esc.nombre,
                "categoria_pot": esc.categoria_pot,
                "requerido": req,
                "actual": act,
                "gap": req - act,
            })
    gap_escenarios.sort(key=lambda r: r["gap"], reverse=True)
    gap_escenarios = gap_escenarios[:10]

    # F) Calidad del dato
    con_firma = qs.filter(firma_mongo_id__isnull=False).count()
    con_soporte_pdf = qs.filter(soporte_legal_mongo_id__isnull=False).count()
    con_soporte_url = qs.filter(soporte_legal_url__isnull=False).exclude(soporte_legal_url="").count()
    con_propuesta = qs.exclude(Q(propuesta_descripcion__isnull=True) | Q(propuesta_descripcion="")).count()
    con_beneficiada_alk = qs.filter(beneficiada_alk=True).count()
    pct_firma = round(100 * con_firma / total, 1) if total else 0
    pct_soporte = round(100 * (con_soporte_pdf + con_soporte_url) / total, 1) if total else 0

    # G) Impacto en políticas públicas
    impacto_mucho = qs.filter(impacto_politicas="mucho").count()
    impacto_parcial = qs.filter(impacto_politicas="parcial").count()
    impacto_nada = qs.filter(impacto_politicas="nada").count()
    impacto_desconoce = qs.filter(impacto_politicas="no_conozco").count()

    # H) Compromisos
    comp_redes = qs.filter(compromiso_redes=True).count()
    comp_carta = qs.filter(compromiso_carta_1ano=True).count()
    comp_actualiza = qs.filter(compromiso_actualizacion=True).count()

    # I) Cruce trascendental: inequidad ALK
    # ¿Las organizaciones beneficiadas previamente se validan más?
    inequidad_alk = []
    for beneficiada_flag, label in [(True, "Ya beneficiada"), (False, "Nueva")]:
        sub = qs.filter(beneficiada_alk=beneficiada_flag,
                        estado__in=["validada", "rechazada"])
        n = sub.count()
        v = sub.filter(estado="validada").count()
        inequidad_alk.append({
            "label": label,
            "n_procesadas": n,
            "validadas": v,
            "tasa_validacion": round(100 * v / n, 1) if n else None,
        })

    # J) Cruce: implementos por inscripción (¿sobre-dimensionamiento?)
    impl_por_insc = (
        InscripcionBancoImplemento.objects
        .values("inscripcion_id")
        .annotate(c=Count("id"))
    )
    if impl_por_insc:
        counts = [r["c"] for r in impl_por_insc]
        impl_stats = {
            "n_inscripciones_con_implementos": len(counts),
            "promedio": round(sum(counts) / len(counts), 1),
            "max": max(counts),
            "min": min(counts),
        }
    else:
        impl_stats = {"n_inscripciones_con_implementos": 0, "promedio": 0, "max": 0, "min": 0}

    return render(request, "banco_iniciativas/insights.html", {
        "total": total,
        "meta": META,
        "avance_pct": avance_pct,
        "funnel": funnel,
        "validadas": validadas,
        "rechazadas": rechazadas,
        "enviadas": enviadas,
        "pct_validacion": pct_validacion,
        "por_upl": por_upl,
        "upls_cubiertas": upls_cubiertas,
        "upls_total": upls_total,
        "por_tipo_org": por_tipo_org,
        "top_disciplinas": top_disciplinas,
        "top_enfoques": top_enfoques,
        "top_beneficios": top_beneficios,
        "gap_escenarios": gap_escenarios,
        "inequidad_alk": inequidad_alk,
        "impl_stats": impl_stats,
        "con_firma": con_firma,
        "con_soporte_pdf": con_soporte_pdf,
        "con_soporte_url": con_soporte_url,
        "con_propuesta": con_propuesta,
        "con_beneficiada_alk": con_beneficiada_alk,
        "pct_firma": pct_firma,
        "pct_soporte": pct_soporte,
        "impacto_mucho": impacto_mucho,
        "impacto_parcial": impacto_parcial,
        "impacto_nada": impacto_nada,
        "impacto_desconoce": impacto_desconoce,
        "comp_redes": comp_redes,
        "comp_carta": comp_carta,
        "comp_actualiza": comp_actualiza,
    })


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
@modulo_required("banco_iniciativas")
@require_POST
def inscripcion_validar(request, pk: int):
    """Cambia el estado de la inscripción a 'validada' o 'rechazada'.

    Si el request viene de HTMX (header HX-Request: true), devuelve solo
    el partial de la card de estado para hacer swap inline sin recargar
    la página (Etapa A Plan Frontend). Si no, mantiene el redirect legacy.
    """
    accion = (request.POST.get("accion") or "").strip().lower()
    if accion not in {"validar", "rechazar"}:
        return HttpResponseBadRequest("Acción inválida")

    insc = get_object_or_404(InscripcionBancoIniciativa, pk=pk)
    nuevo_estado = "validada" if accion == "validar" else "rechazada"
    insc.estado = nuevo_estado
    insc.updated_at = timezone.now()
    insc.save(update_fields=["estado", "updated_at"])

    if request.headers.get("HX-Request"):
        return render(
            request,
            "banco_iniciativas/_inscripcion_estado_card.html",
            {"inscripcion": insc},
        )

    messages.success(
        request,
        f"Inscripción #{insc.id} marcada como {nuevo_estado}.",
    )
    return redirect("banco_iniciativas:inscripcion_detalle", pk=insc.id)


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

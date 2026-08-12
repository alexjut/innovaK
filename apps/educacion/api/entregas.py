"""API de gestión de Educación: detalle de sede, entregas de insumos y resumen.

Vistas de función con `JsonResponse`, que es la convención del proyecto para
endpoints AJAX (sin DRF). Todas exigen sesión: esto es ejecución de contrato,
no la capa pública del mapa.

**Y exigen el módulo `educacion`.** Hasta el 2026-08-12 solo pedían sesión, así
que cualquier usuario autenticado —incluido `Visor`, que es de solo lectura—
podía CREAR y BORRAR entregas de insumos de un contrato. Contradecía el §3 de
`CLAUDE.md`, que exige gate por módulo en todo endpoint de gestión.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.educacion.models import ColegioSede, EntregaInsumoColegio
from apps.login.decorators import modulo_required_json

logger = logging.getLogger(__name__)


def _ok(data, status=200):
    return JsonResponse(data, safe=False, status=status,
                        json_dumps_params={"ensure_ascii": False})


def _error(msg, status=400):
    return _ok({"ok": False, "error": msg}, status=status)


def _sede_json(s: ColegioSede) -> dict:
    return {
        "id": s.id,
        "dane_sede": s.dane_sede,
        "dane_establecimiento": s.dane_establecimiento,
        "colegio": s.nombre_establecimiento,
        "sede": s.nombre_sede,
        "orden_sede": s.orden_sede,
        "es_principal": s.es_principal,
        "clase": s.clase,
        "clase_nombre": s.clase_nombre,
        "direccion": s.direccion,
        "barrio": s.barrio_declarado,
        "telefono": s.telefono,
        "email": s.email,
        "upz_codigo": s.upz_codigo,
        "estrato_ideca": s.estrato_ideca,
        "matricula_total": s.matricula_total,
        "matricula_corte": s.matricula_corte.isoformat() if s.matricula_corte else None,
        "latitud": float(s.latitud) if s.latitud is not None else None,
        "longitud": float(s.longitud) if s.longitud is not None else None,
        "fecha_corte": s.fecha_corte.isoformat() if s.fecha_corte else None,
    }


def _entrega_json(e: EntregaInsumoColegio) -> dict:
    return {
        "id": e.id,
        "colegio_sede_id": e.colegio_sede_id,
        "colegio": e.colegio_sede.nombre_establecimiento if e.colegio_sede_id else None,
        "sede": e.colegio_sede.nombre_sede if e.colegio_sede_id else None,
        "contrato_id": e.contrato_id,
        "contrato": str(e.contrato) if e.contrato_id else None,
        "vigencia": e.vigencia,
        "implemento_codigo": e.implemento_id,
        "insumo": e.insumo_nombre,
        "descripcion": e.descripcion,
        "cantidad": float(e.cantidad or 0),
        "unidad": e.unidad,
        "valor_unitario": float(e.valor_unitario) if e.valor_unitario is not None else None,
        "valor_total": float(e.valor_total) if e.valor_total is not None else None,
        "beneficiarios": e.beneficiarios,
        "fecha_entrega": e.fecha_entrega.isoformat() if e.fecha_entrega else None,
        "acta_numero": e.acta_numero,
        "observacion": e.observacion,
    }


@login_required
@modulo_required_json("educacion")
@require_http_methods(["GET"])
def api_colegio_detalle(request, sede_id: int):
    """Vista 360° de una sede: sus datos + todo lo que se le ha entregado."""
    try:
        sede = ColegioSede.objects.get(pk=sede_id)
    except ColegioSede.DoesNotExist:
        return _error("La sede no existe.", status=404)

    entregas = (EntregaInsumoColegio.objects
                .filter(colegio_sede_id=sede_id)
                .select_related("colegio_sede", "contrato", "implemento"))

    # Las sedes hermanas del mismo colegio: sirven para no registrar dos veces
    # la misma entrega en la sede equivocada.
    hermanas = (ColegioSede.objects
                .filter(dane_establecimiento=sede.dane_establecimiento)
                .exclude(pk=sede_id))

    total_valor = sum(float(e.valor_total or 0) for e in entregas)
    return _ok({
        "sede": _sede_json(sede),
        "sedes_hermanas": [_sede_json(h) for h in hermanas],
        "entregas": [_entrega_json(e) for e in entregas],
        "totales": {
            "entregas": len(entregas),
            "valor": total_valor,
            "beneficiarios": sum(e.beneficiarios or 0 for e in entregas),
        },
    })


@login_required
@modulo_required_json("educacion")
@require_http_methods(["GET"])
def api_entregas_list(request):
    """Entregas con filtros: ?vigencia= &contrato= &sede= &implemento=."""
    qs = (EntregaInsumoColegio.objects
          .select_related("colegio_sede", "contrato", "implemento"))

    vigencia = request.GET.get("vigencia")
    if vigencia and vigencia.isdigit():
        qs = qs.filter(vigencia=int(vigencia))
    contrato = request.GET.get("contrato")
    if contrato and contrato.isdigit():
        qs = qs.filter(contrato_id=int(contrato))
    sede = request.GET.get("sede")
    if sede and sede.isdigit():
        qs = qs.filter(colegio_sede_id=int(sede))
    implemento = request.GET.get("implemento")
    if implemento and implemento.isdigit():
        qs = qs.filter(implemento_id=int(implemento))

    filas = list(qs[:1000])
    return _ok({
        "items": [_entrega_json(e) for e in filas],
        "count": len(filas),
    })


@login_required
@modulo_required_json("educacion")
@require_http_methods(["POST"])
def api_entrega_crear(request):
    """Registra una entrega de insumos a una sede.

    Body JSON: colegio_sede_id, vigencia (obligatorios) + implemento_codigo o
    descripcion, cantidad, unidad, valor_unitario, valor_total, beneficiarios,
    fecha_entrega, acta_numero, contrato_id, observacion.
    """
    try:
        datos = json.loads(request.body or "{}")
    except ValueError:
        return _error("El cuerpo no es JSON válido.")

    sede_id = datos.get("colegio_sede_id")
    if not sede_id or not ColegioSede.objects.filter(pk=sede_id).exists():
        return _error("Falta una sede válida (colegio_sede_id).")

    vigencia = datos.get("vigencia")
    try:
        vigencia = int(vigencia)
    except (TypeError, ValueError):
        return _error("Falta la vigencia (año).")

    implemento = datos.get("implemento_codigo")
    descripcion = (datos.get("descripcion") or "").strip()
    # El mismo CHECK que en BD, pero acá se puede explicar: una entrega sin
    # catálogo ni texto no dice qué se entregó y no sirve para nada.
    if not implemento and not descripcion:
        return _error("Indica qué se entregó: escoge un insumo del catálogo "
                      "o descríbelo.")

    cantidad = _decimal(datos.get("cantidad"), Decimal("0"))
    if cantidad is None or cantidad < 0:
        return _error("La cantidad debe ser un número mayor o igual a cero.")

    valor_unitario = _decimal(datos.get("valor_unitario"), None)
    valor_total = _decimal(datos.get("valor_total"), None)
    # Comodidad real del cargue: casi siempre viene el unitario y la cantidad,
    # y el total se calcula. Si mandan el total, manda el total.
    if valor_total is None and valor_unitario is not None:
        valor_total = (valor_unitario * cantidad).quantize(Decimal("0.0001"))

    entrega = EntregaInsumoColegio(
        colegio_sede_id=sede_id,
        contrato_id=datos.get("contrato_id") or None,
        vigencia=vigencia,
        implemento_id=implemento or None,
        descripcion=descripcion or None,
        cantidad=cantidad,
        unidad=(datos.get("unidad") or "").strip() or None,
        valor_unitario=valor_unitario,
        valor_total=valor_total,
        beneficiarios=_int(datos.get("beneficiarios")),
        fecha_entrega=datos.get("fecha_entrega") or None,
        acta_numero=(datos.get("acta_numero") or "").strip() or None,
        observacion=(datos.get("observacion") or "").strip() or None,
        registrado_por=request.user,
    )
    try:
        entrega.save(force_insert=True)
    except Exception as exc:  # el CHECK de BD y la FK de contrato caen acá
        logger.exception("No se pudo registrar la entrega")
        return _error(f"No se pudo registrar la entrega: {exc}", status=422)

    entrega = (EntregaInsumoColegio.objects
               .select_related("colegio_sede", "contrato", "implemento")
               .get(pk=entrega.pk))
    return _ok({"ok": True, "entrega": _entrega_json(entrega)}, status=201)


@login_required
@modulo_required_json("educacion")
@require_http_methods(["POST"])
def api_entrega_eliminar(request, entrega_id: int):
    """Borra una entrega mal registrada. Solo quien la registró, o un admin.

    Se borra de verdad y no con baja lógica: mientras se está cargando el
    histórico de 2025 lo normal es equivocarse de sede, y dejar basura marcada
    como inactiva ensuciaría los conteos desde el primer día.
    """
    try:
        entrega = EntregaInsumoColegio.objects.get(pk=entrega_id)
    except EntregaInsumoColegio.DoesNotExist:
        return _error("La entrega no existe.", status=404)

    if (entrega.registrado_por_id != request.user.id
            and not request.user.is_superuser
            and not request.user.groups.filter(name="Admin").exists()):
        return _error("Solo quien registró la entrega puede borrarla.", status=403)

    entrega.delete()
    return _ok({"ok": True})


@login_required
@modulo_required_json("educacion")
@require_http_methods(["GET"])
def api_insumos_catalogo(request):
    """Catálogo `implemento`, con la categoría para poder agrupar.

    Devuelve todo el catálogo, no solo lo educativo: un colegio puede recibir
    implementación deportiva, y obligar a duplicar el ítem en otra categoría
    es justo lo que rompe la comparabilidad entre áreas.
    """
    from apps.banco_iniciativas.models import Implemento

    items = [{"codigo": i.codigo, "nombre": i.nombre, "categoria": i.categoria}
             for i in Implemento.objects.filter(activo=True)]
    return _ok({"items": items, "count": len(items)})


@login_required
@modulo_required_json("educacion")
@require_http_methods(["GET"])
def api_resumen_vigencia(request, vigencia: int):
    """Cuánto se entregó en una vigencia, por insumo y por colegio.

    Es la pregunta que motivó el módulo: "en 2025, ¿qué le entregamos a
    quién?". Se responde con dos agregados y no con la lista cruda porque la
    lista cruda es la que hoy vive en actas sueltas.
    """
    base = (EntregaInsumoColegio.objects
            .filter(vigencia=vigencia)
            .select_related("colegio_sede", "implemento"))

    por_insumo = {}
    por_colegio = {}
    for e in base:
        clave = e.insumo_nombre
        acc = por_insumo.setdefault(clave, {"insumo": clave, "cantidad": 0.0,
                                            "valor": 0.0, "sedes": set()})
        acc["cantidad"] += float(e.cantidad or 0)
        acc["valor"] += float(e.valor_total or 0)
        acc["sedes"].add(e.colegio_sede_id)

        if e.colegio_sede_id:
            nombre = e.colegio_sede.nombre_establecimiento
            col = por_colegio.setdefault(e.colegio_sede.dane_establecimiento, {
                "dane_establecimiento": e.colegio_sede.dane_establecimiento,
                "colegio": nombre, "entregas": 0, "valor": 0.0,
                "beneficiarios": 0, "matricula": 0, "sedes": set(),
            })
            col["entregas"] += 1
            col["valor"] += float(e.valor_total or 0)
            col["beneficiarios"] += e.beneficiarios or 0
            if e.colegio_sede_id not in col["sedes"]:
                col["sedes"].add(e.colegio_sede_id)
                col["matricula"] += e.colegio_sede.matricula_total or 0

    for acc in por_insumo.values():
        acc["sedes"] = len(acc["sedes"])
    for col in por_colegio.values():
        col["sedes"] = len(col["sedes"])

    return _ok({
        "vigencia": vigencia,
        "por_insumo": sorted(por_insumo.values(), key=lambda x: -x["valor"]),
        "por_colegio": sorted(por_colegio.values(), key=lambda x: -x["valor"]),
        "totales": {
            "entregas": base.count(),
            "valor": float(base.aggregate(v=Sum("valor_total"))["v"] or 0),
            "sedes": base.values("colegio_sede_id").distinct().count(),
        },
    })


def _decimal(valor, defecto):
    if valor in (None, ""):
        return defecto
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None


def _int(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None

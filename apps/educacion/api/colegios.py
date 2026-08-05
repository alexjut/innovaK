"""Endpoints GeoJSON de las sedes de colegios distritales.

Público, como el resto de capas cartográficas del Mapa Kennedy: es dato
oficial de la Secretaría de Educación, no información de personas.

La excepción es el resumen de entregas de insumos. Eso sí es ejecución de
contrato y solo se agrega para usuarios con sesión — el ciudadano ve dónde
están los colegios y cuántos alumnos tienen, no qué se le entregó a cada uno
mientras la vigencia está abierta.
"""
from __future__ import annotations

import logging

from django.db import ProgrammingError, connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# Traducción de los dominios de SED. Se hace acá y no en el front para que
# ningún cliente tenga que aprenderse los códigos.
CLASE = {
    1: "Distrital",
    2: "Distrital - Administración Contratada",
    3: "Oficial - Régimen Especial",
    4: "Privado",
    5: "Privado - Matrícula Contratada",
    6: "Privado - Régimen Especial",
}


def _ok(data):
    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})


@require_http_methods(["GET"])
def api_colegios_geojson(request):
    """`GET /educacion/api/colegios/geojson/` — sedes como FeatureCollection.

    Filtros opcionales:
      ?clase=1            código de clase (repetible)
      ?upz=44             código de UPZ (repetible)
      ?solo_principales=1 solo la sede A de cada colegio
      ?q=texto            busca en nombre de colegio, de sede y dirección

    Además del FeatureCollection devuelve `sin_ubicacion`: las sedes que la
    fuente reporta sin coordenada. No se pintan —no hay dónde— pero se listan,
    porque una sede que no aparece en el mapa se lee como "no existe" en vez
    de "no sabemos dónde queda".

    Se lee con SQL directo y tolerante a que la tabla no exista: la capa la
    consume un mapa público y es mejor una colección vacía que un 500.
    """
    clases = [c for c in request.GET.getlist("clase") if c.strip().isdigit()]
    upzs = [u for u in request.GET.getlist("upz") if u.strip().isdigit()]
    solo_principales = request.GET.get("solo_principales") == "1"
    q = (request.GET.get("q") or "").strip()

    sql = [
        "SELECT id, dane_sede, dane_establecimiento, nombre_establecimiento,",
        "       nombre_sede, orden_sede, clase, direccion, barrio_declarado,",
        "       telefono, email, upz_codigo, latitud, longitud, estrato_ideca,",
        "       matricula_total, matricula_corte, fecha_corte",
        "FROM colegio_sede WHERE activo IS TRUE",
    ]
    params: list = []
    if clases:
        sql.append("AND clase = ANY(%s)")
        params.append([int(c) for c in clases])
    if upzs:
        sql.append("AND upz_codigo = ANY(%s)")
        params.append([int(u) for u in upzs])
    if solo_principales:
        sql.append("AND upper(coalesce(orden_sede, '')) = 'A'")
    if q:
        sql.append("AND (nombre_establecimiento ILIKE %s OR nombre_sede ILIKE %s "
                   "OR coalesce(direccion, '') ILIKE %s)")
        params.extend([f"%{q}%"] * 3)
    sql.append("ORDER BY nombre_establecimiento, orden_sede")

    try:
        with connection.cursor() as cur:
            cur.execute("\n".join(sql), params)
            columnas = [c[0] for c in cur.description]
            filas = [dict(zip(columnas, r)) for r in cur.fetchall()]
    except ProgrammingError:
        logger.warning("api_colegios_geojson: la tabla `colegio_sede` no existe todavía")
        return _ok({"type": "FeatureCollection", "features": [], "count": 0,
                    "sin_ubicacion": [], "count_sin_ubicacion": 0,
                    "matricula_total": 0, "disponible": False})

    entregas = _resumen_entregas(request, [f["id"] for f in filas])

    features, sin_ubicacion = [], []
    for f in filas:
        props = {
            "id": f["id"],
            "dane_sede": f["dane_sede"],
            "dane_establecimiento": f["dane_establecimiento"],
            "colegio": f["nombre_establecimiento"],
            "sede": f["nombre_sede"],
            "orden_sede": f["orden_sede"],
            "es_principal": (f["orden_sede"] or "").strip().upper() == "A",
            "clase": f["clase"],
            "clase_nombre": CLASE.get(f["clase"], "Sin dato"),
            "direccion": f["direccion"],
            "barrio": f["barrio_declarado"],
            "telefono": f["telefono"],
            "upz_codigo": f["upz_codigo"],
            "estrato_ideca": f["estrato_ideca"],
            "matricula_total": f["matricula_total"],
            "matricula_corte": _iso(f["matricula_corte"]),
            "fecha_corte": _iso(f["fecha_corte"]),
        }
        if entregas is not None:
            props.update(entregas.get(f["id"], {"entregas_n": 0, "entregas_valor": 0.0}))

        if f["latitud"] is None or f["longitud"] is None:
            sin_ubicacion.append(props)
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [float(f["longitud"]), float(f["latitud"])]},
            "properties": props,
        })

    return _ok({
        "type": "FeatureCollection",
        "features": features,
        "count": len(features),
        "sin_ubicacion": sin_ubicacion,
        "count_sin_ubicacion": len(sin_ubicacion),
        "colegios": len({f["dane_establecimiento"] for f in filas}),
        "matricula_total": sum(f["matricula_total"] or 0 for f in filas),
        "disponible": True,
    })


def _resumen_entregas(request, sede_ids):
    """`{sede_id: {entregas_n, entregas_valor}}`, o `None` para anónimos.

    `None` (y no un dict vacío) para que el caller distinga "no se muestra" de
    "no hay entregas": pintar cero entregas a un ciudadano cuando en realidad
    no se le está contando sería peor que no mostrar el campo.
    """
    if not request.user.is_authenticated or not sede_ids:
        return None
    try:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT colegio_sede_id, count(*), coalesce(sum(valor_total), 0) "
                "FROM entrega_insumo_colegio WHERE colegio_sede_id = ANY(%s) "
                "GROUP BY colegio_sede_id",
                [list(sede_ids)],
            )
            return {r[0]: {"entregas_n": r[1], "entregas_valor": float(r[2])}
                    for r in cur.fetchall()}
    except ProgrammingError:
        logger.warning("_resumen_entregas: `entrega_insumo_colegio` no existe todavía")
        return None


def _iso(valor):
    return valor.isoformat() if valor else None

"""Servicios del módulo Infraestructura (panel + insights + seguimiento).

Trabaja sobre los contratos de obra (categoria VIAS/PARQUES/INTERVENTORIA) y
sus tramos viales / intervenciones de parque.
"""
import json
import urllib.parse
import urllib.request
from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum

from apps.presupuesto.models import (
    Contrato, TramoVialContrato, IntervencionParque,
)
from apps.presupuesto.services.marcador_avance import marcador, observaciones

# Malla Vial Integral (SDM/IDU) — geometría de los ejes viales por CIV.
FEATURESERVER = (
    "https://services2.arcgis.com/NEwhEo9GGSHXcRXV/arcgis/rest/services/"
    "Malla_Vial_Integral_Bogota_D_C/FeatureServer/0/query"
)
CIV_FIELD = "MVICIV"

# Categorías de contrato de obra y qué captura cada una (data-driven).
CATEGORIAS = {
    "VIAS": {"label": "Vías", "captura": "tramos"},
    "PARQUES": {"label": "Parques", "captura": "parques"},
    "INTERVENTORIA": {"label": "Interventoría", "captura": "ninguna"},
}


def consultar_malla_vial(civs):
    """Devuelve {civ_int: geojson_geometry} para una lista de CIV. Una llamada."""
    if not civs:
        return {}
    where = f"{CIV_FIELD} IN ({','.join(str(int(c)) for c in civs)})"
    params = {"where": where, "outFields": CIV_FIELD,
              "returnGeometry": "true", "outSR": "4326", "f": "geojson"}
    url = FEATURESERVER + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "innovaK/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    out = {}
    for feat in data.get("features", []):
        civ_val = feat.get("properties", {}).get(CIV_FIELD)
        geom = feat.get("geometry")
        if civ_val is not None and geom:
            out[int(round(float(civ_val)))] = geom
    return out


def recalcular_ejecucion(contrato_id):
    """Recalcula el % ejecución del contrato como promedio de sus unidades
    (tramos para VIAS, intervenciones para PARQUES). Devuelve el nuevo valor."""
    c = Contrato.objects.filter(id=contrato_id).first()
    if not c:
        return None
    pcts = []
    if c.categoria == "VIAS":
        pcts = [t.pct_avance or 0 for t in
                TramoVialContrato.objects.filter(contrato_id=contrato_id)]
    elif c.categoria == "PARQUES":
        pcts = [iv.pct_avance or 0 for iv in
                IntervencionParque.objects.filter(contrato_id=contrato_id)]
    if pcts:
        c.ejecucion = round(sum(pcts) / len(pcts))
        c.save(update_fields=["ejecucion"])
    return c.ejecucion


def sincronizar_kpi(contrato_id):
    """Alimenta el KPI del proyecto con las unidades terminadas (avance=100):
    tramos para VIAS, parques para PARQUES. Idempotente (un AvanceIndicador
    'MANUAL' por contrato, se actualiza). Devuelve la magnitud o None."""
    from apps.presupuesto.models import AvanceIndicador
    from apps.presupuesto.models.core import ContratoProyecto
    from apps.presupuesto.models.indicadores import Indicador

    c = Contrato.objects.filter(id=contrato_id).first()
    if not c or c.categoria not in ("VIAS", "PARQUES"):
        return None
    cp = ContratoProyecto.objects.filter(contrato_id=contrato_id).first()
    if not cp:
        return None
    ind = (Indicador.objects.filter(meta_proyecto__proyecto_id=cp.proyecto_id,
                                    activo=True).order_by("id").first())
    if not ind:
        return None

    if c.categoria == "VIAS":
        magnitud = TramoVialContrato.objects.filter(
            contrato_id=contrato_id, pct_avance__gte=100).count()
    else:
        magnitud = IntervencionParque.objects.filter(
            contrato_id=contrato_id, pct_avance__gte=100).count()

    # El marcador va DELIMITADO: acá el filtro es solo por indicador, y todos
    # los contratos de obra comparten el KPI del proyecto. Con el marcador
    # suelto, `infra_contrato=10` emparejaba `infra_contrato=102/103/104` y este
    # UPDATE pisaba el avance de OTRO contrato, en silencio. Ver
    # `services/marcador_avance.py`.
    marca = marcador("infra_contrato", contrato_id)
    hoy = date.today()
    av = (AvanceIndicador.objects
          .filter(indicador_id=ind.id, observaciones__contains=marca)
          .order_by("-id").first())
    if av:
        av.magnitud_aportada = magnitud
        av.fecha_aporte = hoy
        av.periodo = hoy.strftime("%Y-%m")
        av.save(update_fields=["magnitud_aportada", "fecha_aporte", "periodo"])
    else:
        AvanceIndicador.objects.create(
            indicador_id=ind.id, magnitud_aportada=magnitud,
            fecha_aporte=hoy, periodo=hoy.strftime("%Y-%m"),
            origen="MANUAL",
            observaciones=observaciones(
                marca, "unidades terminadas (seguimiento infraestructura)"),
        )
    return magnitud


def _estado_avance(pct):
    if pct is None:
        return "sin_dato"
    if pct >= 100:
        return "terminado"
    if pct <= 0:
        return "sin_iniciar"
    return "parcial"


def _contratos_infra_qs():
    return (Contrato.objects
            .exclude(categoria__isnull=True)
            .order_by("categoria", "-contrato_vigencia", "-contrato_numero"))


def panel_infraestructura():
    """Tiles + lista de contratos de obra para el panel principal."""
    contratos = list(_contratos_infra_qs())
    ids = [c.id for c in contratos]

    tramos_por_contrato = dict(
        TramoVialContrato.objects.filter(contrato_id__in=ids)
        .values("contrato_id").annotate(n=Count("id"))
        .values_list("contrato_id", "n"))
    parques_por_contrato = dict(
        IntervencionParque.objects.filter(contrato_id__in=ids)
        .values("contrato_id").annotate(n=Count("id"))
        .values_list("contrato_id", "n"))

    filas = []
    for c in contratos:
        filas.append({
            "id": c.id,
            "numero": str(c),
            "categoria": c.categoria,
            "objeto": c.objeto,
            "proyecto_codigo": c.proyecto_codigo,
            "proyecto_nombre": c.proyecto_nombre,
            "valor": float(c.valor) if c.valor is not None else None,
            "ejecucion": c.ejecucion,
            "interventoria_contrato": c.interventoria_contrato,
            "n_tramos": tramos_por_contrato.get(c.id, 0),
            "n_parques": parques_por_contrato.get(c.id, 0),
        })

    valor_total = sum((c.valor or 0) for c in contratos)
    ejecs = [c.ejecucion for c in contratos if c.ejecucion is not None]
    return {
        "tiles": {
            "n_contratos": len(contratos),
            "valor_total": float(valor_total),
            "avance_global": round(sum(ejecs) / len(ejecs), 1) if ejecs else 0,
            "n_tramos": TramoVialContrato.objects.filter(contrato_id__in=ids).count(),
            "n_parques": IntervencionParque.objects.filter(contrato_id__in=ids)
                         .values("parque_id").distinct().count(),
        },
        "contratos": filas,
    }


def detalle_contrato_infra(contrato_id):
    """Detalle de un contrato: sus tramos y parques con avance + geo_status."""
    c = _contratos_infra_qs().filter(id=contrato_id).first()
    if not c:
        return None
    tramos = [{
        "id": t.id, "civ": t.civ, "eje_vial": t.eje_vial,
        "desde": t.desde, "hasta": t.hasta,
        "valor_intervencion": float(t.valor_intervencion) if t.valor_intervencion is not None else None,
        "pct_avance": t.pct_avance, "geo_status": t.geo_status,
        "estado": _estado_avance(t.pct_avance),
    } for t in TramoVialContrato.objects.filter(contrato_id=contrato_id).order_by("eje_vial")]
    parques = [{
        "id": iv.id, "parque_id": iv.parque_id,
        "codigo_parque": iv.parque.id_parque if iv.parque_id else None,
        "nombre": iv.parque.nombre if iv.parque_id else None,
        "direccion": iv.direccion,
        "pct_avance": iv.pct_avance, "estado": _estado_avance(iv.pct_avance),
    } for iv in IntervencionParque.objects.select_related("parque")
                  .filter(contrato_id=contrato_id)]
    return {
        "id": c.id, "numero": str(c), "categoria": c.categoria,
        "objeto": c.objeto, "proyecto_codigo": c.proyecto_codigo,
        "proyecto_nombre": c.proyecto_nombre,
        "valor": float(c.valor) if c.valor is not None else None,
        "ejecucion": c.ejecucion,
        "interventoria_contrato": c.interventoria_contrato,
        "interventoria_valor": float(c.interventoria_valor) if c.interventoria_valor is not None else None,
        "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
        "fecha_fin": c.fecha_fin.isoformat() if c.fecha_fin else None,
        "tramos": tramos,
        "parques": parques,
    }


def _reducir_imagen(blob, mime, max_lado=1280, calidad=70):
    """Redimensiona (lado máx 1280px) y comprime la foto a JPEG para que la
    evidencia ocupe poco en Mongo. Si no es imagen procesable, devuelve el
    original sin tocar."""
    import io
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(blob))
        img = ImageOps.exif_transpose(img)  # respeta orientación de la cámara
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.thumbnail((max_lado, max_lado))  # mantiene proporción, solo reduce
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=calidad, optimize=True)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return blob, (mime or "image/jpeg")


def _guardar_evidencia(blob, mime, corte_id, contrato_id, cual):
    """Reduce y cifra una foto del corte en Mongo. Devuelve el mongo_id o None."""
    if not blob:
        return None
    try:
        from apps.documentos.services import mongo_storage
        b, m = _reducir_imagen(blob, mime)
        return mongo_storage.guardar(
            b, m, owner={"tipo": "corte_avance_obra", "corte_id": corte_id,
                         "contrato_id": contrato_id, "cual": cual})
    except Exception:
        return None


def registrar_corte(contrato_id, objeto_tipo, objeto_id, fecha, pct,
                    observacion=None, foto_antes=None, foto_antes_mime=None,
                    foto_despues=None, foto_despues_mime=None, autor_id=None):
    """Registra un corte de avance (historial) y aplica el % al objeto:
      - objeto_tipo='contrato' → contrato.ejecucion = pct (caso interventoría).
      - objeto_tipo='tramo'    → tramo.pct_avance = pct → recalcula ejecución + KPI.
      - objeto_tipo='parque'   → intervencion.pct_avance = pct → recalcula + KPI.
    Evidencia ANTES y DESPUÉS: cada foto se reduce y cifra en Mongo.
    Devuelve la instancia CorteAvanceObra creada."""
    from apps.presupuesto.models import (
        CorteAvanceObra, Contrato, TramoVialContrato, IntervencionParque,
    )
    pct = max(0, min(100, int(pct or 0)))
    corte = CorteAvanceObra.objects.create(
        contrato_id=contrato_id, objeto_tipo=objeto_tipo,
        objeto_id=objeto_id if objeto_tipo != "contrato" else None,
        fecha=fecha, pct=pct, observacion=observacion, autor_id=autor_id,
    )
    antes = _guardar_evidencia(foto_antes, foto_antes_mime, corte.id, contrato_id, "antes")
    despues = _guardar_evidencia(foto_despues, foto_despues_mime, corte.id, contrato_id, "despues")
    if antes or despues:
        corte.foto_antes_mongo_id = antes
        corte.foto_despues_mongo_id = despues
        corte.save(update_fields=["foto_antes_mongo_id", "foto_despues_mongo_id"])

    # Aplica el % al objeto y propaga.
    if objeto_tipo == "contrato":
        Contrato.objects.filter(id=contrato_id).update(ejecucion=pct)
    elif objeto_tipo == "tramo":
        TramoVialContrato.objects.filter(id=objeto_id).update(pct_avance=pct)
        recalcular_ejecucion(contrato_id)
        sincronizar_kpi(contrato_id)
    elif objeto_tipo == "parque":
        IntervencionParque.objects.filter(id=objeto_id).update(pct_avance=pct)
        recalcular_ejecucion(contrato_id)
        sincronizar_kpi(contrato_id)
    return corte


def listar_cortes(contrato_id=None, objeto_tipo=None, objeto_id=None):
    """Historial de cortes filtrable por contrato o por objeto (tramo/parque)."""
    from apps.presupuesto.models import CorteAvanceObra
    qs = CorteAvanceObra.objects.all()
    if contrato_id:
        qs = qs.filter(contrato_id=contrato_id)
    if objeto_tipo:
        qs = qs.filter(objeto_tipo=objeto_tipo)
    if objeto_id is not None:
        qs = qs.filter(objeto_id=objeto_id)
    return [{
        "id": x.id, "objeto_tipo": x.objeto_tipo, "objeto_id": x.objeto_id,
        "fecha": x.fecha.isoformat() if x.fecha else None,
        "pct": x.pct, "observacion": x.observacion,
        "tiene_foto_antes": bool(x.foto_antes_mongo_id),
        "tiene_foto_despues": bool(x.foto_despues_mongo_id),
        "autor_id": x.autor_id,
    } for x in qs]


def geojson_contrato(contrato_id):
    """FeatureCollection con la geometría del contrato (tramos LineString +
    parques Point) para el mini-mapa del detalle. Cada feature lleva `tipo`
    (tramo|parque) y `pct_avance` para colorear por avance."""
    from apps.georeferenciacion.api.views import _centroide
    features = []
    for t in TramoVialContrato.objects.filter(
            contrato_id=contrato_id, geo_status=TramoVialContrato.OK):
        features.append({
            "type": "Feature", "geometry": t.geom,
            "properties": {"tipo": "tramo", "eje_vial": t.eje_vial,
                           "desde": t.desde, "hasta": t.hasta, "civ": t.civ,
                           "pct_avance": t.pct_avance},
        })
    for iv in (IntervencionParque.objects.select_related("parque")
               .filter(contrato_id=contrato_id)):
        centro = _centroide(iv.parque.geometry if iv.parque_id else None)
        if not centro:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": centro},
            "properties": {"tipo": "parque",
                           "codigo_parque": iv.parque.id_parque,
                           "nombre": iv.parque.nombre,
                           "pct_avance": iv.pct_avance},
        })
    return {"type": "FeatureCollection", "features": features, "count": len(features)}


def insights_infraestructura():
    """Agregados para el dashboard de insights (Chart.js)."""
    contratos = list(_contratos_infra_qs())
    ids = [c.id for c in contratos]
    tramos = list(TramoVialContrato.objects.filter(contrato_id__in=ids))
    parques = list(IntervencionParque.objects.filter(contrato_id__in=ids))

    # Distribución de tramos por estado de avance.
    dist = {"sin_iniciar": 0, "parcial": 0, "terminado": 0}
    for t in tramos:
        dist[_estado_avance(t.pct_avance)] = dist.get(_estado_avance(t.pct_avance), 0) + 1

    # Avance por contrato.
    por_contrato = [{
        "contrato": str(c), "categoria": c.categoria,
        "ejecucion": c.ejecucion or 0,
        "valor": float(c.valor) if c.valor is not None else 0,
    } for c in contratos]

    # Valor invertido por categoría.
    por_categoria = {}
    for c in contratos:
        por_categoria[c.categoria] = por_categoria.get(c.categoria, 0) + float(c.valor or 0)

    # Valor de intervención de tramos por estado.
    valor_por_estado = {"sin_iniciar": 0.0, "parcial": 0.0, "terminado": 0.0}
    for t in tramos:
        valor_por_estado[_estado_avance(t.pct_avance)] += float(t.valor_intervencion or 0)

    n_tramos_ok = sum(1 for t in tramos if (t.pct_avance or 0) >= 100)
    return {
        "kpis": {
            "n_contratos": len(contratos),
            "valor_total": float(sum((c.valor or 0) for c in contratos)),
            "n_tramos": len(tramos),
            "tramos_terminados": n_tramos_ok,
            "pct_tramos_terminados": round(100 * n_tramos_ok / len(tramos), 1) if tramos else 0,
            "n_parques": len({p.parque_id for p in parques}),
            "geo_pendientes": sum(1 for t in tramos
                                  if t.geo_status != TramoVialContrato.OK),
        },
        "tramos_por_estado": dist,
        "valor_tramos_por_estado": {k: round(v, 2) for k, v in valor_por_estado.items()},
        "avance_por_contrato": por_contrato,
        "valor_por_categoria": [{"categoria": k, "valor": round(v, 2)}
                                for k, v in sorted(por_categoria.items())],
    }

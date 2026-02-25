# apps/georeferenciacion/views/mapa_kennedy_view.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any

from django.shortcuts import render
from django.db.models import F
from django.utils import timezone

# cache es opcional: si no está configurado, igual funciona.
try:
    from django.core.cache import cache
except Exception:  # pragma: no cover
    cache = None  # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Importar modelos de forma flexible (según tu estructura real)
# ---------------------------------------------------------------------
try:
    from apps.georeferenciacion.models.models_localizacion import UPZ, Barrio
except Exception as e:  # pragma: no cover
    logger.warning("No se pudieron importar modelos específicos: %s", e)
    UPZ = None  # type: ignore
    Barrio = None  # type: ignore

# ---------------------------------------------------------------------
# Fallback a choices.py (si la BD no tiene datos o modelos)
# Estructuras esperadas:
#   UPZ_CHOICES      -> [(codigo, nombre), ...]
#   BARRIO_CHOICES   -> [(codigo, nombre, upz_codigo) o (codigo, nombre)]
# ---------------------------------------------------------------------
try:
    from apps.georeferenciacion.choices import UPZ_CHOICES, BARRIO_CHOICES
except Exception:  # pragma: no cover
    UPZ_CHOICES = []
    BARRIO_CHOICES = []


# ---------------------------------------------------------------------
# Utilidades para construir las listas para el template
# ---------------------------------------------------------------------
def _upz_y_barrios_desde_bd() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Lee UPZ y Barrios desde BD.
    Retorna:
      - upz_list:    [{codigo, nombre, label}]
      - barrio_list: [{codigo, nombre, upz_codigo, label}]
    """
    if UPZ is None or Barrio is None:
        return [], []

    # Si hay problemas de conexión/tablas, caemos a choices
    try:
        has_upz = UPZ.objects.exists()
        has_barrio = Barrio.objects.exists()
    except Exception as e:  # pragma: no cover
        logger.warning("Falló verificación de existencia de UPZ/Barrio: %s", e)
        return [], []

    if not (has_upz or has_barrio):
        return [], []

    # UPZ
    try:
        upz_list = list(UPZ.objects.values("codigo", "nombre").order_by("nombre"))
    except Exception as e:  # pragma: no cover
        logger.error("Error consultando UPZ: %s", e)
        upz_list = []

    for u in upz_list:
        u["label"] = (u.get("nombre") or "").strip() or f"UPZ {u.get('codigo')}"

    # Barrios: si el modelo tiene campo upz_codigo directo lo usamos,
    # de lo contrario lo anotamos desde la FK upz__codigo.
    try:
        if hasattr(Barrio, "upz_codigo"):
            barrio_vals = list(
                Barrio.objects.values("codigo", "nombre", "upz_codigo").order_by("nombre")
            )
        else:
            qs = (
                Barrio.objects
                .annotate(_upz_codigo=F("upz__codigo"))
                .values("codigo", "nombre", "_upz_codigo")
                .order_by("nombre")
            )
            barrio_vals = [
                {
                    "codigo": b["codigo"],
                    "nombre": b["nombre"],
                    "upz_codigo": b["_upz_codigo"],
                }
                for b in qs
            ]
    except Exception as e:  # pragma: no cover
        logger.error("Error consultando Barrios: %s", e)
        barrio_vals = []

    for b in barrio_vals:
        b["label"] = (b.get("nombre") or "").strip() or f"Barrio {b.get('codigo')}"

    return upz_list, barrio_vals


def _upz_y_barrios_desde_choices() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Convierte UPZ_CHOICES y BARRIO_CHOICES en las estructuras
    esperadas por la plantilla.
    """
    upz_list = [{"codigo": c, "nombre": n, "label": (n or f"UPZ {c}")} for c, n in UPZ_CHOICES]

    barrio_list: List[Dict[str, Any]] = []
    for item in BARRIO_CHOICES:
        if not isinstance(item, (list, tuple)):
            continue
        if len(item) == 3:
            codigo, nombre, upz_codigo = item
        elif len(item) == 2:
            codigo, nombre = item
            upz_codigo = ""
        else:
            continue
        barrio_list.append(
            {
                "codigo": codigo,
                "nombre": nombre,
                "upz_codigo": upz_codigo,
                "label": (nombre or f"Barrio {codigo}"),
            }
        )
    return upz_list, barrio_list


def _cargar_listas_con_cache(ttl_seconds: int = 300) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Intenta usar caché (5 min por defecto). Si no hay caché o falla, consulta normal.
    """
    cache_key = "georef_upz_barrio_lists:v1"
    if cache:
        data = cache.get(cache_key)
        if data and isinstance(data, (tuple, list)) and len(data) == 2:
            return data  # type: ignore

    upz_list, barrio_list = _upz_y_barrios_desde_bd()
    if not upz_list and not barrio_list:
        upz_list, barrio_list = _upz_y_barrios_desde_choices()

    if cache:
        try:
            cache.set(cache_key, (upz_list, barrio_list), ttl_seconds)
        except Exception as e:  # pragma: no cover
            logger.debug("No se pudo cachear listas UPZ/Barrios: %s", e)

    return upz_list, barrio_list


# ---------------------------------------------------------------------
# Vista
# ---------------------------------------------------------------------
def mapa_kennedy(request):
    """
    Renderiza el mapa principal con listas de UPZ y Barrios.
    Template: geo-mapas/mapa_kennedy_standalone.html
    Contexto:
      - upz_list, barrio_list: listas normalizadas
      - ultima_actualizacion: timezone.now() (para cache busting del JS)
    """
    upz_list, barrio_list = _cargar_listas_con_cache(ttl_seconds=300)

    context = {
        "upz_list": upz_list,
        "barrio_list": barrio_list,
        "ultima_actualizacion": timezone.now(),
    }

    # Coincide con tu archivo existente:
    # apps/georeferenciacion/templates/geo-mapas/mapa_kennedy_standalone.html
    return render(request, "geo-mapas/mapa_kennedy_standalone.html", context)

import os
import json
import pandas as pd
import folium
from django.shortcuts import render
from django.conf import settings

# ---- Helpers robustos ----------------------------------------

def load_geojson(path):
    """Carga GeoJSON desde ruta (admite ruta relativa) y devuelve dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def pick_field(props_keys, *candidates):
    """Devuelve el primer campo existente según candidatos."""
    for c in candidates:
        if c and c in props_keys:
            return c
    return None

def tooltip_fields_from_sample(geojson_dict, candidates_by_label):
    """
    A partir de un geojson y un dict {alias: [candidatos]},
    devuelve (campos, aliases) en el mismo orden solo con los que existen.
    """
    # toma cualquier feature con propiedades
    feat = next((ft for ft in geojson_dict.get("features", []) if ft.get("properties")), None)
    if not feat:
        return [], []
    keys = set(feat["properties"].keys())

    fields, aliases = [], []
    for alias, candidate_list in candidates_by_label.items():
        f = pick_field(keys, *candidate_list)
        if f:
            fields.append(f)
            aliases.append(alias)
    return fields, aliases

# --------------------------------------------------------------

def mapa_escuelas_view(request):
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "../data")

    # CSV de puntos
    csv_path = os.path.join(data_dir, "escuelas.csv")
    # Si el CSV viene con acentos/latin-1, descomenta la siguiente línea:
    # df = pd.read_csv(csv_path, encoding="latin-1")
    df = pd.read_csv(csv_path)

    mapa = folium.Map(location=[4.63, -74.16], zoom_start=13, control_scale=True)

    # Marcadores de escuelas (tolerante a faltantes)
    for _, row in df.iterrows():
        lat = row.get("LATITUD")
        lon = row.get("LONGITUD")
        if pd.isna(lat) or pd.isna(lon):
            continue
        nombre = row.get("NOMBRE", "Sin nombre")
        tipo = row.get("TIPO", "N/A")
        direccion = row.get("DIRECCION", "Dirección no registrada")

        folium.Marker(
            location=[float(lat), float(lon)],
            popup=f"{nombre} ({tipo})\n{direccion}",
            icon=folium.Icon(color="green" if str(tipo).lower() == "deporte" else "blue"),
        ).add_to(mapa)

    # ---- Barrios ------------------------------------------------
    barrios_path = os.path.join(data_dir, "barrios_kennedy.geojson")
    barrios_gj = load_geojson(barrios_path)

    b_fields, b_aliases = tooltip_fields_from_sample(
        barrios_gj,
        {
            "Barrio": ["NOMB_BARR", "NOMBRE", "BARRIO", "Nomb_Barr"],
            "Código barrio": ["BAR_COD", "BAR_ID"],
            "Zona": ["COD_ZONA"],
            "Localidad": ["COD_LOC"],
        },
    )

    folium.GeoJson(
        barrios_gj,
        name="Barrios",
        style_function=lambda x: {"fillColor": "#ffff99", "color": "gray", "weight": 1, "fillOpacity": 0.3},
        tooltip=folium.GeoJsonTooltip(fields=b_fields, aliases=b_aliases, localize=True) if b_fields else None,
    ).add_to(mapa)

    # ---- UPZ ----------------------------------------------------
    upz_path = os.path.join(data_dir, "Upz.geojson")
    upz_gj = load_geojson(upz_path)

    upz_fields, upz_aliases = tooltip_fields_from_sample(
        upz_gj,
        {
            "UPZ": ["NOMBRE", "NOM_UPZ", "UPZ", "NOMBRE_UPZ"],
            "Código": ["COD_UPZ", "CODIGO", "ID_UPZ"],
        },
    )

    folium.GeoJson(
        upz_gj,
        name="UPZ",
        style_function=lambda x: {"fillColor": "#99ccff", "color": "#0077cc", "weight": 2, "fillOpacity": 0.2},
        tooltip=folium.GeoJsonTooltip(fields=upz_fields, aliases=upz_aliases, localize=True) if upz_fields else None,
    ).add_to(mapa)

    # ---- Parques ------------------------------------------------
    parques_path = os.path.join(data_dir, "parques.geojson")
    parques_gj = load_geojson(parques_path)

    p_fields, p_aliases = tooltip_fields_from_sample(
        parques_gj,
        {
            "Parque": ["NOMBRE", "NOM_PARQ", "NOM_PARQUE", "NOM_PAR", "parque"],
            "Tipo": ["TIPO", "TIPO_PARQ"],
        },
    )

    folium.GeoJson(
        parques_gj,
        name="Parques",
        style_function=lambda x: {"fillColor": "#99ff99", "color": "#00aa00", "weight": 1, "fillOpacity": 0.4},
        tooltip=folium.GeoJsonTooltip(fields=p_fields, aliases=p_aliases, sticky=False, localize=True) if p_fields else None,
    ).add_to(mapa)

    # ---- Contorno localidad ------------------------------------
    loc_path = os.path.join(data_dir, "localidad_kennedy.geojson")
    if os.path.exists(loc_path):
        folium.GeoJson(
            load_geojson(loc_path),
            name="Localidad Kennedy",
            style_function=lambda x: {"fillColor": "#cccccc", "color": "black", "weight": 2, "fillOpacity": 0.05},
            tooltip="Localidad Kennedy",
        ).add_to(mapa)

    # Control de capas
    folium.LayerControl(collapsed=False).add_to(mapa)

    # Salida HTML (static/dist/mapas)
    output_dir = os.path.join(getattr(settings, "BASE_DIR", ""), "static", "dist", "mapas")
    os.makedirs(output_dir, exist_ok=True)
    mapa_path = os.path.join(output_dir, "mapa_escuelas.html")
    mapa.save(mapa_path)

    return render(request, "geo-mapas/mapa_embebido.html")

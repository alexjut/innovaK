"""
import os
import pandas as pd
import folium
from django.shortcuts import render

def mapa_escuelas_view(request):
    csv_path = os.path.join(os.path.dirname(__file__), '../data/escuelas.csv')
    df = pd.read_csv(csv_path)

    mapa = folium.Map(location=[4.63, -74.16], zoom_start=13)

    for _, row in df.iterrows():
        folium.Marker(
            location=[row['LATITUD'], row['LONGITUD']],
            popup=f"{row['NOMBRE']} ({row['TIPO']})\n{row['DIRECCION']}",
            icon=folium.Icon(color='green' if row['TIPO'] == 'Deporte' else 'blue')
        ).add_to(mapa)

    output_dir = os.path.join('static', 'dist', 'mapas')
    os.makedirs(output_dir, exist_ok=True)

    mapa_path = os.path.join(output_dir, 'mapa_escuelas.html')
    mapa.save(mapa_path)

    return render(request, 'geo-mapas/mapa_embebido.html')
"""

import os
import pandas as pd
import folium
from django.shortcuts import render

def mapa_escuelas_view(request):
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, '../data')

    csv_path = os.path.join(data_dir, 'escuelas.csv')
    df = pd.read_csv(csv_path)

    mapa = folium.Map(location=[4.63, -74.16], zoom_start=13)

    # 🎯 Marcadores de escuelas
    for _, row in df.iterrows():
        folium.Marker(
            location=[row['LATITUD'], row['LONGITUD']],
            popup=f"{row['NOMBRE']} ({row['TIPO']})\n{row['DIRECCION']}",
            icon=folium.Icon(color='green' if row['TIPO'] == 'Deporte' else 'blue')
        ).add_to(mapa)

    # 🟫 Polígonos de barrios
    folium.GeoJson(
        os.path.join(data_dir, 'barrios_kennedy.geojson'),
        name='Barrios',
        style_function=lambda x: {
            'fillColor': '#ffff99',
            'color': 'gray',
            'weight': 1,
            'fillOpacity': 0.3
        },
        tooltip=folium.GeoJsonTooltip(fields=['NOMBRE'], aliases=['Barrio:'])
    ).add_to(mapa)

    # 🔷 Polígonos de UPZ
    folium.GeoJson(
        os.path.join(data_dir, 'Upz.geojson'),
        name='UPZ',
        style_function=lambda x: {
            'fillColor': '#99ccff',
            'color': '#0077cc',
            'weight': 2,
            'fillOpacity': 0.2
        },
        tooltip=folium.GeoJsonTooltip(fields=['NOMBRE'], aliases=['UPZ:'])
    ).add_to(mapa)

    # 🟢 Polígonos de parques
    folium.GeoJson(
        os.path.join(data_dir, 'parques.geojson'),
        name='Parques',
        style_function=lambda x: {
            'fillColor': '#99ff99',
            'color': '#00aa00',
            'weight': 1,
            'fillOpacity': 0.4
        },
        tooltip=folium.GeoJsonTooltip(fields=['NOMBRE'], aliases=['Parque:'], sticky=False)
    ).add_to(mapa)

    # 🖤 Contorno de la localidad
    folium.GeoJson(
        os.path.join(data_dir, 'localidad_kennedy.geojson'),
        name='Localidad Kennedy',
        style_function=lambda x: {
            'fillColor': '#cccccc',
            'color': 'black',
            'weight': 2,
            'fillOpacity': 0.05
        },
        tooltip="Localidad Kennedy"
    ).add_to(mapa)

    # Control de capas
    folium.LayerControl(collapsed=False).add_to(mapa)

    output_dir = os.path.join('static', 'dist', 'mapas')
    os.makedirs(output_dir, exist_ok=True)
    mapa_path = os.path.join(output_dir, 'mapa_escuelas.html')
    mapa.save(mapa_path)

    return render(request, 'geo-mapas/mapa_embebido.html')

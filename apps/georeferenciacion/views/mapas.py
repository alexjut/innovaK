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

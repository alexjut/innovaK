import os
import folium
from django.shortcuts import render

def mapa_escuelas_view(request):
    os.makedirs("static/mapas", exist_ok=True)
    mapa = folium.Map(location=[4.60971, -74.08175], zoom_start=12)
    folium.Marker(
        [4.60971, -74.08175],
        popup="Escuela de ejemplo",
        tooltip="Click para más info"
    ).add_to(mapa)

    mapa.save("static/mapas/mapa_escuelas.html")

    return render(request, "geo-mapas/mapa_embebido.html")
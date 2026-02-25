# apps/georeferenciacion/views/mapa_kennedy.py
from django.shortcuts import render
from ..models import UPZ, Barrio

def mapa_kennedy_view(request):
    ctx = {
        "upz_list": UPZ.objects.all().order_by("nombre"),
        "barrio_list": Barrio.objects.all().order_by("nombre"),
    }
    return render(request, "geo-mapas/mapa_kennedy_standalone.html", ctx)

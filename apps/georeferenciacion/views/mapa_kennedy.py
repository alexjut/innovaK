# apps/georeferenciacion/views/mapa_kennedy.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import UPZ, Barrio


@login_required
def mapa_kennedy_view(request):
    ctx = {
        "upz_list": UPZ.objects.all().order_by("nombre"),
        "barrio_list": Barrio.objects.all().order_by("nombre"),
    }
    return render(request, "geo-mapas/mapa_kennedy_standalone.html", ctx)

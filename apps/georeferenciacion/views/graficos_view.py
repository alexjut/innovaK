# -*- coding: utf-8 -*-
from django.shortcuts import render

def graficos_dashboard(request):
    # Si quieres pasar contexto, hazlo aquí.
    return render(request, "geo-mapas/graficos.html", {})

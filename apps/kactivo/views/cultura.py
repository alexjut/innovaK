from django.shortcuts import render
from kactivo.models import CaracterizacionCultura

def listado_caracterizaciones(request):
    datos = CaracterizacionCultura.objects.all()
    return render(request, 'kactivo/cultura/listado.html', {'caracterizaciones': datos})
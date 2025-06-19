from django.shortcuts import render
from kactivo.models import Acudiente

def listado_acudientes(request):
    acudientes = Acudiente.objects.all()
    return render(request, 'kactivo/deporte/listado.html', {'acudientes': acudientes})
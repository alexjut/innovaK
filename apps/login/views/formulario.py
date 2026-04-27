from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def index_view(request):
    return render(request, 'login/formulario/index.html')


@login_required
def evento_view(request):
    return render(request, 'login/formulario/evento.html')


@login_required
def form_view(request):
    return render(request, 'login/formulario/formulario.html')


@login_required
def listado_view(request):
    personas = [
        {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
            "nombres": "Ana",
            "apellidos": "Pérez",
            "entidad": "Alcaldía Local de Kennedy",
            "correo": "ana.perez@example.com"
        },
        {
            "tipo_documento": "TI",
            "numero_documento": "987654321",
            "nombres": "Carlos",
            "apellidos": "Ramírez",
            "entidad": "Fundación Cultural",
            "correo": "carlos.ramirez@example.com"
        }
    ]
    return render(request, 'login/formulario/listado.html', {"personas": personas})

from django.shortcuts import render

def index_view(request):
    return render(request, 'login/formulario/index.html')

def evento_view(request):
    return render(request, 'login/formulario/evento.html')

def form_view(request):
    return render(request, 'login/formulario/formulario.html')


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

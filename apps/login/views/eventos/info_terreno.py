"""Info terreno: confirmación de llegada del funcionario al campo.

Migrado a Angular (`/app/p/info-terreno/<id>`): el flujo público de
confirmación (GPS + fotos) lo sirven los endpoints DRF AllowAny en
`apps.login.api.public_info_terreno`. Estas vistas solo redirigen los
QR/bookmarks viejos a la página Angular nativa.
"""
from django.shortcuts import redirect


def confirmar_llegada_info_terreno(request, evento_id):
    return redirect(f'/app/p/info-terreno/{evento_id}')


def info_terreno_exitoso(request, evento_id):
    return redirect(f'/app/p/info-terreno/{evento_id}')

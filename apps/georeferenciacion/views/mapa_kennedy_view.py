# apps/georeferenciacion/views/mapa_kennedy_view.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def mapa_kennedy(request):
    """Migrado a Angular: el mapa de Kennedy vive en /app/mapa."""
    return redirect("/app/mapa")

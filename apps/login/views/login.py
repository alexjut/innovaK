from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def login_view(request):
    # Full Angular (PR-2, 2026-06-11): única puerta de entrada el SPA.
    # El login de sesión Django queda solo en /admin (staff).
    return redirect('/app/auth/login')


@login_required
def logout_view(request):
    # Mata la sesión Django residual (admin/staff) y manda al SPA.
    if request.method == 'POST':
        logout(request)
    return redirect('/app/auth/login')

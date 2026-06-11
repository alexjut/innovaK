from django.shortcuts import redirect


def home_view(request):
    # Full Angular (PR-2): la raíz aterriza en el SPA; el authGuard
    # decide si va al hub o a /app/auth/login.
    return redirect('/app/')

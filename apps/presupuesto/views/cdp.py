# apps/presupuesto/views/cdp.py
"""CDP — migrado a Angular (Etapa D PR-1).

Solo queda `cdp_list` como puente (lo referencia el sidebar de
`templates/base.html`). El resto de la gestión de CDP vive en Angular.
"""
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import redirect


@login_required
@modulo_required("presupuesto_cdp")
def cdp_list(request):
    """Migrado a Angular: listado de CDPs."""
    return redirect("/app/presupuesto/cdps")

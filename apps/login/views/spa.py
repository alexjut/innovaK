"""SPA Angular servida desde Django.

Etapa D PR-5 alternativa: en lugar de servir Angular en un puerto
distinto (`ng serve` :4200, bloqueado por firewall), Django sirve el
build de producción de Angular bajo `/app/*`. Ventajas:

- Mismo dominio que Django → cero CORS.
- Mismo puerto 8034 que ya está abierto al exterior.
- Reemplazable después (PR-15) por Nginx static directo, sin tocar
  rutas Angular ni código.

Comportamiento:
- `/app/`             → devuelve index.html (Angular monta).
- `/app/foo/bar`      → devuelve index.html (Angular routing client-side).
- `/app/main-xxx.js`  → devuelve el asset del build.
- `/app/styles.css`   → idem.

Para rebuildear, en el host:
    cd frontend && npm run build -- --base-href=/app/

El build queda en `frontend/dist/innovak-frontend/browser/` y esta vista
lo lee directo del filesystem.
"""
import mimetypes
from pathlib import Path

from django.http import FileResponse, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET


# Apunta a frontend/dist/innovak-frontend/browser/ desde apps/login/views/spa.py
FRONTEND_BUILD = (
    Path(__file__).resolve().parent.parent.parent.parent
    / 'frontend' / 'dist' / 'innovak-frontend' / 'browser'
)


@csrf_exempt
@require_GET
def angular_spa(request, resource: str = ''):
    """Sirve el build de Angular en `/app/<resource>`.

    Si `resource` apunta a un archivo existente del build, lo devuelve
    con su MIME correcto. Si no (ruta de routing client-side de Angular),
    devuelve `index.html` para que Angular monte y muestre la vista.
    """
    if not FRONTEND_BUILD.exists():
        return HttpResponse(
            "Angular no está compilado. Corre en el host:\n"
            "    cd frontend && npm run build -- --base-href=/app/",
            status=503,
            content_type='text/plain; charset=utf-8',
        )

    # Sanitiza el path para evitar traversal.
    safe = (resource or '').lstrip('/')
    if '..' in safe.split('/'):
        return HttpResponse('Bad path', status=400)

    candidate = (FRONTEND_BUILD / safe).resolve() if safe else None
    if candidate and candidate.is_file() and FRONTEND_BUILD in candidate.parents:
        return _send_file(candidate, immutable=_is_hashed_asset(candidate.name))

    # Fallback: index.html para rutas de Angular (login, hub, etc.).
    index = FRONTEND_BUILD / 'index.html'
    if not index.is_file():
        return HttpResponse("index.html no encontrado en el build.", status=503)
    return _send_file(index, immutable=False)


def _is_hashed_asset(filename: str) -> bool:
    """Los chunks de Angular tienen hash en el nombre (chunk-XXXXX.js).
    Esos pueden cachearse con immutable; el resto no.
    """
    if not filename:
        return False
    name = filename.rsplit('.', 1)[0]
    return any(
        name.startswith(prefix) and len(name) > len(prefix) + 4
        for prefix in ('main-', 'polyfills-', 'styles-', 'chunk-')
    )


def _send_file(path: Path, *, immutable: bool):
    content_type, _ = mimetypes.guess_type(path.name)
    response = FileResponse(open(path, 'rb'), content_type=content_type or 'application/octet-stream')
    if immutable:
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
    else:
        response['Cache-Control'] = 'no-cache'
    return response

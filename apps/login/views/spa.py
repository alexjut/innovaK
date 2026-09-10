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
from django.views.decorators.http import require_http_methods


# Apunta a frontend/dist/innovak-frontend/browser/ desde apps/login/views/spa.py
FRONTEND_BUILD = (
    Path(__file__).resolve().parent.parent.parent.parent
    / 'frontend' / 'dist' / 'innovak-frontend' / 'browser'
)


@csrf_exempt
@require_http_methods(["GET", "HEAD"])
def angular_spa(request, resource: str = ''):
    """Sirve el build de Angular en `/app/<resource>`.

    Si `resource` apunta a un archivo existente del build, lo devuelve
    con su MIME correcto. Si no (ruta de routing client-side de Angular),
    devuelve `index.html` para que Angular monte y muestre la vista.

    ACEPTA HEAD, y no es un detalle de purista. Con `@require_GET` un HEAD
    devolvía **405** en vez de las cabeceras, así que cualquier monitor de
    disponibilidad que use HEAD —que es lo normal, porque no quiere el
    cuerpo— vería la aplicación caída estando sana. También despista a quien
    diagnostica con `curl -I`: leyendo las cabeceras del 405 se concluye que
    la SPA se sirve sin `Cache-Control`, que es exactamente lo contrario de
    lo que pasa.
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
        return _send_file(candidate, immutable=_is_hashed_asset(candidate.name),
                          solo_cabeceras=request.method == 'HEAD')

    # Fallback: index.html para rutas de Angular (login, hub, etc.).
    index = FRONTEND_BUILD / 'index.html'
    if not index.is_file():
        return HttpResponse("index.html no encontrado en el build.", status=503)
    return _send_file(index, immutable=False,
                      solo_cabeceras=request.method == 'HEAD')


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


def _send_file(path: Path, *, immutable: bool, solo_cabeceras: bool = False):
    content_type, _ = mimetypes.guess_type(path.name)
    tipo = content_type or 'application/octet-stream'
    if solo_cabeceras:
        # HEAD: las MISMAS cabeceras y ningún cuerpo. No se abre el archivo —
        # un monitor que pregunta cada minuto no tiene por qué hacer leer el
        # bundle entero— pero sí se declara su tamaño, que es la mitad de lo
        # que un HEAD viene a averiguar.
        response = HttpResponse(content_type=tipo)
        response['Content-Length'] = path.stat().st_size
    else:
        response = FileResponse(open(path, 'rb'), content_type=tipo)
    if immutable:
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
    else:
        response['Cache-Control'] = 'no-cache'
    return response

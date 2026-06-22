# Despliegue del Frontend Angular — innovaK

**Estado:** Etapa D cerrada al 2026-06-01.
**Modo actual:** Angular servido desde Django bajo `/app/*`.

---

## Decisión de despliegue

El frontend Angular se sirve **desde el mismo Django bajo `/app/*`** en
lugar de un servicio Nginx separado. Razones:

1. **Cero apertura de puertos**. El firewall del servidor remoto solo
   expone `:8034` (Django/Nginx) y `:8080` (code-server). Servir
   Angular bajo `/app/*` del puerto 8034 evita coordinar firewall
   adicional con TI.

2. **Cero CORS**. Angular y backend comparten dominio, así las
   peticiones `/api/*` no disparan preflight ni allow-origin.

3. **Coexistencia transparente**. El usuario sigue entrando a
   `http://intranet.../` (Django HTML). Para probar Angular abre
   `http://intranet.../app/`. Nada se rompe ni cambia para nadie.

4. **Sin tocar `docker-compose.yml` ni `nginx.conf`**. Ambos archivos
   requieren doble confirmación según `CLAUDE.md`. Esta solución no
   los toca.

## Cómo funciona

Cuando llega un request a `/app/<resource>`:

```
Navegador → /app/auth/login
              ↓
       innova_nginx (8034)
              ↓
       innova_k Gunicorn (8032)
              ↓
       core/urls.py — re_path(r'^app/(?P<resource>.*)$', angular_spa)
              ↓
       apps/login/views/spa.py::angular_spa
              ↓
       Lee frontend/dist/innovak-frontend/browser/index.html
       (o el asset .js/.css solicitado, con Cache-Control immutable
        para chunks hasheados)
```

- `/app/` → `index.html` (Angular monta y resuelve la ruta `''`).
- `/app/banco` → `index.html` (Angular router maneja `/banco`).
- `/app/banco/12` → `index.html`.
- `/app/main-XXX.js` → el archivo real con `Cache-Control: public, max-age=31536000, immutable`.
- `/app/styles-XXX.css` → ídem.
- Las APIs siguen en `/api/...`, `/banco-iniciativas/api/...`, etc.

## Build de producción

```bash
cd frontend
npm run build -- --base-href=/app/
```

Resultado en `frontend/dist/innovak-frontend/browser/`. Django lo lee
directo del filesystem; **no necesitas reiniciar el container** ni
correr `collectstatic`.

## Build para CI/CD (Docker)

Hoy el build se ejecuta en el host (no en el container). Cuando se
quiera automatizar:

```dockerfile
# Etapa de build dentro del Dockerfile (multi-stage)
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build -- --base-href=/app/

# Stage final
FROM python:3.10-slim AS runtime
# ... resto del Dockerfile actual ...
COPY --from=frontend-build /build/dist /app/frontend/dist
```

Esto se puede agregar en un PR futuro al `Dockerfile` con doble
confirmación.

## Comparación con alternativas

| Modo | Pros | Contras |
|---|---|---|
| **Actual: Django sirve `/app/*`** | Cero firewall, cero CORS, cero cambios a Nginx. Reaprovecha auth/JWT del mismo dominio. | El asset serving pasa por Python (overhead pequeño en dev; en prod con `Cache-Control immutable` el navegador casi nunca pide los chunks). |
| Nginx sirve `/app/*` directo | Más rápido (Nginx static). Sin Python en la cadena. | Requiere editar `nginx.conf` (doble confirmación). Misma ventaja de cero CORS. |
| Subdominio Angular separado | Aislamiento total. | Implica CORS, cookies cross-site, certificados extra. Sobrecomplica para el caso actual. |

**Recomendación:** mantener el modo actual hasta que (a) se quiera
optimizar serving estático con Nginx, o (b) llegue tráfico que
justifique el cambio. Para el volumen actual de la Alcaldía
Kennedy, esto es más que suficiente.

## URLs de referencia

| URL | Sirve |
|---|---|
| `http://10.100.102.12:8034/` | Django HTML legacy (lo de siempre, sin cambios) |
| `http://10.100.102.12:8034/api/*` | API REST DRF |
| `http://10.100.102.12:8034/api/docs/` | Swagger UI |
| `http://10.100.102.12:8034/api/schema/` | OpenAPI YAML |
| `http://10.100.102.12:8034/app/` | **Angular SPA** ← entrada del frontend nuevo |

## Cuando llegue otra alcaldía

Cambiar 3 variables en `frontend/src/environments/environment.prod.ts`:
- `appName`
- `alcaldiaName`
- `apiBaseUrl` (URL del backend de esa alcaldía)

Build, copia el `dist/` al servidor, y queda servido bajo `/app/*` de
la nueva instalación Django. **Cero código tocado.**

# Frontend Angular — Etapa D Plan Frontend

**Estado:** PR-1 scaffold · **Versión Angular:** 18 LTS · **Plantilla UI:** Tabler Angular (MIT)

## Reglas duras (decisión Alex 2026-05-28)

### Regla 0: Estado final → TODO vive en Angular (excepto formularios públicos)

El objetivo de Etapa D es **migrar la totalidad de templates HTML
y estilos SCSS** de Django a Angular. Al cerrar Etapa D, Django queda
únicamente con:

- **API REST DRF** (`/api/*`, `/dashboard/api/*`, módulos `*/api/*`).
- **Formularios públicos QR** (regla B abajo) en HTML legacy.

Todo lo demás — sidebar, hubs, organizadores, dashboards, admin de
roles, mapa, cursos del docente, reportes — vive en Angular. Cada PR
de Etapa D **migra un grupo de templates** y **switchea Nginx** a
servir Angular en esas rutas, retirando los templates Django
correspondientes.

Los **estilos SCSS** (design tokens `--accent`, componentes `.ui-*`,
breadcrumbs, cards, progress bars color-condicionales, etc.) se
mueven a `frontend/src/styles/` y se consumen como capa base sobre
Tabler.

### Regla A: URLs públicas no cambian

Los usuarios siguen entrando a la misma URL que conocen hoy
(`https://intranet.alcaldia.gov.co/` o el ngrok actual). Nginx hace
routing transparente entre Angular SPA y Django HTML legacy:

```
URL Usuario
    ↓
  Nginx
    ├── /api/*, /admin/*, /static/*        → Django backend (sin cambio)
    ├── Formularios públicos QR            → Django HTML (sin cambio)
    │   (banco, jóvenes, caracterización,
    │    inscripción evento, votaciones)
    └── Resto (organizador, dashboard,     → Angular SPA (build estático)
        hubs, admin, mapa, cursos)
```

- **QRs físicos impresos siguen funcionando idénticos** — su URL no se toca.
- **Rollout gradual feature por feature** — switch en Nginx vuelve al HTML
  legacy en segundos si algo falla.
- **Cero cambio de dominio**, cero nueva URL para los usuarios.

### Regla B: los formularios públicos SÍ se migraron a Angular

> **Corregido el 2026-08-06.** Hasta hoy esta sección decía lo contrario —
> «Formularios públicos NO se migran a Angular», con una lista de rutas
> Django marcadas como *intocables*. **Es falso desde el 2026-06-04**, cuando
> Alex decidió «B — todo va para Angular», los públicos incluidos. Están
> **todos** migrados y viven en `frontend/src/app/features/publico/`
> (`publico.routes.ts`, 10 rutas bajo `/app/p/*`); las vistas Django de la
> lista vieja hoy **redirigen** a la SPA, para que ningún QR impreso se rompa.
> Era la misma mentira que ya tumbó producción una vez desde otro archivo: un
> documento que declara «intocable» lo que en realidad se movió hace dos meses.

Lo público sigue siendo público — ese es el constraint permanente, y no cambió:
las rutas van **fuera del `authGuard`** y sus endpoints son `AllowAny` (hoy con
`QrTokenPermission` en modo suave). El ciudadano escanea el QR y llena el
formulario sin cuenta.

**Dónde vive cada formulario público hoy:**

| Ruta Angular (la viva) | Qué es | La vista Django vieja |
|---|---|---|
| `/app/p/banco/:id` | Inscripción colectivos recreodeportivos | redirige |
| `/app/p/jovenes/:id` | Entrega de becas (convenios 773-2025, 955-2025) | redirige |
| `/app/p/caracterizacion/:id` | 6 wizards (cultura, deporte, mujer, salud, poblacional, participación) | redirige |
| `/app/p/inscripcion/:id` | Inscripción genérica QR a evento | redirige |
| `/app/p/entrega/:id` | Entrega de insumos | redirige |
| `/app/p/captura/:id` | Motor genérico de captura por `tipo_evento` | redirige |
| `/app/p/info-terreno/:id` | Info-terreno (GPS + fotos) | redirige |
| `/app/p/festival-percepcion/:slug` | Encuesta de percepción ciudadana | — |
| `/votaciones/scan/` + `/votaciones/api/vote/` | Scan QR y voto | **se queda en Django**: kiosko autocontenido, decisión del 2026-06-09 |

El **único** público que no es Angular es el kiosko de votación, y es a
propósito: es un flujo sensible y autocontenido, fuera del SPA.

**Endpoints DRF públicos** (Etapa C #2) también se conservan:

- `POST /api/eventos/<id>/inscripciones/` — AllowAny + 10/min/IP.
- `POST /votaciones/api/v2/voters/validate/` — AllowAny + 30/min/IP.
- `POST /votaciones/api/v2/votes/` — AllowAny + 5/min/IP.

**Angular SOLO cubre el área autenticada**: dashboards organizadores,
validar/rechazar inscripciones, KPIs, mapa, admin de roles, cursos del
docente, reportes, etc.

---

## Filosofía y decisiones arquitectónicas

El frontend de innovaK es **modular, reusable y desplegable independiente**.

### Tres pilares

1. **Aislamiento del backend** — El frontend ignora cómo está implementado el backend (Django+DRF, FastAPI, Node, lo que sea). Solo conoce el contrato JSON (`/api/schema/`). Si mañana la alcaldía cambia el stack del backend, el frontend sigue igual.

2. **Reusabilidad por alcaldía** — La estructura sirve para innovaK Kennedy hoy, Bosa mañana, Suba después. Cada despliegue solo cambia variables de entorno y branding (logo, colores, nombre de la alcaldía). El código es el mismo.

3. **Desplegable independiente** — Build estático servido por Nginx. Puede vivir en un dominio diferente al backend, en un CDN, en un balanceador, sin tocar Django.

### Stack

- **Angular 18** — Standalone components, signals, control flow nuevo (`@if`, `@for`).
- **Tabler Angular** (MIT, Tabler Icons monoline) — Plantilla UI.
- **TypeScript estricto** — `strict: true` en `tsconfig.json`.
- **HttpClient** (no fetch crudo) — interceptor JWT + manejo de 401.
- **RxJS** para observables (estándar Angular).
- **Standalone routing** con lazy loading por feature.
- **SCSS** con design tokens (mismas variables que el SCSS Django para consistencia visual durante coexistencia).

## Ubicación

```
/home/innova/Proyectos/innovaK/
├── apps/                       # Backend Django (apps por dominio)
├── core/                       # Settings Django + URLs
├── frontend/                   # ← AQUÍ vive Angular
│   ├── package.json
│   ├── angular.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/           # singletons (auth, http, config)
│   │   │   ├── shared/         # componentes UI reusables
│   │   │   ├── features/       # módulos de negocio (lazy)
│   │   │   ├── api/            # cliente generado del OpenAPI (no editar manual)
│   │   │   ├── app.config.ts
│   │   │   ├── app.routes.ts
│   │   │   └── app.component.ts
│   │   ├── environments/
│   │   │   ├── environment.ts          # dev (apunta a localhost:8034)
│   │   │   └── environment.prod.ts     # prod (env var INNOVAK_API_URL)
│   │   ├── index.html
│   │   └── main.ts
│   └── dist/                   # build estático (no commitear)
├── docker-compose.yml          # backend + redis + nginx
└── docs/
    └── FRONTEND_ANGULAR.md     # este documento
```

**Por qué monorepo y no submodule:**
- Un solo `git clone` baja todo.
- Cambios coordinados backend↔frontend van en un PR.
- Cuando crezca a otras alcaldías, se puede extraer a su propio repo sin reescribir nada (solo `git filter-repo --subdirectory-filter frontend/`).

## Estructura interna del frontend

```
src/app/
├── core/                           # Cargado UNA SOLA VEZ al boot
│   ├── auth/
│   │   ├── auth.service.ts         # login, logout, refresh, currentUser$
│   │   ├── token.storage.ts        # localStorage de access/refresh
│   │   ├── jwt.interceptor.ts      # Authorization: Bearer + retry on 401
│   │   └── auth.guard.ts           # bloquea rutas privadas
│   ├── config/
│   │   ├── config.service.ts       # lee environment.ts
│   │   └── app.config.ts           # constantes globales
│   ├── http/
│   │   ├── error.interceptor.ts    # captura errores y notifica
│   │   └── api-base.service.ts     # wrapper sobre HttpClient
│   └── theme/
│       └── theme.service.ts        # dark/light mode (Tabler soporta)
│
├── shared/                         # Reutilizable en cualquier feature
│   ├── components/
│   │   ├── ui-card/                # card Tabler con --accent token
│   │   ├── ui-table/               # tabla paginada
│   │   ├── ui-progress-bar/        # color-condicional (verde/amarillo/rojo)
│   │   └── ui-empty-state/
│   ├── directives/
│   ├── pipes/
│   └── shared.module.ts            # SOLO si se necesita; standalone preferred
│
├── features/                       # Lazy loaded
│   ├── auth/
│   │   ├── login/
│   │   └── auth.routes.ts
│   ├── dashboard/                  # hub principal + KPIs
│   ├── banco-iniciativas/
│   ├── jovenes-a-la-e/
│   ├── caracterizacion/
│   ├── presupuesto/
│   ├── eventos/                    # incluye curso docente
│   ├── votaciones/
│   ├── mapa/                       # Leaflet + Tabler
│   └── admin/                      # roles, módulos, organización
│
├── api/                            # NO EDITAR (auto-generado)
│   ├── services/                   # 1 service por tag de OpenAPI
│   ├── models/                     # interfaces TS de cada response
│   └── README.md                   # cómo regenerar
│
├── app.config.ts                   # providers globales (HttpClient, router, interceptors)
├── app.routes.ts                   # rutas top-level (todas lazy)
└── app.component.ts                # layout root (sidebar Tabler + outlet)
```

## Variables de entorno

```typescript
// src/environments/environment.ts (DEV)
export const environment = {
  production: false,
  appName: 'innovaK',
  alcaldiaName: 'Alcaldía Local de Kennedy',
  apiBaseUrl: 'http://localhost:8034',
  apiSchemaUrl: 'http://localhost:8034/api/schema/',
  jwtAccessKey: 'innovak_access_token',
  jwtRefreshKey: 'innovak_refresh_token',
};
```

```typescript
// src/environments/environment.prod.ts (PROD — placeholders sustituidos por Docker entrypoint)
export const environment = {
  production: true,
  appName: '${APP_NAME}',
  alcaldiaName: '${ALCALDIA_NAME}',
  apiBaseUrl: '${API_BASE_URL}',
  apiSchemaUrl: '${API_BASE_URL}/api/schema/',
  jwtAccessKey: 'innovak_access_token',
  jwtRefreshKey: 'innovak_refresh_token',
};
```

**Para reutilizar en otra alcaldía:** solo cambias las env vars al desplegar. Cero código tocado.

## Cliente API auto-generado

El cliente vive en `src/app/api/` y se regenera automáticamente desde el schema OpenAPI publicado por el backend.

```bash
# Desde frontend/
npm run api:gen
```

Que internamente ejecuta:
```bash
npx @openapitools/openapi-generator-cli generate \
  -i $API_SCHEMA_URL \
  -g typescript-angular \
  -o src/app/api/ \
  --additional-properties=ngVersion=18.0,providedInRoot=true,fileNaming=kebab-case
```

**Beneficio:** cuando el backend agrega/cambia un endpoint, regeneras el cliente y los componentes Angular fallan en tiempo de compilación si el contrato cambió. Cero drift backend↔frontend.

## Despliegue

Tres modos soportados:

### Modo 1: Dev local
```bash
cd frontend/
npm install
npm start   # ng serve en :4200, proxy a backend :8034
```

### Modo 2: Build estático servido por Nginx (recomendado prod)
```bash
cd frontend/
npm run build
# Output en frontend/dist/innovak-frontend/browser/
# Nginx sirve esto + proxy_pass /api/ → backend
```

> **El `<base href>` ya no depende de que alguien lo recuerde.** La SPA se sirve
> bajo `/app/`, así que necesita `<base href="/app/">`: sin eso el `index.html`
> pide `/main.js` y `/styles.css` en la raíz del dominio, da 404 en todo y la
> aplicación queda **en blanco** — es exactamente lo que pasó el 2026-06-18.
> Hasta el 2026-08-06 esta guía decía `npm run build` a secas y `angular.json`
> no fijaba el `baseHref`: **seguir la guía al pie de la letra rompía
> producción.** Ahora la configuración `production` de `angular.json` lleva
> `"baseHref": "/app/"`, de modo que el comando de arriba ya sale correcto y el
> viejo `-- --base-href=/app/` quedó redundante (no molesta si lo pones).
>
> Cómo comprobarlo en un segundo, después de cualquier build:
> ```bash
> grep -o '<base href="[^"]*">' dist/innovak-frontend/browser/index.html
> # → <base href="/app/">
> ```

### Modo 3: Docker (futuro PR-5 de Etapa D)
```yaml
# docker-compose.yml — servicio nuevo
innovak_frontend:
  build: ./frontend
  ports:
    - "8035:80"
  environment:
    - INNOVAK_API_URL=http://innovak_backend:8032
```

## Reglas de oro (Plan Frontend §1)

Todo código frontend debe respetar:

1. **Lógica fuera de templates** — servicios y signals/observables, no `*ngIf` con cálculo.
2. **Datos JSON-exponibles** — props serializables (sin `Date` directo, usar ISO string).
3. **Fragmentos no páginas** — preferir update parcial sobre redirect.
4. **Tipado estricto** — `strict: true`, `any` solo con `// FIXME: any` justificado.
5. **Componentes standalone** — evitar NgModule salvo justificación clara.
6. **Lazy loading por feature** — `loadComponent` en routes.
7. **API solo vía cliente generado** — no llamar `HttpClient` directo desde componentes.

## Para crecer a otras alcaldías

Cuando llegue el momento "trabajar todo Bogotá con los proyectos de Bogotá todas las alcaldías":

1. **Backend**: cada alcaldía tiene su instancia Django + Postgres, o el backend se vuelve multi-tenant. El frontend NO cambia.
2. **Frontend**: una instancia Angular por alcaldía (despliegue independiente) o multi-tenant via subdomain con env var dinámica.
3. **Branding**: 1 SCSS de tema por alcaldía (`themes/kennedy.scss`, `themes/bosa.scss`) cargado por env var.
4. **Idioma**: Angular i18n (`@angular/localize`) con `es-CO` por default.
5. **Catálogos compartidos**: si todas las alcaldías comparten catálogos (tipos de actividad, sectores), va al backend central. Si son específicos, env var.

## Roadmap de migración a Angular (Etapa D completa)

Plan ordenado para migrar TODOS los templates Django (excepto formularios
públicos regla B) a Angular sin afectar usuarios:

| PR | Qué migra | Templates Django retirados | Nginx switch |
|---|---|---|---|
| **PR-1** (este) | Scaffold + plan + JWT interceptor + ping a API | — | — |
| **PR-2** | **Estilos**: design tokens SCSS → `frontend/src/styles/` (variables, ui-*, breadcrumbs, cards, progress) | — | — |
| **PR-3** | **Layout**: sidebar Tabler + topbar + breadcrumbs (replica `templates/base.html`) | — | — |
| **PR-4** | **Auth**: login form Angular contra `/api/token/` + cliente API generado del OpenAPI | `templates/login/` | `/login/` → Angular |
| **PR-5** | **Hub principal + sub-hubs** (Actividades, Presupuesto, Admin, Votaciones) | `templates/dashboard/hub*.html` | `/dashboard/hub/*` → Angular |
| **PR-6** | **Banco de Iniciativas organizador**: list + detalle + validar/rechazar + insights | `templates/banco_iniciativas/` (organizador) | `/banco-iniciativas/inscripciones*` → Angular |
| **PR-7** | **Jóvenes a la E organizador** | `templates/jovenes_a_la_e/` (organizador) | `/jovenes-a-la-e/entregas*` → Angular |
| **PR-8** | **Caracterización organizador**: list por sector + detalle | `templates/dashboard/caracterizaciones_*` | rutas correspondientes |
| **PR-9** | **Presupuesto**: proyectos list/detalle, CDPs, contratos, metas, KPIs, avances | `templates/presupuesto/` | `/presupuesto/*` (no APIs) → Angular |
| **PR-10** | **Eventos**: listar, editar, crear, QR, asistencia | `templates/eventos/` | `/evento/*` editor → Angular |
| **PR-11** | **Cursos del docente**: panel, sesiones, tomar lista, notas, reporte | `templates/curso_docente/` | `/cursos/*` → Angular |
| **PR-12** | **Mapa Kennedy**: Leaflet + filtros | `templates/geo-mapas/` | `/geo/mapa-kennedy/` → Angular |
| **PR-13** | **Admin de roles + organización**: roles, módulos, dependencias, subgrupos, funcionarios, beneficiarios, organizaciones | `templates/roles/` + `templates/admin_org/` + `templates/login/formulario/` | `/org/*` → Angular |
| **PR-14** | **Votaciones organizador** (no scan público): eventos, candidatos, dashboard, resultados | `templates/votaciones/organizador*` | `/votaciones/organizador/*` → Angular |
| **PR-15** | **Docker Compose**: servicio `innovak_frontend` con Nginx + build estático | — | Despliegue prod |
| **PR-16** | **Limpieza**: borrar templates Django retirados, retirar dependencias `django-bootstrap4`, `widget_tweaks` si ya nadie las usa | Carpeta `templates/` reducida al mínimo (solo formularios QR + admin Jazzmin) | — |

Al cerrar PR-16:
- `templates/` solo contiene formularios públicos QR + admin Jazzmin.
- `static/css/` y `static/js/` solo los de admin + QR forms.
- `apps/*/templates/` mayormente vacíos.
- Angular tiene la totalidad del UI autenticado.
- Despliegue: backend Django + Angular SPA separados, Nginx orquesta.

## Historial

- **2026-05-28** PR-1: scaffold inicial + plan + interceptor JWT + landing ping.
- **PR-2 (próximo)**: estilos SCSS Django → Angular styles.
- (resto del roadmap arriba)

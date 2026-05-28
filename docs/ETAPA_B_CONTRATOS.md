# Contratos JSON — Etapa B Plan Frontend (innovaK API REST)

**Estado:** Cerrada el 2026-05-28 · **Tests cobertura:** 318/318 · **Versión OpenAPI:** 1.0.0

Este documento inventa todos los endpoints REST DRF de innovaK con su
permission, contrato JSON de request/response y ejemplos curl/HTTPie.
El destinatario es el equipo Angular (Etapa D) y cualquier integrador
externo que consuma la API.

**Documentación interactiva en vivo:**
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- Schema OpenAPI 3 YAML: `/api/schema/`

---

## 1. Autenticación

Dos esquemas coexisten:

### 1.1 Session (cookies del browser)
Para usuarios logueados desde los templates Django (sidebar, hubs,
formularios HTML). Se establece automáticamente con `/login/`.

### 1.2 JWT (Bearer token)
Para clientes externos (Angular, móvil, scripts, integraciones).

**Endpoints:**
```
POST /api/token/         {username, password} → 200 {access, refresh}
POST /api/token/refresh/ {refresh}            → 200 {access}
POST /api/token/verify/  {token}              → 200 | 401
```

**Vida útil:** access 15 min, refresh 7 días (`SIMPLE_JWT` en
`core/settings.py`).

**Uso desde Angular:**
```typescript
// Interceptor recomendado
const headers = { Authorization: `Bearer ${accessToken}` };
this.http.get('/api/...', { headers });
```

### 1.3 Permisos por endpoint

| Permission | Significado |
|---|---|
| `AllowAny` | Sin auth obligatoria. Si llega JWT/Session, se usa para auditoría. |
| `IsAuthenticated` | Cualquier usuario logueado (Session o JWT) |
| `ModuloRequiredPermission("X")` | Usuario con módulo X asignado (superuser pasa siempre) |

---

## 2. Endpoints públicos (AllowAny)

Estos endpoints sirven los flujos vía QR sin auth.

### 2.1 Inscripción a evento

```
POST /api/eventos/<evento_id>/inscripciones/
```

**Permission:** `AllowAny` (acepta JWT para auditar `usuario_editor`).

**Request body:**
```json
{
  "nombre1": "Juan",
  "apellido1": "Pérez",
  "nombre2": "Carlos",
  "apellido2": "Gómez",
  "fecha_nacimiento": "1990-05-12",
  "sexo_biologico": "M",
  "identidad_genero": "M",
  "documento": "1234567890",
  "telefono": "3001234567",
  "correo": "juan@ejemplo.com",
  "upz": "78",
  "barrio": "001"
}
```
Obligatorios: `nombre1`, `apellido1`. Resto opcional.

**Response 201:**
```json
{
  "persona_id": 7421,
  "participante_id": 5102,
  "participante_evento_id": 2891
}
```

**Errores:** `400` (validación), `404` (evento no existe o inactivo).

### 2.2 Banco de Iniciativas — formulario público

```
POST /banco-iniciativas/<evento_id>/inscribir/  (HTML form legacy)
```
Existe endpoint DRF público para el caso Angular — ver Swagger.

### 2.3 Jóvenes a la E — formulario público beca

```
POST /jovenes-a-la-e/<evento_id>/beca/  (HTML form legacy)
```
Ídem.

### 2.4 Votaciones — eventos y candidatos

```
GET /votaciones/api/v2/eventos/                       AllowAny
GET /votaciones/api/v2/eventos/<id>/candidatos/       AllowAny
```

**Response GET eventos:**
```json
{
  "count": 2,
  "results": [
    {
      "id": 1, "name": "Encuentro Cultural 2026",
      "starts_at": "2026-06-01T08:00:00Z",
      "ends_at": "2026-06-01T18:00:00Z",
      "is_open": true,
      "status": "open",
      "status_message": "La votación está disponible."
    }
  ]
}
```

**Response GET candidatos (200 si abierto, 403 si cerrado):**
```json
{
  "event": { "id": 1, "name": "...", "is_open": true, ... },
  "identidades": [
    {"id": 5, "name": "...", "genre": "Mujer", "group": "IDENTIDADES",
     "curul": "MUJER", "code": "M01", "photo_url": "https://...",
     "bio": "...", "is_active": true, "event_id": 1}
  ],
  "derechos": [ ... ],
  "count_identidades": 4,
  "count_derechos": 6
}
```

---

## 3. Módulos productivos (gated por permiso)

### 3.1 Banco de Iniciativas (`banco_iniciativas`)

```
GET    /banco-iniciativas/api/inscripciones/                 paginado
GET    /banco-iniciativas/api/inscripciones/<id>/            detalle 360°
POST   /banco-iniciativas/api/inscripciones/<id>/estado/     validar/rechazar
GET    /banco-iniciativas/api/insights/                      KPIs JSON
```

**GET inscripciones response:**
```json
{
  "count": 3580, "next": "?page=2", "previous": null,
  "results": [
    {"id": 1, "estado": "validada", "numero_documento": "1234",
     "nombre_completo": "...", "evento_id": 5, "fecha_inscripcion": "..."}
  ]
}
```

**POST estado/ body:**
```json
{"estado": "validada", "observacion": "OK"}
```

### 3.2 Jóvenes a la E (`jovenes_a_la_e`)

```
GET    /jovenes-a-la-e/api/entregas/?estado=enviada&evento=100055&q=PEREZ
GET    /jovenes-a-la-e/api/entregas/<id>/                    detalle
POST   /jovenes-a-la-e/api/entregas/<id>/estado/             validar/rechazar
GET    /jovenes-a-la-e/api/insights/
```

Filtros query: `estado` (enviada/validada/rechazada), `evento` (id),
`q` (búsqueda por documento/nombre1/apellido1).

### 3.3 Caracterización (`caracterizacion`)

```
GET /caracterizacion/api/cultura/
GET /caracterizacion/api/deporte/
GET /caracterizacion/api/mujer/
GET /caracterizacion/api/salud/
GET /caracterizacion/api/poblacional/
GET /caracterizacion/api/participacion/
```

Detalle: `/caracterizacion/api/<sector>/<id>/`.

Cada sector tiene su propio serializer con los campos del wizard
correspondiente. Ver Swagger UI para schema completo por sector.

### 3.4 Presupuesto

```
GET /presupuesto/api/proyectos/                       presupuesto_proyectos
GET /presupuesto/api/proyectos/<id>/                  presupuesto_proyectos
GET /presupuesto/api/cdps/                            presupuesto_cdp
GET /presupuesto/api/cdps/<id>/                       presupuesto_cdp
GET /presupuesto/api/contratos/                       presupuesto_cdp
GET /presupuesto/api/contratos/<id>/                  presupuesto_cdp
GET /presupuesto/api/indicadores/                     presupuesto_metas
GET /presupuesto/api/indicadores/<id>/                presupuesto_metas
```

### 3.5 Eventos / Cursos (login)

#### Inscripción

```
POST /api/eventos/<id>/inscripciones/   AllowAny (ya documentado §2.1)
```

#### Sesiones del curso

```
GET  /api/eventos/<id>/sesiones/        cursos
POST /api/eventos/<id>/sesiones/        cursos — bulk
```

**POST body:**
```json
{
  "sesiones": [
    {"fecha": "2026-06-01", "hora_inicio": "07:00", "hora_fin": "09:00",
     "lugar": "Aula 3", "nombre": "Sesión 1: Postura"}
  ]
}
```

#### Asistencia por sesión

```
GET  /api/sesiones/<clase_id>/asistencia/    eventos_asistencia
POST /api/sesiones/<clase_id>/asistencia/    eventos_asistencia — bulk upsert
```

**POST body:**
```json
{
  "fecha": "2026-06-01",
  "marcas": [
    {"participante_id": 5, "presente": true, "observacion": "llegó tarde"},
    {"participante_id": 6, "presente": false}
  ]
}
```

#### Notas / Evaluaciones

```
GET    /api/eventos/<id>/notas/             cursos — lista + promedios
POST   /api/eventos/<id>/notas/             cursos — bulk upsert
DELETE /api/notas/<evaluacion_id>/          cursos
```

**POST body:**
```json
{
  "notas": [
    {"participante_id": 5, "nota": "4.5", "etiqueta": "Parcial 1",
     "fecha": "2026-04-20"},
    {"participante_id": 5, "nota": "3.8", "etiqueta": "Final",
     "fecha": "2026-05-25", "evaluacion_id": 12}
  ]
}
```
Si `evaluacion_id` viene, actualiza esa fila; si no, crea nueva.

#### Reporte consolidado

```
GET /api/eventos/<id>/reporte/   cursos
```

**Response:**
```json
{
  "evento_id": 56,
  "evento_nombre": "Yoga Comunitario",
  "count": 12,
  "results": [
    {"participante_id": 5, "persona_nombre": "Ana Gómez",
     "documento": "1234", "asistencias": 8, "inasistencias": 2,
     "total_marcas": 10, "pct_asistencia": 80.0,
     "notas": ["4.50 (Parcial 1) 2026-04-20", ...],
     "promedio": "4.20", "aprobado": true}
  ]
}
```

Descargables HTML (no DRF): `/cursos/<id>/reporte/excel/`, `/cursos/<id>/reporte/pdf/`.

### 3.6 Votaciones (`votaciones_admin`)

Ya descritos en §2.4 los públicos. Los staff:

```
GET /votaciones/api/v2/eventos/<id>/resultados/             votaciones_admin
GET /votaciones/api/v2/eventos/0/resultados/latest/         votaciones_admin
```

**Response:**
```json
{
  "event": {"id": 1, "name": "Encuentro..."},
  "total_votes": 248, "unique_voters": 248,
  "ranking_identidades": [
    {"candidate_id": 5, "candidate_name": "...", "photo_url": "...",
     "curul": "MUJER", "votes": 89, "percentage": 35.9}
  ],
  "ranking_derechos": [ ... ],
  "total_identidades_votes": 248,
  "total_derechos_votes": 248
}
```

### 3.7 Dashboard presupuestal

8 endpoints v2 que alimentan Chart.js (hoy) y Angular components (futuro):

```
GET /dashboard/api/v2/presupuesto/resumen-ejecutivo/         presupuesto_proyectos
GET /dashboard/api/v2/presupuesto/cascada-resumen/           presupuesto_proyectos
GET /dashboard/api/v2/presupuesto/objetivos-por-proyecto/    presupuesto_proyectos
GET /dashboard/api/v2/presupuesto/objetivos-y-programas/     presupuesto_proyectos
GET /dashboard/api/v2/presupuesto/eventos-mes-tipo/          presupuesto_proyectos
GET /dashboard/api/v2/presupuesto/top-sectores/              presupuesto_proyectos
GET /dashboard/api/v2/presupuesto/metas-progreso/            presupuesto_metas
GET /dashboard/api/v2/presupuesto/kpis-avance/               presupuesto_metas
```

**Ejemplo `metas-progreso`:**
```json
{
  "stats": {
    "total": 47, "cumplidas": 12, "en_progreso": 25,
    "en_riesgo": 8, "sin_avance": 2
  },
  "metas": [
    {"id": 23771, "codigo": "...", "nombre": "...",
     "progreso": 64.3, "estado": "en_progreso"}
  ]
}
```

### 3.8 Georreferenciación

```
GET /geo/api/lugares/           AllowAny — markers del mapa
GET /geo/api/conteos/           agregados
GET /geo/api/eventos/           eventos georreferenciados
```

---

## 4. Patrones comunes

### 4.1 Paginación
Todos los listados paginados usan `PageNumberPagination` con
`PAGE_SIZE=50`. Query params: `?page=N&page_size=N` (max 100 donde aplica).

**Response:**
```json
{"count": 3580, "next": "?page=2", "previous": null, "results": [...]}
```

### 4.2 Errores
- `400` Bad Request → `{"detail": "...", "campo": ["error"]}`
- `401` Unauthorized → `{"detail": "Authentication credentials were not provided."}`
- `403` Forbidden → `{"detail": "You do not have permission ..."}`
- `404` Not Found → `{"detail": "Not found."}`
- `500` Server Error → log + `{"detail": "..."}`

### 4.3 Filtrado y búsqueda
- Filtros: query params específicos (`?estado=X&evento=Y`).
- Búsqueda libre: `?q=texto` aplica ILIKE sobre campos definidos por
  endpoint.
- Ordenamiento: implícito por `-created_at` o por `id` salvo
  documentación específica.

### 4.4 Fechas
ISO 8601: `YYYY-MM-DD` para fechas, `YYYY-MM-DDTHH:MM:SSZ` para
datetimes con timezone UTC.

### 4.5 Decimales
Strings JSON con punto: `"4.50"`, `"5000.00"`. Razón: precisión
exacta (no flotante) para presupuesto y notas SED.

### 4.6 Idempotencia
Endpoints con bulk upsert (`tomar_lista`, `registrar_nota`) son
idempotentes: reenviar la misma petición no duplica.

---

## 5. Para el equipo Angular

### 5.1 Generar el cliente TypeScript

```bash
# Usando openapi-generator (npm install @openapitools/openapi-generator-cli)
npx openapi-generator-cli generate \
  -i https://intranet.../api/schema/ \
  -g typescript-angular \
  -o src/app/api/generated/ \
  --additional-properties=ngVersion=18.0,providedInRoot=true
```

Resultado: services Angular tipados (`*.service.ts`) + modelos (`*.ts`).

### 5.2 Interceptor JWT recomendado

```typescript
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler) {
    const token = localStorage.getItem('access_token');
    if (token) {
      req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
    }
    return next.handle(req).pipe(catchError(this.handle401));
  }
  // 401 → refresh con /api/token/refresh/ → reintentar req original
}
```

### 5.3 Reglas de uso (decisión Plan Frontend §1)

- **Angular-ready obligatorio**: lógica separada de presentación,
  datos JSON-exponibles, fragmentos no páginas.
- **NO crear nuevos endpoints solo para Angular**: el contrato ya
  está estable. Si falta un campo, abrir issue para extender el
  serializer existente.
- **NO usar templates Django desde Angular**: si necesitas una
  página HTML, es signal que ese flujo no debe migrar todavía.

---

## 6. Pendientes conocidos (PRs futuros)

- **OpenAPI cobertura completa**: 215 errors / 12 warnings al validar
  schema. Causa: endpoints que devuelven `dict` raw sin serializer.
  Solución: añadir `@extend_schema(responses=...)` decorators a cada
  APIView. Cada error es un endpoint sin schema explícito de respuesta.
- **Mutación votaciones-DRF**: `validate_voter` y `vote` siguen en
  `JsonResponse` legacy. Migración cuando Angular esté listo.
- **Caracterización wizards públicos**: hoy son HTML form. Endpoints
  DRF para wizard Angular pendientes (Etapa D).
- **Rate limiting** en endpoints AllowAny: implementación con
  `django-ratelimit` o nginx (decisión #6 PR-1 fusión).

---

## 7. Cambios recientes

- **2026-05-28** Etapa C cerrada: OpenAPI 3 + Swagger UI + ReDoc;
  JWT opcional en AllowAny endpoints; tests E2E read-only; este
  documento.
- **2026-05-27** Curso Docente PR-A→PR-D: sesiones + asistencia +
  notas + reporte/export.
- **2026-05-27** Fusión kactivo→Evento: -4.907 LOC, módulos
  unificados.
- **2026-05-27** Votaciones-DRF read-only + Dashboard-DRF (Etapa B
  cierra).
- **2026-05-21** Jóvenes a la E PR-1+PR-2 a producción.
- **2026-04-30** Caracterización N12 (6 wizards) en producción.

Mantenido por: el equipo backend de innovaK. Sincronizado con el
schema OpenAPI en vivo (`/api/schema/`).

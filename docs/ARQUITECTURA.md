# Arquitectura — innovaK

> Fuente de verdad de alto nivel sobre el proyecto **innovaK** (Alcaldía Local
> de Kennedy, Bogotá). Este documento se mantiene a mano; los detalles de
> deuda viven en [DEUDA_TECNICA.md](./DEUDA_TECNICA.md).

---

## 1. Visión general

**innovaK** es un sistema de información interno para la Alcaldía Local de
Kennedy. Gestiona la **población atendida** por la alcaldía (caracterización
socio-demográfica en el modelo `Persona` y sus ~26 catálogos asociados), los
**eventos, cursos y actividades culturales y deportivas** (`kactivo`), la
**planeación y ejecución presupuestal** (`presupuesto`: proyectos, CDPs,
CRPs, indicadores y avances) y la **georreferenciación** de lugares y
hechos dentro del territorio de Kennedy.

Usuarios:

- **Funcionarios** de la alcaldía (registrados en `Funcionario` con
  dependencia + subgrupo), clasificados por roles/grupos.
- **Docentes** de cultura/deporte (en `kactivo.Docente`).
- **Participantes** del territorio (en `Participante` → `Persona`).
- Además existe un flujo de **votaciones** independiente (`votaciones`) para
  eventos puntuales tipo festival.

El proyecto se despliega on-premise con Docker en el servidor de la
alcaldía y expone un intranet (ruta pública vía túnel ngrok
`intranet-public-alk.ngrok.app`).

---

## 2. Stack tecnológico

| Capa | Componente | Versión |
|------|-----------|---------|
| Lenguaje | Python | 3.10-slim (Dockerfile) |
| Framework | Django | 4.2.11 |
| Servidor WSGI | gunicorn | 21.2.0 (3 workers, timeout 120, puerto 8032) |
| BD | PostgreSQL **externa** | `poblacion_kennedy` en `10.100.102.12:5432` |
| Driver | psycopg2-binary | 2.9.10 |
| Caché / colas | Redis | 7-alpine (maxmemory 256mb, allkeys-lru) |
| Reverse proxy | Nginx | alpine (puerto 8034 → 80) |
| Admin UI | Jazzmin | 2.6.0 |
| Dashboards | Dash + Plotly + django-plotly-dash | Dash 3.2+, Plotly 5.21+ |
| IA | OpenAI SDK | 1.10.0 (modelo vía `OPENAI_API_KEY`) |
| Geo | Folium (backend) + Leaflet (frontend, via estáticos) | Folium 0.15.1 |
| PDF | WeasyPrint, PyPDF2, ReportLab | 53.3 / 3.0.1 / 4.0.7 |
| Excel | openpyxl | 3.1.2+ |
| QR | qrcode[pil] | 8.2 |
| Mensajería web | channels | 4.0.0 (habilitado, sin ASGI declarado en settings) |
| Almacenamiento binario | MongoDB + GridFS (pymongo 4.6.3) | Solo para documentos |
| Frontend assets | Node 18 + webpack + SCSS | Compilados en `static/dist/` |

> Django reporta versión 4.2.11, pero los comentarios en `settings.py`
> referencian la doc de 5.2. El código real corre sobre 4.2.

### Servicios Docker declarados en `docker-compose.yml`

- `innova_k` — Django + gunicorn (expose 8032, sin puerto publicado).
- `innova_nginx` — Proxy estático + media (publica 8034 → 80).
- `innova_redis` — Cache y futuros canales.

### Servicios que **no** están en este compose

Se ejecutan desde otro compose externo al repo (probablemente
`docker-compose.override.yml` o uno en `/home/innova/Proyectos/`):

- `innova_adminer` — admin web de PostgreSQL.
- `innova_mailhog` — captura de emails en desarrollo.

Los backups automáticos de PostgreSQL los corre un cron a las **02:00 AM**
desde `~/Proyectos/postgres/backup_postgres.sh` (fuera del container).

---

## 3. Estructura de carpetas

```
innovaK/
├── core/                  # settings, urls raíz, wsgi/asgi
├── apps/
│   ├── login/             # Persona, Usuario, Funcionario, Evento, catálogos
│   ├── kactivo/           # Cultura + Deporte: cursos, clases, asistencias
│   ├── georeferenciacion/ # Lugar, Barrio, UPZ, Localidad, GeoReferenciacion
│   ├── presupuesto/       # Proyecto, Programa, CDP, CRP, Indicadores
│   ├── dashboard/         # Dash/Plotly + IA (OpenAI) para consultas
│   ├── votaciones/        # Flujo de votación con QR (Event, Candidate, Vote)
│   ├── documento/         # (NO montada) GridFS/MongoDB — abandonada
│   ├── kordial/           # Scaffold vacío
│   └── VitalK/            # Scaffold vacío
├── templates/             # Templates centralizados (no por app)
│   ├── base.html          # Layout principal
│   ├── home.html, login/, eventos/, cursos/, dashboard/, geo-mapas/,
│   ├── kactivo/, partials/, presupuesto/, votaciones/
├── static/                # Fuentes SCSS/JS + dist/ compilado por webpack
│   ├── dist/              # bundle.js, css
│   ├── mapas/             # Leaflet, GeoJSONs
│   └── package.json       # dependencias npm del front
├── media/                 # Uploads (montado como volumen)
├── core/settings.py       # Config Django
├── docker-compose.yml     # 3 servicios (k, nginx, redis)
├── Dockerfile             # Build: python 3.10 + node 18 + webpack
├── nginx.conf             # Proxy a gunicorn:8032
├── requirements.txt
├── manage.py
└── .env                   # NO versionado (en .gitignore)
```

### Rol de cada app

| App | Registrada en INSTALLED_APPS | URL prefix | Rol |
|-----|------------------------------|------------|-----|
| `login` | ✅ | `/` | Autenticación, personas, funcionarios, eventos (nuevo modelo) |
| `kactivo` | ✅ | `/kactivo/` | Cultura y deporte — caracterizaciones, cursos, asistencia, validación documental |
| `georeferenciacion` | ✅ | `/geo/` | Mapa Kennedy (Leaflet), APIs GeoJSON, dashboard de gráficos |
| `presupuesto` | ✅ | `/presupuesto/` | Planeación: proyectos, programas, CDPs, indicadores |
| `dashboard` | ✅ | `/dashboard/` | Consultas inteligentes con IA (Dash + OpenAI) y KPIs de presupuesto |
| `votaciones` | ✅ | `/votaciones/` | Flujo de votación independiente con QR |
| `documento` | ❌ **NO** | — | Código abandonado (ver deuda técnica) |
| `kordial` | ✅ | ❌ sin URLs | Vacío (solo `__init__.py` en models y views) |
| `VitalK` | ✅ | ❌ sin URLs | Vacío (solo `__init__.py` en models y views) |

### Convenciones internas de cada app

La mayoría de apps siguen este layout:

```
apps/<nombre>/
├── apps.py
├── admin.py
├── urls.py
├── forms.py            # Donde aplique
├── models/
│   ├── __init__.py     # Re-exporta clases
│   └── <dominio>.py    # Un archivo por subgrupo de modelos
├── views/
│   ├── __init__.py
│   └── <vista>.py      # Un archivo por página o grupo de endpoints
└── services/           # Lógica de negocio reutilizable
    └── <servicio>.py
```

Excepciones:

- `apps/login/` tiene además un archivo `models.py` además del paquete
  `models/` (el archivo es código muerto; Django resuelve el paquete).
- `apps/presupuesto/` tiene `forms.py`, `forms_cdp.py`, `forms_indicadores.py`.
- `apps/kactivo/` tiene subdirectorio `sub_grupo_cultura/` (dominio específico).
- `apps/votaciones/` **no** tiene `apps.py`; Django usa AppConfig por defecto.

---

## 4. Diagramas de relaciones clave

### 4.1 Cadena geográfica

```
Evento
  └─ lugar_incidencia_id ──▶ LugarIncidencia
                                  └─ geo_referenciacion_id ──▶ GeoReferenciacion
                                                                    ├─ latitud (Decimal 9,6)
                                                                    ├─ longitud (Decimal 9,6)
                                                                    ├─ fuente (CharField 10)
                                                                    ├─ precision (CharField 20)
                                                                    └─ lugar_id ──▶ Lugar
                                                                                       ├─ localidad_codigo ──▶ Localidad
                                                                                       ├─ upz_codigo       ──▶ UPZ
                                                                                       └─ barrio_codigo    ──▶ Barrio
```

- Todos los FK de `Lugar` a Localidad/UPZ/Barrio usan `to_field='codigo'` con
  `on_delete=SET_NULL`.
- `UPZ` y `Barrio` tienen `localidad_codigo` / `upz_codigo` como IntegerField
  **sin FK formal**. La relación es por valor, no por constraint.
- `LugarIncidencia.coordenadas` es `@property` que devuelve
  `{lat, lon}` encadenando hacia `GeoReferenciacion`.

### 4.2 Cadena del plan (eje del dashboard presupuestal)

```
Evento ──▶ ActividadPlan ──▶ Proyecto ──▶ Programa ──▶ Objetivo
                          │                  ├─ Tematica
                          │                  └─ Vigencia
                          └─ Actividad
                  MetaProyectoBD (FK Proyecto + MetaBD)
                          │
                          └─ Indicador ──▶ AvanceIndicador
                                        │
                                        └─ ImpactoActividadIndicador (FK ActividadPlan)

Proyecto ──▶ PresupuestoProyecto
Proyecto ──▶ Cdp ──▶ Crp
Proyecto ──▶ ProyectoInversionItem ──▶ ProyectoInversion
Proyecto ──▶ PresupuestoTiempo (por FaseProyecto)

Contrato ──▶ ContratoProyecto ──▶ Proyecto
          ├─ ContratoActividad ──▶ Actividad (catálogo SIPSE, legacy)
          └─ ContratoActividadPlan ──▶ ActividadPlan
                                   ├─ MetaProyecto (rubro de negocio)
                                   └─ ConceptoGasto (rubro presupuestal)
```

**Sesión 2026-04-25/26 — Cadena completa funcional end-to-end:**

```
Proyecto
  ├─ CDPs (dinero asignado)
  ├─ Contratos (vía ContratoProyecto)
  │    └─ ContratoActividadPlan (PR-H3, NUEVO):
  │         monto + fecha_inicio + fecha_fin + meta_proyecto_id + concepto_gasto_id
  ├─ MetaProyecto
  │    └─ Indicador (KPI)
  │         ↑ ActividadIndicador
  │         └─ AvanceIndicador (origen=EVENTO|MANUAL|AJUSTE)
  └─ ActividadPlan
       ├─ ContratoActividadPlan (financia)
       ├─ ActividadIndicador (aporta a KPI)
       └─ Evento → genera AvanceIndicador con magnitud_aportada

Saldo presupuestal del Proyecto:
   ΣCDPs.valor − Σ contrato_actividad_plan.monto WHERE actividad_plan.proyecto = X
```

**Vinculación contrato↔actividad — dos tablas:**
- `contrato_actividad` (legacy, 98 filas, vincula a `Actividad` del catálogo SIPSE; no se usa en flujo nuevo).
- `contrato_actividad_plan` (PR-H3, vincula a `ActividadPlan` real con monto/meta/rubro).

### 4.3 Persona y sus catálogos

```
Persona (43 campos, 14 FKs)
  ├─ lugar_nacimiento_id   ──▶ LugarNacimiento  (→ País, Depto, Municipio)
  ├─ grupo_etario_id       ──▶ GrupoEtario
  ├─ sexo_id               ──▶ Sexo
  ├─ identidad_genero_id   ──▶ IdentidadGenero
  ├─ orientacion_sexual_id ──▶ OrientacionSexual
  ├─ grupo_etnico_id       ──▶ GrupoEtnico
  ├─ tipo_discapacidad_id  ──▶ TipoDiscapacidad
  ├─ tipo_victima_id       ──▶ TipoVictima
  ├─ zona_id               ──▶ Zona  (⚠ duplicada con geo.Zona)
  ├─ nivel_educativo_id    ──▶ NivelEducativo
  ├─ ocupacion_id          ──▶ Ocupacion
  ├─ sector_economico_id   ──▶ SectorEconomico
  ├─ persona_documento_id  ──▶ PersonaDocumento (→ TipoDocumento)
  └─ usuario_id            ──▶ Usuario (AbstractUser)

Persona 1──1 Sisben  (OneToOne)
Persona 1──1 ContactoPersona  (por id, integer PK)
Persona 1──N Participante 1──N Inscripcion ──▶ Curso | Evento(kactivo)
Persona 1──1 Funcionario ──▶ Dependencia ──▶ Subgrupo
                          └─ Cargo, TipoFuncionario
```

### 4.4 Cultura / Deporte (kactivo)

```
Participante ──┬─▶ ClaseParticipante ──▶ Clase ──▶ Grupo / Disciplina / Lugar
               ├─▶ ParticipanteEvento ──▶ Evento (kactivo — LEGACY)
               ├─▶ Acudiente
               ├─▶ DocumentoParticipante ──▶ TipoArchivo
               ├─▶ ValidacionDocumental (OneToOne) ──▶ DocumentoRequisito
               ├─▶ EvaluacionParticipante
               └─▶ NotaMedica

Clase ──▶ HorarioClase
      └─▶ Asistencia (tabla asistencia_clase)

Curso ──▶ Clase
      └─▶ Programa (kactivo — ⚠ duplicado con presupuesto)

Docente ──▶ Persona
```

### 4.5 Votaciones

```
Event ──N── Candidate
  │           │
  │           └─── dos categorías (artistas identidades / derechos)
  └─ Vote
      ├─ event_id (PROTECT)
      ├─ candidate_identidades_id (PROTECT)
      └─ candidate_derechos_id (PROTECT)

Voter (independiente, con unique email)
```

---

## 5. Flujos principales del usuario

### 5.1 Registro de persona

1. `/login/` → autenticación con `Usuario` (AuthUser subclase).
2. `login:crear_persona` (`/crear-persona/`) → formulario con catálogos en
   cascada (ver sección "Endpoints cascada" más abajo).
3. Al guardar, se genera ID manualmente con
   `SELECT COALESCE(MAX(id), 0) + 1 FROM persona` dentro de
   `transaction.atomic()` porque la tabla no tiene `DEFAULT nextval`.
4. Redirect a `login:crear_participante` para vincular como participante.

### 5.2 Inscripción a evento

1. `GET /evento/inscripcion/<id>/` (público — no requiere login).
2. Usuario ingresa documento → AJAX `login:obtener_barrios` y similares
   rellenan dropdowns.
3. `POST` crea `Persona` si no existe (mismo patrón MAX(id)+1), luego
   `Participante`, luego registra inscripción vía raw SQL.
4. Redirect a `login:registro_exitoso`.

### 5.3 Creación de evento (actualizado 2026-04-26)

**Funciona end-to-end** (`login/views/eventos.py:233+`, `crear_evento`):

- Formulario con cascada Proyecto → ActividadPlan → Indicador (KPI).
- Captura magnitud aportada al KPI.
- Selección/creación de `LugarIncidencia` vía modal Leaflet.
- Al guardar:
  1. Inserta `evento` (FKs `actividad_plan_id`, `indicador_id`, `lugar_incidencia_id`).
  2. Crea `AvanceIndicador` con `origen='EVENTO'` automáticamente.

**Edición** (`editar_evento`, refactor PR-F):
- Form completo (nombre, descripción, fechas, magnitud).
- Si la magnitud cambia, sincroniza el `AvanceIndicador` asociado y
  cambia su origen a `'AJUSTE'` con observación auditable.
- NO permite cambiar `indicador_id` ni `actividad_plan_id` (destructivo).
- Muestra al final lista de "Contratos que financian esta actividad"
  con número, fechas, monto, meta, rubro.

### 5.5 Hub de tableros y sub-hubs (PR-A→C)

`/dashboard/` muestra 5-6 cards top-level por módulo:
- Presupuesto → `/dashboard/hub/presupuesto/` (12 cards: dashboard KPIs,
  CRUD proyectos/programas/CDPs/conceptos/objetivos/metas/meta-proyecto/
  KPIs/avances/vinculación/contratos)
- Actividades → `/dashboard/hub/actividades/` (lista, crear, tipos)
- Territorio → `/geo/mapa-kennedy/` (directo)
- Votaciones → `/dashboard/hub/votaciones/`
- Consulta IA → `/dashboard/ai/`
- Administración → `/dashboard/hub/admin/` (8 cards: usuarios, tipos act.,
  dependencias, subgrupos, funcionarios, organizaciones, proveedores,
  beneficiarios)

Componentes UI (PR-B/C):
- Breadcrumb global (context processor + partial + SCSS).
- Botón `.ui-back-link` "Volver a {parent}" en sub-hubs y formularios.
- `.ui-empty-state` para placeholders.
- Cache-buster automático en CSS/JS via mtime de `base.css`.

### 5.6 Vista 360° (PR-G/H4)

`/presupuesto/proyectos/<id>/` — TODO el flujo del proyecto en una pantalla:
- 5 tiles: CDPs, Metas, KPIs, % avance, **Saldo presupuestal** (verde si
  cdp_total ≥ comprometido, rojo si <).
- Sección Dinero (CDPs + total).
- Sección Contratos (con monto comprometido por contrato en este proyecto).
- Sección Metas (con KPIs hijos + barras color-condicional ≥80/≥50/<50).
- Sección Actividades del plan (link a vista 360 de cada una).

`/presupuesto/actividades-plan/<id>/` — TODO de UNA ActividadPlan:
- 4 tiles: KPIs vinculados, eventos ejecutados, contratos, total $.
- Sección KPIs con aporte de esta actividad vs aporte global.
- Sección Eventos ejecutados.
- Sección Contratos que financian.

`/presupuesto/contratos/<id>/` — Detalle de contrato + vinculaciones a
actividades del plan con monto/meta/rubro/fechas.

### 5.4 Carga de documentos

- `kactivo:cargue_documento` (por participante) — sube archivos a MongoDB
  vía `kactivo/services/mongo_upload.py` (GridFS).
- `kactivo:validacion_documental` — revisa y marca estado aprobado/rechazado.
- El flujo paralelo en `apps/documento/` (no montado) hace lo mismo pero
  desde su propio paquete; está abandonado.

---

## 6. Integración con servicios externos

| Servicio | Uso | Archivos clave |
|----------|-----|----------------|
| PostgreSQL (externo) | Fuente única de verdad del dominio | `core/settings.py`, todas las apps |
| Redis | Cache y futuras sesiones/canales | `docker-compose.yml` |
| MongoDB/GridFS | Almacenamiento de PDFs escaneados | `apps/kactivo/services/mongo_upload.py`, `apps/documento/utils/mongo_conexion.py` (inactivo) |
| OpenAI | Intent analyzer del dashboard AI | `apps/dashboard/services/intent_analyzer.py` |
| OneDrive | Upload (stub incompleto) | `apps/kactivo/services/onedrive_upload.py` |
| Ngrok | Exposición pública temporal | `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` |

Cron del host (fuera de Docker):

- `~/Proyectos/postgres/backup_postgres.sh` — backup diario 02:00 AM.

---

## 7. Convenciones detectadas

### ✅ Convenciones que **se respetan**

- **BD externa, todo `managed=False`.** Ninguna app ejecuta migraciones de
  Django sobre este schema. El contenido de `apps/*/migrations/` **no se
  usa** y suele estar gitignored (`**/migrations/*.py` en `.gitignore`).
- **Nombres en español** tanto en modelos, campos, vistas, URLs y templates
  (`crear_persona`, `lugar_incidencia`, `actividad_plan`). Algunos nombres
  bilingües aislados en `votaciones` (Event, Candidate, Voter, Vote).
- **Function-based views (FBV)** en todas las apps. No hay CBV en el
  proyecto. Decoradores `@login_required` y `@group_required` son el
  mecanismo de control de acceso.
- **Un archivo por subgrupo de modelos** dentro de `models/`, re-exportados
  desde `__init__.py`.
- **Templates centralizados** en `/templates/` raíz con subcarpetas por
  módulo, no por app.
- **FKs con `db_column` explícito** para alinearse con el schema existente
  (consistente en presupuesto, votaciones, kactivo mayoritariamente).
- **`to_field='codigo'`** para FKs a tablas con PK de código conocido
  (catálogos: Pais, Departamento, Municipio, Localidad, UPZ, Barrio,
  Tematica, CategoriaTematica, TipoEvento).
- **Lógica de dominio en `services/`** (bien usado en dashboard, presupuesto,
  votaciones).
- **AJAX endpoints prefijados con `api/`** y devolviendo `JsonResponse`
  (no se usa Django REST Framework en ninguna parte).

### ⚠️ Convenciones **mezcladas o inconsistentes**

- **Prefijo `public.` en `db_table`**: solo en `Contrato`, `ContratoProyecto`
  y `ContratoActividad` (`presupuesto/core.py:69,77,85`). El resto (>50
  clases) no lo usa. Funcionalmente equivalente en PostgreSQL.
- **Tipo de PK**: algunas tablas usan `IntegerField` como PK manual
  (catálogos), otras `BigAutoField` (Lugar, GeoReferenciacion, Persona),
  otras `AutoField`. Mezcla heredada del schema.
- **`on_delete`**: `CASCADE`, `SET_NULL`, `PROTECT`, `DO_NOTHING` usados sin
  criterio uniforme. `DO_NOTHING` dominante en presupuesto, `CASCADE` en
  relaciones fuertes de kactivo.
- **`@login_required`**: cobertura estimada ~62% (110 decoradores sobre 178
  funciones en views/). Varias vistas sensibles sin protección
  (ver [DEUDA_TECNICA.md](./DEUDA_TECNICA.md)).

### ❌ Convenciones **no aplicadas**

- No hay **tests reales**: `tests.py` existen como stubs vacíos. Tampoco
  hay configuración de pytest.
- No hay **paginación sistemática** en endpoints que devuelven listas —
  solo 3 archivos usan `Paginator`.
- No hay **logger estructurado** fuera de `dashboard/apps.py`. La mayoría
  de apps usan `print()` o no logean nada.
- No hay **signals** en ninguna app (revisado con grep sobre `@receiver`).
- No hay **Celery ni colas** — `channels` está instalado pero sin ASGI
  declarado en settings.

---

## 8. Notas importantes para futuros desarrolladores

1. **Nunca toques `apps/*/migrations/`**. La BD es externa, managed=False
   en todos los modelos; las migraciones no se aplican.
2. **Cambios de schema** requieren ejecutar el SQL directamente sobre la
   BD externa y luego actualizar el modelo Django para reflejarlo.
   El dueño (Alex) confirma antes de cualquier cambio.
3. **Las apps `kordial`, `VitalK` y `documento` no hacen nada en runtime
   actual**. No dependas de ellas. Si necesitas funcionalidad similar,
   revisa primero qué hay en `kactivo/services/` antes de reutilizar.
4. **El Dockerfile es engañoso**: expone 8000 y arranca `runserver`, pero
   `docker-compose.yml` lo sobrescribe con gunicorn en 8032. La imagen
   se usa por el build, no por su CMD.
5. **Los 6 índices de performance del dashboard** fueron creados
   manualmente en la BD y **no están reflejados como `indexes = [...]`**
   en los modelos. Si revisas el código Python, no los verás — pero
   existen en PostgreSQL.

---

## 9. Stack: versiones exactas (snapshot 2026-04-27)

### Runtime
| Componente | Versión |
|------------|---------|
| Python | 3.10.20 |
| Django | 4.2.11 |
| Gunicorn | 21.2.0 (3 workers, timeout 120s) |
| PostgreSQL (externo) | 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1) |
| Redis | 7.4.7 (alpine, 256MB max, allkeys-lru) |
| Nginx | 1.29.7 (alpine) |
| pymongo | 4.6.3 (cliente; servidor en otro host) |

### Dependencias Python clave (ver `requirements.txt` para lista completa)
| Paquete | Versión |
|---------|---------|
| psycopg2-binary | 2.9.10 |
| Dash | 3.2.0 |
| dash-bootstrap-components | 2.0.4 |
| django-plotly-dash | 2.5.0 |
| plotly | 5.21+ |
| pandas | 2.3.3 |
| Flask | 3.1.3 (sub-dep de Dash) |
| openai | 1.10.0 |
| folium | 0.15.1 |
| channels | 4.0.0 (instalado, no usado en runtime) |
| qrcode[pil] | 8.2 |
| weasyprint | 53.3 |
| reportlab | 4.0.7+ |
| openpyxl | 3.1.5 |
| PyPDF2 | 3.0.1 |
| python-docx | 1.1.0 |
| django-jazzmin | 2.6.0 (admin theme) |
| django-select2 | 8.4.8 |
| django-widget-tweaks | 1.5.1 |

### Servicios Docker (`docker-compose.yml`)
| Container | Imagen | Puerto host | Estado |
|-----------|--------|-------------|--------|
| `innova_k` | innovak-innova_k (Django 4.2 + Python 3.10 alpine-ish build) | expose 8032 | healthy |
| `innova_nginx` | nginx:alpine | **8034:80** (entrada pública) | healthy |
| `innova_redis` | redis:7-alpine | (interno) | healthy |
| `innova_adminer` | adminer:latest | (gestionado fuera del compose principal) | up |
| `innova_mailhog` | mailhog/mailhog | (testing email) | up |

### BD externa (no en compose)
- Host: `host.docker.internal:5432` desde container · `10.100.102.12:5432` desde la red local.
- Database: `poblacion_kennedy` (compartida con otros sistemas distritales).
- Usuario: `innova-bd` (lectura/escritura controlada).
- Backups: cron del host a las **02:00 AM** → `~/Proyectos/postgres/backups/poblacion_kennedy_diario.dump` (~1.8MB).

---

## 10. Red e IPs

### IPs del servidor host (LAN Alcaldía)
| Interfaz | IP/CIDR | Uso |
|----------|---------|-----|
| `enp0s31f6` | **10.100.102.12/25** | LAN privada de la Alcaldía. Punto de entrada para BD compartida. |
| `docker0` | 172.17.0.1/16 | Bridge Docker default |
| `br-787ed47f83cd` | 172.19.0.1/16 | Bridge Docker compose innovaK |
| `br-9ffba5771b3b` | 172.18.0.1/16 | Bridge secundario |

### IP pública (saliente)
- **186.30.30.242** (NAT del router de la Alcaldía hacia internet).
- ⚠️ Esta IP cambia si el ISP la rota; **si gov.net abre puerta**, considerar IP fija o rango ASN del proveedor.

### Túneles ngrok activos (acceso temporal externo)
| URL pública | Apunta a | Uso |
|-------------|----------|-----|
| `intranet-public-alk.ngrok.app` | innova_nginx:8034 | Validación de cambios en producción desde fuera de LAN |
| `dev-desarrollo-alk.ngrok.dev` | kennedyconecta_web1:8000 | Otro proyecto del host |
| `ander-dev-alk.ngrok.dev` | host.docker.internal:8081 | Otro proyecto del host |

### Para gov.net (RAVEC) — Apertura recomendada
Si el gobierno nos abre puerta hacia red gubernamental:
- **Puerto entrante**: 443 HTTPS (terminar TLS en Nginx, hoy escucha 8034 sin TLS — habría que agregar certificado).
- **Puerto BD saliente** (si la integración requiere acceso a otra BD): 5432.
- **API REST**: hoy NO exponemos endpoints REST públicos versionados; los `/api/*` y `/ajax/*` están detrás de `@login_required`. Si la integración con gov.net es API-to-API se necesitaría capa de auth nueva (JWT/OAuth o API Key con rate limiting).
- **Filtrado por IP origen** en Nginx si el gobierno provee rango fijo.

---

## 11. APIs externas que consumimos

| Servicio | Versión SDK | Variable .env | Uso |
|----------|-------------|---------------|-----|
| OpenAI | openai 1.10.0 | `OPENAI_API_KEY` | Consultas IA en `/dashboard/ai/` (intent → SQL → resumen) |
| Microsoft Graph (OneDrive) | requests 2.31+ | `ONEDRIVE_TOKEN` | Subida de documentos a OneDrive (`/v1.0/me/drive/root`) |
| OpenStreetMap tiles | (sin SDK, JS Leaflet) | — | Tile layer del mapa Kennedy |
| CartoDB Voyager | (sin SDK, JS Leaflet) | — | Tile layer alternativo del mapa |
| jsDelivr / unpkg / cdnjs | (CDN público) | — | Bootstrap 5.3.3, Leaflet 1.9.4, Select2 4.1, jQuery 3.7, Font Awesome 6.5.2, Bootstrap Icons 1.10 |
| MongoDB | pymongo 4.6.3 | `MONGO_URI`, `MONGO_DB` | GridFS para documentos de participantes (kactivo) |
| MailHog (testing) | smtp directo | `EMAIL_HOST=mailhog`, `EMAIL_PORT=1025` | Captura de emails en dev |

---

## 12. APIs internas que exponemos

Todas montadas en Django sin DRF (vistas function-based + `JsonResponse`).
**Todas requieren `@login_required`** salvo las marcadas como públicas.

### Login / Personas
- `GET /api/personas/search/?q=...&page=N` — Select2 autocomplete (PR-N5)
- `POST /api/buscar-persona/` — búsqueda específica por cédula (votaciones)
- `GET /api/subgrupos/?area_id=N`
- `GET /api/funcionarios/?subgrupo_id=N`
- `GET /api/cursos/?area=...`

### Presupuesto
- `GET /presupuesto/api/proyectos/`
- `GET /presupuesto/api/subgrupos/`
- `POST /presupuesto/api/subgrupos/create/`
- `GET /presupuesto/api/actividades-por-proyecto/<id>/`
- `GET /presupuesto/api/plan-actividades-por-proyecto/<id>/`
- `GET /presupuesto/api/indicadores-por-actividad/<id>/`
- `GET /presupuesto/ajax/conceptos/`
- `GET /presupuesto/ajax/proyectos/`

### Georeferenciación
- `GET /geo/api/eventos/` — FeatureCollection de eventos con filtros
- `GET /geo/api/kennedy/barrios/`, `upz/`, `contorno/`, `parques/`, `escuelas/`
- `POST /geo/api/lugar/` — crear LugarIncidencia desde modal Leaflet
- `GET /ajax/barrios/?upz=N`

### Dashboard
- `GET /dashboard/api/resumen-ejecutivo/`
- `GET /dashboard/api/eventos-mes-tipo/`
- `GET /dashboard/api/top-sectores/`
- `GET /dashboard/api/objetivos-por-proyecto/`
- `GET /dashboard/api/metas-progreso/`
- `GET /dashboard/api/kpis-avance/`

### Votaciones
- `GET /votaciones/api/listado-votantes/`
- `GET /votaciones/api/tipos-documento/`
- `POST /votaciones/api/registrar-votante/`
- `POST /votaciones/api/validate-voter/`

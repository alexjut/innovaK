# Arquitectura — innovaK

> Fuente de verdad de alto nivel sobre el proyecto **innovaK** (Alcaldía Local
> de Kennedy, Bogotá). Este documento se mantiene a mano; los detalles de
> deuda viven en [DEUDA_TECNICA.md](./DEUDA_TECNICA.md).
>
> **Última actualización: 2026-07-06.** Cambios de esta revisión (sincronización
> con el código real): se eliminó por completo la app `kactivo` (fusionada en
> `apps.login` el 2026-05-27 y borrada del repo — cursos, clases, asistencia y
> participantes viven ahora bajo el modelo unificado `login.Evento`); se
> documentaron las 6 apps nuevas (`banco_iniciativas`, `caracterizacion`,
> `jovenes_a_la_e`, `entregas`, `festivales`, `documentos`); se corrigió el stack
> (MongoDB 7 para PII cifrada, DRF + JWT, frontend Angular servido desde Django en
> `/app/*`); y se actualizó el estado de la capa de templates (Django hoy es
> API/exports/kiosko/admin; toda la UI de organizador migró a Angular). El
> prefijo `public.` en las tablas de contrato ya no existe (deuda S5 resuelta).

---

## 1. Visión general

**innovaK** es un sistema de información interno para la Alcaldía Local de
Kennedy. Gestiona la **población atendida** por la alcaldía (caracterización
socio-demográfica en el modelo `Persona` y sus ~26 catálogos asociados), toda
la **actividad territorial** unificada en el modelo `Evento` de `apps.login`
(eventos, cursos, capacitaciones, asistencia, entregas, caracterizaciones e
inscripciones — cada tipo diferenciado por `TipoEvento`), la **planeación y
ejecución presupuestal** (`presupuesto`: proyectos, CDPs, CRPs, contratos,
metas, indicadores y avances) y la **georreferenciación** de lugares y hechos
dentro del territorio de Kennedy.

Sobre esa base viven los **módulos de captura específicos** (una app por
programa, todos colgando de la cadena presupuestal): Banco de Iniciativas
recreodeportivas, Caracterización ciudadana por sectores, Jóvenes a la E
(becas), Entregas de insumos y Festivales.

Usuarios:

- **Funcionarios** de la alcaldía (registrados en `Funcionario` con
  dependencia + subgrupo), clasificados por roles/grupos dinámicos (N15).
- **Docentes** de cursos/capacitaciones (en `login.Docente`, que vincula un
  `Funcionario` al rol formal; el gating de "qué cursos ve" es por
  `Evento.funcionario_id`).
- **Participantes** del territorio (en `Participante` → `Persona`), inscritos a
  eventos vía `ParticipanteEvento`.
- **Ciudadanos** que diligencian formularios públicos vía QR (sin login), tanto
  en el frontend Angular (`/app/p/*`) como en los flujos de captura.
- Además existe un flujo de **votaciones** independiente (`votaciones`) para
  eventos puntuales tipo festival.

El proyecto se despliega on-premise con Docker en el servidor de la
alcaldía. La UI es una **SPA Angular servida por el propio Django bajo `/app/*`**
(mismo origen, sin nginx aparte para el front); Django expone además la API REST
(DRF + JWT), los exports y el kiosko de votación. Se publica como intranet vía
túnel ngrok `intranet-public-alk.ngrok.app`.

---

## 2. Stack tecnológico

| Capa | Componente | Versión |
|------|-----------|---------|
| Lenguaje | Python | 3.10-slim (Dockerfile) |
| Framework | Django | 4.2.11 |
| Servidor WSGI | gunicorn | 21.2.0 (3 workers, timeout 120, puerto 8032) |
| BD relacional | PostgreSQL **externa** | `poblacion_kennedy` en `10.100.102.12:5432` (todo `managed=False`) |
| Driver | psycopg2-binary | 2.9.10 |
| BD documental / PII | MongoDB | 7 (PII y firmas **cifradas AES-256** vía `apps.documentos`; pymongo 4.6.3) |
| Caché / sesiones | Redis | 7-alpine (maxmemory 256mb, allkeys-lru; DB `/1` cache, sesiones en cache) |
| Reverse proxy | Nginx | alpine (puerto 8034 → gunicorn 8032) |
| API REST | Django REST Framework + SimpleJWT | JWT (Bearer) primero, SessionAuth de respaldo |
| OpenAPI | drf-spectacular | `/api/schema/`, `/api/docs/` (Swagger), `/api/redoc/` |
| Frontend | **Angular** (SPA) | servido por Django bajo `/app/*` (build en `frontend/dist/`, base-href `/app/`) |
| Admin UI | Jazzmin | 2.6.0 (solo `/admin/`) |
| Dashboards | Dash + Plotly + django-plotly-dash | Dash 3.2+, Plotly 5.21+ |
| IA | OpenAI SDK | 1.10.0 (modelo vía `OPENAI_API_KEY`) |
| Geo | Folium (backend) + Leaflet (frontend) | Folium 0.15.1 |
| PDF | WeasyPrint, PyPDF2, ReportLab | 53.3 / 3.0.1 / 4.0.7 |
| Excel | openpyxl | 3.1.2+ |
| QR | qrcode[pil] | 8.2 (QR públicos con token HMAC `?t=`, modo suave) |
| CORS | django-cors-headers | Angular dev `:4200` en DEBUG; en prod mismo origen |
| Mensajería web | channels | 4.0.0 (instalado, sin ASGI declarado — no usado en runtime) |

> Django reporta versión 4.2.11; algunos comentarios en `settings.py`
> referencian la doc de 5.2. El código real corre sobre 4.2.11.

### Servicios Docker declarados en `docker-compose.yml`

- `innova_k` — Django + gunicorn (expose 8032, sin puerto publicado).
- `innova_nginx` — Proxy estático + media (publica 8034 → 80).
- `innova_redis` — Cache + sesiones (redis:7-alpine, volume persistente).
- `innova_mongo` — MongoDB 7 (storage cifrado de firmas/PII, volume persistente,
  healthcheck `mongosh ping`). `innova_k` depende de él.

La PostgreSQL es **externa** (`10.100.102.12:5432`), no está en este compose.

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
├── apps/                  # 11 apps activas (ver tabla) + 2 scaffolds muertos
│   ├── login/             # Persona, Usuario, Funcionario, Evento (unificado),
│   │                      #   cursos/clases/asistencia, roles dinámicos, API DRF
│   ├── georeferenciacion/ # Lugar, Barrio, UPZ, Localidad, GeoReferenciacion, mapa
│   ├── dashboard/         # Hub, Dash/Plotly + IA (OpenAI), KPIs presupuestales
│   ├── presupuesto/       # Proyecto, Programa, CDP, CRP, Contrato, Indicadores
│   ├── votaciones/        # Flujo de votación con QR (Event, Candidate, Vote)
│   ├── banco_iniciativas/ # Captura pública recreodeportiva (proyecto 2784)
│   ├── caracterizacion/   # 7 wizards de caracterización por sector
│   ├── jovenes_a_la_e/    # Entrega de becas (convenios 773/955-2025)
│   ├── entregas/          # Entrega de insumos (tipo_evento ENTREGA)
│   ├── festivales/        # Festivales (agrupan N eventos) — Cultura 2780
│   ├── documentos/        # Servicio: cifrado AES-256 + MongoDB (firmas/PII)
│   ├── kordial/           # ⚰ scaffold vacío NO instalado (pendiente de borrar)
│   └── VitalK/            # ⚰ scaffold vacío NO instalado (pendiente de borrar)
├── frontend/              # SPA Angular (código fuente); build en dist/ → /app/*
│   ├── src/app/           # features, servicios, guards, interceptores
│   └── dist/              # build de producción (gitignored; rebuild al deploy)
├── templates/             # Solo lo que Django sigue renderizando:
│   ├── base.html          #   layout legacy (residual)
│   ├── _partials/         #   parciales (breadcrumb, etc.)
│   └── votaciones/        #   kiosko de votación (se queda en Django)
├── static/                # Estáticos legacy (SCSS/JS) + dist/ webpack + mapas/
├── media/                 # Uploads (montado como volumen)
├── core/settings.py       # Config Django
├── docker-compose.yml     # servicios (k, nginx, redis; mongo en compose aparte)
├── Dockerfile             # Build: python 3.10 + node
├── nginx.conf             # Proxy a gunicorn:8032
├── requirements.txt
├── manage.py
└── .env                   # NO versionado (en .gitignore)
```

> **Migración Full-Angular (2026-06):** casi toda la UI de organizador que antes
> vivía como templates Django (`eventos/`, `cursos/`, `dashboard/`, `presupuesto/`,
> `login/`, etc.) fue migrada a Angular. Las vistas Django viejas quedaron como
> `redirect('/app/...')` y sus templates se están retirando por lotes. Django hoy
> actúa como **API REST + exports + kiosko de votación + `/admin/`**.

### Rol de cada app (11 activas en `INSTALLED_APPS`)

| App | URL prefix | Rol |
|-----|------------|-----|
| `login` | `/` y `/api/*` | Núcleo: autenticación (`Usuario` = AUTH_USER_MODEL), `Persona` + ~26 catálogos, `Funcionario`/`Dependencia`/`Subgrupo`, **modelo unificado `Evento`/`TipoEvento`**, cursos (`Clase`, `HorarioClase`, `AsistenciaClase`, `EvaluacionParticipante`, `Docente`, `Grupo`, `Acudiente`, `NotaMedica`), inscripción a eventos (`ParticipanteEvento`), documentos de evento, motor genérico de captura (`captura_generica`), sistema de roles dinámico (N15) y buena parte de la API DRF |
| `georeferenciacion` | `/geo/` | Mapa de Kennedy (Leaflet), `Lugar`/`Barrio`/`UPZ`/`Localidad`/`Parque`/`Escuela`/`GeoReferenciacion`/`LugarIncidencia`, APIs GeoJSON |
| `dashboard` | `/dashboard/` | Hub principal, consultas IA (Dash + OpenAI), KPIs presupuestales, breadcrumbs, `HubCard` |
| `presupuesto` | `/presupuesto/` | Planeación y ejecución: `Proyecto`, `Programa`, `Cdp`/`Crp`, `Contrato`/`ContratoProyecto`/`ContratoActividad`/`ContratoActividadPlan`, `ActividadPlan`, metas e indicadores |
| `votaciones` | `/votaciones/` | Flujo de votación con QR (`Event`, `Candidate`, `Voter`, `Vote`) — kiosko en Django, en inglés por excepción |
| `banco_iniciativas` | `/banco-iniciativas/` | Banco de Iniciativas recreodeportivas (proyecto 2784): inscripción pública + evaluación por rúbrica + ~11 catálogos + tablas puente M2M |
| `caracterizacion` | `/caracterizacion/` | 7 caracterizaciones por sector (cultura, deporte, mujer, salud, poblacional, participación ciudadana, seguridad) + `InformacionHogar`; wizard schema-driven |
| `jovenes_a_la_e` | `/jovenes-a-la-e/` | Entrega de becas del programa "Jóvenes a la E" (convenios 773/955-2025): `EntregaBeca` + elementos + catálogo `ElementoDotacion` |
| `entregas` | `/entregas/` | Entrega de insumos a beneficiarios (`tipo_evento='ENTREGA'`): `EntregaInsumo` + `EntregaInsumoElemento` (catálogo = `Implemento`) |
| `festivales` | `/festivales/` | Festivales culturales (Cultura 2780): `Festival` agrupa N eventos; días, asistencia, evaluación, archivos, ficha pública |
| `documentos` | — (servicio interno) | Almacenamiento **cifrado AES-256** en MongoDB de firmas/PII (`services/cifrado.py`, `services/mongo_storage.py`); reusado por Banco, Caracterización, Jóvenes y Entregas. Sin `urls.py` ni modelos SQL |

**Apps NO instaladas (código muerto en disco):** `apps/kordial/` y `apps/VitalK/`
son scaffolds vacíos (solo `models/` y `migrations/` sin uso). No están en
`INSTALLED_APPS` ni en `core/urls.py`; pendientes de borrar. La antigua
`apps/kactivo/` y `apps/documento/` (singular) **ya no existen** en el repo.

### Convenciones internas de cada app

La mayoría de apps siguen este layout:

```
apps/<nombre>/
├── apps.py
├── admin.py            # Donde aplique
├── urls.py
├── forms/ o forms.py   # Donde aplique
├── models/
│   ├── __init__.py     # Re-exporta clases
│   └── <dominio>.py    # Un archivo por subgrupo de modelos
├── views/
│   ├── __init__.py
│   └── <vista>.py      # Un archivo por página o grupo de endpoints
├── api/                # Vistas/serializers DRF (endpoints Angular-ready)
└── services/           # Lógica de negocio reutilizable
    └── <servicio>.py
```

Excepciones y detalles:

- `apps/login/` es la app más grande: paquete `models/` con ~18 archivos de
  dominio, `views/` y `api/` amplios, `services/`, `management/` y
  `templatetags/`. Ya **no** existe el archivo `models.py` suelto (borrado; el
  paquete `models/` es la única fuente).
- `apps/presupuesto/` tiene `forms.py` y `forms_cdp.py`.
- `apps/documentos/` es un módulo de servicio: solo `services/` (cifrado +
  MongoDB), sin `models/`, `urls.py` ni `views/`.
- `apps/festivales/` no tiene `views/` HTML; todo se sirve por `api/` DRF.
- `apps/votaciones/` sí tiene `apps.py`; sus modelos y vistas están en inglés
  (única excepción a la convención de español).

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

**Cadena de negocio central (obligatoria; toda captura debe ligarse a ella):**

```
Proyecto → MetaProyecto → Meta (KPI) ← Indicador ← ActividadPlan ← Evento → Beneficiario
   │                                                     ↑
   └── CDP → Contrato → ContratoActividadPlan ───────────┘
```

De esa cadena se derivan las dos matrices estándar de reporte (presupuestal +
ejecución contractual). Nombres Python reales de los modelos: `Meta`→`MetaBD`
(`metas`), `MetaProyecto`→`MetaProyectoBD` (`meta_proyecto`), `Indicador`
(`presu_indicador_meta_proyecto`), `ActividadIndicador` (`actividad_indicador`),
`AvanceIndicador` (`presu_avance_ind_periodo`).

```
Evento ──▶ ActividadPlan ──▶ Proyecto ──▶ Programa ──▶ Objetivo
                          │                  ├─ Tematica
                          │                  └─ Vigencia
                          └─ Actividad
                  MetaProyectoBD (FK Proyecto + MetaBD)
                          │
                          └─ Indicador ──▶ AvanceIndicador
                                        │
                                        └─ ActividadIndicador (FK ActividadPlan)

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
Persona 1──N Participante 1──N Inscripcion  (Inscripcion.curso_id es IntegerField
                              suelto — se cortó el FK a la extinta kactivo.Curso)
Persona 1──N Participante 1──N ParticipanteEvento ──▶ Evento (login, unificado)
Persona 1──1 Funcionario ──▶ Dependencia ──▶ Subgrupo
                          └─ Cargo, TipoFuncionario
```

### 4.4 Cursos, capacitaciones y asistencia (modelo unificado en `apps.login`)

La antigua app `kactivo` (Cultura + Deporte) fue **fusionada en `apps.login` y
borrada del repo el 2026-05-27**. No hay app ni URL `kactivo`. Los cursos y
capacitaciones ya no son un tipo aparte: son `Evento` con su `TipoEvento`
(`CURSO`, etc.), y la asistencia/notas cuelgan de ahí. Solo sobrevivieron las
piezas con datos reales; el resto (17 de 20 tablas antiguas estaban a 0 filas)
se descartó.

```
Evento (login)  ── TipoEvento (CURSO / CARACTERIZACION / ENTREGA / BANCO_* / ...)
   │              funcionario_id ──▶ Funcionario  (docente titular del curso)
   │
   ├─▶ ParticipanteEvento ──▶ Participante ──▶ Persona   (inscripción + estado/cupo)
   ├─▶ Clase ──▶ HorarioClase
   │        └─▶ AsistenciaClase           (quién asistió)
   │        └─▶ dictada_por ──▶ Funcionario (suplente que dictó la sesión; NULL = titular)
   ├─▶ EvaluacionParticipante             (notas escala 0–5 SED)
   └─▶ DocumentoEvento ──▶ TipoArchivo    (soportes del evento)

Docente (login)  ──1:1──▶ Funcionario     (rol formal; gating por Evento.funcionario_id)
Grupo, Acudiente, NotaMedica              (modelos residuales en login.curso_sesiones)
```

- El panel del docente/curso vive en Angular (`/app/cursos/:id`): docente
  titular vs. suplente por sesión (`Clase.dictada_por`), inscritos con
  aceptar/rechazar (`ParticipanteEvento.estado`, respeta cupo/lista de espera) e
  insights.
- La cadena de inscripción `Persona → Participante → ParticipanteEvento` es
  atómica (`login/services/inscripcion_evento.inscribir_persona`), expuesta tanto
  al form HTML legacy como al endpoint DRF `POST /api/eventos/<id>/inscripciones/`.

### 4.5 Caracterización por sectores (N12)

App `apps/caracterizacion/` con **7 sectores implementados**. El ciudadano
diligencia por QR sin login; el wizard es **schema-driven** (el backend
introspecta el Django Form del sector y devuelve la lista de campos; el
componente Angular en `/app/p/caracterizacion/:id` los renderiza). La vista
Django `/caracterizacion/<evento_id>/` redirige al SPA.

```
Evento (login)──tipo='CARACTERIZACION'──┐
                                        │
              sector_caracterizacion ───┤
                                        │
                                        ▼
                  ┌─────────────────────────────────────────────────┐
                  │ apps/caracterizacion/sectores.py                │
                  │   SECTORES_IMPLEMENTADOS (7):                    │
                  │     cultura → caracterizacion_cultura           │
                  │     deporte → caracterizacion_deporte           │
                  │     mujer   → informacion_hogar +               │
                  │               caracterizacion_mujer (atómico)   │
                  │     salud   → caracterizacion_salud +           │
                  │               firma cifrada en Mongo            │
                  │     poblacional → caracterizacion_poblacional   │
                  │     participacion_ciudadana → ídem              │
                  │     seguridad  → caracterizacion_seguridad      │
                  └─────────────────────────────────────────────────┘
```

Persona se reutiliza vía `services/persona_lookup.obtener_o_crear_persona`
(política A: si existe el documento, no se sobrescribe el nombre).

Salud (y los documentos de Explorarte/Cultura) reusan
`apps/documentos/services/mongo_storage.guardar()` para cifrar en Mongo,
idéntico al pipeline del Banco de Iniciativas.

### 4.7 Módulos de captura específicos

Cada programa con captura propia es una app aislada que **cuelga de la cadena
presupuestal** (su `Evento` está atado a un `actividad_plan_id` → KPI → meta →
proyecto) y reusa `documentos` para las firmas:

- **`banco_iniciativas`** — Banco de Iniciativas recreodeportivas (proyecto
  2784). Cabecera `inscripcion_banco_iniciativa` + ~11 catálogos + tablas puente
  M2M + evaluación por rúbrica (`BancoRubrica`, `BancoEvaluacionInscripcion`).
- **`jovenes_a_la_e`** — Entrega de becas (convenios 773/955-2025). `EntregaBeca`
  + `EntregaBecaElemento`, catálogo `ElementoDotacion`. Al validar sincroniza
  `AvanceIndicador` (+1 al KPI).
- **`entregas`** — Entrega de insumos (`tipo_evento='ENTREGA'`). `EntregaInsumo`
  + `EntregaInsumoElemento`; el catálogo de insumos es `Implemento` (banco).
- **`festivales`** — `Festival` agrupa N eventos (Cultura 2780); días, asistencia,
  evaluación, archivos y ficha pública. Solo API DRF.
- **Motor genérico de captura** (`login.captura_generica`, tabla con `datos JSONB`
  + columnas fijas para búsqueda/dedup): permite agregar un tipo de captura nuevo
  como una entrada en `login/services/captura_schema.CAPTURA_SCHEMAS`, **sin DDL
  ni componente nuevo**. Ya lo consume Cultura (`CULTURA_ORG`, `ESTIMULO_CULTURAL`,
  `PROYECTO_CULTURAL`).

### 4.6 Votaciones

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

### 5.4 Carga de documentos y PII cifrada

- Todo blob sensible (firmas de consentimiento, soportes con datos personales)
  se cifra con **AES-256** y se persiste en **MongoDB** vía
  `apps/documentos/services/mongo_storage.guardar(plaintext, mime, owner)`.
  El `owner` (dict con tipo + id del registro SQL) identifica al dueño; solo se
  guarda el `mongo_id` en la tabla relacional.
- Lo consumen Banco de Iniciativas, Caracterización (Salud, Explorarte),
  Jóvenes a la E y Entregas. La lógica de cifrado/descifrado está en
  `apps/documentos/services/cifrado.py` (clave desde `DOCUMENTOS_AES_KEY`).
- El antiguo flujo de GridFS de `kactivo` y la app `apps/documento/` (singular)
  ya **no existen**; `apps.documentos` (plural) es el único servicio de storage.

---

## 6. Integración con servicios externos

| Servicio | Uso | Archivos clave |
|----------|-----|----------------|
| PostgreSQL (externo) | Fuente única de verdad del dominio relacional | `core/settings.py`, todas las apps |
| Redis | Cache + sesiones (backend de sesión en cache) | `core/settings.py` (`CACHES`, `SESSION_ENGINE`) |
| MongoDB 7 | Almacenamiento cifrado (AES-256) de firmas/PII | `apps/documentos/services/{cifrado,mongo_storage}.py` |
| OpenAI | Intent analyzer del dashboard AI | `apps/dashboard/services/intent_analyzer.py` |
| OneDrive | Upload de soportes (Microsoft Graph) | `ONEDRIVE_TOKEN`, `ONEDRIVE_UPLOAD_URL` en settings |
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
- **Function-based views (FBV)** en las vistas Django clásicas. La API DRF sí
  usa vistas basadas en clase (APIView). El control de acceso en las vistas HTML
  es `@login_required` + `@modulo_required(codigo)` (sistema de roles dinámico
  N15, con caché Redis versionada); el viejo `@group_required` fue **retirado**.
  Los endpoints públicos por QR usan `AllowAny` + `QrTokenPermission` (token HMAC
  `?t=`, hoy en modo suave).
- **Un archivo por subgrupo de modelos** dentro de `models/`, re-exportados
  desde `__init__.py`.
- **Templates centralizados** en `/templates/` raíz con subcarpetas por
  módulo, no por app.
- **FKs con `db_column` explícito** para alinearse con el schema existente
  (consistente en presupuesto, votaciones y las apps de captura).
- **`to_field='codigo'`** para FKs a tablas con PK de código conocido
  (catálogos: Pais, Departamento, Municipio, Localidad, UPZ, Barrio,
  Tematica, CategoriaTematica, TipoEvento).
- **Lógica de dominio en `services/`** (bien usado en dashboard, presupuesto,
  votaciones).
- **Endpoints AJAX/JSON** conviven dos estilos: los legacy con vistas FBV +
  `JsonResponse`, y los nuevos con **Django REST Framework** (paquetes `api/` de
  cada app) que son la base Angular-ready. DRF es hoy la convención para lo nuevo.

### ⚠️ Convenciones **mezcladas o inconsistentes**

- **Prefijo `public.` en `db_table`**: ya **no se usa** (deuda S5 resuelta). Las
  tablas de contrato (`Contrato`, `ContratoProyecto`, `ContratoActividad`) fueron
  corregidas a `db_table` sin prefijo; Django comillaba `"public.contrato"` y
  rompía las queries.
- **Tipo de PK**: algunas tablas usan `IntegerField` como PK manual
  (catálogos), otras `BigAutoField` (Lugar, GeoReferenciacion, Persona),
  otras `AutoField`/`BIGSERIAL`. Las tablas nuevas de captura ya nacen con
  secuencia (`BIGSERIAL`). Mezcla heredada del schema.
- **`on_delete`**: `CASCADE`, `SET_NULL`, `PROTECT`, `DO_NOTHING` usados sin
  criterio uniforme. `DO_NOTHING` dominante en presupuesto.
- **`@login_required`**: cobertura estimada ~62% (110 decoradores sobre 178
  funciones en views/). Varias vistas sensibles sin protección
  (ver [DEUDA_TECNICA.md](./DEUDA_TECNICA.md)).

### ❌ Convenciones **no aplicadas**

- No hay `manage.py test` clásico (BD externa `managed=False`): en su lugar
  existe una **suite de smoke tests** (`scripts/run_smoke_tests.py`, ~360+
  tests, corre en el hook pre-push). Cobertura mayormente GETs + contratos de
  endpoints; ver §13.
- No hay **signals** relevantes (revisado con grep sobre `@receiver`).
- No hay **Celery ni colas** — `channels` está instalado pero sin ASGI
  declarado en settings, no se usa en runtime.
- Sí hay **logger estructurado** (formato key=value en `settings.LOGGING`);
  aún queda código legacy con `print()`.

---

## 8. Notas importantes para futuros desarrolladores

1. **Nunca toques `apps/*/migrations/`**. La BD es externa, managed=False
   en todos los modelos; las migraciones no se aplican.
2. **Cambios de schema** requieren ejecutar el SQL directamente sobre la
   BD externa y luego actualizar el modelo Django para reflejarlo.
   El dueño (Alex) confirma antes de cualquier cambio.
3. **`apps/kordial` y `apps/VitalK` son scaffolds vacíos NO instalados**
   (código muerto pendiente de borrar). No dependas de ellas. La antigua
   `kactivo` y `apps/documento` (singular) ya no existen: cursos/asistencia
   viven en `apps.login` (modelo `Evento`), y el storage de PII en
   `apps.documentos`.
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
| `innova_k` | innovak-innova_k (Django 4.2 + Python 3.10) | expose 8032 (gunicorn) | healthy |
| `innova_nginx` | nginx:alpine | **8034:80** (entrada pública) | healthy |
| `innova_redis` | redis:7-alpine | (interno) — Django cache + sesiones | healthy |
| `innova_mongo` | mongo:7 | (interno) — storage cifrado firmas/PII | healthy |
| `innova_adminer` | adminer:latest | (gestionado fuera del compose principal) | up |
| `innova_mailhog` | mailhog/mailhog | (testing email) | up |

### nginx.conf — features activas
- gzip nivel 6 sobre HTML/CSS/JSON/SVG (ahorra 50-80% bandwidth)
- 5 security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, server_tokens off
- Rate limiting: zona `general` 60 req/s con burst 120, zona `login` 5 req/s con burst 10 (anti brute-force)
- Upstream con keepalive 32 + max_fails=3 / fail_timeout=30s
- Endpoint público `/healthz` (sin auth, sin log) → 200 "ok"
- Failover: si `innova_k` cae (502/503/504), nginx muestra HTML estático "Servicio temporalmente no disponible"
- Cache headers: static 30d immutable, media 7d public

### Django CACHES (Redis)
```python
CACHES["default"] = RedisCache @ redis://redis:6379/1  # KEY_PREFIX='innovak'
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
```

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
| MongoDB 7 | pymongo 4.6.3 | `MONGO_HOST`/`MONGO_PORT`/`MONGO_DB`/`DOCUMENTOS_AES_KEY` | Storage cifrado AES-256 de firmas/PII (`apps.documentos`) |
| MailHog (testing) | smtp directo | `EMAIL_HOST=mailhog`, `EMAIL_PORT=1025` | Captura de emails en dev |

---

## 12. APIs internas que exponemos

Conviven dos capas: (a) endpoints AJAX legacy con vistas FBV + `JsonResponse`
(lista parcial abajo, algunos ya retirados en la fusión kactivo), y (b) la **API
REST DRF** que consume el SPA Angular, documentada en OpenAPI 3 (`/api/schema/`,
Swagger en `/api/docs/`). La API DRF autentica con **JWT (Bearer) primero** y
SessionAuth de respaldo; los formularios públicos por QR usan `AllowAny` +
`QrTokenPermission`. La lista canónica y siempre actualizada de endpoints es el
schema OpenAPI, no esta sección.

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

---

## 13. Tests (smoke)

Primer suite de smoke tests añadido en sesión 2026-04-27 (resuelve M10).

### Estrategia

- **Sin `manage.py test`**: la BD es externa con `managed=False`; intentar crear BD test fallaría porque las tablas no se generan desde migrations Django.
- **`unittest.TestCase` puro** (no `django.test.TestCase`) — bypass del runner de Django.
- **Test Client + `force_login`** del primer superuser que exista en BD.
- **Solo GETs**: read-only, seguro contra la BD compartida de producción.
- Los tests verifican status 200 + presencia de elementos clave en HTML.

### Cobertura actual (~360+ tests, crece por sesión)

La suite arrancó con 40 tests (2026-04-27) y hoy supera los 360, repartidos en
`apps/<app>/tests/test_smoke.py` y `tests/` de cada app (dashboard, login,
presupuesto, banco_iniciativas, caracterizacion, jovenes_a_la_e, entregas,
festivales, motor de captura genérica, endpoint DRF de inscripción, etc.).
Corre en el hook **pre-push**. Para el número exacto de hoy, ejecutar el runner
(abajo). *(La distribución por módulo cambia cada sesión; ver
`scripts/run_smoke_tests.py` para la lista registrada.)*

### Cómo correr

```bash
docker exec innova_k python scripts/run_smoke_tests.py        # quiet
docker exec innova_k python scripts/run_smoke_tests.py -v     # verbose
```

Tiempo de ejecución actual: ~1 segundo. Salida: `OK` / código de salida 0 si todo pasa, 1 si alguno falla.

### Cómo agregar tests nuevos

1. Crear archivo `apps/<app>/tests/test_smoke.py` (o agregar a uno existente).
2. Patrón mínimo:
   ```python
   import unittest
   from django.test import Client
   from django.contrib.auth import get_user_model

   class MisTests(unittest.TestCase):
       @classmethod
       def setUpClass(cls):
           super().setUpClass()
           cls.user = get_user_model().objects.filter(is_superuser=True).first()
           cls.client = Client(); cls.client.force_login(cls.user)

       def test_algo(self):
           r = self.client.get("/ruta/", HTTP_HOST="localhost")
           self.assertEqual(r.status_code, 200)
   ```
3. Registrar el módulo en `scripts/run_smoke_tests.py` (lista `module_name`).

### Limitaciones conocidas

- **Sin tests de POST**: cualquier escritura contaminaría la BD compartida. Para POST usar transacciones rollback (Django TestCase con `--keepdb`) — pendiente decisión.
- **Sin CI**: ejecución manual antes de cascade. Ideal: hook de git pre-push o CI con runner Docker.
- **Coverage no medido**: agregar `coverage.py` si se quiere métrica.

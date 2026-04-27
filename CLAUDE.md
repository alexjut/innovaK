# CLAUDE.md — Memoria del proyecto innovaK

> Este archivo lo lee Claude al comenzar cada sesión. Está escrito **para
> otro Claude** (o un desarrollador nuevo), no para el humano. Sé denso,
> específico y verifica siempre contra el código actual antes de actuar.

---

## 1. Contexto

**innovaK** es el sistema de información interno de la **Alcaldía Local de
Kennedy** (Bogotá). Gestiona población atendida (`Persona` + ~26
catálogos), cursos y eventos culturales/deportivos (`kactivo`), planeación
presupuestal (`presupuesto`: proyectos → programas → indicadores) y
georreferenciación de hechos en el territorio de la localidad.

El stack es Django 4.2.11 + Python 3.10 + PostgreSQL **externa**
(`poblacion_kennedy` en `10.100.102.12:5432`, todo `managed=False`) +
Redis 7 + Nginx, todo orquestado con Docker. El dueño del proyecto es
**Alex** (git user `alexjut`, email `ingaguilarsistemas@gmail.com`).

---

## 2. Stack y arquitectura

Detalles en [`docs/ARQUITECTURA.md`](./docs/ARQUITECTURA.md). Deuda técnica
acumulada en [`docs/DEUDA_TECNICA.md`](./docs/DEUDA_TECNICA.md). Ambos
archivos son fuente de verdad mantenida; si encuentras que divergen del
código actual, prefiere el código y actualiza el doc.

Apps activas (en `INSTALLED_APPS`):

- `apps.login` — Persona, Usuario, Funcionario, Evento (nuevo), catálogos.
- `apps.kactivo` — Cultura + Deporte.
- `apps.georeferenciacion` — Lugar, Barrio, UPZ, Localidad, GeoReferenciacion.
- `apps.presupuesto` — Proyectos, programas, CDPs, indicadores.
- `apps.dashboard` — Dash/Plotly + OpenAI para consultas inteligentes.
- `apps.votaciones` — Flujo de votación con QR (independiente).

Apps **inactivas** aunque estén en el repo:

- `apps.documento` — NO está en INSTALLED_APPS. Abandonada. No la toques.
- `apps.kordial`, `apps.VitalK` — scaffolds vacíos.

---

## 3. Convenciones

### Las que **sí** respetas

- **Todo `managed=False`.** La BD es externa; ningún modelo dispara
  migraciones. Si cambias un modelo Django pero el cambio de schema no se
  aplicó en la BD, la query fallará en runtime.
- **Español en todo**: nombres de modelos, campos, URLs, vistas,
  templates. Excepción: `apps.votaciones` (Event/Candidate/Voter/Vote).
- **Function-based views.** No uses CBV. No hay DRF; las APIs son
  `JsonResponse` directas.
- **`db_column` explícito** en todas las FKs (el proyecto lo exige por
  el schema externo). Verifica al agregar una FK nueva.
- **`to_field='codigo'`** para FKs a catálogos cuya PK semántica es el
  código (País, Departamento, Municipio, Localidad, UPZ, Barrio, Tematica,
  TipoEvento).
- **Templates centralizados** en `/templates/<modulo>/`, no en
  `apps/<app>/templates/`.
- **Lógica de negocio en `services/`**, no en views.
- **`@login_required`** (y `@group_required` de `apps/login/decorators.py`)
  como mecanismo de autorización. Úsalos siempre excepto en endpoints
  explícitamente públicos.

### Las que **no** respeta el proyecto (y por qué las evitas tú)

- **`MAX(id) + 1` manual** (5 sitios conocidos). Está en el código pero es
  una deuda S5 — la solución canónica es `DEFAULT nextval()` en la BD.
  Cuando escribas un INSERT nuevo, **no copies ese patrón**; pídele a Alex
  que agregue la secuencia a la nueva tabla.
- **Prefijo `public.`** en `db_table`: solo 3 clases lo usan (contratos).
  No lo agregues a nuevas tablas.
- **Código duplicado**: `apps/login/models.py` vs `apps/login/models/`;
  varias clases con la misma `db_table` en apps distintas (`Evento`,
  `Actividad`, `Programa`, `Zona`). Si tocas uno, confirma con Alex cuál
  es el "vivo".

---

## 4. Comandos frecuentes

### Docker y Django

```bash
# Shell interactiva de Django dentro del container
docker exec -it innova_k python manage.py shell

# Correr comandos de gestión (inspectdb, etc.)
docker exec -it innova_k python manage.py <comando>

# Logs en tiempo real
docker logs -f innova_k
docker logs -f innova_nginx
docker logs -f innova_redis

# Reiniciar el servicio django
docker compose -f /home/innova/Proyectos/innovaK/docker-compose.yml restart innova_k

# Entrar al container como root (para debug puntual)
docker exec -it -u 0 innova_k bash
```

### Backups

```bash
# Backup manual (el cron ya lo corre a las 2 AM)
~/Proyectos/postgres/backup_postgres.sh

# Ver backups recientes
ls -lht ~/Proyectos/postgres/backups/ | head
```

> **Regla:** nunca ejecutes comandos destructivos sobre la BD sin haber
> verificado primero que hay un backup reciente (< 24 h).

### PostgreSQL

Solo para **lectura exploratoria**, siempre confirmando antes:

```bash
# Conexión rápida desde el host
psql -h 10.100.102.12 -U innova-bd -d poblacion_kennedy
# (password en .env)

# O vía Adminer en http://localhost:<puerto_adminer>
```

**No ejecutes SQL de escritura sin aprobación explícita de Alex.**

### Git

```bash
git status
git branch -a
git log --oneline -10
git diff
git diff --stat main..HEAD
```

---

## 5. Ramas y flujo de git

**FLUJO OFICIAL: STAGING ASCENDENTE**
feat/* → desarrollo → Pruebas → produccion

`main` NO forma parte del flujo operativo. Es rama histórica de GitHub
que quedó del arranque del proyecto y no se usa ni se actualiza.

| Rama | Propósito | Quién aprueba merge |
|------|-----------|---------------------|
| `produccion` | Lo que está corriendo en el servidor | Alex (dueño) |
| `Pruebas` | QA antes de producción | Alex |
| `desarrollo` | Integración de features listas | Alex o líder técnico |
| `feat/*` | Features en desarrollo | Self-merge permitido entre colaboradores |
| `main` | Rama histórica de GitHub. NO se usa. | - |

**Reglas:**
- NUNCA mergear directo a `produccion`, `Pruebas` o `desarrollo` sin
  pasar por las fases anteriores.
- NUNCA pushear force (`--force`, `--force-with-lease`) a ninguna rama
  compartida.
- NUNCA hacer merge a `main`. Se ignora.

**Ejemplos de trabajo:**
- Feature nueva: crear `feat/<descripcion>` desde `desarrollo` → PR a `desarrollo`
- Fix de bug: crear `fix/<descripcion>` desde `desarrollo` → PR a `desarrollo`
- Docs: crear `docs/<descripcion>` desde `desarrollo` → PR a `desarrollo`
- Hotfix urgente: crear `hotfix/<descripcion>` desde `produccion` →
  PR a `produccion` + cherry-pick a `desarrollo` y `Pruebas`

---

## 6. Archivos y carpetas **intocables**

| Ruta | Razón |
|------|-------|
| `.env` | Secrets de BD. Nunca `cat` por miedo a mostrar en logs compartidos. Nunca commitear. |
| `apps/*/migrations/` | BD externa, no se usan. Están en `.gitignore`. |
| `docker-compose.yml` | Si hace falta tocarlo, **doble confirmación**. Afecta la topología en el servidor. |
| `nginx.conf` | Idem: afecta routing en prod. Doble confirmación. |
| `~/Proyectos/postgres/` | Backups y scripts del host. Fuera del repo. No tocar. |
| BD externa directamente | Ningún DDL/DML sin confirmación explícita. |

---

## 7. Decisiones ya tomadas (contexto histórico)

Estos son hechos del proyecto, no propuestas. Respétalos:

1. **BD externa, sin migraciones Django.** Todos los modelos `managed=False`.
   Las migraciones de Django están ignoradas.
2. **Backups automáticos a las 02:00 AM** desde `~/Proyectos/postgres/backup_postgres.sh`
   (cron del host, fuera de Docker).
3. **Gunicorn en puerto 8032** detrás de Nginx en 8034. El Dockerfile
   menciona 8000 pero compose sobrescribe.
4. **Plan activo: integración geo-eventos-dashboard.** Rama
   `feat/integracion-geo-eventos-dashboard`. Ya aplicado en BD (no repetir):
   - `evento.actividad_plan_id` (bigint, FK → `actividad_plan.id`, ON DELETE SET NULL)
   - `evento.descripcion`, `evento.created_at`, `evento.updated_at` (nuevos)
   - **Borradas** de `evento`: `disciplina_id`, `grupo_id`, `curso_id`, `convocatoria_id`
   - 6 índices de performance para el dashboard (viven solo en BD, no
     declarados en `Meta.indexes` — ver deuda P4)
5. **Modelos ya actualizados** (no tocar salvo refactor explícito):
   - `apps/login/models/evento.py` nuevo con `TipoEvento` + `Evento` (14 campos).
   - `apps/login/models/__init__.py` exporta `TipoEvento` y `Evento`.
   - `GeoReferenciacion.latitud/longitud` → `DecimalField(9,6)`.
   - `GeoReferenciacion.fuente` → `CharField(max_length=10)`.
   - `GeoReferenciacion.precision` → `CharField(max_length=20)`.
   - `LugarIncidencia.geo_referenciacion` → `ForeignKey` formal.
6. **Lenguaje y zona horaria.** `LANGUAGE_CODE = 'es'`,
   `TIME_ZONE = 'America/Bogota'` (están duplicados en settings — ver deuda M7).
7. **Sin DRF.** Los endpoints AJAX son vistas normales con `JsonResponse`.
8. **Sin Celery.** `channels` está instalado pero no configurado (sin ASGI
   declarado).

---

## 8. Próximos pasos conocidos

Dentro de la rama actual `feat/integracion-geo-eventos-dashboard` quedan
tareas de código aún por ejecutar:

1. **Refactor `crear_evento`** (`apps/login/views/eventos.py`): debe
   usar los campos nuevos (`actividad_plan_id`, `lugar_incidencia_id`,
   `descripcion`, `tipo_evento_codigo`) y dejar de inventar `disciplina_id`,
   `grupo_id`, `curso_id`, `convocatoria_id` (esos FK ya no existen en BD).
2. **Endpoints en cascada** para el formulario de evento:
   - `dependencia` → `subgrupo` → `funcionario` (ya existen).
   - `proyecto` → `metas_proyecto` → `actividad_plan` (por hacer).
   - Probablemente en `apps/presupuesto/views/api.py`.
3. **Modal Leaflet para crear/seleccionar `LugarIncidencia`** desde el
   formulario de evento, consumiendo
   `apps/georeferenciacion/views/apis.py` (`api_crear_lugar` ya existe).
4. **Dashboard público** con la cadena completa (Evento →
   ActividadPlan → Proyecto → Indicador). Base en `apps/dashboard/` y
   endpoints de `dashboard/views_presupuesto.py`.

---

## 9. Quién aprueba qué

- **Cambios de schema BD** (DDL: ALTER, CREATE, DROP, índices) → **Alex**
  confirma **siempre**. Sin excepción. La BD es compartida.
- **Cambios en ramas `produccion` o `main`** → confirmación doble. Si la
  instrucción del usuario dice solo "merge", pregunta a qué rama.
- **Refactors grandes en apps críticas** (`login`, `kactivo`,
  `presupuesto`, `georeferenciacion`) → plan previo, validado antes de
  tocar código. Preferir PR pequeños.
- **`docker-compose.yml`, `nginx.conf`, `Dockerfile`, `.env`** →
  doble confirmación.
- **`git push` a origin (cualquier rama)** → pedir confirmación antes.
- **Borrar código muerto** (p. ej. `apps/documento/`, `apps/kordial/`,
  `apps/VitalK/`, `apps/login/models.py`) → requiere decisión explícita
  de Alex, aunque parezca obvio.

### Cuando Claude debe frenar y preguntar

- Antes de ejecutar: `docker exec`, `docker compose`, `psql`, `python
  manage.py` (salvo shell de lectura), `git push`, `git reset --hard`,
  `rm -rf`.
- Antes de correr scripts en `apps/georeferenciacion/scripts/` o
  `management/commands/` — pueden modificar datos.
- Antes de tocar cualquier cosa bajo `~/Proyectos/postgres/`.

### Cuando Claude puede proceder sin preguntar

- Lectura de archivos (`Read`, `Grep`, `Glob`).
- Ediciones dentro de una rama `feat/*` que no toquen `core/settings.py`,
  `.env`, `docker-compose.yml`, `Dockerfile` ni `migrations/`.
- Creación de nuevos archivos en `docs/`.
- `git status`, `git diff`, `git log` — todos los comandos de lectura.

---

## 10. Heurísticas para Claude al recibir una tarea

1. **Primero lee el código actual.** Los docs envejecen; el código manda.
2. **Antes de escribir SQL**: mira si ya existe una query similar en
   `apps/*/views/` o `services/`. El patrón del proyecto es raw SQL con
   parámetros `%s`, no ORM para inserts en tablas sin secuencia.
3. **Antes de agregar un campo a un modelo**: confirma con Alex que el
   cambio ya se aplicó en la BD (DDL). El proyecto no migra.
4. **Antes de borrar algo que parece muerto**: `grep -r` por el símbolo
   en todo el repo, incluidos templates. Varias cosas sobreviven solo por
   referencias en HTML.
5. **Si dudas, pregunta.** El costo de una pregunta es bajo; el costo de
   un borrado incorrecto o un push equivocado es alto.

---

## 11. Bitácora de sesiones

### 2026-04-20 — Auditoría, limpieza y consolidación de Git

Sesión de ~7 horas que cubrió:

**Infraestructura:**
- Git normalizado: 4 ramas operativas + flujo documentado
- Backups automáticos a las 02:00 AM (~/Proyectos/postgres/backup_postgres.sh)
- Sudoers configurado para backup sin password

**Base de datos (6 scripts DDL aplicados en poblacion_kennedy):**
- evento.actividad_plan_id (bigint, FK a actividad_plan, ON DELETE SET NULL)
- evento.descripcion, created_at, updated_at (nuevas columnas)
- Borradas: evento.disciplina_id, grupo_id, curso_id, convocatoria_id
- 6 índices de performance para dashboard

**Código:**
- Modelo Evento y TipoEvento nuevos en apps/login/models/evento.py
- Corrección de tipos en GeoReferenciacion (DecimalField 9,6, CharField 10 y 20)
- LugarIncidencia con FK formal (en vez de IntegerField)

**Documentación:**
- docs/ARQUITECTURA.md (fuente de verdad del proyecto)
- docs/DEUDA_TECNICA.md (31 hallazgos priorizados)
- CLAUDE.md (memoria operativa para Claude Code)

**Limpieza:**
- Eliminadas 3 apps abandonadas (documento, kordial, VitalK)
- Eliminado apps/login/models.py (archivo muerto)
- Eliminadas 3 carpetas/archivos vacíos misceláneos

**Balance numérico:**
- 31 archivos eliminados
- 742 líneas netas de deuda fuera
- 1130 líneas de documentación nueva
- 7 ramas intermedias consolidadas en 1 sola (chore/limpieza-codigo-muerto)

**Estado final:** feat/integracion-geo-eventos-dashboard tiene todo
consolidado, lista para seguir con refactor de crear_evento, endpoints
cascada, modal Leaflet y dashboard público.

### 2026-04-20 (final) — Hotfix propagado a producción

Fix crítico S1-S4 mergeado en cascada:
feat/ → desarrollo → Pruebas → produccion

Las 4 ramas principales sincronizadas con el mismo código (commit final
del hotfix visible en git log --oneline de cada una).

El contenedor innova_k no fue reiniciado en los merges porque ya corría
con el fix desde la Fase 1E (validación inicial). Las 4 ramas de Git
ahora reflejan el estado real del servidor.

Estado de deuda crítica: RESUELTA (0 CRÍTICOS, 4 ALTOS restantes).

Ramas eliminadas al cierre:
- fix/settings-env-loading (mergeada en todo el flujo)
- chore/limpieza-codigo-muerto (mergeada en feat/ anteriormente)

### 2026-04-20 (noche) — Análisis profundo + hallazgos críticos

Sesión final del día (después del hotfix S1-S4 propagado a las 4 ramas).

**Diagnósticos realizados:**
1. Fase 0 del refactor de crear_evento (código + template + modelos).
2. Investigación SIPSE (Sistema oficial de la Alcaldía de Bogotá).
3. Verificación del esquema real de BD (actividad_plan, meta_proyecto, etc.).

**Hallazgos importantes:**

1. **Modelo de negocio correcto** (según usuario):
   Proyecto → Meta → KPI ← Actividad → Evento (suma avance al KPI).

2. **Estructura actual de BD** es INCOMPLETA:
   - Falta tabla `presu_indicador_meta_proyecto`.
   - Falta tabla `presu_avance_ind_periodo`.
   - Falta relación actividad ↔ meta.
   - Ver `docs/HALLAZGO_BD_INCOMPLETA.md`.

3. **Requisito nuevo identificado**: Instancias (grupos de participantes).
   - Evento 1:N Instancias.
   - Ver `docs/INSTANCIAS_REQUISITO.md`.

**Documentos creados esta sesión:**
- `docs/REFACTOR_CREAR_EVENTO_ANALISIS.md` (diagnóstico técnico).
- `docs/CONTEXTO_SIPSE.md` (marco oficial).
- `docs/INSTANCIAS_REQUISITO.md` (requisito nuevo).
- `docs/MODELO_NEGOCIO_SIPSE.md` (cadena completa).
- `docs/HALLAZGO_BD_INCOMPLETA.md` (hallazgo crítico).

**Para retomar mañana (orden sugerido):**

1. Leer los 5 documentos (30 min).
2. Coordinar con Alex para verificar:
   - ¿Qué pasó con el script 006 (índices sobre tablas inexistentes)?
   - ¿Hay tablas de KPIs con otros nombres?
   - ¿Cuál es la relación correcta actividad ↔ meta?
3. Decidir alcance del refactor de crear_evento:
   - Opción mínima: solo limpiar código + agregar `actividad_plan_id`.
   - Opción completa: esperar a que BD esté lista, luego refactor integral.
4. Si se decide opción completa:
   - Escribir scripts DDL para KPIs + avances.
   - Agregar relación actividad-meta.
   - Entonces hacer el refactor alimentando avance.
5. Paralelamente planificar Instancias (reunión con Alex).

**Estado al cierre:**
- `feat/integracion-geo-eventos-dashboard`: limpia, todo commiteado, sincronizada.
- Las 4 ramas principales: con hotfix de seguridad S1-S4 aplicado.
- Contenedor `innova_k`: sirviendo producción estable.
- Working tree: limpio.

### 2026-04-23 — Refactor completo mapa-kennedy (feat/mapa-kennedy-dashboard)

Sesión larga de ~12 commits sobre `feat/mapa-kennedy-dashboard` llevando
el dashboard geográfico de prototipo decorativo a app funcional con
datos reales.

**Fase A — Endpoint de eventos** (`bbc358c`):
- `GET /geo/api/eventos/` retorna FeatureCollection GeoJSON con filtros
  (tipo_evento, fechas, dependencia_id, subgrupo_id). 10 eventos seed.

**Fase B1 — Renderizado** (`52af0fa`):
- Markers circulares coloreados por tipo (verde/azul/naranja/morado).
- Popups con nombre, fecha, dependencia, funcionario, dirección, KPI.
- Cambio tileLayer `openstreetmap.bzh` → CartoDB Voyager (vía override
  en runtime sin tocar JS core).

**Fase C1 — Limpieza** (`9d32071`):
- Removidos 8 controles decorativos (Frecuencia, Reportar Problema,
  Exportar/Refrescar flotantes, Capas duplicadas, btn-update, Tabla
  self-link, columnas Acciones/Estado de la tabla).
- IDs `actualizados-hoy`/`pendientes-verificacion` → `kpi-hoy`/`kpi-pend`.
  `setKPI` pasa a `querySelectorAll('#'+id)` para manejar duplicados.
- Leyenda hardcoded escuelas → tipos reales de evento.

**Fase C2 — Organización** (`3940118`):
- JS de B1 extraído a `apps/georeferenciacion/static/...js/mapa_kennedy_eventos.js`.
- CSS dedicado en `.../css/mapa_kennedy.css` con utility classes para
  legend-color y marker-evento.

**Fase C3 — Filtros reales** (`3f98771`):
- View pasa `tipos_evento_list`, `dependencias_list`, `subgrupos_list`
  al contexto.
- Nuevo select `f-dependencia`. Cascada Dependencia→Subgrupo client-side.
- Botones Aplicar/Limpiar conectados a `cargarEventos(qs)`.

**Fase C4.1 — Limpieza static/** (`d814f48`):
- Eliminados duplicados tracked en `static/georeferenciacion/`
  (`mapa_kennedy.js`, `mapa_kennedy copy.js`, el último era código muerto).
- `/static/georeferenciacion/` agregado a `.gitignore` (es output de
  collectstatic por el volume mount `static:/app/staticfiles`).

**Fase C4.2 — Capas a endpoints reales** (`c7d06f0`):
- Nuevo endpoint `api_kennedy_upz` sirviendo `Upz.geojson` del disco.
- JS re-apuntado: `API.barrios` → `/api/kennedy/barrios/`, `API.upz`
  → `/api/kennedy/upz/`, `API.localidadKennedy` → `/api/kennedy/contorno/`.

**Fase C4.3c/d/e — Carga BD masiva** (`447b098`, `32c71ef`, `323ddb2`):
- Scripts DDL + importers con verificaciones (reproyección 3 landmarks,
  backup pre-DROP). Ahora archivados en
  `apps/georeferenciacion/scripts/aplicados_2026-04-23/`.
- BD nueva:
  - `upz.geometry JSONB` poblado (12/12)
  - `barrio.geometry JSONB` poblado (32/111 — 79 mismatch IDECA, M22)
  - `parque` creada con 554 rows (552 Kennedy, reproyección 3857→WGS84)
  - `escuela` creada con 241 rows (Cultura 86, Deporte 155)
  - `escuelas_staging` DROPPED (backup SQL en `data/_backups/`)
- Modelos `Parque` y `Escuela` managed=False.
- Endpoints `/geo/api/kennedy/parques/` y `/escuelas/` con filtros.
- Checkboxes Parques y Escuelas en el sidebar conectados con markers
  cuadrados rosa/teal y polígonos verdes.

**Ajuste UX final** (`7f11bed`):
- Leyenda con 3 grupos visuales (Eventos ●, Escuelas ▪, Capas de
  referencia) indicando forma + color.
- Cascada UPZ→Barrio análoga a Dependencia→Subgrupo.

**Deuda abierta:**
- **M22** (nueva): 79/111 barrios sin geometry por mismatch códigos.
- **Config patológica**: `STATICFILES_DIRS` incluye `static/`, pero
  `static/` también es el mount de `STATIC_ROOT` → collectstatic copia
  a sí mismo. Hoy mitigado con `.gitignore` de `static/georeferenciacion/`,
  pero la raíz requiere tocar `docker-compose.yml` (doble confirmación).
- **`staticfiles/` del host** (207 archivos root-owned tracked): carpeta
  huérfana sin uso en runtime, remanente histórico.
- **Multiselect completo en endpoints**: `/api/eventos/` solo acepta un
  `tipo_evento`/`subgrupo_id` por query. Para soporte de listas habría
  que agregar `__in` en el endpoint.

**Estado al cierre:**
- Rama `feat/mapa-kennedy-dashboard` al día con origin (12 commits).
- BD con schema aplicado + datos cargados.
- Backup pre-C4.3 en `~/Proyectos/postgres/backups/poblacion_kennedy_pre_c4_3_20260423_102810.dump`.
- Scripts ejecutados archivados con README en `aplicados_2026-04-23/`.
- Working tree: limpio al final de la sesión.

### 2026-04-25/26 — Sesión completa: hub UX + cierre del flujo presupuestal

Sesión maratón de ~9 PRs cascadeados a producción que llevaron innovaK de
"módulos sueltos" a "flujo de gestión presupuestal completo Proyecto →
CDP/Contrato → Meta → KPI ← Actividad ← Evento → Avance".

**PR-A cierre** (`3c7a599`, hash producción `f38bfb9`):
Fix menú "Inicio" → apunta al hub `/dashboard/` (antes iba al `home.html`).

**PR-B** (`a943046`, producción `f38bfb9`):
- Card "Gestión Presupuestal" en hub.
- Grupo "Presupuesto" en sidebar (Admin+Líder): Proyectos, Programas, CDPs, Conceptos.
- Breadcrumb global: helper `apps/dashboard/services/breadcrumbs.py` con mapa
  de view_names + context processor `apps/dashboard/context_processors.py`
  + partial `templates/_partials/breadcrumb.html` + SCSS `_breadcrumb.scss`.
- Token `--accent` agregado a `.ui-card` (teal #0D9488).

**PR-C** (`85347bd`, producción `a6db7b8`):
- Hub principal reestructurado a 5-6 cards top-level por módulo:
  Presupuesto, Actividades, Territorio, Votaciones, Consulta IA, Administración.
- Sub-hubs nuevos por módulo (`/dashboard/hub/<modulo>/`).
- Renombre eventos→actividades en UI (URLs y nombres internos NO cambian):
  "Crear evento"→"Crear actividad", "Eventos"→"Actividades", "Tipos de evento"
  →"Tipos de actividad". Templates afectados: 5 en `templates/eventos/`.
- Componentes `.ui-back-link` (botón "Volver a {parent}") y `.ui-empty-state`
  (placeholders "Próximamente").
- 3 placeholders inicialmente en sub-hub Presupuesto (Metas, Indicadores, Avances)
  reemplazados por listas reales en PR-D y PR-E.

**PR-D** (`9a14b90`, producción `05ec7d6`):
- CRUD Meta (catálogo, tabla `metas` 20 filas) + MetaProyecto (asociación a
  proyecto, tabla `meta_proyecto` 39 filas).
- Login `login_view` ahora redirige a `dashboard:home` (antes `login:dashboard`
  → `home.html`). `home_view` (URL `/`) queda como redirect a `dashboard:home`.
- Limpieza: eliminados `templates/home.html` (página intermedia) y
  `templates/dashboard/index_old_pre_pra.html` (backup pre-PR-A).
- Hallazgo: tabla `metas` tiene secuencia oculta `metas_codigo_seq`
  operativa pero sin DEFAULT en columna; ORM la usa via `nextval()` explícito
  porque el modelo es `AutoField`. Fallback `MAX+1` queda como defensa.

**PR-E** (`720b5ae`, producción `1e52489`):
- CRUD Indicador (KPI, tabla `presu_indicador_meta_proyecto` 34 filas):
  vinculado a MetaProyecto, con campos nombre, descripcion, unidad_medida,
  meta_magnitud, tipo_agregacion (SUMA/ULTIMO/PROMEDIO/MAX).
- CRUD AvanceIndicador (tabla `presu_avance_ind_periodo` 62 filas) con
  origen EVENTO/MANUAL/AJUSTE. Form de avance manual fuerza origen='MANUAL'.
- Vinculación ActividadPlan ↔ Indicador (tabla `actividad_indicador` 20 filas).
- Vista detalle de KPI con barra de progreso + lista avances + actividades vinculadas.
- Cards "Indicadores", "Avances", "Vinculación Act↔KPI" en sub-hub Presupuesto.

**PR-G** (`a91c22c`, producción `1edf32e`):
- Vista 360° del Proyecto en `/presupuesto/proyectos/<id>/`:
  4 tiles (CDPs, Metas, KPIs, % avance), sección Dinero (CDPs + total),
  sección Metas (con KPIs hijos + barras de progreso color-condicional
  verde≥80/amarillo≥50/rojo<50), sección Actividades del plan.
- 1 query optimizado con `prefetch_related` anidado, ~5 queries propias.
- Botón "Ver flujo" en listado de proyectos.
- Bug colateral arreglado: `Lower` sin importar en `actividad_nueva`.

**PR-F** (`ac156d4`, producción `882a5ff`):
- Refactor `editar_evento`: form completo (nombre, descripción, fecha_inicio,
  fecha_fin, magnitud_aportada). Si la magnitud cambia, sincroniza el
  `AvanceIndicador` asociado y cambia origen a `'AJUSTE'` con observación
  auditable. NO permite cambiar indicador ni actividad_plan (destructivo).
- CRUD Dependencia (5 filas), Subgrupo (44 filas), Funcionario (18 activos)
  bajo `/org/*` (NO `/admin/*` por colisión con `django.contrib.admin`).
- Sub-hub Admin con 5 cards (después PR-H2 → 8). Sidebar Admin + 3 items.
- Hallazgo: `verbose_name_plural="Funcionarios"` copy-pasted en Dependencia,
  Subgrupo y Cargo (cosmético).

**PR-H1** (`a8a3557`, producción `3b44cb7`):
- Cache-buster en CSS/JS estáticos: context processor `static_version` lee
  mtime de `staticfiles/dist/css/base.css` y se inyecta como `?v={N}` en
  `base.css` y `menu.js`. Cada rebuild invalida cache automáticamente.
- Síntoma original: las 3 cards `--accent` (Metas/KPIs/Avances) en sub-hub
  Presupuesto se veían con `hub-card__icon` blanco en lugar del teal porque
  el browser cacheaba CSS pre-PR-B.

**PR-H2** (`235a335`, producción `8071160`):
- Modelos Django nuevos en `apps/login/models/contratos.py`:
  - `Organizacion` (59 filas, secuencia OK)
  - `Proveedor` (0 filas, **id sin secuencia → fallback MAX+1**)
  - `Beneficiario` (3580 filas, **polimórfico**: persona/proveedor/organizacion;
    el form valida cruzado y bloquea si la persona es Funcionario activo).
- CRUDs en `/org/*` con templates BEM consistentes.
- Sub-hub Admin con 8 cards (+ Organizaciones, Proveedores, Beneficiarios).

**PR-H3** (`868e758`, producción `56738eb`):
- **DDL aplicado en `poblacion_kennedy`** (con confirmación explícita de Alex):
  - `ALTER TABLE contrato ADD COLUMN fecha_inicio DATE, fecha_fin DATE, valor NUMERIC(18,4)`.
  - `CREATE TABLE contrato_actividad_plan` (id BIGINT con secuencia,
    contrato_id, actividad_plan_id, meta_proyecto_id, concepto_gasto_id,
    monto NUMERIC(18,4), fecha_inicio, fecha_fin, activo, created_at,
    updated_at; UNIQUE (contrato_id, actividad_plan_id)).
- Modelos Django: `Contrato` actualizado (3 campos PR-H3) y `ContratoActividadPlan`
  nuevo en `apps/presupuesto/models/sql.py`.
- CRUD Contrato (lista + detalle + editar) + CRUD vinculación Contrato↔ActividadPlan
  con monto/meta/rubro/fechas + soft delete.
- **Vista 360° del Proyecto ampliada**: 5to tile "Saldo presupuestal" =
  Σ CDPs - Σ comprometido. Sección "Contratos del proyecto".
- **`editar_evento`** muestra al final "Contratos que financian esta actividad"
  con número, fechas, monto, meta, rubro.
- **Bug crítico arreglado al pasar**: `Contrato.db_table = "public.contrato"`
  generaba SQL inválido (`relation "public.contrato" does not exist` porque
  Django comilla los nombres). Mismo fix en `ContratoProyecto` y
  `ContratoActividad`. Sin esto las queries fallaban silenciosamente. Esto
  resuelve la S5 que estaba documentada en deuda técnica.
- Sub-hub Presupuesto con 12 cards.

**PR-H4** (`a26c9f7`, producción `0779941`):
- Vista 360° de UNA `ActividadPlan` en `/presupuesto/actividades-plan/<id>/`:
  4 tiles (KPIs, eventos, contratos, total $), sección KPIs (con aporte de
  esta actividad vs aporte global), sección Eventos ejecutados, sección
  Contratos que financian.
- Botón "Ver detalle" agregado en `proyecto_detalle.html` y
  `actividades_por_subgrupo.html` (link directo si única, dropdown si múltiples).

**PR-I** (esta entrada): docs actualizados.

**Deuda nueva detectada esta sesión** (ver `docs/DEUDA_TECNICA.md` para
priorización completa):
- `proveedor.id` sin secuencia (S5 nueva entrada).
- `Contrato.id` sin secuencia → `contrato_nuevo` falta fallback MAX+1 (PR-mini pendiente).
- `ContratoProyecto`/`ContratoActividad` sin `id` propio en BD (mapeé contrato como PK; 1:1 efectivo en datos actuales).
- `meta_proyecto_id`/`concepto_gasto_id` en `ContratoActividadPlan` como `IntegerField` sueltos (sin FK formal).
- `Beneficiario.tipo_documento_codigo` como `IntegerField` suelto.
- Persona select sin paginación/Select2 en `FuncionarioForm` y `BeneficiarioForm`
  (carga 6938 personas).
- `verbose_name_plural` copy-paste en Dependencia/Subgrupo/Cargo.
- Hub presupuesto con 12 cards y topbar con 13 tabs (densidad).
- `Proyecto.__str__` y `ActividadPlan.__str__` no definidos.
- Tabla `metas` con secuencia oculta sin DEFAULT en columna.

**Deuda RESUELTA esta sesión:**
- S5 `db_table = "public.contrato*"` (3 modelos) → cambiado a sin prefijo. Las queries de Contrato ya funcionan.
- Bug latente: `Lower()` sin importar en `actividad_nueva` → corregido en PR-G.
- Cache permanente de CSS viejo en browser → cache-buster con mtime.

**Estado al cierre:**
- 9 PRs cascadeados a producción (PR-A→PR-H4 + PR-I docs).
- BD con DDL aplicado en sesión: 3 columnas a `contrato` + tabla `contrato_actividad_plan`.
- Backup más reciente: `~/Proyectos/postgres/backups/poblacion_kennedy_diario.dump` 2026-04-27 02:00.
- Working tree limpio al final.
- Templates legacy borrados: `home.html`, `dashboard/index_old_pre_pra.html`.
- Cadena de gestión presupuestal completa y navegable end-to-end:
  Proyecto → CDP/Contrato → Meta → KPI ← ActividadPlan ← Evento → Avance.

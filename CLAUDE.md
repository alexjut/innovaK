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

Detalles en [`docs/arquitectura/ARQUITECTURA.md`](./docs/arquitectura/ARQUITECTURA.md). Deuda técnica
acumulada en [`docs/arquitectura/DEUDA_TECNICA.md`](./docs/arquitectura/DEUDA_TECNICA.md). Plan de
evolución del frontend en [`docs/frontend/PLAN_FRONTEND.md`](./docs/frontend/PLAN_FRONTEND.md)
(camino híbrido con destino Angular condicional — léelo antes de proponer
cualquier reescritura UI). Estos archivos son fuente de verdad mantenida;
si encuentras que divergen del código actual, prefiere el código y
actualiza el doc.

**Regla de oro del frontend (PLAN_FRONTEND.md §1):** todo lo nuevo nace
*Angular-ready* — lógica separada de presentación, datos exponibles
como JSON, mentalidad de "fragmentos que se actualizan" no "páginas que
recargan". Vite y Tailwind masivo **EN PAUSA** salvo aprobación
explícita.

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
- **Prefijo `Coordinador` = poder de creación (RBAC).** Cualquier grupo cuyo
  nombre **empiece por `Coordinador`** (Coordinador, CoordinadorDeportes,
  CoordinadorEducacion…) obtiene poder de **creación** de actividades/eventos/
  contratos en su área (gate `es_coordinador`/`puede_crear_en_area` en
  `apps/login/services/permisos.py`, limitado por scope). **NUNCA nombres así a
  un rol de solo-lectura o menor privilegio** — entraría a los flujos de
  creación sin querer. Para un "coordinador que no crea", usa otro prefijo.

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
- docs/arquitectura/ARQUITECTURA.md (fuente de verdad del proyecto)
- docs/arquitectura/DEUDA_TECNICA.md (31 hallazgos priorizados)
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
   - Ver `docs/_historico/2026-04-22_hallazgo_bd_incompleta.md` (resuelto en PR-D/PR-E).

3. **Requisito nuevo identificado**: Instancias (grupos de participantes).
   - Evento 1:N Instancias.
   - Ver `docs/propuestas/instancias_eventos.md`.

**Documentos creados esta sesión:**
- `docs/_historico/2026-04-24_refactor_crear_evento_analisis.md` (diagnóstico técnico, ya ejecutado).
- `docs/referencia/SIPSE.md` (marco oficial — consolidado).
- `docs/propuestas/instancias_eventos.md` (requisito nuevo, sin ejecutar).
- `docs/_historico/2026-04-22_hallazgo_bd_incompleta.md` (hallazgo, resuelto).

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

**Deuda nueva detectada esta sesión** (ver `docs/arquitectura/DEUDA_TECNICA.md` para
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

### 2026-04-28/29 — Cierre cadena financiera + Banco de Iniciativas

Sesión de continuación que cerró la cadena financiera y arrancó el primer
módulo de captura específico (Banco de Iniciativas Recreodeportivas).

**Cadena financiera bloqueante** (commits `9ca75f0`, `22c0b5c`):
- DDL: `ALTER TABLE contrato ADD COLUMN cdp_id INTEGER REFERENCES cdp(id)`
  + index `idx_contrato_cdp`.
- Modelo `Contrato.cdp` FK (nullable, contratos legacy).
- ContratoForm + ContratoEditarForm: select de CDPs filtrado al proyecto;
  `clean()` valida `valor <= cdp.saldo_disponible`. Mensaje:
  *"Saldo insuficiente del CDP {n}: disponible $X, contrato $Y. El proyecto
  no tiene más dinero."*
- ContratoActividadPlanForm.clean(): valida `Σ vinculaciones <= contrato.valor`
  con mensaje de sobre-asignación.
- Vista 360° del proyecto reemplazada: cada CDP es card propia con
  contratos hijos + saldo + barra color-condicional (verde/amarillo/rojo).
- Detalle CDP nuevo: `/presupuesto/cdp/<id>/` con tiles + tabla contratos.
- cdp_list ampliada con columnas Comprometido y Saldo libre.
- crear_evento: agregados campos opcionales `fecha_fin` y `contrato_financia`.
  Endpoint nuevo `api_contratos_por_proyecto`. Si selecciona contrato →
  crea ContratoActividadPlan (monto=0) automático.

**Cadena financiera completa funcionando:**
```
Proyecto → CDPs → Contratos (con cdp_id) → ContratoActividadPlan → Eventos
                  ↑                          ↑
                  saldo_cdp >= 0             Σ vinculaciones <= valor
```

**Banco de Iniciativas Recreodeportivas** (commit `53bdaa4`, primer
proyecto real cargado: 2784 - Kennedy fuerza local, meta 280 colectivos):

DDL aplicado (esquema diseñado por agente `bd` con skill
`supabase-postgres-best-practices`, principio DRY: reusar al máximo lo
existente):
- 11 catálogos nuevos (122 filas total): `upl` (9 UPLs Kennedy POT 2022),
  `tipo_organizacion`, `rango_experiencia`, `escenario` (13),
  `implemento` (35 con categoría deportivo/tecnologico/logistico),
  `rango_poblacion_atendida`, `rango_etario`, `caracteristica_poblacion`
  (16), `enfoque_diferencial` (12), `tipo_beneficio_alk`,
  `disciplina_deportiva`.
- 1 tabla cabecera `inscripcion_banco_iniciativa` (~30 columnas).
- 5 tablas puente M2M con ON DELETE CASCADE.
- ALTER `organizacion` + `tipo_organizacion_codigo` SMALLINT FK +
  `redes_sociales` JSONB.
- INSERT en `nivel_educativo` codigo 9 'Curso o diplomado'.
- INSERT en `tipo_evento` codigo 'BANCO_INICIATIVAS' (vía management
  command idempotente `seed_banco_iniciativas`).

App nueva `apps/banco_iniciativas/` (no contamina presupuesto):
- 12 modelos managed=False (11 catálogos + cabecera + 5 puentes M2M)
- Form público en `/banco-iniciativas/<evento_id>/inscribir/` SIN login
  (la organización lo llena desde celular tras escanear QR del evento).
  Mobile-first, 8 secciones colapsables.
- Vistas organizador (login + group_required Admin/Lider): list paginada
  con filtros, detalle, validar/rechazar.
- crear_evento detecta tipo='BANCO_INICIATIVAS' → genera QR apuntando al
  form público (en lugar de inscripción de participantes individuales).
- 6 smoke tests nuevos (total 46/46 OK).

**Estado al cierre:**
- 35+ ítems de deuda resueltos en sesiones recientes.
- Cadena financiera bloqueante operativa (saldo_cdp + saldo_contrato).
- Módulo Banco de Iniciativas listo para recibir las 280 organizaciones
  de la meta del proyecto 2784.
- Hook pre-push activo: cada push corre 46 smoke tests.
- BD: ~140 filas nuevas en catálogos. Tabla `contrato.cdp_id` lista para
  poblar (96 contratos legacy con NULL pendientes de migración manual).

**Pendiente reconocido (no bloquea):**
- Extender modelo `Organizacion` para mapear `tipo_organizacion_codigo`
  y `redes_sociales` (hoy se actualiza vía SQL crudo en form.save()).
- Migración de 59 organizaciones legacy con `tipo='Por definir'` →
  `tipo_organizacion_codigo` correcto cuando se reinscriban.
- Migración de 96 contratos legacy con `valor=NULL` y `cdp_id=NULL`.
- Templates dinámicos por tipo de evento para futuros cuestionarios
  específicos. Por ahora cada tipo nuevo requiere tabla específica
  (patrón EventoBancoIniciativas, EventoInfoTerreno).

### 2026-04-30 — Sesión maratón: Daniel Lugo, fix Banco firma, N12 (4/6) y N15 PR-1+PR-2

Sesión muy larga con 5 entregas a producción y arranque de la
infraestructura de roles dinámicos.

**Cascadeado a `produccion`:**

1. **Daniel Lugo (CoordinadorDeportes) operativo** (`8b4ea63`):
   - Nuevo grupo `CoordinadorDeportes` + Usuario `daniel.lugo` vinculado
     a Persona 6944 (DANIEL LUGO funcionario subgrupo Deporte).
   - 4 `@group_required` del Banco extendidos a incluir el grupo nuevo.
   - Card "Banco de Iniciativas" del hub Actividades visible a Coordinador.
   - Card "Presupuesto" del hub principal ahora gated por Admin/Lider
     (antes la veían todos).
   - Vistas nuevas `/perfil/` y `/perfil/cambiar-password/` con
     `PasswordChangeForm` Django nativo + `update_session_auth_hash`.
     Topbar "Mi Perfil" antes era `href="#"`, ahora ruta real.

2. **N14 firma del Banco obligatoria + UX cámara móvil** (`ba21448`):
   - QA reveló 0/4 inscripciones reales con firma en Mongo. Causa: campo
     `firma_imagen.required = False` y sin validación cruzada con URL.
   - `clean()` exige al menos uno de los dos (imagen O url).
   - Botón grande "📸 Tomar foto de la firma" reemplaza al input nativo
     feo. Preview en vivo + botón "Quitar". Validación size <2MB JS.
   - URL externa queda colapsada con "¿No puedes tomar foto?".

3. **N12 wizards de caracterización 4/6** (`153ee59`):
   - DDL aplicado en `poblacion_kennedy` (script
     `apps/caracterizacion/scripts/001_n12_setup.sql`):
     - `evento.sector_caracterizacion VARCHAR(20)` (selector de wizard).
     - 5 secuencias BIGSERIAL para `caracterizacion_*` (cierra deuda S5).
     - DROP de los 5 `UNIQUE(persona_id)` (permite re-caracterizar).
     - ADD `evento_id` en salud/poblacional/participación + índices.
     - ADD `firma_mongo_id VARCHAR(64)` en caracterizacion_salud.
     - `caracterizacion_cultura.persona_id` → NOT NULL.
   - App nueva `apps/caracterizacion/` con 6 modelos managed=False +
     `InformacionHogar` + despachador público en `/caracterizacion/<id>/`.
   - Wizards implementados: **Cultura, Deporte, Poblacional,
     ParticipacionCiudadana**. Faltan Mujer (atómico con
     InformacionHogar) y Salud (firma cifrada Mongo).
   - Servicio `persona_lookup.obtener_o_crear_persona` con política A:
     si la persona ya existe (vía `numero_documento`), se reusa sin
     tocar nombre1/apellido1.
   - Mueve URL `/caracterizacion/<id>/` de wrapper en kactivo a la app
     nueva. Borra `apps/kactivo/{urls_caracterizacion,views/
     caracterizacion_publica}.py`.
   - Poblacional reusa catálogos `RangoEtario` y `EnfoqueDiferencial`
     del módulo banco_iniciativas (persiste `codigo`, no `nombre`).
   - Backup pre-N12: `poblacion_kennedy_pre_n12_20260430_115315.dump`.

4. **N15 PR-1+PR-2 admin de roles dinámico** (`f8428fa`):

   PR-1 — cimientos:
   - DDL aplicado (script `apps/login/scripts/001_n15_setup.sql`):
     3 tablas nuevas (`modulo`, `rol_modulo`, `rol_meta`) + rename grupo
     `lider participacion` → `LiderParticipacion` + seed `rol_meta` para
     7 grupos (Admin protegido).
   - Modelos managed=False + servicio `permisos.py` con caché Redis
     versionada (clave `permisos:schema_version` invalida todas las
     cachés con un `INCR` — patrón O(1)). TTL 600s. Bypass `is_superuser`.
   - Decorador `@modulo_required(codigo)` coexiste con `@group_required`
     legacy (PRs N15-3 a N15-5 lo migrarán endpoint por endpoint).
   - Management command `seed_modulos.py` idempotente. Catálogo inicial
     de 16 módulos. Asignación rol→módulos refleja `@group_required`
     actuales. Granularidad fina kactivo (Decisión 3b) se difiere a
     PR N15-5 cuando se migran sus 27 endpoints.
   - Escotilla `reset_modulos_admin()` para emergencias.
   - Backup pre-N15: `poblacion_kennedy_pre_n15_20260430_171530.dump`.

   PR-2 — UI gestión:
   - URLs `/org/roles/{,nuevo,<id>/,<id>/editar,<id>/toggle,
     <id>/modulos,<id>/usuarios/agregar,<id>/usuarios/<uid>/quitar/}`.
   - Templates `roles_list.html`, `rol_detalle.html`, `rol_form.html`.
   - Sidebar Admin → "Roles y permisos". Hub Admin → card "Roles y
     permisos" en primera posición.
   - Protecciones: Admin (es_protegido) no se puede desactivar, no
     puede perder módulo `roles`, no puede quedar sin último usuario.
   - Cada cambio invalida caché global al instante.

   Hotfix descubierto en QA inmediata: la tabla `usuario_grupos` (M2M
   User.groups) NO tenía `UNIQUE(usuario_id, group_id)`. `alexjut`
   tenía 3 filas duplicadas en grupo Admin → en la UI aparecía 3
   veces. Aplicado script
   `apps/login/scripts/002_n15_fix_usuario_grupos_unique.sql`:
   borra duplicados (17→15 filas) + ADD CONSTRAINT UNIQUE compuesto.
   Defensa adicional en código: `.distinct()` en filter(groups=).

5. **Decisiones de Alex consolidadas (N15)**:
   - 1a: 15 módulos (16 con caracterizacion).
   - 2a: Bypass `is_superuser=True` siempre pasa.
   - 3b: Granularidad fina kactivo (acción por acción) — diferida a PR-5.
   - 4a: Solo Admin protegido.
   - 5a: Renombrado `lider participacion` → `LiderParticipacion`.

**Estado al cierre:**

- 4 ramas (`desarrollo`, `Pruebas`, `produccion`, + `feat/n12...` y
  `feat/roles-dinamicos-pr1`) con todos los cambios.
- Container `innova_k` reiniciado 4 veces (1 por cada cascada).
- 83 smoke tests pasaron en cada push (pre-push hook activo).
- Backup más reciente útil:
  `poblacion_kennedy_pre_n15_20260430_171530.dump`.
- Ramas locales mergeadas listas para borrar:
  `fix/coordinador-deportes-banco`, `fix/banco-firma-obligatoria`,
  `docs/deuda-2026-04-30`, `feat/n12-caracterizacion-wizards`,
  `feat/roles-dinamicos-pr1`.

**Para retomar mañana (orden sugerido):**

1. **N15 PR-3**: migrar 43 endpoints simples (banco, votaciones,
   admin_org, eventos, registro, tipos_evento) a `@modulo_required` (1d).
2. **N15 PR-4**: sidebar dinámico vía context processor
   `modulos_usuario`. Resuelve el bug latente de substring match en
   `templates/base.html:117,140,235`. (1-2d)
3. **N12 PR-3**: sector Mujer (form atómico que escribe 2 tablas:
   `informacion_hogar` + `caracterizacion_mujer`). (2d)
4. **N12 PR-4**: sector Salud (con `firma_mongo_id` + reusar pipeline
   cifrado de Banco). (2d)
5. **N15 PR-5**: 27 endpoints de kactivo + expansión catálogo a
   módulos finos por acción + retiro `@group_required`. (2d)

**Catálogo de módulos sembrado en BD (`seed_modulos`):**

```
mapa_kennedy, eventos, tipos_evento,
presupuesto_proyectos, presupuesto_cdp, presupuesto_metas,
banco_iniciativas,
kactivo_cultura, kactivo_deporte, kactivo_asistencia, kactivo_consultas,
votaciones, dashboard_ia, caracterizacion,
org_admin, roles
```

**Asignación inicial CoordinadorDeportes** (Daniel):
`mapa_kennedy, eventos, banco_iniciativas, caracterizacion, dashboard_ia`.

### 2026-05-04 — Sesión maratón: cierra N15, N12, M1 parcial + 4 ítems de deuda

Sesión muy larga con **8 cascadas a producción** y cierre de tres
iniciativas grandes (sistema de roles dinámico, wizards de caracterización,
limpieza de modelos duplicados).

**Cascadeado a `produccion` (8 PRs):**

1. **N15 PR-3 — migra @group_required → @modulo_required** (`2110c0b`)
   - 119 endpoints migrados en 19 archivos: 43 originales (banco,
     votaciones, admin_org, eventos, registro, tipos_evento, roles)
     + 76 de presupuesto/dashboard que solo tenían `@login_required`
     + `roles.py` que cerraba un TODO de PR-2.
   - Módulo nuevo `personas_registro` (Admin, Lider, Coordinador) —
     una persona creada sirve para participante/beneficiario/contratista/
     funcionario, no es exclusivo de kactivo.
   - Hubs siguen con `@login_required` solo (filtran cards
     internamente — eso lo cierra PR-4).

2. **N15 PR-3.1 — separa votaciones en admin + votantes** (`d6e6b2b`)
   - Reemplaza módulo único `votaciones` por `votaciones_admin`
     (organizer eventos+artistas, dashboard, api_results) +
     `votaciones_votantes` (registro/listado de votantes).
   - `seed_modulos` ahora limpia módulos legacy automáticamente.

3. **N15 PR-3.2 — afina matriz minuciosa de roles** (`0986286`)
   - 3 ajustes: Coordinador kactivo +caracterizacion (los wizards N12
     arrancan desde el flujo kactivo), Docente +kactivo_consultas
     (consulta sus cursos), CoordinadorDeportes -votaciones_votantes
     (ya no aplica).

4. **N15 PR-4 — sidebar y hubs dinámicos por módulo** (`8e58d70`)
   - Context processor `modulos_usuario` (frozenset cacheado, bypass
     superuser) en `apps/login/context_processors.py`.
   - Refactor de `templates/base.html`: 4 bloques del sidebar ahora
     gateados por módulo individual, no por nombre de grupo.
   - Refactor de los 5 hubs en `apps/dashboard/views.py`: helper
     `_modulos_de(user)`, redirect si sin permisos, cards por módulo.
   - **3 bugs latentes resueltos**: substring match `'Lid' in
     'Admin,Lider'`, solo primer grupo (`groups.first()`), lógica
     duplicada en 4 hubs.
   - Renombre "Crear usuario" → "Crear persona".

5. **N15 PR-5 — kactivo a @modulo_required (CIERRA N15)** (`c184689`)
   - 26 endpoints kactivo migrados (último archivo del repo con
     `@group_required`). Decorador legacy completamente retirado.
   - Módulo nuevo `kactivo_participantes` (Admin, Coordinador,
     UsuarioGeneral) para los 3 endpoints públicos del flujo de
     inscripción (acudiente/resumen/cargue) que UsuarioGeneral debe
     usar pero no encajan en cultura/deporte específicos.
   - `consulta_asistencia_cultura/deporte` migrados a
     `kactivo_asistencia` (no `_cultura/_deporte`) para preservar
     acceso del rol Docente.

6. **Deuda 4 ítems — N16, N10, P4, M6** (`dbb06e5`)
   - **N16**: borrado documento Mongo huérfano `_id=69f26eb...e424`
     (firma del `inscripcion_banco_iniciativa #1` ya inexistente
     en SQL). delete_one defensivo con filtro doble.
   - **N10**: `redis>=5.0,<6` → `redis==5.3.1` pin exacto.
   - **P4**: 15 índices BD declarados en `Meta.indexes` de Evento,
     ActividadPlan, MetaProyecto, Indicador, AvanceIndicador.
     Solo declaración Django (managed=False), no DDL.
   - **M6**: `apps/login/views/eventos.py` (1077 líneas) → paquete
     `eventos/` con 5 sub-archivos por dominio (`crud`, `inscripcion`,
     `asistencia`, `info_terreno`, `_helpers`). Ningún archivo >550
     líneas. `__init__.py` re-exporta para que urls.py no cambie.

7. **M1 — elimina 9 de 11 modelos duplicados** (`39402a2`)
   - Análisis arquitectónico previo reveló **11 grupos duplicados**
     (no 3 como decía el doc).
   - Borrados de `apps/kactivo/models/`: Actividad, Programa,
     TipoEvento, Evento, Lugar, Dependencia, Subgrupo,
     CaracterizacionCultura, CaracterizacionDeporte.
   - 5 FK string refs migradas cross-app (`'Programa'` →
     `'presupuesto.Programa'`, `'Evento'` → `'login.Evento'`, etc.).
   - 8 archivos con imports actualizados.
   - Resuelve bugs latentes: `kactivo.Evento.lugar_incidencia` con
     FK rota (mismatch tabla destino), `kactivo.Caracterizacion*`
     con schema atrasado vs DDL N12, `CaracterizacionCulturaForm`
     muerto.
   - Pendiente M1.6: `zona` (login vs georeferenciacion) — requiere
     `\d zona` en BD para confirmar PK real.
   - Deuda colateral documentada: `apps/kactivo/views/cultura.py:160`
     y `deporte.py:164` con `Lugar.objects.filter(tipo='Cultura')`
     y `Disciplina.objects.filter(tipo='Cultura')` — ningún modelo
     ni la tabla tienen el campo `tipo`. Bug latente, URLs no
     navegadas, antes y ahora roto igual (sin regresión).

8. **N12 PR-3 Mujer + PR-4 Salud (CIERRA N12 6/6)** (`b965af3`)
   - **PR-3 Mujer**: wizard atómico SQL — `transaction.atomic()` que
     escribe a 2 tablas (`informacion_hogar` + `caracterizacion_mujer`).
     Política: reusa fila de hogar existente para la persona si la hay
     (actualizándola), sino crea. Form con 3 secciones (Identificación,
     Hogar 8 campos, Caracterización 3 campos). UX progresiva (JS):
     `formacion_esperada` y `menores_cargo` aparecen condicional.
   - **PR-4 Salud**: wizard con firma cifrada Mongo. Reusa pipeline
     del Banco: `mongo_storage.guardar(blob, mime, owner={"tipo":
     "caracterizacion_salud", "caracterizacion_id": <id>, "campo":
     "firma"})`. Owner del Mongo doc identifica al SQL row. La firma
     es OBLIGATORIA (consentimiento informado para datos sensibles).
     11 campos del schema + checkbox `firma_digital` + `firma_imagen`
     (cámara). Validación cruzada: `tiene_certificado_discapacidad`
     requiere `presenta_discapacidad=true`.
   - Los 6 wizards en producción: Cultura, Deporte, Mujer, Salud,
     Poblacional, Participación Ciudadana.

**Estado del catálogo de módulos al cierre:**

```
mapa_kennedy, eventos, tipos_evento,
presupuesto_proyectos, presupuesto_cdp, presupuesto_metas,
banco_iniciativas,
kactivo_cultura, kactivo_deporte, kactivo_asistencia, kactivo_consultas,
kactivo_participantes,
votaciones_admin, votaciones_votantes,
dashboard_ia, caracterizacion,
org_admin, personas_registro, roles
```

**Total: 19 módulos** (antes 16). El módulo legacy `votaciones` quedó
desactivado por el seed.

**Matriz de roles consolidada (fuente de verdad: `seed_modulos.ASIGNACION_INICIAL`):**

| Rol | # módulos | Áreas principales |
|-----|-----------|-------------------|
| Admin | 19 | Todo |
| Lider | 11 | Presupuesto, banco, votaciones, caracterización, personas |
| LiderParticipacion | 6 | Mapa, eventos, votaciones, IA, caracterización |
| Coordinador (kactivo) | 9 | Kactivo full + caracterización + personas |
| Docente | 4 | Mapa, asistencia, consultas, IA |
| CoordinadorDeportes (Daniel) | 5 | Mapa, eventos, banco, IA, caracterización |
| UsuarioGeneral | 5 | Mapa, cultura, deporte, participantes, IA |

**Bugs latentes resueltos esta jornada:**

1. Substring match en `templates/base.html` (3 sitios) — `'Lid' in
   'Admin,Lider'` daba `True`.
2. Solo primer grupo (`groups.first()`) — usuarios multi-grupo
   perdían permisos visualmente.
3. `kactivo.Evento.lugar_incidencia` con FK a tabla equivocada.
4. Modelos `kactivo.Caracterizacion*` desactualizados vs schema N12
   (faltaba `id` con secuencia, `evento_id` nullable, drop UNIQUE).
5. `CaracterizacionCulturaForm` muerto referenciando schema viejo.
6. Comentario hack `evento_id=` en `info_terreno.py` (antes
   compensaba FK cruzado de M1).

**Deuda colateral documentada (no resuelta esta sesión, scope para PR aparte):**

- `apps/kactivo/views/cultura.py:160,222` y `deporte.py:164,227`:
  filtros `Lugar.objects.filter(tipo='Cultura')` y `Disciplina.
  objects.filter(tipo='Cultura')` — ningún modelo tiene `tipo`.
  Bug dormido (URLs no navegadas).
- `LugarForm` referenciada en views pero no definida en
  `apps/kactivo/forms.py`. ImportError si se llaman las URLs.
- M1.6 Zona: requiere inspección BD.

**Estado final al cierre:**

- 4 ramas principales sincronizadas (`desarrollo`, `Pruebas`,
  `produccion` + ramas feat).
- Container `innova_k` reiniciado **8 veces** (1 por cada cascada).
- Smoke tests pasaron en cada push (83/83 al inicio, 87/87 al final
  con +4 nuevos para Mujer y Salud).
- Backup más reciente útil: `poblacion_kennedy_diario.dump` 02:00 AM.
- Working tree limpio al cierre.
- Documentación actualizada: `docs/arquitectura/DEUDA_TECNICA.md` (47 resueltos,
  6 pendientes), este `CLAUDE.md`.

**Pendiente reconocido (no urgente):**

- Crear evento real con `tipo_evento_codigo='CARACTERIZACION'` y
  `sector_caracterizacion='mujer'` o `'salud'` para probar end-to-end
  los 2 wizards nuevos. La infra cripto/persistencia ya está validada
  por el Banco en producción.
- M1.6 Zona: inspeccionar `\d zona` en BD para decidir cuál borrar.
- N3 `id BIGSERIAL UNIQUE` en `ContratoProyecto`/`ContratoActividad`
  — requiere DDL.
- C5 rename votaciones a español — riesgo medio en templates.
- N9 hub presupuesto denso — UX visible.
- Bugs colaterales kactivo: views `cultura/lugares` y `deporte/lugares`
  con `filter(tipo=...)` que no existe — posible decisión de borrar
  como código muerto.

**Para retomar mañana (orden sugerido):**

1. Coordinar con Alex creación de evento de prueba CARACTERIZACION
   sectores Mujer/Salud → smoke E2E.
2. M1.6 Zona (~30 min con `\d zona`).
3. Decidir destino de las views `kactivo:lugares` con filtro buggy
   (borrar o reparar).
4. C5 rename votaciones a español (PR aparte, mediana complejidad).
5. N9 reorganización hub presupuesto (UX, agrupación visual).

### 2026-05-21 — PR-1+PR-2 Jóvenes a la E (subgrupo Educación)

Sesión arranque del módulo nuevo `jovenes_a_la_e`. Alex pasa planilla
externa con 3 metas / 2 convenios del subgrupo Educación (id=8):

- **Proyecto A — Becas** (convenio 773-2025 ADICION):
  meta 23771 acceso (700 estudiantes posmedia) + meta 23772
  permanencia (700 estudiantes posmedia).
- **Proyecto B — Dotación a sedes** (convenio 955-2025):
  meta 23773 dotar 74 sedes con recursos pedagógicos/tecnológicos.

**Análisis previo de BD:**
- `proyecto.id=2805` "Kennedy Germinando Futuros" (codigo `0002377`,
  subgrupo_id=8 "Educación") ya existe pero **incompleto**: sólo 1 meta
  (id=8 stub) en `meta_proyecto`, 0 KPIs en `presu_indicador_meta_proyecto`,
  0 CDPs, 0 contratos, 1 actividad_plan stub.
- Faltan las 3 metas oficiales (23771/23772/23773), los KPIs, los
  contratos (773-2025 y 955-2025) y las actividades reales — todo se
  crea por UI de presupuesto, **fuera del scope del módulo**.
- Existe subgrupo "Educación" (id=8) y dependencia INVERSIÓN LOCAL (id=3).
  No hay tabla previa de becas/colegios/sedes/dotación/entregas.

**Decisión arquitectónica — Opción A** (recomendada por agente
`arquitectura` sobre las opciones B y C):

- App nueva `apps/jovenes_a_la_e/` aislada (no contamina Banco ni
  Caracterización).
- **Dos tablas cabecera separadas** (no 1 tabla con `tipo_entrega` ENUM):
  - `entrega_beca` (FK persona, cumplimiento_acceso/permanencia,
    nivel_formacion, programa_academico, firma).
  - `entrega_dotacion_sede` (FK sede, responsable acta, fecha, firma).
- Tabla nueva `sede_educativa` (NO reusar `escuela` de kactivo — son
  escuelas culturales/deportivas, no colegios formales).
- Catálogo `elemento_dotacion` con `aplica_a ENUM('persona','sede','ambos')`.
- Dos `tipo_evento` nuevos: `JOVENES_BECA` y `JOVENES_DOTACION_SEDE`,
  ambos con `requiere_actividad_plan=TRUE` (cada evento de captura
  está atado a su `actividad_plan_id` → KPI → meta → proyecto, igual
  que Banco).

**Entregado en PR-1 (rama `feat/jovenes-a-la-e`, sin push):**

- DDL script preparado en `apps/jovenes_a_la_e/scripts/001_jovenes_setup.sql`
  (sin aplicar — espera confirmación Alex y backup previo).
  Crea: 6 tablas (`sede_educativa`, `elemento_dotacion` + seed 14 filas,
  `entrega_beca`, `entrega_beca_elemento`, `entrega_dotacion_sede`,
  `entrega_dotacion_elemento`) + 2 tipos_evento + 11 índices + FKs
  blandas. PKs `BIGSERIAL` (cierra S5 día 1).
- App esqueleto: `apps.py`, `urls.py` (5 rutas con placeholders 501),
  `views/placeholders.py`, `forms/` vacía (real en PR-2/PR-3).
- 6 modelos managed=False: `SedeEducativa`, `ElementoDotacion`,
  `EntregaBeca`, `EntregaBecaElemento`, `EntregaDotacionSede`,
  `EntregaDotacionElemento`.
- Management command `seed_jovenes_a_la_e` (idempotente, refuerza
  tipos_evento y catálogo elementos).
- Registrada en `INSTALLED_APPS`, `core/urls.py` y `seed_modulos.py`.
- Módulo `jovenes_a_la_e` asignado a roles `Admin` y `Lider` (otros
  roles se agregan cuando llegue el usuario operativo, p. ej.
  `CoordinadorEducacion`).
- 6 smoke tests en `tests/test_smoke.py` (4 OK + 2 skipped que se
  activan cuando se aplique el DDL).

**Tests:** 128 totales pasan (122 OK + 6 nuevos, 2 skipped esperando DDL).

**TODO post-DDL (por confirmar con Alex):**

1. Alex aplica `001_jovenes_setup.sql` tras backup. Después corre
   `python manage.py seed_jovenes_a_la_e` para reforzar el seed.
2. Alex crea/verifica vía UI de presupuesto: 2 proyectos (o ajusta
   el 2805) + 3 metas (23771/23772/23773) + 3 KPIs + 2 contratos
   (773-2025, 955-2025) + actividades_plan + vinculación KPI↔actividad.
3. Alex crea los 2 eventos de captura (uno BECA, otro DOTACION) →
   genera QR de cada uno.
4. PR-2: form público beca (siguiendo patrón Banco) + vista detalle
   organizador.
5. PR-3: form público dotación + vistas organizador list/insights/export.
6. PR-4: card hub Actividades + sidebar + matrix de roles refinada.

**Pendiente reconocido (no bloquea PR-1):**

- Catálogo de 74 sedes target (meta 23773) — Alex debe pasar planilla
  con DANE codigos para crear `seed_sedes_jovenes`.
- Rol nuevo `CoordinadorEducacion` (análogo a `CoordinadorDeportes`
  de Daniel) — pendiente de definir cuándo llegue el usuario.
- Si el proyecto 2805 termina siendo un proyecto único (no dos), revisar
  el campo denormalizado `proyecto_codigo` en ambas cabeceras —
  hoy default '0002377' para ambos.

---

**Continuación misma jornada — PR-2 (form público real) + ajustes:**

Decisión Alex post PR-1: el flujo de **dotación a sedes** (convenio
955-2025, meta 23773) reusa el `tipo_evento='ENTREGA'` ya existente
(suministros) — NO se crea tabla `entrega_dotacion_sede` ni
`sede_educativa`. Esto **redujo el DDL** dejando solo:
- `elemento_dotacion` (5 elementos persona)
- `entrega_beca` + `entrega_beca_elemento`
- `tipo_evento JOVENES_BECA` (renombrado en UI a "Entrega de becas").

**Cambios aplicados en BD esta jornada:**

1. DDL inicial `001_jovenes_setup.sql` aplicado en `poblacion_kennedy`
   (backup `pre_jovenes_20260521_093929.dump`).
2. Hotfix `002_fix_puente_id.sql`: `ALTER TABLE entrega_beca_elemento
   ADD COLUMN id BIGSERIAL UNIQUE` — Django requiere columna `id` única
   en tablas puente con PK compuesta (mismo patrón que
   `inscripcion_banco_escenario`).
3. `UPDATE tipo_evento codigo='JOVENES_BECA' SET nombre='Entrega de becas'`
   + descripción mencionando "se alimenta de caracterización".
4. `UPDATE actividad_plan id=105` fix typo "Jóvenes a la U" → "Jóvenes a
   la E — Convenio 773-2025 (becas)".
5. `INSERT INTO evento` evento real `id=100055` "Jóvenes a la E"
   (tipo JOVENES_BECA, subgrupo Educación, actividad_plan 105).
6. Seed módulos: 20 módulos sincronizados, +1 nuevo (`jovenes_a_la_e`)
   asignado a Admin y Lider. Caché de permisos invalidada (v225).

**Código nuevo (rama `feat/jovenes-a-la-e`):**

- `apps/jovenes_a_la_e/` app completa: models managed=False
  (`ElementoDotacion`, `EntregaBeca`, `EntregaBecaElemento`),
  `forms/entrega_beca.py` (form atómico con validación cruzada),
  `views/public.py` (form público + éxito), template mobile-first
  con cámara para firma + autollenado JS desde
  `/caracterizacion/api/persona/?doc=`, smoke tests (8/8 OK).
- Fix en `_url_publica_por_tipo` (`apps/login/views/eventos/_helpers.py`):
  los tipos específicos por `codigo` se chequean ANTES de los flags
  genéricos (`permite_inscripcion`) — antes JOVENES_BECA caía al
  Banco por el fallback.
- Mejora en `apps/dashboard/views.py:hub_actividades_tipo`: agrega
  `empty_cta` cuando no hay eventos del tipo, con botón "Crear actividad"
  para usuarios con módulo `eventos`. Antes solo mostraba mensaje
  vacío sin CTA.
- Template `templates/dashboard/hub.html` renderiza el `empty_cta`.
- Template `form_publico.html` muestra errores por campo (no solo
  `non_field_errors`).

**Resumen del flujo end-to-end probado:**

```
Hub Actividades → card "Entrega de becas"
  └── Subgrupo Educación (1 actividad)
        └── Evento "Jóvenes a la E" (id=100055)
              └── QR público → /jovenes-a-la-e/100055/beca/
                    └── Form mobile (cédula → autollenado caracterización
                                     → cumplimiento acceso/permanencia
                                     → elementos M2M → firma cámara)
                          └── save atómico:
                                Persona (reusa o crea, política A)
                                Beneficiario (idempotente)
                                EntregaBeca (metas_codigos='23771,23772')
                                EntregaBecaElemento (M2M)
                          └── /jovenes-a-la-e/exitoso/<pk>/
```

**Bugs encontrados y resueltos en pruebas E2E:**

1. **Tabla puente sin `id`** → ALTER aplicado (script 002).
2. **Routing al Banco por permite_inscripcion=TRUE** → fix en
   `_url_publica_por_tipo` (orden de chequeos).
3. **Errores por campo no se renderizaban** → template ahora itera
   `form.errors` con labels claros.
4. **IntegrityError de UNIQUE doc+evento se mostraba como genérico**
   → ahora se muestra mensaje específico en `numero_documento`.

**Demos limpiados al cierre:**

- Persona ficticia "JUAN PRUEBA TEST" cédula 99887766: 1 EntregaBeca,
  2 EntregaBecaElemento, 1 Beneficiario, 1 Persona, 1 PersonaDocumento.
  Total filas borradas en pruebas E2E. BD limpia.

**Decisión Alex 2026-05-21 — Regla guardada en memoria:**

Cuando llegue un proyecto nuevo, **antes de proponer schema** debo
verificar que cada pieza se conecte hacia arriba en la cadena obligatoria:

```
Proyecto → MetaProyecto → Meta (KPI)
   ↓           ↓
   CDP → Contrato → ContratoActividadPlan → ActividadPlan
                                               ↓
                                          Evento → Beneficiarios
```

Toda matriz de reporte (presupuestal + ejecución contractual) se
deriva de esa cadena — no se agregan columnas inventadas, todo
debe estar ligado. Memoria
`feedback_matrices_estandar.md` registra el formato exacto.

**Tests al cierre:** 128/128 OK + 8/8 del módulo Jóvenes a la E OK
(sin skips). Container reiniciado y endpoints en vivo.

**Pendientes registrados en `docs/arquitectura/DEUDA_TECNICA.md`** como scope
diferido (NO deuda):

- **J1** Vista organizador (list + detalle + validar/rechazar) — 1.5 h.
- **J2** Sync con `AvanceIndicador` al validar (+1 al KPI 23771/23772) — 30 min.
- **J3** Pipeline cripto Mongo para `firma_imagen` (hoy `pending-mongo:`) — 1 h.
- **J4** Selects de UPL/Barrio en form público — 30 min.
- **J5** Insights + Matriz 1/2 export Excel — 3 h.

**Estado al cierre:**

- Rama `feat/jovenes-a-la-e` con todo stageado (sin commit aún —
  Alex aprueba cuando dé OK).
- Container `innova_k` reiniciado, sirviendo el módulo nuevo.
- `produccion`, `desarrollo`, `Pruebas`: sin cambios — la cascada
  espera la luz verde de Alex.
- Backup pre-DDL preservado en
  `~/Proyectos/postgres/backups/poblacion_kennedy_pre_jovenes_20260521_093929.dump`.
- Caracterización (6 wizards) y Banco/Deporte: validados intactos
  (suite completa 128 tests pasa).

---

**Cierre del día — PR-3 Jóvenes a la E (J1+J2+J3+J4):**

Continuación tras la cascada de PR-1+PR-2. Cerrados los 4 pendientes
operativos (queda solo J5 — insights/Excel — como nice-to-have).

**J1 — Vista organizador** (`apps/jovenes_a_la_e/views/organizador.py`):
- `/jovenes-a-la-e/entregas/` listado paginado con chips de estado
  (Todas/Enviadas/Validadas/Rechazadas) + filtros por evento_id +
  búsqueda por cédula/nombre.
- `/jovenes-a-la-e/entregas/<id>/` detalle con 5 cards (estudiante,
  cumplimiento, académicos, elementos, firma) + panel lateral con
  contexto del evento, KPIs vinculados y acciones.
- `POST .../validar/` + `POST .../rechazar/` con observación.
- Templates BEM consistentes con Banco (`entregas_list.html`,
  `entrega_detalle.html`).

**J2 — Sync AvanceIndicador**: al validar una entrega, crea una fila
en `presu_avance_ind_periodo` por cada `ActividadIndicador` vinculado
a la `actividad_plan` del evento. Magnitud = número de cumplimientos
marcados (1 si solo acceso o solo permanencia, 2 si ambos). `origen='EVENTO'`,
trazabilidad en `observaciones=entrega_beca=<id>; metas=23771,23772`.
Idempotente (no duplica si se revalida). Al rechazar una entrega
validada, los avances con ese marcador se borran (revert limpio).
Validado en pruebas E2E: la actividad_plan 105 tiene 5 KPIs → cada
entrega validada crea 5 avances correctamente.

**J3 — Cripto Mongo**: `EntregaBecaForm.save()` reusa
`apps/documentos/services/mongo_storage.guardar` (mismo pipeline del
Banco): cifra el blob, persiste a Mongo con
`owner={"tipo":"jovenes_beca","entrega_id":...,"campo":"firma"}` y
guarda el `firma_mongo_id` en EntregaBeca. Si Mongo está caído NO
rompe la entrega (log + URL queda como fallback si la había).

**J4 — Selects UPL/Barrio**: `ModelChoiceField` con `Upl` (Banco) y
`Barrio` (georeferenciacion) — antes era texto libre. Persistencia en
`upl_codigo` y `barrio_codigo` de `entrega_beca`. Template actualizado
con los dos selects.

**Tests:** 128/128 OK (8/8 del módulo, sin skips).
**Container reiniciado**, endpoints en vivo (`HTTP 302` listado tras
redirect a login, `HTTP 200` form público).

**Demos limpiados al cierre:**
- Persona "ANA GOMEZ" cédula 88776655 (1 EntregaBeca + 1 Beneficiario + 1 Persona + 1 Documento).
- 5 AvanceIndicador huérfanos creados durante prueba de validación.
- BD verificada: `EntregaBeca total = 0`, sin docs demo restantes.

**Pendiente registrado en `docs/arquitectura/DEUDA_TECNICA.md`:**
- **J5** Insights Chart.js + descarga Excel (Matriz 1 presupuestal +
  Matriz 2 ejecución contractual) — patrón Banco. 3h. Sin urgencia.

**Estado al cierre:**
- Rama `feat/jovenes-a-la-e` con código nuevo stageado (sin commit aún).
- Las 4 ramas principales en commit `f9f3b96` del cierre anterior
  (PR-1+PR-2). Sin push al remoto (gh no autenticado en shell de Claude).
- Container `innova_k` sirviendo el módulo nuevo con organizador
  funcional.

### 2026-05-27 — Fusión kactivo→Evento (PR-2..5) cascadeada a producción

Sesión continuación de la Etapa B Plan Frontend. Cerrada la app paralela
`apps/kactivo/` por completo. Todo el flujo de cursos/capacitaciones
vive ahora bajo el modelo unificado `Evento` (de `apps/login`).

**Decisión disparadora de Alex:** "kactivo o eso de curso o capacitación
es para todos y en el mismo vía de kactivo todo cuando se cree esa
actividad debe ser una combinación de kactivo y lo que hay de evento
curso y capacitación". Fusión COMPLETA, sin coexistencia (nadie usa el
flujo legacy de kactivo hoy).

**PR-1 — Auditoría** (`docs/propuestas/fusion_kactivo_evento.md`):
Reporte del agente `arquitectura`. Hallazgo clave: kactivo es
mayoritariamente código zombi (17 de 20 tablas a 0 filas; views con
campos inexistentes `Lugar.tipo`, `Disciplina.tipo`, `Docente.area_encargada`).
Solo 3 piezas vivas: `tipo_archivo` (1 fila), `documento_evento` (2),
`participante_evento` (2.545). 8 decisiones consolidadas para Alex.

**PR-2 — Modelos vivos a apps.login** (`fe7ad40` parte 1):
- `TipoArchivo`, `DocumentoEvento` → `apps/login/models/documentos_evento.py`
- `ParticipanteEvento` → `apps/login/models/inscripcion_evento.py`
- FK `'kactivo.Curso'` en `Inscripcion` → `IntegerField(null=True)`
  (decisión #3 Opción B — corta acoplamiento)
- Imports actualizados en `apps/login/views/eventos/info_terreno.py:53,88`
- Admins relevantes (`Evento`, `TipoEvento`, `Participante`,
  `TipoArchivo`, `DocumentoEvento`) movidos a `apps/login/admin.py`
- Modelos duplicados de kactivo (`TipoArchivo`, `DocumentoEvento`,
  `DocumentoParticipante`, `ParticipanteEvento`) borrados para evitar
  reverse-accessor clash
- 12 tests nuevos en `apps/login/tests/test_fusion_kactivo.py`

**PR-3 — Service + endpoint DRF Angular-ready** (`fe7ad40` parte 2):
- `apps/login/services/inscripcion_evento.py::inscribir_persona()` —
  extrae la cadena atómica Persona→Participante→ParticipanteEvento
  del raw SQL inline de la view HTML. Whitelist defensiva de columnas,
  FK opcional según `has_column`.
- `apps/login/api/serializers.py::InscripcionPublicaSerializer` +
  `InscripcionResultadoSerializer`.
- `apps/login/api/views.py::InscripcionEventoCreateView` con
  `permission_classes = [AllowAny]` (decisión #6 Opción A —
  hardening HMAC del QR queda para PR aparte).
- URL `POST /api/eventos/<int:evento_id>/inscripciones/`.
- View HTML legacy refactorizada para llamar al mismo service (-85 LOC).
- 8 tests nuevos en `apps/login/tests/test_api_inscripcion.py`
  (gating, validación serializer, contrato del service).

**PR-4 — Limpieza zombi + reorg módulos** (`fe7ad40` parte 3):
- Borrados: 9 views (`asistencia`, `consulta_*`, `cultura*`, `deporte`,
  `formulario_participante`, `index`, `ping_db`), 6 archivos
  (`forms.py`, `services/{mongo_upload,onedrive_upload,botones}.py`,
  `templatetags/`), paquete `sub_grupo_cultura/` completo, 30 templates
  (`templates/cursos/*` + `templates/kactivo/*` + duplicados).
- Endpoint `cursos_por_area` + import `kactivo.Curso` fuera de
  `apps/login/views/api.py` + URL en `apps/login/urls.py:61`.
- Decisión #8: flujo zombi `inscribir_participante` en
  `apps/login/views/registro.py` borrado junto con `InscripcionForm`
  (`apps/login/forms.py`), `InscripcionAdmin` (`apps/login/admin.py`)
  y template `templates/login/inscribir_participante.html`.
- `seed_modulos`: 5× `kactivo_*` (cultura, deporte, asistencia,
  consultas, participantes) colapsados en 2 nuevos (decisión #5
  Opción A):
  - `cursos`: cursos/capacitaciones (cultura, deporte, formación)
  - `eventos_asistencia`: asistencia a cualquier actividad
  La limpieza legacy del comando desactivó los 5 módulos antiguos y
  borró sus 15 `RolModulo`. Caché de permisos invalidada (v277).
- `apps/dashboard/views.py` (4 sitios): `KACTIVO = {kactivo_*}` →
  `CURSOS = {"cursos", "eventos_asistencia"}`.
- Link hardcoded `templates/login/formulario/index.html:69` →
  `{% url 'dashboard:hub_actividades_tipo' 'CURSO' %}`.
- `templates/eventos/insights.html:162` copy "Inversión Local,
  kactivo, etc." → "Inversión Local, Educación, etc.".
- `core/urls.py:27`: quitado `include('apps.kactivo.urls')`.

**PR-5 — Apagado total de apps.kactivo** (`fe7ad40` parte 4):
- `'apps.kactivo'` fuera de `INSTALLED_APPS` (`core/settings.py:65`).
- Icon mapping `kactivo` retirado del `JAZZMIN_SETTINGS`
  (`core/settings.py:329,338`).
- Carpeta `apps/kactivo/` borrada por completo (admin.py, apps.py,
  models/, migrations/, urls.py, __init__.py, tests.py).

**Matriz de roles consolidada (PR-4 + cascada):**

| Rol | Antes (kactivo_*) | Después |
|-----|-------------------|---------|
| Admin | 5 módulos kactivo_* | `cursos`, `eventos_asistencia` |
| Coordinador | 5 módulos kactivo_* | `cursos`, `eventos_asistencia` |
| Docente | `kactivo_asistencia` + `kactivo_consultas` | `cursos`, `eventos_asistencia` |
| UsuarioGeneral | `kactivo_cultura` + `_deporte` + `_participantes` | `cursos` |

**Cadena Angular-ready operativa:**

```
Cliente Angular  →  POST /api/eventos/<id>/inscripciones/  (AllowAny, JSON)
QR móvil HTML    →  POST /evento/inscripcion/<id>/          (legacy form, login_required)
                              ↓
       apps.login.services.inscripcion_evento.inscribir_persona()
                              ↓
       Persona → Participante → ParticipanteEvento (atómico, raw SQL + secuencias BD)
```

**Tests al cierre:** 222/222 OK + 8 skipped esperados (4 pushes con
pre-push hook, cada uno corrió la suite). 20 tests nuevos en esta
sesión (12 de fusión + 8 de endpoint DRF).

**BD intacta:** `tipo_archivo: 1`, `documento_evento: 2`,
`participante_evento: 2545` filas preservadas. Cero DDL ejecutado en
la fusión (solo el seed_modulos que escribe en `modulo`/`rol_modulo`
— idempotente y reversible re-corriéndolo).

**Balance final:** 119 LOC añadidos · 5026 LOC eliminados · **net
-4.907 LOC de código zombi fuera del repo**. **9 apps innovaK** activas
(antes 10).

**Cascada completa a producción:**
- `feat/fusion-kactivo-pr2` → `4eba409` (`desarrollo`) → `3351312`
  (`Pruebas`) → `786f8db` (`produccion`).
- Container `innova_k` reiniciado una vez al final.
- Verificación post-restart: `manage.py check` limpio, `HTTP 302` en
  `/` (redirect a login), `HTTP 200` en `/login/`.

**Pendiente reconocido (no urgente):**
- Smoke E2E manual desde navegador: inscripción real vía endpoint DRF
  + hub Actividades por cada rol (Coordinador, Docente, UsuarioGeneral)
  para verificar que el colapso de módulos no rompió accesos.
- Hardening del endpoint público: HMAC del QR en lugar de `AllowAny`
  puro (decisión #6 — ticket aparte).
- Borrado físico de las 17 tablas BD vacías (`acudiente`, `curso`,
  `disciplina`, `grupo`, `clase`, etc.): PR DDL dedicado con backup,
  no bloqueante.
- Idempotencia por documento+evento en `inscribir_persona`: el flujo
  actual crea Persona nueva cada vez. Cambiar comportamiento es PR
  aparte si Alex lo decide.

**Decisiones tomadas consolidadas** (en `docs/propuestas/fusion_kactivo_evento.md §7`):

| # | Decisión | Elección |
|---|---|---|
| 1 | Fusión total vs. coexistencia | Total |
| 2 | Nombre Python para `participante_evento` | Conservar `ParticipanteEvento` |
| 3 | FK `'kactivo.Curso'` | Opción B: `IntegerField(null=True)` |
| 4 | `DocumentoRequisito` (3 filas seed) | Modelo borrado, tabla queda |
| 5 | Colapso de módulos | Opción A: `cursos` + `eventos_asistencia` |
| 6 | Auth endpoint DRF público | `AllowAny` + hardening después |
| 7 | Borrar tablas vacías post-fusión | NO en esta serie |
| 8 | `inscribir_participante` zombi de `registro.py` | Borrado |

### 2026-06-04 — Etapa D: forms públicos QR → Angular + módulo Entrega de insumos (cascada a producción)

Sesión que migró los **formularios públicos de QR** (que llena el ciudadano
sin login) a Angular nativo bajo `/app/p/*`, y creó el módulo nuevo de
**Entrega de insumos**. Decisión Alex: **"B — todo va para Angular"**, incluidos
los públicos. Constraint permanente reafirmado: **lo público sigue público**
(mapa + forms son AllowAny + rutas fuera del authGuard; el ciudadano los usa
sin login). Cascadeada a las 4 ramas y pusheada a GitHub.

**Patrón establecido para cada form público** (replicable):
1. Endpoint DRF `AllowAny` (catálogos GET + crear POST, multipart si hay firma).
2. Ruta Angular en `frontend/src/app/features/publico/publico.routes.ts` (sin guard).
3. `_url_publica_por_tipo` (`apps/login/views/eventos/_helpers.py`) apunta el QR a `/app/p/*`.
4. La vista Django vieja **redirige** a la Angular (enlaces/bookmarks/QR viejos no rompen).

**Migrado a Angular (públicos, `/app/p/*`):**
- **Banco** → `/app/p/banco/:id` (endpoints `apps/banco_iniciativas/api/public.py`).
- **Caracterización (6 sectores)** → `/app/p/caracterizacion/:id`. UN wizard
  dinámico **schema-driven**: el backend (`apps/caracterizacion/api/`) introspecta
  el Django Form del sector y devuelve `fields:[{name,label,type,options,...}]`;
  el componente Angular lo renderiza por `@switch(field.type)`. Salud usa
  multipart (firma cámara). Dispatcher `caracterizacion_publica` redirige.
- **Jóvenes beca** → `/app/p/jovenes/:id` (`apps/jovenes_a_la_e/api/public.py`).
  Autollenado por cédula vía `/caracterizacion/api/persona/?doc=`.
- **QR del evento** → `/app/eventos/:id/qr` (Angular print-friendly).
  `EventoQRView` GET `/api/eventos/<id>/qr/`. La vista `qr_evento` redirige.

**Módulo NUEVO — Entrega de insumos** (`apps/entregas/`, tipo_evento ENTREGA):
- Resolvía un hueco real: los 21 eventos ENTREGA no capturaban beneficiarios
  (no había forma de registrar a quién se le entregó qué insumo).
- **DDL aplicado** en `poblacion_kennedy` (backup diario 02:00 < 24h):
  `apps/entregas/scripts/001_entregas_setup.sql` — `entrega_insumo` (cabecera,
  espejo de `entrega_beca`) + `entrega_insumo_elemento` (puente con `cantidad`).
  PKs BIGSERIAL. Catálogo de insumos = `implemento` (35 filas).
  Nota: el `dbshell` del contenedor NO tiene `psql`; el DDL se aplicó vía
  `connection.cursor().execute(open(script).read())`.
- Decisión Alex: captura = **form público QR** (como Jóvenes), datos = **insumo + cantidad**.
- Form público `/app/p/entrega/:id` (selector insumo+cantidad con stepper, firma).
  Endpoints `apps/entregas/api/public.py` (AllowAny). FormData manda
  `implementos[]` + `cantidades[]` como listas paralelas (el form las empareja
  por índice en `clean()`).
- Panel organizador Angular `/app/entregas` (list + detalle con tabla de insumos
  y cantidades + firma + validar/rechazar). Al validar sincroniza `AvanceIndicador`
  (+1 al KPI de la actividad_plan, origen EVENTO, idempotente) como Jóvenes J2.
- Módulo `entregas` en `seed_modulos` → Admin + Lider.
- Cadena Persona→Beneficiario→EntregaInsumo→elementos **probada E2E** (insumo
  1×2 + 5×3) y datos de prueba **limpiados** (BD verificada en 0).

**Fix importante** (`actividades-eventos.component.ts`): los botones
Beneficiarios/Formulario/QR se gateaban solo por `permite_inscripcion` /
`permite_caracterizacion`; ENTREGA no tiene esos flags → quedaba solo "Editar"
(por eso "no se veían los beneficiarios"). Se agregó `esEntrega()`
(`codigo==='ENTREGA'`). **Cualquier tipo_evento nuevo sin esos flags necesita
el mismo trato.**

**Tests:** 329 OK (9 skipped). Ajustados por cambios de esta sesión:
- 3 de georeferenciación: `403 → (401|403)`. El fix de auth **JWT-first** en
  `core/settings.py` (hecho antes para resolver el 403 en POSTs del SPA) hace
  que DRF devuelva **401** sin credenciales (correcto), no 403.
- 1 de Jóvenes: `(200|410) → 302`, porque la vista vieja ahora redirige a la SPA.

**Doc:** `docs/frontend/MIGRACION_HTML_ANGULAR.md` corregido — estaba desactualizado
(marcaba los públicos como "NO migrar"); ahora refleja la decisión B.

**Cascada a producción (push a GitHub OK, hook corrió 329 tests):**
- `feat/etapa-d-pr5-1-spa-served-from-django` `a583441`
- `desarrollo` `ce6eecb` · `Pruebas` `0e8c4fa` · `produccion` `dc88c06`
- Contenedor `innova_k` sirviendo: `/` 302, `/app/` 200, catálogos entrega 200.
- `frontend/dist` está **gitignored** — el build de la SPA lo genera el server
  al desplegar (no se commitea). Recordatorio de deploy: correr
  `cd frontend && npm run build -- --base-href=/app/` en el server tras pull.

**PARA MAÑANA (orden sugerido):**
1. **Forms públicos que faltan** (mismo patrón: ruta `/app/p/*` + endpoint
   AllowAny + Django redirige):
   - Inscripción genérica de evento (`/evento/inscripcion/<id>/`).
   - Info-terreno (`/evento/info-terreno/confirmar/<id>/`, GPS + fotos).
   - Evaluar scan de voto (`votaciones/scan/`) — ¿migrar o dejar?
2. **Crear un evento ENTREGA con `fecha_fin` futura** para smoke E2E del form
   público abierto (los de demo están cerrados → muestran pantalla "cerrada").
3. **Organizador que falta** (de `docs/frontend/MIGRACION_HTML_ANGULAR.md`, ❌):
   - Presupuesto: asignar/quitar CDP↔proyecto · gestión actividad-plan
     (nueva/renombrar/eliminar/migrar/detalle) · editar/desactivar vinculación
     contrato↔actividad · detalle de programa · eliminar concepto.
   - Exports: Banco CSV · Jóvenes Excel · Beneficiarios CSV/Excel · Curso
     Excel/PDF · Asistencia PDF.
   - Form de editar tipo de evento · gestión de usuarios del rol.
4. **Zombi a borrar** (tras confirmar que todo está en Angular):
   `templates/login/formulario/*` · `dashboard/placeholder/*` ·
   `presupuesto/ping/` · `mapa_kennedy_standalone copy.html`.

**Estado al cierre:**
- 4 ramas sincronizadas y pusheadas. Working tree limpio (commit `a583441`).
- BD: 2 tablas nuevas (`entrega_insumo`, `entrega_insumo_elemento`) sin datos.
- Backup útil: `poblacion_kennedy_diario.dump` 2026-06-04 02:00.

### 2026-06-09 — Cierre migración Angular: públicos + organizador presupuesto + exports + zombis (cascada a producción)

Sesión que **cierra la migración HTML→Angular del organizador** y los
formularios públicos restantes. 1 commit cascadeado a las 4 ramas.

**Públicos QR → Angular** (`/app/p/*`, AllowAny, Django redirige):
- **Inscripción genérica** → `/app/p/inscripcion/:id`. POST ya existía
  (`InscripcionEventoCreateView`); nuevo GET catálogos
  `apps/login/api/public_inscripcion.py`. `_url_publica_por_tipo` default+None
  → Angular. Vista `inscribir_participante` redirige.
- **Info-terreno** (GPS+fotos) → `/app/p/info-terreno/:id`. Nuevos endpoints
  `apps/login/api/public_info_terreno.py` (`InfoTerrenoPublicView` GET ctx +
  POST multipart). Las vistas Django viejas estaban **rotas** (usaban
  messages/transaction/timezone sin importar) → ahora redirigen.
- **Decisión**: `votaciones/scan/` SE QUEDA en Django (kiosko de voto
  autocontenido, flujo sensible, fuera del SPA). **No quedan públicos pendientes.**

**Organizador presupuesto** (5 endpoints DRF nuevos en `api/views.py` + UI):
- Asignar/quitar CDP↔proyecto (picker `cdps/sin-proyecto/` + PATCH proyecto_id).
- Actividad-plan: renombrar (PATCH) / eliminar (DELETE con guard de uso) /
  detalle expandible (`actividades-plan/<id>/` GET con KPIs+eventos+contratos).
- Vinculación contrato↔actividad: editar monto (PATCH) / desactivar (DELETE soft).
- Detalle de programa (`programas/<id>/` GET con resumen + proyectos).
- Eliminar concepto (DELETE, captura ProtectedError → 400).
- Fix drift: tabla vinculaciones leía `v.actividad_descripcion` (clave
  inexistente) → `v.actividad_plan_descripcion`.

**Quick wins**:
- Editar tipo de evento: form inline en `/eventos/tipos` (PATCH ya existía).
- Gestión usuarios del rol: `AdminRolUsuariosView` (POST/DELETE) +
  `AdminUsuariosSearchView`. OJO: usar `get_user_model()`, NO
  `django.contrib.auth.models.User` (swappeado a `login.Usuario`). UI
  buscar/agregar/quitar con protección rol Admin (último usuario).

**Exports** (botones Angular → endpoints Django con sesión de `MeView`,
same-origin; NO se reimplementó lógica): Banco CSV, Jóvenes Excel,
Beneficiarios CSV/Excel, Curso Excel/PDF, Asistencia PDF. Los 7 endpoints
verificados 200 con content-type correcto.

**Limpieza zombi** (cadena completa borrada tras verificar 0 features/enlaces):
- `templates/login/formulario/*` (scaffold demo, datos hardcodeados) + 4 URLs
  + item sidebar `base.html` + breadcrumb.
- `dashboard/placeholder.html` (reemplazado en PR-D/E) + 3 URLs + vista + breadcrumbs.
- `presupuesto/ping/` (healthcheck) + URL + vista.
- `mapa_kennedy_standalone copy.html` (duplicado).

**Estado migración**: organizador 100% en Angular. Único pendiente NO
bloqueante: `actividades/por-subgrupo/` (vista agregada) y `actividades/migrar/`
(bulk catálogo). Ver `docs/frontend/MIGRACION_HTML_ANGULAR.md`.

**Estado al cierre**:
- 4 ramas sincronizadas y pusheadas (feat `572c97d`, produccion `81c053c`).
- 329/329 tests OK (9 skipped) en cada push (hook pre-push).
- Container `innova_k` reiniciado, sirviendo en vivo: `/app/` 200,
  `/app/p/inscripcion/:id` 200, zombis `/formulario/` y `/presupuesto/ping/` 404.
- Cero DDL esta sesión. `frontend/dist` regenerado (gitignored; rebuild en server al deploy).

### 2026-06-09 (tarde) — Motor genérico de captura + Cultura 2780/2788 + Explorarte

Sesión de la tarde que construyó el **motor genérico de captura manejado por
`tipo_evento`** (Opción A — JSONB, aprobado por Alex "a de una") con Cultura
como primer consumidor, y dejó la cadena presupuestal 2780/2788 completa en BD.

**Motor genérico de captura (reusable por cualquier subgrupo):**
- Tabla nueva `captura_generica` (BIGSERIAL, `datos JSONB` + columnas fijas
  para búsqueda/matrices/dedup: documento, nombre_legal, firma, estado;
  índice GIN sobre datos). Script `scripts/ddl_captura_generica_2026_06_09.py`.
- `apps/login/services/captura_schema.py` — `CAPTURA_SCHEMAS` data-driven:
  agregar un tipo de captura nuevo = una entrada en el dict; SIN DDL ni
  componente nuevo. Types: text, textarea, number, money, select, checkbox.
  `map_to` promueve campos a columnas fijas; `catalogo` para selects dinámicos
  (upls, barrios).
- Endpoints públicos `apps/login/api/public_captura.py` (GET schema + POST
  submit, AllowAny) y organizador `apps/login/api/captura_organizador.py`
  (list/detalle/validar-rechazar/insights, módulo eventos).
- Angular: form público `/app/p/captura/:eventoId` (sin guard, QR ciudadano,
  renderiza por `@switch(field.type)` como caracterización) + panel
  organizador `/app/captura` (list + insights).
- `_url_publica_por_tipo`: si `schema_de(tipo.codigo)` existe → QR apunta a
  `/app/p/captura/<id>` (chequeo ANTES de los flags genéricos).

**Cultura 2780/2788 (cadena completa en BD, scripts en `scripts/`):**
- Proyectos con nombres reales: 2780 "KENNEDY PROYECTA TALENTO" + 2788
  "KENNEDY IMPULSO CREATIVO" (creado).
- 5 metas generales del cuatrienio en `metas` (Capacitar 4000 EXPLORARTE /
  Beneficiar 60 org / Otorgar 140 estímulos MÁS CULTURA LOCAL / Financiar
  proyectos / Realizar eventos OPERADOR LOGÍSTICO) + KPIs con **aporte de
  vigencia** separado (1000/15/38/35/60) — regla general vs. aporte respetada.
- 3 tipo_evento nuevos: `CULTURA_ORG`, `ESTIMULO_CULTURAL`, `PROYECTO_CULTURAL`
  (requiere_actividad_plan=TRUE).
- 4 eventos de captura 2026: Explorarte (69, CURSO), Beneficio a
  organizaciones (70), Estímulos (71), Proyectos financiados (72).

**Explorarte — caracterización completa según Anexo:**
- DDL aditivo a `caracterizacion_cultura`: `fecha_nacimiento`, 5 campos de
  acudiente (menores de edad), 3 punteros Mongo (`doc_identidad_mongo_id`,
  `doc_acudiente_mongo_id`, `autorizacion_mongo_id`).
- `CulturaForm` ampliado: validación cruzada menor→acudiente obligatorio +
  3 FileFields; `guardar_cultura` cifra los documentos a Mongo (pipeline
  `mongo_storage.guardar`, owner tipo `caracterizacion_cultura`).
- `tipo_evento CURSO` → `permite_caracterizacion=TRUE`; evento 69 con
  `sector_caracterizacion='cultura'` → QR cae en `/app/p/caracterizacion/69`.

**Tests:** +21 nuevos en `apps/login/tests/test_captura_generica.py`
(schema service, contrato público, gating organizador, routing QR).
Suite 350/350 OK (11 skipped). Módulo registrado en
`scripts/run_smoke_tests.py`.

**Estado al cierre:**
- Cascadeado a las 4 ramas y pusheado. Container sirviendo en vivo
  (`/app/p/captura/70` 200, schema JSON OK, build SPA al día).
- BD: `captura_generica` en 0 filas (sin E2E aún). Queda 1 evento demo por
  confirmar borrado.
- **Pendiente próximo día:** smoke E2E manual de los 3 forms de captura
  (70/71/72) + caracterización Explorarte con menor de edad (acudiente +
  docs Mongo); confirmar sync de avance al KPI al validar capturas.

### 2026-06-11 — Smoke E2E motor captura + Explorarte + cierre migración organizador 100%

**Smoke E2E motor de captura (eventos 70/71/72) — todo OK:**
- GET schema público 200 ×3; POST 201 ×3 (CULTURA_ORG, ESTIMULO_CULTURAL,
  PROYECTO_CULTURAL); obligatorios faltantes → 400 por campo; firma
  ciudadano cifrada a Mongo OK.
- Organizador: validar crea 1 `AvanceIndicador` por captura en KPIs
  12/13/14, revalidar idempotente (kpi_aportes=0), **rechazar revierte**
  el avance. Insights data-driven y detalle OK.
- Caracterización Explorarte (evento 69) con MENOR: sin acudiente → 400
  con 8 errores; completo → 201 con acudiente persistido y los 3 docs
  (identidad menor, doc acudiente, autorización) cifrados en Mongo y
  verificados descifrables. Cadena Persona→Beneficiario creada.
- Datos de prueba limpiados y verificados en 0 (SQL + Mongo). Cero DDL.

**Aclaraciones de Alex consolidadas:**
- La tabla de metas 2780/2788 que pasó era ACLARATORIA — la BD queda
  como está (KPI 13 = 38 estímulos, KPI 15 = 60 eventos NO se tocan).
- **Evento 62 "Banco — Prueba Piloto" NO es demo**: es el evento real del
  Banco de Deportes (24 inscripciones del piloto 2026-05-09). Solo se
  borra/depura cuando el área de Deportes lo pida. (Memoria guardada.)

**J5 Jóvenes: descubierto ya hecho desde 2026-06-09** (insights API +
panel Angular Chart.js + Excel 4 hojas con Matriz 1/Matriz 2). Verificado
en vivo (200, xlsx válido). Matrices vacías hasta que exista un evento
JOVENES_BECA real (el 100055 fue borrado). Marcado cerrado en deuda.

**Migración organizador CERRADA al 100%** (commit `33dbdad`, cascadeado):
- `GET /presupuesto/api/actividades/por-subgrupo/` — agregado SIPSE por
  subgrupo, 6 filtros en cascada + catálogos en una sola petición.
- `POST /presupuesto/api/actividades/migrar/` — bulk texto libre →
  catálogo (espejo DRF de `actividad_migrar_desde_texto`).
- Angular `/app/presupuesto/actividades`: tiles (% en catálogo), filtros
  en cascada, tablas por subgrupo (badge catálogo/texto), detalle inline
  por plan (KPIs/eventos/contratos, link a proyecto 360°), botón
  "Migrar a catálogo". Card nueva en hub Presupuesto.
- Vista Django `actividades_por_subgrupo` redirige a la SPA (body legacy
  preservado como `_actividades_por_subgrupo_legacy`, candidato a borrar
  con su template en una limpieza futura).
- 6 smoke tests nuevos → suite 356/356 OK (11 skipped).

**Estado al cierre:**
- 4 ramas sincronizadas y pusheadas (produccion `55a6c99`). Hook corrió
  356 tests en cada push. Container reiniciado 1 vez, sirviendo
  `/app/presupuesto/actividades` 200.
- `docs/frontend/MIGRACION_HTML_ANGULAR.md`: migración HTML→Angular 100% completa.
- Deuda activa: 0. Pendientes que requieren decisión/insumo de Alex:
  HMAC del QR público (hardening, decisión #6), borrado físico 17 tablas
  vacías (DDL), 96 contratos legacy con valor/cdp NULL, planilla DANE
  para M-EDU (sede_educativa), idempotencia doc+evento en
  `inscribir_persona`, limpieza template legacy por-subgrupo.

**Adenda misma jornada — limpieza #5 + HMAC fase 1 (QR públicos):**
- Borrada cadena zombi por-subgrupo: template + `_actividades_por_subgrupo_legacy`
  + vistas POST `actividad_renombrar/eliminar/migrar_desde_texto` (-401 LOC).
  La vista `actividades_por_subgrupo` queda solo como redirect (su URL name
  sigue referenciado por 4 templates legacy).
- **HMAC QR fase 1 (decisión #6)**: `apps/login/services/qr_token.py`
  (HMAC-SHA256 de SECRET_KEY, estable por evento, sin expiración) +
  `QrTokenPermission` reemplaza `AllowAny` en las 13 vistas públicas de los
  8 módulos (captura, inscripción, info-terreno, banco, caracterización,
  jóvenes, entregas). `_url_publica_por_tipo` agrega `?t=` (todos los QR
  nuevos lo llevan). Angular: `qrTokenInterceptor` global reenvía el `t`
  de la página pública a toda llamada API.
- **Modo suave activo**: sin token → warning en logs, NO bloquea (QR
  impresos siguen vivos). **Fase 2**: `QR_TOKEN_ENFORCE=true` en `.env` +
  restart → 403 sin token válido. Decidir con Alex cuándo activar (tras
  reimprimir QRs vigentes).
- +4 tests (token estable/validación, URL con token, modo suave, enforce
  con override_settings). Suite 360 tests OK.

### 2026-06-11 (tarde) — FULL ANGULAR: corte del HTML viejo en 3 PRs + mapa Cultura

Decisión Alex: "si ya está full Angular, pasarnos a Angular de una; ya no
debería tener acceso al HTML antiguo". Ejecutado en 3 PRs cascadeados,
precedidos por plan del agente arquitectura.

**Antes del corte (misma jornada):**
- Manual de prueba Cultura (`docs/manuales_modulos/cultura.md`): URLs con token de
  los 3 forms (70/71/72), paso a paso, checklist y texto de solicitud de
  responsable. Solo los 3 que pasaron; Explorarte (69) va aparte.
- Fix datos: eventos 69-72 sin `dependencia_id` (script los creó solo con
  subgrupo) → INVERSIÓN LOCAL. La lista /app/eventos ya la muestra.
- Mapa: eventos 69-72 ubicados en la Alcaldía (LugarIncidencia 100055) +
  **automático**: `get_lugar_incidencia_default()` en EventoCRUDView.post
  — todo evento creado sin coordenadas queda en la Alcaldía.

**PR-0 (`d65aedd`) — precondición JWT:**
- Hallazgo del plan: exports (`window.open`) y polígonos del mapa
  (`/geo/api/kennedy/*`) eran `@login_required` por SESIÓN — funcionaban
  solo porque coexistía la sesión del HTML viejo.
- `jwt_or_session_required` (apps/login/decorators.py): Bearer JWT o
  sesión; 401 JSON sin credenciales. Aplicado a 5 geo + 7 exports +
  firma Banco.
- Angular `DescargasService` (blob + Bearer) reemplaza los 4 window.open.
- Verificado JWT puro: 401 sin auth / 200 con Bearer en los 12 endpoints.

**PR-1 (`708763d`) — organizador HTML → redirects al SPA (agente backend):**
- ~70 vistas render → `redirect('/app/...')`: eventos, tipos, hubs
  dashboard, presupuesto completo, banco, jóvenes, entregas, admin org,
  roles, cursos docente, votaciones organizador, perfil, registro,
  mapa-kennedy. Net **-4.193 LOC**.
- Se quedan en Django: `caracterizacion_interna` + wizards de sector
  (llenado interno SIN equivalente Angular — decisión pendiente),
  votaciones scan/QR (kiosko), exports, AJAX JSON, APIs DRF, redirects
  públicos, /admin.
- ~50 tests ajustados a 302+Location.

**PR-2 (`72752d8`) — una sola puerta:**
- `login_view` → `/app/auth/login` (login HTML muere; sesión Django solo
  vía /admin). `logout_view` mata sesión y va al SPA. `/` → `/app/`.
- Firma del Banco: `<img src>` directo → blob autenticado en el detalle
  Angular (un img no puede mandar Bearer).
- Cadena verificada: anónimo a URL vieja → /login/ → /app/auth/login 200.

**Estado al cierre:** produccion `72752d8` (vía cascada, último merge),
357/357 tests OK en cada push. innovaK es **UI Angular única** + Django
como API/exports/kiosko/admin.

**Decisiones pendientes de Alex:**
1. Llenado interno de caracterización (funcionario sin QR): hoy quedó
   inaccesible (era HTML con sesión). ¿Se migra a Angular (~½ día,
   extender wizard público con modo interno) o no se usa?
2. PR-3 (borrado físico de templates/vistas redirigidas): esperar ~1
   semana de estabilidad como dicta RETIRO_TEMPLATES_DJANGO.md, luego
   borrar en lotes. RETIRO doc quedó desactualizado — reescribir en PR-4.
3. QR_TOKEN_ENFORCE (fase 2 HMAC) sigue en modo suave.

### 2026-06-18 — Panel del docente completo: docente/suplente, inscritos, insights de cursos

Sesión sobre `feat/cursos-escuela-mapa-calor` que cerró el panel del
curso (`/app/cursos/:id`) en Angular y agregó el dashboard de insights.
Sin cascada a producción (queda en la rama feat, sin commit aún).

**Backend (`apps/login`):**
- `CursoDetalleView.patch` ahora también acepta `funcionario_id` →
  asigna/cambia/quita el **docente titular** del curso
  (`Evento.funcionario`), validando que exista y esté activo.
- `CursoInscritosView` (`/api/cursos/<id>/inscritos/`): GET lista de
  inscritos con estado; PATCH `{participante_evento_id, estado}` para
  **aceptar/rechazar** (espera→inscrito respeta el cupo; rechazar →
  rechazado). Reusa `ParticipanteEvento.estado` (PR-1 cupo/lista espera).
- `DocentesDisponiblesView` (`/api/cursos/docentes/`): funcionarios
  activos asignables (titular o suplente).
- `SesionDetalleView` (`PATCH /api/sesiones/<id>/`): asigna **quién
  dictó** la sesión (`Clase.dictada_por`). NULL = la dictó el titular;
  un funcionario distinto = **suplente** (el supervisor lo asigna; la
  salud del titular no es asunto del registro, solo se anota quién dictó).
- `CursosInsightsView` (`/api/cursos/insights/`) + servicio
  `curso_sesiones.insights_cursos()`: KPIs (cursos, inscritos, en
  espera, sesiones, % asistencia, suplencias, sin docente), distribución
  por subgrupo/estado, top docentes, timeline mensual, distribución de
  notas (escala 0–5 SED) y calidad del dato.
- Modelo `Clase` + campo `dictada_por` (FK `funcionario`, `SET_NULL`).
  `ClaseSerializer` expone `dictada_por_id` + `dictada_por_nombre`;
  `SesionesEventoView.get` agrega `select_related('dictada_por__persona')`.

**DDL aplicado en `poblacion_kennedy`** (confirmado por Alex, backup
diario de hoy <24h, vía `connection.cursor()` porque el contenedor no
trae `psql`):
- `apps/login/scripts/008_clase_dictada_por.sql` (+ rollback):
  `ALTER TABLE clase ADD COLUMN dictada_por_id INTEGER` + FK a
  `funcionario(id) ON DELETE SET NULL` + `idx_clase_dictada_por`.

**Frontend Angular (`frontend/src/app/features/cursos/`):**
- `cursos-insights.component.ts` NUEVO (Chart.js nivel Power BI: línea
  mensual, barras subgrupo/docentes/notas, doughnut de estado, barras de
  calidad). Ruta `/cursos/insights` (antes de `:id`) + botón "Insights"
  en el listado.
- `curso-detalle.component.ts`: caja de **docente titular** con selector
  (asignar/cambiar/quitar); pestaña **Inscritos** (aceptar/rechazar con
  badges de estado); columna **"Dictada por"** con selector de suplente
  por sesión.
- **Reemplazo del textarea de "Crear sesiones bulk"** (texto libre con
  formato `YYYY-MM-DD HH:MM …`, que Alex marcó como "horrible") por un
  **formulario estructurado**: tabla con `input[type=date]` /
  `input[type=time]` / texto por fila, botones agregar/quitar fila.
- `cursos.types.ts` + `cursos.api.ts`: tipos y métodos nuevos
  (`docentes`, `asignarDocente`, `inscritos`, `cambiarEstadoInscrito`,
  `asignarSuplente`, `insights`).

**Verificación:** `manage.py check` limpio · suite smoke **379 OK**
(8 skipped) · contenedor reiniciado, `/app/` 200, `/api/cursos/insights/`
401 sin auth (no 500).

**Dos bugs de cierre encontrados y resueltos en QA inmediata:**
1. **SPA en blanco / 404 de assets**: el primer `ng build` fue SIN
   `--base-href=/app/`, así el `index.html` pedía `/main.js`,
   `/styles.css`, `/chunk-*.js` en la raíz → 404 (la app parecía
   "caída" aunque el contenedor estaba `Up healthy`). Fix: rebuild con
   `npx ng build --base-href=/app/` (comando de deploy correcto). **Regla:
   el SPA SIEMPRE se construye con `--base-href=/app/`.**
2. **Insights vacío (HTTP 500)**: `insights_cursos()` usaba
   `EvaluacionParticipante` sin importarlo → `NameError` en
   `/api/cursos/insights/`. Fix: import local en el servicio.

**Pendiente:** commit + cascada a producción esperan luz verde de Alex
(la rama tiene también los cambios de PR-1/PR-2 de cupo y conexión
cursos↔escuela↔mapa sin commitear).

### 2026-07-06 — Ordenar la casa: limpieza de ramas/CSS/vistas + documentación profesional

Sesión de orden y saneamiento "modo arquitecto" para que un desarrollador
nuevo entienda el proyecto. Cascadeada a producción (rama de trabajo
`chore/ordenar-casa-2026-07-06`, 7 commits → 3 troncales, tree único `b701c89`).

**Ramas (el desorden grande):**
- Locales **138 → 8**, remotas en origin **126 → 5**. Borradas 121 ramas 100%
  mergeadas (local + remoto), verificando una por una que ninguna tuviera
  trabajo único. Preservadas: 3 troncales + `feat/{dashboard-presupuesto-cadenas,
  usuarios-georef,etapa-d-pr5...,banco-insights-ranking}` + `fix/subgrupo2-qr-form-visible`.

**Higiene / seguridad:**
- `.gitignore` blindado: `*.local.txt` + `credenciales_*` (el archivo de
  credenciales declaraba "no subir a git" pero NO estaba protegido) y
  `.claude/worktrees/`.
- Mascota → `frontend/public/kenny/mascota-innovak.mp4`. `docs/infra/`
  versionado (dossier k8s + artefactos, sin secretos: solo `${VAR}`).

**Código muerto post full-Angular:**
- 20 archivos CSS/HTML muertos borrados (~27k líneas + 2.25 MB duplicado).
- **L1:** trim de `base.scss` → 11 partials huérfanos fuera; `base.css`
  181 KiB → 121 KiB (-31%). Chrome vivo (votaciones/breadcrumb) intacto.
- **L2/L5:** 69 vistas-puente `redirect('/app/...')` + 69 URLs + template
  `votaciones/dashboard.html` retirados. Públicos QR, kiosko scan, exports,
  DRF y login intactos. Puentes referenciados por templates vivos / smoke
  tests conservados. `manage.py check` limpio, **523/523 tests OK**.
- **L3:** `staticfiles/` (STATIC_ROOT, 207 archivos) desversionado + gitignored.
- **L4 PENDIENTE:** `apps/kordial` y `apps/VitalK` (scaffolds muertos) no se
  pudieron borrar del disco: solo quedan `.pyc` root-owned. Requieren
  `sudo rm -rf apps/kordial apps/VitalK`.

**Documentación profesional (para el extraño):**
- Nuevos: `/README.md` (no existía), `docs/GETTING_STARTED.md`, `docs/GLOSARIO.md`,
  `docs/propuestas/onboarding_kenny.md` (spec de la mascota Kenny — feature
  futura, NO implementada).
- `docs/arquitectura/ARQUITECTURA.md` sincronizado con el código (−20
  referencias a la app `kactivo` ya borrada; documenta las 11 apps reales +
  MongoDB + la cadena de negocio).
- Archivadas a `_historico/` 5 propuestas ejecutadas + `RETIRO_TEMPLATES_DJANGO.md`
  (plan ya ejecutado). `propuestas/` queda solo con lo NO ejecutado.
- `DEUDA_TECNICA.md`: catalogada la limpieza residual (L1–L5).

**Estado al cierre:**
- 3 troncales sincronizadas y pusheadas (`produccion=9a58faf`). Container
  `innova_k` reiniciado, sirviendo `/app/` 200, `/api/docs/` 200,
  `manage.py check` 0 issues.
- Deuda: 0 crítica. Queda M-EDU (bloqueada por planilla DANE) + L4 (`sudo rm`).
- Pendientes de decisión de Alex: cascada de las ramas en vuelo
  (`dashboard-presupuesto-cadenas` WIP, `usuarios-georef`, `subgrupo2-qr`);
  QR_TOKEN_ENFORCE fase 2.

### 2026-07-06 (tarde) — Onboarding Kenny en producción (PR-1..4)

Feature nueva completa y cascadeada a producción en la misma jornada
(`produccion=1741dd8`). Onboarding guiado con la mascota Kenny.

**Backend (app nueva `apps/onboarding/`, aislada):**
- Modelo `OnboardingProgreso` managed=False (usuario FK, tour_id, completado,
  fecha; UNIQUE usuario+tour). Endpoints DRF `IsAuthenticated`:
  GET `/api/onboarding/estado/` · POST `/api/onboarding/completado/`.
- **DDL aplicado** (OK explícito de Alex + backup 02:00): tabla
  `onboarding_progreso` (BIGSERIAL, FK usuario ON DELETE CASCADE, índice).
  Script en `apps/onboarding/scripts/001_onboarding_setup.sql`.

**Frontend (`frontend/src/app/features/onboarding/`):**
- `MascotPresenterComponent` standalone: video por estado
  (idle/saludo/senalando/celebrando), aislado — expone SOLO `setEstado()`.
- `TourService` envuelve **driver.js 1.6** (startTour/next/prev/skip). Tours
  como DATA (`tours.data.ts`). Desacople vía `MascotStateService` (el motor
  nunca conoce el render). Persistencia: backend + respaldo localStorage.
- `OnboardingHostComponent`: mascota flotante en el chrome (LayoutComponent).
- Marcadores `data-tour` en topbar (menu-toggle, perfil) y hub (cards).
  HubComponent arranca el tour la primera vez.

**Diseño respetado:** motor desacoplado del render (video/Lottie/3D
intercambiable), tours data-driven, managed=False + DDL (sin migración),
assets en `frontend/public/kenny/` → `/kenny/*.mp4`.

**Estado:** 530 tests OK (7 nuevos de onboarding, flujo E2E pasa contra BD
real). Container reiniciado, `/app/` 200, endpoint 401 gateado, video servido.
**Pendiente menor:** producir 3 de los 4 videos de estado (hoy los 4 usan el
único mp4).

### 2026-07-06 (cierre) — Ramas en vuelo cascadeadas a producción

Cerradas las ramas pendientes que quedaban tras la limpieza:
- **fix subgrupo QR/Formulario por evento** — restaura botones QR/Form en el
  panel de Área (sus 3 archivos no habían divergido; merge limpio).
- **command `crear_usuarios_georef`** — herramienta admin (dry-run, roster a
  archivo gitignored, --reset-all).
- **Cockpit presupuestal** (`/app/presupuesto/dashboard`) — dashboard ejecutivo
  Chart.js (bandas Plata/Gente + cadena por proyecto). Estaba WIP: la ruta y la
  card ya existían, faltaba el component (mergeado) y **2 fixes de auth full-Angular**:
  (a) el component usaba `fetch` con cookies → cambiado a HttpClient (Bearer JWT);
  (b) los 12 endpoints `api/presupuesto` eran `@login_required` (302 con JWT) →
  `@jwt_or_session_required`. Verificado E2E con token real: 200 + datos reales.

**Estado:** `produccion=976efbe`. 537 tests OK. Container reiniciado, `/app/` 200,
endpoints presupuesto 401 sin token (aceptan JWT). Ramas restantes: 3 troncales +
2 casos borde (`feat/banco-insights-ranking` en worktree, `feat/etapa-d-pr5...`
ahead 1). Ramas totales: 138→7 local en la jornada.

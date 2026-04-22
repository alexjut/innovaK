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

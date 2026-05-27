# PR-1: Auditoría y mapeo — Fusión kactivo → Evento unificado

**Fecha:** 2026-05-27 · **Rama destino sugerida:** `feat/fusion-kactivo-pr2` (creada desde `desarrollo`) · **Arquitecto:** agente `arquitectura` (Claude Opus 4.7)

> Este documento es el entregable de PR-1 (auditoría) de la serie de 5 PRs para fusionar `apps/kactivo` dentro del modelo unificado de `Evento` (en `apps/login`). Cubre inventario, mapeo destino, riesgos, contratos JSON Angular-ready y decisiones tomadas. Lo lee Claude en sesiones futuras sin contexto.

---

## 0. Resumen ejecutivo

`apps/kactivo/` (1.815 LOC, 9 archivos Python con código vivo + 38 templates + 21 URLs) es **mayoritariamente código zombi**: 17 de 20 tablas relacionadas están a 0 filas; 9 modelos vivos sobre tablas vacías; varias views referencian columnas inexistentes (`Lugar.tipo`, `Disciplina.tipo`, `Docente.area_encargada`, `Asistencia.presente`, `Grupo.numero`, `Persona.identificacion`, `Curso.tipo_curso`, `Curso.cupo_disponible()`) y reventarían con `FieldError` al primer POST.

**Lo único realmente vivo en kactivo es la tabla `participante_evento`** con **2.545 filas en 28 eventos** (top: evento 33 con 833 inscripciones) — y todas son `tipo_evento_codigo='GENERICO'`. Pero **kactivo NO la usa**: la tabla la escribe/lee `apps.login.views.eventos.inscripcion` (raw SQL en `inscribir_participante`) y `apps.login.views.eventos.asistencia` (raw SQL en `lista_asistencia` + `lista_asistencia_pdf`). El modelo `ParticipanteEvento` de `apps/kactivo/models/kasistencia.py:177` **no se importa en ningún sitio** del repo fuera de su propio archivo.

Las únicas dependencias reales cross-app hacia kactivo son **3 lugares**:

1. `apps/login/views/api.py:3,107` — `from apps.kactivo.models.kasistencia import Curso` para el endpoint `cursos_por_area` (consume `curso.clase.disciplina.categoria` — todas vacías; endpoint muerto en runtime pero importado en URLs).
2. `apps/login/views/eventos/info_terreno.py:53,88` — `DocumentoEvento` + `TipoArchivo` para guardar fotos del flujo INFO_TERRENO. **Estas 2 tablas SÍ se usan** (`documento_evento`: 2 filas, `tipo_archivo`: 1 fila).
3. `apps/login/models/inscripcion.py:11` — `kactivo.Curso` como FK de `Inscripcion` (tabla `inscripcion`: 0 filas).

**Conclusión arquitectónica:** la fusión es **factible y de bajo riesgo de datos** porque casi todo está vacío. El riesgo real está en (a) preservar el flujo público de inscripción simple a evento (`/evento/inscripcion/<id>/`, que ya vive en `apps.login.views.eventos.inscripcion`), (b) reubicar los modelos `DocumentoEvento`/`TipoArchivo` antes de borrar kactivo, y (c) no romper el guard de permisos del hub Actividades que depende del set `KACTIVO = {kactivo_cultura, kactivo_deporte, kactivo_asistencia, kactivo_consultas}` (mencionado en 4 sitios de `apps/dashboard/views.py`).

**Estimación total de la serie PR-2 → PR-5:** 3–5 días de trabajo en cascada, sin DDL, sin downtime. PR-2 (modelos) + PR-3 (rutas públicas/inscripción) son los más sensibles; PR-4 (consultas/asistencia) es mayoritariamente borrado; PR-5 (apagar app) es 1 hora.

---

## 1. Inventario exhaustivo de `apps/kactivo/`

### 1.1 Modelos

| Modelo | Archivo:línea | `db_table` | Filas BD | Bug latente | Estado |
|---|---|---|---|---|---|
| `Acudiente` | `models/kasistencia.py:6` | `acudiente` | 0 | — | Zombi (era paso 3 del flujo inscripción cursos) |
| `Docente` | `models/kasistencia.py:26` | `docente` | 0 | `views.cultura.py:136,160` filtra por `area_encargada` que no existe en BD | Zombi |
| `Curso` | `models/kasistencia.py:45` | `curso` | 0 | `views.cultura.py:31` accede a `Participante.curso` (FK inexistente), `views.deporte.py:117` referencia `CursoExtendido` nunca importado | Zombi (única referencia útil: `login/models/inscripcion.py:11` FK string, también con 0 filas) |
| `Disciplina` | `models/kasistencia.py:61` | `disciplina` | 0 | `views.cultura.py:162` y `views.deporte.py:166` filtran por `tipo` que no existe (columna real: `categoria`) — bug ya documentado en deuda M1 cierre 2026-05-04 | Zombi |
| `Grupo` | `models/kasistencia.py:74` | `grupo` | 0 | `views.deporte.py:94` referencia `Grupo.numero` y `Grupo.curso` (no existen en modelo ni BD) | Zombi |
| `Clase` | `models/kasistencia.py:86` | `clase` | 0 | FK a `georeferenciacion.Lugar` y `login.Evento` correctas; views fallan por joins inválidos | Zombi |
| `HorarioClase` | `models/kasistencia.py:105` | `horario_clase` | 0 | Modelo declara FK `clase`, views invocan `lugar`, `fecha_inicio`, `fecha_fin`, `dias_semana`, `tipo_clase` que no existen | Zombi |
| `Asistencia` | `models/kasistencia.py:120` | `asistencia_clase` | 0 | Modelo dice `asistencia` (boolean), views usan `presente` (no existe) | Zombi |
| `Convocatoria` | `models/kasistencia.py:136` | `convocatoria` | 0 | — | Zombi |
| `TipoAsistencia` | `models/kasistencia.py:153` | `tipo_asistencia` | (no consultado, pero asumimos 0) | — | Zombi |
| `ClaseParticipante` | `models/kasistencia.py:165` | `clase_participante` | 0 | — | Zombi |
| `ParticipanteEvento` | `models/kasistencia.py:177` | `participante_evento` | **2545** | El modelo no se importa en NINGÚN lado del repo (`grep` confirma); la tabla la usa raw SQL de `apps.login.views.eventos.inscripcion` y `…asistencia` | **Tabla viva / Modelo huérfano** |
| `TipoArchivo` | `models/kdocumentos.py:8` | `tipo_archivo` | 1 | — | **Vivo** — usado por `info_terreno.py:55` |
| `DocumentoParticipante` | `models/kdocumentos.py:18` | `documento_participante` | 0 | — | Zombi |
| `DocumentoEvento` | `models/kdocumentos.py:34` | `documento_evento` | 2 | — | **Vivo** — usado por `info_terreno.py:59,89` (fotos de visita en terreno) |
| `DocumentoRequisito` | `models/kdocumentos.py:49` | `documento_requisito` | 3 | Catálogo seed con 3 filas, pero los views que lo consumen (`formulario_participante.py:152`) ya fueron desactivados (HTTP 410) | Zombi de datos, catálogo histórico |
| `ValidacionDocumental` | `models/kdocumentos.py:67` | `validacion_documental` | 0 | — | Zombi |
| `EvaluacionParticipante` | `models/kregistro.py:9` | `evaluacion_participante` | 0 | — | Zombi |
| `NotaMedica` | `models/kregistro.py:23` | `nota_medica` | 0 | — | Zombi |

**Totales:** 19 modelos · 3 vivos (`TipoArchivo`, `DocumentoEvento`, `DocumentoRequisito`) · 16 zombi · 1 modelo huérfano sobre tabla viva (`ParticipanteEvento`).

### 1.2 URLs (`apps/kactivo/urls.py`, 21 rutas)

| Ruta | View | Estado |
|---|---|---|
| `cultura/` | `cultura_shell.inicio` | Shell vivo (HTML) — render `cursos/inicio.html` |
| `cultura/participante/` | `cultura_shell.participante` | Shell vivo |
| `cultura/docente/` | `cultura_shell.docente` | Shell vivo |
| `cultura/cursos/` | `cultura_shell.cursos` | Shell vivo |
| `cultura/cargue-documental/` | `cultura_shell.cargue_documental` | **Semi-vivo**: POST sube a Mongo con `apps.kactivo.services.mongo_upload`. NO persiste en SQL (sólo mensaje flash con `mongo_id`) — utilidad real cuestionable |
| `cultura/consultas/` | `cultura_shell.consultas` | Shell vivo |
| `cultura/asistencia/` | `cultura_shell.asistencia` | Shell vivo |
| `registro/` | `formulario_participante_view` | **DEPRECADO** — devuelve HTTP 410 (banner) |
| `datos-complementarios/<id>/` | `datos_complementarios` | Zombi runtime (referencia `Persona.ocupacion_actual`, etc. — campos ya no existen tras refactor) |
| `acudiente/<id>/` | `registrar_acudiente` | Zombi runtime |
| `resumen/<id>/` | `resumen_registro` | Zombi runtime (`Participante.curso_extendido` no existe) |
| `documentos/<id>/` | `cargue_documento` | Zombi runtime (`participante.nombre` no existe) |
| `validacion/<id>/` | `validacion_documental_view` | Zombi runtime |
| `validaciones/` | `lista_validaciones` | Funciona en runtime (`ValidacionDocumental.objects.all()` devuelve []) pero sin datos |
| `cultura/caracterizaciones/` | `listado_caracterizaciones_cultura` | Funciona — lee `CaracterizacionCultura` de `apps.caracterizacion` (datos reales N12) |
| `cultura/participantes/` | `consulta_participantes_cultura` | Zombi runtime — accede a `Participante.curso`, `nombre`, `identificacion` (FK/campos inexistentes) |
| `cultura/participantes/exportar-excel/` | `exportar_participantes_excel` | Zombi runtime — usa `Participante.curso_extendido`, `.nombre`, `.identificacion`, `.correo`, `.telefono`, `.fecha_inscripcion` |
| `cultura/crear-lugar/` | `crear_lugar_cultura` | **Broken** — importa `LugarForm` que NO existe en `forms.py` |
| `cultura/crear-curso/` | `crear_curso_cultura` | Roto — `Curso` no expone esos campos |
| `cultura/docentes/` | `consulta_docentes_cultura` | Zombi runtime (`Docente.area_encargada` no existe) |
| `cultura/asistencia/` | `consulta_asistencia_cultura` | Zombi runtime |
| `cultura/lugares/` | `consulta_lugares_cultura` | Zombi runtime (`Lugar.tipo` no existe) |
| `cultura/ping-db/` | `ping.ping_db` | Funciona — diagnóstico interno |

**Más URLs no expuestas en `urls.py` pero declaradas en views:**
- `apps/kactivo/views/deporte.py` (244 LOC) — **NO está incluido en `urls.py`**. Es código completamente colgado.
- `apps/kactivo/views/asistencia.py` (110 LOC) — define funciones no alcanzables.
- `apps/kactivo/views/consulta_cursos.py` (18 LOC) — no en `urls.py`.
- `apps/kactivo/views/consulta_participantes.py:36` — no en `urls.py`.
- `apps/kactivo/views/index.py` `index_kactivo_view` — no en `urls.py` (pero templates aluden a `kactivo:index_kactivo` — link roto).
- `apps/kactivo/sub_grupo_cultura/` — sub-paquete con sus propios `urls.py`, `views.py`, `forms.py`. **NO incluido en `urls.py` raíz**.

### 1.3 Templates (38 archivos)

- `templates/cursos/*.html` (7) — shell de navegación Bootstrap. Cada link va a un endpoint zombi.
- `templates/kactivo/*.html` (15) — incluye `_tabs.html`, `base_kactivo.html`, formularios y consultas legacy.
- `apps/kactivo/templates/sub_grupo_cultura/*.html` (2) — duplicado de `apps/kactivo/sub_grupo_cultura/templates/*.html` (2).

**Patrón duplicado:** existen dos copias idénticas de `lista.html` y `formulario.html` para `sub_grupo_cultura`. Resto de plantillas referencia `{% url 'kactivo:index_kactivo' %}` que no está registrado — links rotos.

### 1.4 Forms (`apps/kactivo/forms.py`, 149 LOC, 8 forms)

Todos sobre modelos zombi salvo `LugarForm` que está referenciado pero **no definido** (deuda ya documentada). `CursoExtendidoForm` y `GrupoYHorarioForm` también importados desde `views/deporte.py:80`, **no definidos** en `forms.py`.

### 1.5 Services

| Archivo | Estado |
|---|---|
| `services/mongo_upload.py` (26 LOC) | **Vivo** pero duplicado con `apps/documentos/services/mongo_storage.py` (mejor: cifrado, metadata, idempotencia). Consolidar |
| `services/onedrive_upload.py` (57 LOC) | **Muerto** — settings no configurados |
| `services/botones.py` (17 LOC) | **Muerto** — `index_kactivo_view` no alcanzable. Usa `user.groups.filter(name='Coordinador')` — patrón pre-N15 |

### 1.6 Otros artefactos

- `apps/kactivo/admin.py` (123 LOC) — registra 14 admins. Útiles: `EventoAdmin`, `TipoEventoAdmin`, `ParticipanteAdmin`, `TipoArchivoAdmin`, `DocumentoEventoAdmin`. Resto sobre tablas vacías.
- `apps/kactivo/templatetags/custom_filters.py` (6 LOC) — filtro `|mayusculas` redundante con built-in `|upper`.
- `apps/kactivo/migrations/__init__.py` — vacío (coherente con `managed=False`).
- `apps/kactivo/tests.py` — vacío.

### 1.7 Referencias cross-app

| Origen | Destino | Naturaleza | Acción |
|---|---|---|---|
| `apps/login/views/api.py:3` | `apps.kactivo.models.kasistencia.Curso` | Import + endpoint `cursos_por_area` (consulta vacía) | Borrar endpoint o reescribir contra `Evento` (PR-4) |
| `apps/login/views/api.py:107` URL `api/cursos_por_area/` | Idem | Endpoint expuesto en `apps/login/urls.py:61` | Quitar de URLs (PR-4) |
| `apps/login/views/eventos/info_terreno.py:53,88` | `kactivo.models.kdocumentos.DocumentoEvento`, `TipoArchivo` | **Persistencia real de fotos de campo** | Reubicar modelos (PR-2) |
| `apps/login/models/inscripcion.py:11` | FK string `'kactivo.Curso'` | FK formal sobre tabla `curso` vacía. `Inscripcion` tampoco se usa (0 filas) | Cambiar FK a `curso_id = IntegerField(null=True)` (PR-2 — decisión #3 Opción B) |
| `apps/dashboard/views.py:36,175,255,510` | Set literal `KACTIVO` | Guard de permisos del hub Actividades | Colapsar a `{"cursos"}` o equivalente (PR-4) |
| `apps/login/management/commands/seed_modulos.py:32-89` | Catálogo + asignación de 5 módulos `kactivo_*` | Sembrado idempotente | Renombrar/consolidar módulos (PR-4) |
| `templates/login/formulario/index.html:69` | `href="/kactivo/cursos/"` hardcoded | Link decorativo | Reapuntar a hub Actividades (PR-4) |
| `templates/eventos/insights.html:162` | String literal "kactivo" en copy | Cosmético | Ajustar copy (PR-4) |
| `core/settings.py:65,329,338` | `'apps.kactivo'` en INSTALLED_APPS + icon mapping | Wiring | Quitar (PR-5) |
| `core/urls.py:27` | `include('apps.kactivo.urls')` | Wiring | Quitar (PR-5) |
| `apps/dashboard/scripts/seeds/cleanup_demo.py:25` | Lista tablas a limpiar incluye `participante_evento evento_id >= 100000` | Seed demo | Mantener (cambia el dueño del modelo, no la tabla) |

---

## 2. Tabla de mapeo destino

### 2.1 Modelos

| Modelo origen | Destino propuesto | Justificación |
|---|---|---|
| `ParticipanteEvento` (kactivo) | **`apps/login/models/inscripcion_evento.py`** | Es la M2M Evento↔Participante. 2.545 filas vivas. Mantener `db_table='participante_evento'`. Tabla NO se renombra. Nombre Python se mantiene como `ParticipanteEvento` (decisión #2 Opción A — menor riesgo) |
| `TipoArchivo` (kactivo) | **`apps/login/models/documentos_evento.py`** | Catálogo genérico (1 fila). `db_table='tipo_archivo'` se mantiene |
| `DocumentoEvento` (kactivo) | **`apps/login/models/documentos_evento.py`** | 2 filas vivas. Persistencia de adjuntos en `INFO_TERRENO`. Pertenece conceptualmente al Evento |
| `DocumentoRequisito` | **Borrar modelo Python (PR-4)** — tabla queda zombi en BD | 3 filas seed sin uso (decisión #4) |
| Resto (Acudiente, Curso, Disciplina, Grupo, Clase, HorarioClase, Asistencia, etc.) | **Borrar modelo Python (PR-4)** — tablas se quedan vacías | Cero filas, cero imports vivos |

### 2.2 Views / URLs

Resumen: **todo el flujo `cultura_shell.*`, `formulario_participante.*`, consultas, deporte, asistencia, sub_grupo_cultura → BORRAR (PR-4).** El hub Actividades `/dashboard/hub/actividades/tipo/CURSO/` ya es el reemplazo data-driven. El flujo público de inscripción a evento ya vive en `apps.login.views.eventos.inscripcion`.

Reescribir/mover a `apps/login/`:
- Service `inscripcion_evento.py::inscribir_persona(evento_id, datos, usuario_editor)` (PR-3)
- Service `documentos_evento.py::adjuntar_foto(evento_id, archivo, tipo_nombre)` (PR-3 — opcional)
- Endpoint DRF `POST /api/eventos/<id>/inscripciones/` (PR-3, Angular-ready)

### 2.3 Templates

Borrar todo `templates/cursos/*.html` (7), `templates/kactivo/*.html` (15) y duplicados en `apps/kactivo/templates/sub_grupo_cultura/` y `apps/kactivo/sub_grupo_cultura/templates/`.

### 2.4 Services

Consolidar `apps/kactivo/services/mongo_upload.py` → reemplazar callers (0 externos) por `apps/documentos/services/mongo_storage.py::guardar`. Borrar `onedrive_upload.py` y `botones.py`.

### 2.5 seed_modulos (matriz de roles)

Hoy: 5 módulos `kactivo_*`. Propuesta (decisión #5 Opción A — un solo módulo + asistencia separada):

| Hoy | Mañana (PR-4) |
|---|---|
| `kactivo_cultura` + `kactivo_deporte` + `kactivo_participantes` + `kactivo_consultas` | **`cursos`** (módulo único) |
| `kactivo_asistencia` | **`eventos_asistencia`** (aplica a cualquier evento, no solo cursos) |

---

## 3. Tablas BD afectadas (lectura real)

Consulta ejecutada `docker exec innova_k python manage.py shell` el 2026-05-27.

| Tabla | Filas | Acción |
|---|---|---|
| `participante_evento` | **2.545** | **CONSERVAR.** Solo se mueve dueño del modelo Python. Sin DDL |
| `documento_evento` | 2 | **CONSERVAR.** Mueve modelo a `apps.login.models.documentos_evento` |
| `tipo_archivo` | 1 | **CONSERVAR.** Mueve modelo |
| `documento_requisito` | 3 | Tabla queda, modelo se borra |
| Resto (16 tablas) | 0 | Tablas quedan vacías; modelos se borran |

**NINGÚN cambio en BD se requiere para PR-2 → PR-5.** Todo el ejercicio es Python.

**Riesgo de FKs huérfanas**: el FK string `'kactivo.Curso'` en `apps/login/models/inscripcion.py:11` dará `RuntimeError` al cargar la app si se borra `apps.kactivo`. **Mitigación (decisión #3 Opción B):** convertir a `curso_id = IntegerField(null=True)` plano en PR-2.

---

## 4. Cadena Angular-ready: endpoints DRF futuros

PLAN_FRONTEND Etapa B está en curso. Contrato propuesto:

### 4.1 Listado de Evento (tipo CURSO/CAPACITACION)
```
GET /api/eventos/?tipo=CURSO&subgrupo_id=<id>&activo=true
→ {"count": 12, "results": [{...evento JSON...}]}
```

### 4.2 Inscripción pública (PR-3)
```
POST /api/eventos/<id>/inscripciones/        (AllowAny — decisión #6 Opción A)
Body: {"nombre1", "apellido1", "fecha_nacimiento", "sexo_biologico", "identidad_genero", "documento", "telefono", "upz_codigo", "barrio_codigo"}
→ 201 {"participante_evento_id", "persona_id"}
```
Internamente: `apps/login/services/inscripcion_evento.py::inscribir_persona`.

### 4.3 Asistentes de un evento
```
GET /api/eventos/<id>/asistentes/?page=1&page_size=50
→ {"count": 833, "results": [{...persona JSON...}]}
```

### 4.4 Asistencia a sesiones (futuro, NO scope PR-2..5)
Si más adelante se quiere registrar asistencia real → modelar `EventoSesion` + `EventoSesionAsistencia` (no reusar `clase`/`asistencia_clase` vacías).

### 4.5 Adjuntos del evento
```
GET  /api/eventos/<id>/documentos/?tipo=foto_terreno
POST /api/eventos/<id>/documentos/   (multipart)
DELETE /api/eventos/<id>/documentos/<doc_id>/
```

### 4.6 Insights
```
GET /api/eventos/insights/?tipo=CURSO&desde=...&hasta=...
→ {"total_eventos", "total_inscritos", "por_subgrupo", "por_mes"}
```

**Angular-ready:** componente `<curso-list>` consume 4.1 + 4.6; `<curso-detalle>` consume 4.3; `<inscripcion-publica>` consume 4.2. Cero acoplamiento a templates Django.

---

## 5. Riesgos

### 5.1 Crítico

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Borrar `apps.kactivo` antes de mover `DocumentoEvento`/`TipoArchivo` → `info_terreno.py` revienta | PR-2 mueve modelos **antes** que PR-5 borre la app |
| R2 | FK string `'kactivo.Curso'` → `RuntimeError` al borrar app | PR-2 cambia FK a `IntegerField(null=True)` |
| R3 | Set `KACTIVO = {...}` en `apps/dashboard/views.py` (4 sitios) deja a usuarios sin acceso al hub | PR-4 actualiza set + seed_modulos siembra módulos nuevos **antes** de retirar viejos |
| R4 | Tabla `participante_evento` (2.545 filas) — riesgo si se renombra accidentalmente | NO renombrar tabla. Smoke test: `ParticipanteEvento.objects.count() == 2545` |

### 5.2 Medio

- R5: Link `templates/login/formulario/index.html:69` → `/kactivo/cursos/` queda 404. Mitigación PR-4.
- R6: `subir_a_mongo` duplica `mongo_storage.guardar`. 0 callers externos verificado.
- R7: Admins `EventoAdmin`/`TipoEventoAdmin`/`ParticipanteAdmin` desaparecen del Django admin. PR-2 los mueve a `apps/login/admin.py`.
- R8: Filtro `|mayusculas` redundante. Verificar templates antes de PR-5.

### 5.3 Bajo

- R9: `RolModulo` de módulos `kactivo_*` quedan sin sembrar tras PR-4. `seed_modulos --reset` resuelve.
- R10: 128 tests existentes — verificar `grep "apps.kactivo" tests/`.
- R11: Pre-push hook 128 tests; PR-2 incluye 2-3 tests nuevos.

### 5.4 Lo que NO está en riesgo

Cero Celery/cron, cero acoplamiento desde Banco/Jóvenes/Caracterización/Votaciones/Presupuesto, datos de 2.545 inscritos se preservan al 100%.

---

## 6. Orden de PRs siguientes

### PR-2 — Modelos vivos (1 día) — **EN CURSO**
1. Crear `apps/login/models/documentos_evento.py` (TipoArchivo + DocumentoEvento, managed=False).
2. Crear `apps/login/models/inscripcion_evento.py` (ParticipanteEvento, managed=False).
3. Migrar imports `apps/login/views/eventos/info_terreno.py:53,88`.
4. Convertir FK `'kactivo.Curso'` → `IntegerField(null=True)` en `apps/login/models/inscripcion.py:11`.
5. Mover `EventoAdmin`/`TipoEventoAdmin`/`ParticipanteAdmin`/`TipoArchivoAdmin`/`DocumentoEventoAdmin` a `apps/login/admin.py`.
6. Tests nuevos en `apps/login/tests/`.

### PR-3 — Service de inscripción + DRF endpoint (1.5 días)
1. Service `apps/login/services/inscripcion_evento.py::inscribir_persona`.
2. Refactor `inscribir_participante` (HTML) para usar el service.
3. Serializer `apps/login/serializers/inscripcion_evento.py::InscripcionPublicaSerializer`.
4. View DRF `InscripcionEventoCreateView` con `AllowAny`.
5. URL `path('api/eventos/<int:evento_id>/inscripciones/', ...)`.

### PR-4 — Limpieza views/templates + reorg módulos (1 día)
1. Borrar `apps/kactivo/views/`, `forms.py`, `urls.py`, `services/`, `sub_grupo_cultura/`, `templatetags/`.
2. Borrar `templates/cursos/*` y `templates/kactivo/*`.
3. Borrar endpoint `cursos_por_area`.
4. Refactor `seed_modulos.py`: añade `cursos` y `eventos_asistencia`, retira módulos `kactivo_*`.
5. Update `apps/dashboard/views.py` (4 sitios): `KACTIVO` → `CURSOS = {"cursos"}`.
6. Reescribir links hardcoded.

### PR-5 — Apagar `apps.kactivo` (0.5 día)
1. Quitar `'apps.kactivo'` de INSTALLED_APPS + icon mapping + urls.
2. Borrar carpeta `apps/kactivo/` completa.
3. `django check` + suite 128 tests.

---

## 7. Decisiones tomadas (consolidadas)

| # | Decisión | Elección |
|---|---|---|
| 1 | Fusión total vs. coexistencia | **Total** (Alex confirmó: nadie usa flujo legacy) |
| 2 | Nombrar modelo Python para `participante_evento` | **Mantener `ParticipanteEvento`** (Opción A — menor cambio) |
| 3 | FK `'kactivo.Curso'` en `inscripcion.py:11` | **Opción B**: `curso_id = IntegerField(null=True)`. Suelta acoplamiento, asume que Evento+actividad_plan reemplaza el concepto Curso |
| 4 | `DocumentoRequisito` (3 filas seed) | **Borrar modelo** (PR-4). Tabla queda zombi en BD |
| 5 | Colapso de módulos `seed_modulos` | **Opción A**: 1 módulo `cursos` + 1 módulo `eventos_asistencia` |
| 6 | Auth del endpoint DRF de inscripción pública | **AllowAny** + ticket de hardening (HMAC del QR) después |
| 7 | Borrar tablas vacías post-fusión | **NO en esta serie**. PR DDL dedicado después si Alex quiere |
| 8 | `apps/login/views/registro.py::inscribir_participante` zombi | Borrar en PR-4 (mismo flujo zombi de kactivo legacy) |

---

## 8. Archivos clave (paths absolutos)

**PR-2 edita:**
- `apps/login/models/documentos_evento.py` (nuevo)
- `apps/login/models/inscripcion_evento.py` (nuevo)
- `apps/login/models/__init__.py`
- `apps/login/models/inscripcion.py:11`
- `apps/login/views/eventos/info_terreno.py:53,88`
- `apps/login/admin.py`
- `apps/kactivo/admin.py` (vaciar parcial)
- `apps/login/tests/test_documentos_evento.py` (nuevo)
- `apps/login/tests/test_inscripcion_evento.py` (nuevo)

**PR-3:**
- `apps/login/services/inscripcion_evento.py` (nuevo)
- `apps/login/serializers/inscripcion_evento.py` (nuevo)
- `apps/login/api/views.py`
- `apps/login/views/eventos/inscripcion.py:23-140` (refactor)
- `apps/login/urls.py`

**PR-4 borra/edita:**
- `apps/kactivo/views/` (8 archivos)
- `apps/kactivo/urls.py`, `forms.py`, `services/`, `sub_grupo_cultura/`, `templatetags/`
- `templates/cursos/` (7), `templates/kactivo/` (15)
- `apps/login/management/commands/seed_modulos.py`
- `apps/dashboard/views.py:36,175,255,510`
- `apps/login/views/api.py:3,104-108` + `apps/login/urls.py:11,61`
- `templates/login/formulario/index.html:69`
- `templates/eventos/insights.html:162`

**PR-5 cierra:**
- `core/settings.py:65,329,338`
- `core/urls.py:27`
- `apps/kactivo/` (carpeta completa)

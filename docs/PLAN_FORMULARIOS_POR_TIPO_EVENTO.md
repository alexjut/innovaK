# Plan: formularios dinámicos por tipo de evento

> **Estado**: borrador para revisión. Nada implementado todavía.
> **Fecha**: 2026-04-23.
> **Rama sugerida**: `feat/evento-form-por-tipo` (desde `desarrollo`
> después de mergear `feat/mapa-kennedy-dashboard`).

---

## 1. Problema

Hoy el formulario `crear_evento` (en `templates/eventos/crear_evento.html`)
pide los mismos campos para los 4 tipos de evento:

| Código | Nombre | ¿Qué necesita el negocio? |
|---|---|---|
| `CAPACITACION` | Clase / Capacitación | docente, tema, duración, cupo |
| `CURSO` | Curso (varias sesiones) | docente, programa, fechas, sesiones, cupo |
| `ENTREGA` | Entrega de utensilios/insumos | qué se entrega, cantidad, a quién |
| `INFO_TERRENO` | Información en terreno | hallazgos, fotos, recorrido |

El form actual (ver `crear_evento.html`) solo tiene: nombre, tipo, fecha,
dependencia/subgrupo/funcionario, descripción, ubicación (mapa),
indicador + magnitud. **No cambia** según el tipo.

Alex pide: al elegir `tipo_evento`, mostrar los campos específicos de
ese tipo — si es ENTREGA, qué se entrega; si es CURSO, datos del curso
(profesor, clases); si es INFO_TERRENO, hallazgos de la salida; etc.

## 2. Inventario de lo que ya existe

### 2.1 Modelos relacionados ya en BD

Entre `apps/kactivo/models/kasistencia.py` y `apps/login/models/`:

- `Evento` (`login/models/evento.py`): nombre, tipo_evento, dependencia,
  subgrupo, funcionario, lugar_incidencia, actividad_plan, fecha_inicio,
  fecha_fin, descripcion, indicador, magnitud_aportada, activo.
- `Clase` (kactivo): grupo, disciplina, lugar, fecha, observaciones,
  **`evento_id`**, nombre, descripcion. **Ya contempla la relación
  Evento 1:N Clase.**
- `Curso` (kactivo): nombre, institucion, `clase_id` (singular — raro),
  `programas_id`.
- `Docente` (kactivo): persona, especialidad, experiencia, titulo.
- `Grupo`, `Disciplina`, `Programa`, `Actividad` (kactivo).
- `HorarioClase` (kactivo): clase, dia_semana, hora_inicio, hora_fin.

### 2.2 Qué NO existe

- Ninguna tabla para **ENTREGA** (qué se entregó, cantidad, beneficiarios).
- Ninguna tabla para **INFO_TERRENO** (hallazgos, recorrido, fotos).
- `kactivo.Curso` existe pero su esquema es ambiguo: su FK
  `clase_id` es SINGULAR y lo hace ver más como "instancia de una clase"
  que como "curso con muchas clases". No está claro si es reusable.

### 2.3 Campos ya útiles en `Evento` (no tocar)

- `indicador` + `magnitud_aportada`: cada evento aporta a un KPI. Esto
  es **transversal a todos los tipos** y ya funciona.
- `lugar_incidencia`: ubicación GPS. Transversal.
- `dependencia`/`subgrupo`/`funcionario`: responsables. Transversal.

## 3. Propuesta de schema por tipo

Dos caminos posibles para materializar los campos específicos:

### Opción JSONB (simple)

Agregar **una sola columna** a `evento`:

```sql
ALTER TABLE evento ADD COLUMN datos_tipo JSONB;
```

El contenido de `datos_tipo` varía según `tipo_evento_codigo`:

```jsonc
// CAPACITACION
{ "docente_id": 12, "tema": "Primeros auxilios", "duracion_min": 90, "cupo": 30 }

// CURSO
{ "docente_id": 12, "programa_id": 3, "sesiones_programadas": 24, "cupo": 25, "fecha_fin_curso": "2026-06-30" }

// ENTREGA
{ "insumos": [{"tipo":"kit_escolar","cantidad":50}, {"tipo":"balon","cantidad":10}], "beneficiarios_estimados": 50 }

// INFO_TERRENO
{ "hallazgos": "...", "recorrido_descripcion": "...", "fotos_urls": [] }
```

- **Pros**: un solo ALTER, sin tablas nuevas, schema-flexible.
- **Contras**: queries difíciles (filtrar "eventos con cupo > 20" es
  `WHERE datos_tipo->>'cupo'::int > 20`), sin integridad referencial,
  validación solo en la app.

### Opción tablas dedicadas (normalizado)

Tabla por tipo, todas con FK `evento_id` única (1:1 con evento):

```sql
CREATE TABLE evento_capacitacion (
  evento_id    INTEGER PRIMARY KEY REFERENCES evento(id) ON DELETE CASCADE,
  docente_id   BIGINT REFERENCES docente(id),
  tema         TEXT,
  duracion_min SMALLINT,
  cupo         SMALLINT
);

CREATE TABLE evento_curso (
  evento_id            INTEGER PRIMARY KEY REFERENCES evento(id) ON DELETE CASCADE,
  docente_id           BIGINT REFERENCES docente(id),
  programa_id          BIGINT REFERENCES programa(id),
  sesiones_programadas SMALLINT,
  cupo                 SMALLINT,
  fecha_fin_curso      DATE
);

CREATE TABLE evento_entrega (
  evento_id INTEGER PRIMARY KEY REFERENCES evento(id) ON DELETE CASCADE,
  beneficiarios_estimados INTEGER
  -- los insumos van en una tabla hija N:1
);
CREATE TABLE evento_entrega_insumo (
  id           SERIAL PRIMARY KEY,
  evento_id    INTEGER REFERENCES evento(id) ON DELETE CASCADE,
  tipo_insumo  TEXT NOT NULL,
  cantidad     INTEGER NOT NULL
);

CREATE TABLE evento_info_terreno (
  evento_id     INTEGER PRIMARY KEY REFERENCES evento(id) ON DELETE CASCADE,
  hallazgos     TEXT,
  recorrido     TEXT
  -- fotos: via tabla evento_foto N:1 si se decide almacenarlas
);
```

- **Pros**: FKs reales, queries normales (`WHERE cupo > 20` directo),
  validación en BD, se integra con kactivo (`docente_id`, `programa_id`).
- **Contras**: 4 tablas nuevas + 1-2 tablas hijas, más DDL.

### Mi recomendación

**Híbrido**: usar tablas dedicadas para los tipos que ya tienen modelos
reusables (`CAPACITACION` y `CURSO` → apuntar a `docente`, `programa`,
y para sesiones usar `kactivo.Clase` con `evento_id`). Para `ENTREGA`
e `INFO_TERRENO` — que son conceptos nuevos sin modelos previos — usar
tablas dedicadas también, no JSONB, para conservar consistencia.

No recomiendo JSONB porque:

- El proyecto ya prefiere schema explícito (`managed=False` pero con
  columnas tipadas — no hay JSONB transversal en otras tablas salvo
  `parque.properties`/`geometry` que son geo).
- La magnitud aportada al KPI podría depender de estos campos (p.ej.
  `cupo` → magnitud en CURSO). Normalizar permite agregaciones.

### ¿Dónde va cada concepto?

| Concepto | Dónde vive | Relación con `Evento` |
|---|---|---|
| Sesión individual (ya existe) | `kactivo.Clase` | 1:N vía `clase.evento_id` |
| Curso "agrupador" | **⚠ decidir**: reusar `kactivo.Curso` (remodelar) o crear `evento_curso` | 1:1 via `evento_curso.evento_id` |
| Docente | `kactivo.Docente` | N:1 vía `evento_curso.docente_id` o `clase.grupo.docente` |
| Entrega | nueva `evento_entrega` + `evento_entrega_insumo` | 1:1 y 1:N |
| Info terreno | nueva `evento_info_terreno` | 1:1 |
| KPI impactado | `evento.indicador` + `magnitud_aportada` (ya existe) | transversal |

## 4. UI — form dinámico

Enfoque mínimo, sin SPA ni framework:

1. El `<select id="tipo_evento">` dispara un listener JS.
2. Hay 4 `<fieldset class="campos-tipo" data-tipo="XXX">` en el template,
   escondidos (`display:none`) por default.
3. Al cambiar tipo, muestra el fieldset correspondiente, oculta los
   otros. Los campos ocultos no se envían (o se envían vacíos y el
   backend los ignora).
4. El backend recibe el POST, valida campos del tipo seleccionado,
   crea `Evento` + el registro hijo correspondiente en `transaction.atomic`.

Cada fieldset es un bloque contenido y reemplazable — facilita agregar
tipos nuevos sin reescribir el formulario.

### Opcional — carga progresiva

Si algún fieldset tiene selects grandes (ej: 200 docentes, 50 programas),
cargar por AJAX solo cuando se active el fieldset. Primera iteración:
embebidos en el template (es solo 4 tipos × 5-10 opciones c/u).

## 5. Fases incrementales

Propongo 3 PRs pequeños secuenciales, no un refactor monstruo:

### PR1 — ENTREGA e INFO_TERRENO (tipos sin modelo previo)

- DDL: `evento_entrega`, `evento_entrega_insumo`, `evento_info_terreno`.
- Modelos Django `managed=False`.
- Template: 2 fieldsets nuevos `class="campos-tipo"`.
- View `crear_evento` acepta el tipo y crea la fila hija en tx atómica.
- Tests: POST con cada tipo, verificar fila creada.

**Valor**: el flujo con los 2 tipos "nuevos" funciona y queda la
estructura lista para los otros 2.

### PR2 — CAPACITACION (reutilizar `kactivo.Clase`)

- Template: fieldset con docente + tema + duración + cupo.
- View: al guardar evento tipo CAPACITACION, crear `Clase` con
  `evento_id = nuevo.id`, `fecha = evento.fecha_inicio`, `descripcion =
  tema`.
- Requiere decidir qué `disciplina`/`grupo` asignar si los del
  formulario no lo piden (¿dejar NULL? `kactivo.Clase` los tiene
  `NOT NULL`… revisar).

**Bloqueo previo**: mirar si `clase.disciplina_id` y `grupo_id` son
realmente NOT NULL en la BD y qué implica.

### PR3 — CURSO (el caso complejo)

Antes del PR hay que **decidir** si `kactivo.Curso` se remodela o se
crea `evento_curso` aparte.

- Si remodela: DDL que corrige `clase_id singular` → tabla `curso_clase`
  M:N. Fuerte. Revisar que `kactivo` esté muerto o vivo antes de tocar.
- Si tabla nueva: `evento_curso` 1:1 con evento + reutilizar
  `kactivo.Clase` para las sesiones.

## 6. Preguntas abiertas para Alex

1. **¿`kactivo.Curso` está vivo?** ¿Hay UI que lo use hoy, o es modelo
   durmiente? (Determina si remodelar o ignorar.)
2. **`clase.disciplina_id` y `clase.grupo_id`**: ¿se pueden crear
   `Clase`s sin esos valores, o son obligatorios? (Si obligatorios,
   habría que pedírselos al usuario al crear CAPACITACION.)
3. **Entrega**: ¿los "insumos" son un catálogo (tabla `insumo` con
   lista cerrada) o texto libre?
4. **Info terreno**: ¿con fotos desde el inicio, o solo texto en PR1
   y fotos en PR futuro?
5. **KPI**: ¿el `magnitud_aportada` sigue siendo campo libre del usuario
   o se auto-calcula (p.ej. CURSO con cupo=25 → magnitud=25)?
6. **Orden de los PRs**: ¿PR1 primero (ENTREGA + INFO_TERRENO), o
   prefieres que CURSO/CAPACITACION vayan primero por ser más usados?

## 7. Riesgos

- **kactivo es zona con deuda** (ver M1 en DEUDA_TECNICA.md: modelos
  duplicados apuntando a misma db_table). Cualquier cosa que toque
  `Curso` o `Clase` debe validar primero cuál de los modelos
  duplicados está vivo.
- **Cada DDL toca BD compartida** → cada PR requiere backup previo +
  confirmación de Alex (política estándar del proyecto).
- El form actual `crear_evento` tiene bugs históricos documentados
  (ver bitácora 2026-04-20 final: `disciplina_id`, `grupo_id`, etc.
  borrados). Antes de PR2/PR3 hay que revisar que el refactor previo
  de `crear_evento` esté cerrado.

## 8. No-objetivos

Este plan NO incluye (quedan para después):

- Edición/listado de eventos por tipo.
- Reportes agregados por tipo.
- Integración con el módulo de asistencia de `kactivo`.
- Importar eventos históricos desde otra fuente.

---

**Siguiente paso**: Alex responde las 6 preguntas de la sección 6,
ajusto el plan, y arrancamos PR1.

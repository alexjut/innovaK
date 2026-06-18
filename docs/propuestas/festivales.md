# Propuesta de arquitectura — Módulo de Festivales (Cultura)

> **Estado:** propuesta (sin código ni DDL ejecutado). Para revisión y decisión de Alex.
> **Fecha:** 2026-06-18 · **Autor:** agente `arquitectura`
> **App destino:** `apps/festivales/` (nueva, aislada)
> **Proyecto presupuestal:** 2780 "KENNEDY PROYECTA TALENTO" · **Meta 4** (KPI 15, "Realizar eventos…", 60 cuatrienio / 15 anual)

---

## 0. Decisiones tomadas (Alex, 2026-06-18)

1. **Qué suma a la meta:** el **FESTIVAL** (+1 al KPI 15 por festival ejecutado, un único avance idempotente/reversible — Interpretación Y de §4). Los actos siguen siendo `Evento` pero NO doble-cuentan (`magnitud_aportada=0` salvo el representativo).
2. **`evento.festival_id`:** **SÍ** se agrega la columna a `evento` (DDL-1b, con backup). Festival(1)→Evento(N) ligado directo.
3. **Jurados:** **funcionario transcribe** la planilla (sin login de jurado). `festival_jurado.usuario_id` queda nullable/sin uso por ahora; la regla "solo el jurado asignado" se respeta por asignación en la planilla.

Defaults aplicados para las demás (D4–D8 de §7) salvo que Alex diga lo contrario: consolidado = **promedio ponderado por `peso`**; cierre vía `festival.estado='cerrado'`; criterios **por festival** con set por defecto clonable; flags `tipo_evento FESTIVAL` = inscripcion/caracterizacion/qr FALSE, requiere_actividad_plan TRUE; módulo `festivales` a Admin/Lider/Coordinador.

---

## 1. Resumen ejecutivo

Cultura necesita gestionar **8 festivales** (Rock Techotiba, Hip Hop, Salsa, Libertad Religiosa, Góspel, Vallenato, Popular y Carranga, Festival de Festivales) bajo el proyecto 2780. La matriz pide 6 módulos: registro de festivales, galería fotográfica, aforo, jurados, evaluación de artistas y publicación web; más un tablero de seguimiento de meta.

**Decisión de modelado de Alex (respetada):** **un festival AGRUPA varios eventos** (`Festival 1 → N Evento`). El ejemplo canónico es *Festival de Festivales* = 8 novenas + 1 gran evento = 9 `Evento`. Los `Evento` son la unidad que ya suma a la meta vía la cadena existente; el `Festival` es la capa organizadora encima.

**Encaje verificado en la cadena 2780 / Meta 4 / KPI 15** (consultado en BD vía contenedor, no asumido):

```
proyecto.codigo='2780' (id=1, subgrupo_id=1)
  └─ meta_proyecto id=20  → meta_id=100019 "Realizar eventos de promoción, circulación y apropiación…"
       └─ presu_indicador_meta_proyecto id=15  "Realizar eventos…" unidad='eventos' meta_magnitud=60 SUMA   ← KPI
            └─ actividad_indicador → actividad_plan id=113 "Realización de eventos culturales (promoción y circulación)"
                 └─ (HOY: 0 eventos ligados — listo para recibir los actos de los festivales)
```

Refs de modelo: `apps/presupuesto/models/indicadores.py:49` (Indicador), `:98` (ActividadIndicador), `:132` (AvanceIndicador); `apps/login/models/evento.py:37` (TipoEvento, PK=`codigo`).

> **Hecho clave para todo el diseño:** la magnitud que sube el KPI 15 **ya fluye por `evento.magnitud_aportada` → `AvanceIndicador` → KPI** al validar (patrón `apps/entregas/views/organizador.py:55-110`). El módulo Festivales **no inventa una vía de avance nueva**: agrupa eventos y captura los datos cualitativos (fotos, aforo, jurados, evaluación) que la cadena presupuestal no modela.

El módulo se construye **aislado** en `apps/festivales/`, replicando el patrón probado de `banco_iniciativas` / `jovenes_a_la_e` / `entregas`: modelos `managed=False`, DDL externo, PKs `BIGSERIAL`, FKs blandas con `db_column`, endpoints DRF, Angular bajo `/app/*` (públicos en `/app/p/*`).

---

## 2. Modelo de datos

### 2.1 Principio: reusar al máximo, crear solo lo genuinamente nuevo

| Concepto de la matriz | Cómo se resuelve | Crear tabla? |
|---|---|---|
| Cada acto/novena/concierto del festival | `Evento` (tipo nuevo `FESTIVAL`) ligado a `actividad_plan=113` → KPI 15 | NO (reusa `evento`) |
| Suma a la meta | `AvanceIndicador` al validar el evento (cadena existente) | NO (reusa `presu_avance_ind_periodo`) |
| Ubicación en el mapa | `evento.lugar_incidencia_id` (los eventos con lugar ya salen en el mapa); default Alcaldía vía `get_lugar_incidencia_default()` (`apps/georeferenciacion/utils.py:65`) | NO |
| Jurado / artista (personas) | `Persona` + `PersonaDocumento` vía `obtener_o_crear_persona` (`apps/caracterizacion/services/persona_lookup.py:31`) | NO para la persona; SÍ para el rol/registro |
| Organización proponente de artista | `Organizacion` (`apps/login/models/contratos.py:14`) | NO |
| Fotos / firmas / actas | `mongo_storage.guardar(plaintext, mime, owner)` (`apps/documentos/services/mongo_storage.py:67`) | NO (solo punteros `mongo_id`) |
| Catálogo de tipos de festival | tabla catálogo nueva pequeña | SÍ |
| **Cabecera del festival** | nuevo | **SÍ** `festival` |
| **Galería** | nuevo | **SÍ** `festival_foto` |
| **Aforo** | nuevo | **SÍ** `festival_aforo` |
| **Jurados** | nuevo | **SÍ** `festival_jurado` |
| **Criterios + evaluación + puntajes** | nuevo | **SÍ** `festival_criterio`, `festival_artista`, `festival_evaluacion` |
| **Publicación web** | columnas en `festival` (no tabla aparte) | NO (campos en `festival`) |

### 2.2 Diagrama textual

```
                          ┌──────────────────────────────────────┐
   metas (100019)         │            festival                  │   tipo_festival (catálogo)
   meta_proyecto (20)     │  id, nombre, tipo_festival_codigo,   │←──  codigo, nombre, activo
   KPI 15 (eventos=60) ───┤  vigencia, numero_edicion, estado,   │
        ▲                 │  fecha_inicio, fecha_fin, lugar_texto,│
        │ avance          │  descripcion, subgrupo_id,           │
        │                 │  publicado, publicado_en, slug,      │
   actividad_plan (113)   │  documentado, created_at…            │
        │                 └───┬───────────┬───────────┬──────────┘
        │                     │ 1:N       │ 1:N       │ 1:N
   Evento (tipo FESTIVAL) ◄───┘           │           │
   id, actividad_plan_id=113,             │           │
   festival_id (FK nueva, ver §2.4),      │           │
   magnitud_aportada, lugar_incidencia    │           │
        │ 1:N (aforo por evento ejecutado)│           │
        ▼                                 ▼           ▼
   festival_aforo                  festival_foto   festival_jurado ──┐
   (evento_id, festival_id,        (festival_id,   (festival_id,     │
    asistentes, desglose JSONB,     etapa, mongo_id, persona_id,     │ N:M evaluación
    mecanismo, validado_por…)       titulo, fecha)  perfil, estado)  │
                                                                     ▼
   festival_criterio (festival_id, nombre, peso, orden)
   festival_artista  (festival_id, persona_id?, organizacion_id?, nombre_artistico, genero, estado, posicion)
   festival_evaluacion (artista_id, jurado_id, criterio_id, puntaje, observacion)   ← planilla por jurado
```

### 2.3 Tablas nuevas (columnas, tipos, FKs, `db_column`)

Todas: `managed=False`, PK `BIGSERIAL`, FKs con `db_column` explícito, sin prefijo `public.`, sin `MAX+1`.

#### `tipo_festival` (catálogo)
| col | tipo | notas |
|---|---|---|
| `codigo` | `SMALLINT PK` | catálogo pequeño |
| `nombre` | `TEXT NOT NULL` | rock, salsa, vallenato, góspel, hip hop, religioso, popular/carranga, festival de festivales |
| `activo` | `BOOLEAN DEFAULT TRUE` | |
| `orden` | `SMALLINT` | |

#### `festival` (cabecera — la capa agrupadora)
| col | tipo | notas |
|---|---|---|
| `id` | `BIGSERIAL PK` | |
| `nombre` | `TEXT NOT NULL` | "Festival Kennedy Territorio Salsa" |
| `tipo_festival_codigo` | `SMALLINT` FK→`tipo_festival(codigo)`, `db_column` | `to_field='codigo'` |
| `vigencia` | `SMALLINT NOT NULL` | **clave multianual** (2026, 2027…) |
| `numero_edicion` | `SMALLINT` | nº edición |
| `estado` | `VARCHAR(20) NOT NULL DEFAULT 'planeado'` | `planeado / ejecutado / cerrado` (ver §2.5 — vive en festival) |
| `subgrupo_id` | `INTEGER` FK blanda→`subgrupo(id)` | Cultura (subgrupo 1) |
| `fecha_inicio` / `fecha_fin` | `DATE` | rango del festival completo |
| `lugar_texto` | `TEXT` | descriptivo; la geo fina va en cada `evento.lugar_incidencia` |
| `descripcion` | `TEXT` | |
| `documentado` | `BOOLEAN DEFAULT FALSE` | derivado: ≥1 foto por etapa (regla módulo 2) |
| `publicado` | `BOOLEAN DEFAULT FALSE` | módulo 6 |
| `publicado_en` | `TIMESTAMPTZ` | |
| `slug` | `VARCHAR(80) UNIQUE` | URL pública compartible |
| `created_at` / `updated_at` | `TIMESTAMPTZ DEFAULT now()` | |

Constraint: `UNIQUE (nombre, vigencia)` → garantiza recurrencia anual sin sobrescribir (regla multianual). Índices: `(vigencia)`, `(estado)`, `(tipo_festival_codigo)`, `(slug)`.

#### `festival_foto` (galería)
| col | tipo | notas |
|---|---|---|
| `id` | `BIGSERIAL PK` | |
| `festival_id` | `BIGINT NOT NULL` FK→`festival(id)` ON DELETE CASCADE | |
| `evento_id` | `INTEGER` FK blanda→`evento(id)` | opcional: foto de un acto específico |
| `etapa` | `VARCHAR(20) NOT NULL` | `audicion / ejecucion` (categoriza la galería) |
| `mongo_id` | `VARCHAR(64) NOT NULL` | puntero a `mongo_storage` (no se guarda el binario en SQL) |
| `mime` | `VARCHAR(60)` | |
| `titulo` | `TEXT` | |
| `descripcion` | `TEXT` | |
| `fotografo` | `TEXT` | opcional |
| `fecha_captura` | `DATE` | |
| `orden` | `SMALLINT` | |
| `created_at` | `TIMESTAMPTZ DEFAULT now()` | |

Índices: `(festival_id, etapa)`. El límite ~10 MB y el mín. 1 foto/etapa se validan en el form/servicio (no en BD).

#### `festival_aforo` (aforo del evento ejecutado)
> **Decisión de dónde vive el aforo:** el aforo es **por evento ejecutado**, no por festival (un festival tiene N actos, cada uno con su asistencia). Por eso `festival_aforo` lleva `evento_id`. El total del festival es la suma. Esto respeta la decisión Alex Festival(1)→Evento(N).

| col | tipo | notas |
|---|---|---|
| `id` | `BIGSERIAL PK` | |
| `evento_id` | `INTEGER NOT NULL` FK→`evento(id)` | el acto ejecutado |
| `festival_id` | `BIGINT NOT NULL` FK→`festival(id)` | denormalizado para sumar rápido |
| `asistentes_total` | `INTEGER NOT NULL DEFAULT 0` | aforo 0 no cierra (regla, en servicio) |
| `desglose` | `JSONB` | rangos edad/género (ej. `{"rango_etario":{...},"genero":{...}}`) — sin tablas puente, patrón captura_generica |
| `mecanismo` | `VARCHAR(20)` | `manual / boleteria / sistema` |
| `fuente` | `TEXT` | |
| `fecha` | `DATE` | |
| `estado` | `VARCHAR(20) DEFAULT 'borrador'` | `borrador / validado` (editable solo antes de validar) |
| `validado_por_id` | `INTEGER` FK blanda→`usuario`/`funcionario` | responsable que confirma |
| `validado_en` | `TIMESTAMPTZ` | |
| `created_at` / `updated_at` | `TIMESTAMPTZ DEFAULT now()` | |

Constraint: `UNIQUE (evento_id)` → un aforo por acto. Índice `(festival_id)`.

#### `festival_jurado` (listado de jurados)
| col | tipo | notas |
|---|---|---|
| `id` | `BIGSERIAL PK` | |
| `festival_id` | `BIGINT NOT NULL` FK→`festival(id)` ON DELETE CASCADE | |
| `persona_id` | `INTEGER` FK blanda→`persona(id)` | resuelta vía `obtener_o_crear_persona` |
| `numero_documento` | `VARCHAR(40) NOT NULL` | denormalizado (regla no-dup) |
| `nombre` | `TEXT NOT NULL` | |
| `perfil` | `TEXT` | perfil artístico / área |
| `institucion` | `TEXT` | trayectoria |
| `estado` | `VARCHAR(20) DEFAULT 'preseleccionado'` | `preseleccionado / confirmado / asistio` |
| `fecha_confirmacion` | `DATE` | |
| `usuario_id` | `INTEGER` FK blanda→`usuario(id)` | opcional: si el jurado loguea para evaluar (ver decisión abierta D3) |
| `created_at` / `updated_at` | `TIMESTAMPTZ DEFAULT now()` | |

Constraint: `UNIQUE (festival_id, numero_documento)` → no duplicar documento en el mismo festival (regla módulo 4).

#### `festival_criterio` (criterios configurables de evaluación)
| col | tipo | notas |
|---|---|---|
| `id` | `BIGSERIAL PK` | |
| `festival_id` | `BIGINT NOT NULL` FK→`festival(id)` ON DELETE CASCADE | criterios por festival (configurables) |
| `nombre` | `TEXT NOT NULL` | "Técnica", "Propuesta escénica", "Impacto" |
| `peso` | `NUMERIC(6,3) DEFAULT 1` | para consolidado ponderado (decisión D2) |
| `puntaje_max` | `SMALLINT DEFAULT 100` | |
| `orden` | `SMALLINT` | |
| `activo` | `BOOLEAN DEFAULT TRUE` | |

#### `festival_artista` (participante a evaluar)
| col | tipo | notas |
|---|---|---|
| `id` | `BIGSERIAL PK` | |
| `festival_id` | `BIGINT NOT NULL` FK→`festival(id)` ON DELETE CASCADE | |
| `evento_id` | `INTEGER` FK blanda→`evento(id)` | acto donde se presenta (opcional) |
| `persona_id` | `INTEGER` FK blanda→`persona(id)` | si es solista |
| `organizacion_id` | `INTEGER` FK blanda→`organizacion(id)` | si es agrupación |
| `nombre_artistico` | `TEXT NOT NULL` | |
| `genero` | `TEXT` | género musical/artístico |
| `estado` | `VARCHAR(20) DEFAULT 'inscrito'` | `inscrito / clasificado / no_clasificado` |
| `puntaje_total` | `NUMERIC(8,3)` | consolidado calculado (cache; recalculable) |
| `posicion` | `SMALLINT` | ranking |
| `created_at` / `updated_at` | `TIMESTAMPTZ DEFAULT now()` | |

#### `festival_evaluacion` (planilla por jurado — el dato fino)
| col | tipo | notas |
|---|---|---|
| `id` | `BIGSERIAL PK` | |
| `artista_id` | `BIGINT NOT NULL` FK→`festival_artista(id)` ON DELETE CASCADE | |
| `jurado_id` | `BIGINT NOT NULL` FK→`festival_jurado(id)` | autoría (regla: solo el jurado asignado ingresa) |
| `criterio_id` | `BIGINT NOT NULL` FK→`festival_criterio(id)` | |
| `puntaje` | `NUMERIC(6,2) NOT NULL` | |
| `observacion` | `TEXT` | |
| `created_at` / `updated_at` | `TIMESTAMPTZ DEFAULT now()` | |

Constraint: `UNIQUE (artista_id, jurado_id, criterio_id)` → un puntaje por (artista, jurado, criterio). El **consolidado automático** (promedio/suma según config) se calcula sobre esta tabla; se persiste en `festival_artista.puntaje_total` + `posicion`. "Una vez publicado el listado no se modifica" → se controla con un flag de cierre de evaluación (campo a discutir, ver D5; puede ser `festival.estado='cerrado'`).

### 2.4 Relación Festival(1) → Evento(N): cómo se ata

Dos opciones para ligar cada `Evento` a su `Festival`:

- **Opción A (recomendada):** agregar columna `festival_id BIGINT NULL` a la tabla `evento` (DDL aditivo, FK blanda → `festival(id)` ON DELETE SET NULL). Es una sola columna, no rompe nada (todos los eventos no-festival quedan NULL), y permite `Festival.eventos` directo. Es consistente con cómo `evento` ya creció antes (`actividad_plan_id`, `linea_id`, `indicador_id` — ver columnas verificadas).
- **Opción B:** tabla puente `festival_evento (festival_id, evento_id)`. Más pura si un evento pudiera pertenecer a varios festivales, pero **no es el caso** (un acto pertenece a un festival). Añade un JOIN sin beneficio.

→ **Recomiendo Opción A.** Es 🚨 **REQUIERE CONFIRMACIÓN ALEX (CLAUDE.md §9)** porque toca la tabla `evento` (DDL en tabla central compartida). Sin esta columna, el módulo igual funciona ligando por `festival_aforo.evento_id` / `festival_foto.evento_id`, pero perdés el agrupador limpio "dame todos los actos de este festival".

### 2.5 Dónde vive `estado` (planeado/ejecutado/cerrado)

**Recomendación: el `estado` del festival vive en `festival.estado`**; el avance a la meta lo sigue dando el `Evento` (cadena existente). Justificación:

- `evento` **no tiene** columna `estado` (verificado: sus columnas son id, nombre, tipo_evento_codigo, lugar_incidencia_id, fecha_inicio, fecha_fin, activo, dependencia_id, subgrupo_id, funcionario_id, actividad_plan_id, descripcion, created_at, updated_at, indicador_id, magnitud_aportada, sector_caracterizacion, linea_id). Agregar `estado` a `evento` contaminaría una tabla compartida por 11 tipos de evento.
- El "festival ejecutado" es un concepto del **festival como conjunto**, no de un acto suelto.
- El avance al KPI 15 **no depende de `estado`**: depende de que el `Evento` (cada acto) se valide y dispare su `AvanceIndicador`. Esto desacopla el contador de meta (eventos) de la maquinaria de festivales.

---

## 3. DDL por fase (texto para Alex — NO ejecutado)

> 🚨 **REQUIERE CONFIRMACIÓN ALEX (CLAUDE.md §9)** para todo el DDL. Aplicar tras `~/Proyectos/postgres/backup_postgres.sh` (< 24 h). El contenedor `innova_k` **no tiene `psql`**: aplicar con `connection.cursor().execute(open(script).read())` (igual que en `entregas`, registrado en bitácora 2026-06-04). Cada script lleva su bloque de reversa.

### DDL-1 (con PR-1) — catálogo + cabecera + tipo_evento

```sql
BEGIN;
CREATE TABLE IF NOT EXISTS tipo_festival (
    codigo SMALLINT PRIMARY KEY,
    nombre TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden  SMALLINT
);
INSERT INTO tipo_festival (codigo,nombre,orden) VALUES
 (1,'Rock',10),(2,'Hip Hop',20),(3,'Salsa',30),(4,'Libertad Religiosa',40),
 (5,'Góspel',50),(6,'Vallenato',60),(7,'Popular y Carranga',70),
 (8,'Festival de Festivales',80),(99,'Otro',999)
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS festival (
    id BIGSERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    tipo_festival_codigo SMALLINT REFERENCES tipo_festival(codigo),
    vigencia SMALLINT NOT NULL,
    numero_edicion SMALLINT,
    estado VARCHAR(20) NOT NULL DEFAULT 'planeado',
    subgrupo_id INTEGER,
    fecha_inicio DATE, fecha_fin DATE,
    lugar_texto TEXT, descripcion TEXT,
    documentado BOOLEAN NOT NULL DEFAULT FALSE,
    publicado   BOOLEAN NOT NULL DEFAULT FALSE,
    publicado_en TIMESTAMPTZ,
    slug VARCHAR(80) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_festival_nombre_vigencia UNIQUE (nombre, vigencia),
    CONSTRAINT ck_festival_estado CHECK (estado IN ('planeado','ejecutado','cerrado'))
);
CREATE INDEX IF NOT EXISTS idx_festival_vigencia ON festival(vigencia);
CREATE INDEX IF NOT EXISTS idx_festival_estado   ON festival(estado);
CREATE INDEX IF NOT EXISTS idx_festival_tipo     ON festival(tipo_festival_codigo);

INSERT INTO tipo_evento (codigo,nombre,descripcion,activo,
   permite_inscripcion,permite_caracterizacion,permite_qr,requiere_actividad_plan)
VALUES ('FESTIVAL','Festival cultural',
   'Acto/concierto/novena de un festival de Cultura. Suma al KPI de eventos (Meta 4, proyecto 2780).',
   TRUE, FALSE, FALSE, TRUE, TRUE)
ON CONFLICT (codigo) DO NOTHING;
COMMIT;
-- REVERSA: DROP TABLE festival, tipo_festival; DELETE FROM tipo_evento WHERE codigo='FESTIVAL';
```

> Decisión a confirmar (flags del tipo): propongo `permite_inscripcion=FALSE`, `permite_caracterizacion=FALSE`, `permite_qr=FALSE` porque los actos de festival **no son captura ciudadana por QR** (la galería/aforo/jurados los carga el organizador). `requiere_actividad_plan=TRUE` para que cada acto quede atado a la cadena. Ver el fix de `actividades-eventos.component.ts` en bitácora 2026-06-04: **cualquier tipo sin flags de inscripción/caracterización necesita su botonera propia en Angular** (no hereda QR).

### DDL-1b (con PR-1, opcional pero recomendado) — `evento.festival_id`

```sql
-- 🚨 toca la tabla central `evento`
ALTER TABLE evento ADD COLUMN IF NOT EXISTS festival_id BIGINT
  REFERENCES festival(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_evento_festival ON evento(festival_id);
-- REVERSA: ALTER TABLE evento DROP COLUMN festival_id;
```

### DDL-2 (con PR-2) — galería

```sql
BEGIN;
CREATE TABLE IF NOT EXISTS festival_foto (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    evento_id INTEGER REFERENCES evento(id) ON DELETE SET NULL,
    etapa VARCHAR(20) NOT NULL,            -- audicion|ejecucion
    mongo_id VARCHAR(64) NOT NULL,
    mime VARCHAR(60), titulo TEXT, descripcion TEXT, fotografo TEXT,
    fecha_captura DATE, orden SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_festival_foto_etapa CHECK (etapa IN ('audicion','ejecucion'))
);
CREATE INDEX IF NOT EXISTS idx_festival_foto_fest ON festival_foto(festival_id, etapa);
COMMIT;
```

### DDL-3 (con PR-3) — aforo

```sql
BEGIN;
CREATE TABLE IF NOT EXISTS festival_aforo (
    id BIGSERIAL PRIMARY KEY,
    evento_id INTEGER NOT NULL REFERENCES evento(id),
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    asistentes_total INTEGER NOT NULL DEFAULT 0,
    desglose JSONB,
    mecanismo VARCHAR(20), fuente TEXT, fecha DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'borrador',
    validado_por_id INTEGER, validado_en TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_festival_aforo_evento UNIQUE (evento_id),
    CONSTRAINT ck_festival_aforo_estado CHECK (estado IN ('borrador','validado'))
);
CREATE INDEX IF NOT EXISTS idx_festival_aforo_fest ON festival_aforo(festival_id);
COMMIT;
```

### DDL-4 (con PR-4) — jurados, criterios, artistas, evaluación

```sql
BEGIN;
CREATE TABLE IF NOT EXISTS festival_jurado (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    persona_id INTEGER REFERENCES persona(id) ON DELETE SET NULL,
    numero_documento VARCHAR(40) NOT NULL,
    nombre TEXT NOT NULL, perfil TEXT, institucion TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'preseleccionado',
    fecha_confirmacion DATE, usuario_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_festival_jurado_doc UNIQUE (festival_id, numero_documento),
    CONSTRAINT ck_festival_jurado_estado CHECK (estado IN ('preseleccionado','confirmado','asistio'))
);
CREATE TABLE IF NOT EXISTS festival_criterio (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL, peso NUMERIC(6,3) NOT NULL DEFAULT 1,
    puntaje_max SMALLINT NOT NULL DEFAULT 100, orden SMALLINT,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS festival_artista (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    evento_id INTEGER REFERENCES evento(id) ON DELETE SET NULL,
    persona_id INTEGER REFERENCES persona(id) ON DELETE SET NULL,
    organizacion_id INTEGER REFERENCES organizacion(id) ON DELETE SET NULL,
    nombre_artistico TEXT NOT NULL, genero TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'inscrito',
    puntaje_total NUMERIC(8,3), posicion SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS festival_evaluacion (
    id BIGSERIAL PRIMARY KEY,
    artista_id BIGINT NOT NULL REFERENCES festival_artista(id) ON DELETE CASCADE,
    jurado_id BIGINT NOT NULL REFERENCES festival_jurado(id),
    criterio_id BIGINT NOT NULL REFERENCES festival_criterio(id),
    puntaje NUMERIC(6,2) NOT NULL, observacion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_festival_eval UNIQUE (artista_id, jurado_id, criterio_id)
);
CREATE INDEX IF NOT EXISTS idx_festival_artista_fest ON festival_artista(festival_id);
CREATE INDEX IF NOT EXISTS idx_festival_eval_artista ON festival_evaluacion(artista_id);
COMMIT;
```

PR-5 (publicación) y PR-6 (seguimiento de meta) **no requieren DDL** (publicación = campos ya creados en `festival`; seguimiento = solo lectura sobre la cadena existente).

---

## 4. Tensión a resolver con Alex (qué suma a la meta)

La matriz dice a la vez: "8 festivales", "15 eventos/año", "cada festival ejecutado suma +1", "máx 15 festivales activos". Con el modelo **Festival(1) → Evento(N)** estas frases entran en conflicto. Hay que decidir **qué es la unidad que cuenta contra el KPI 15 (meta = 60 cuatrienal / 15 anual)**:

- **Interpretación X — el EVENTO suma** (consistente con la cadena existente y la decisión de modelado de Alex): cada acto validado dispara su `AvanceIndicador` (+1 al KPI 15). Festival de Festivales = 9 eventos = +9. Con 8 festivales eso fácilmente supera 15/año → la "meta de 15 eventos" se cumple/desborda. La frase "cada festival ejecutado suma +1" sería **incorrecta** bajo este modelo.
- **Interpretación Y — el FESTIVAL suma** (literal a "cada festival ejecutado suma +1", "máx 15 activos"): la meta de 60/15 cuenta **festivales**, no actos. Pero esto **choca con la cadena existente**, donde el KPI 15 mide `unidad='eventos'` y se alimenta de `evento.magnitud_aportada`. Habría que: o bien marcar **un solo evento "representativo" por festival** como el que aporta (`magnitud_aportada=1`) y los demás con `0`; o sumar a nivel festival con un avance manual.

> **Recomendación: Interpretación Y operativa, implementada vía X.** La meta de Cultura (60/15) cuenta **festivales como hito**, pero el avance se registra **por el festival, no por cada acto**, para no inflar el KPI. Mecanismo concreto, sin romper la cadena: cuando un `festival` pasa a `estado='ejecutado'` y cumple sus reglas (aforo validado), el servicio crea **un único `AvanceIndicador` de +1** sobre el KPI 15, ligado al `evento` "principal" del festival (o sin evento, `origen='EVENTO'` con marcador `festival=<id>`), idempotente y reversible — exactamente el patrón de `_sincronizar_avance` de entregas (`apps/entregas/views/organizador.py:55`). Los demás actos del festival quedan con `magnitud_aportada=0` (sí salen en el mapa y agrupan datos, pero no doble-cuentan).
>
> Esto reconcilia las 4 frases: 1 festival ejecutado = +1 al KPI; "máx 15 activos/año" = tope anual de festivales que es **igual** a la meta anual de 15; los actos siguen siendo `Evento` (decisión de modelado intacta) pero solo uno aporta magnitud.
>
> **Alex decide:** ¿la meta de 60/15 cuenta festivales (Y, recomendado) o actos (X)? De esto depende dónde se dispara el `+1` y con qué idempotencia. **No avanzar PR-3/PR-6 sin esta definición** porque cambia el servicio de avance.

Regla "máx 15 activos/año": se valida en el servicio de creación de festival (`COUNT(*) FROM festival WHERE vigencia=? AND estado<>'cerrado' < 15`), no en BD (es regla de negocio, puede cambiar por vigencia).

---

## 5. Plan de PRs (incremental, cada uno cascadeable con smoke tests)

Orden por **valor/riesgo**: primero el esqueleto + CRUD (valor inmediato, riesgo bajo), galería y aforo (datos que ya quieren cargar), luego jurados/evaluación (más lógica), publicación y seguimiento al final. Todo **interno** salvo donde se marque. Cada PR sigue el patrón: app/modelos `managed=False` + DDL externo (Alex aplica) + endpoints DRF + Angular feature + smoke tests + `seed_*` idempotente.

### PR-0 — Esqueleto de app + módulo de permisos (sin DDL de datos)
- App `apps/festivales/` registrada en `INSTALLED_APPS`, `core/urls.py`.
- `seed_modulos`: módulo nuevo `festivales` en `MODULOS_CATALOGO` + asignación a `Admin`, `Lider`, `Coordinador` (Cultura) en `ASIGNACION_INICIAL` (`apps/login/management/commands/seed_modulos.py:27,50`). Invalida caché de permisos.
- Decorador `@modulo_required("festivales")` en todas las vistas internas.
- Angular: carpeta `frontend/src/app/features/festivales/` + ruta lazy `/app/festivales` + card en hub Actividades.
- **Reusa:** todo el andamiaje de permisos/hub; **nuevo:** registro del módulo.
- **Riesgo:** mínimo. **Ejecuta:** sesión principal + agente `backend`.

### PR-1 — Registro de festivales (CRUD) · Módulo 1 [INTERNO]
- **DDL-1** (+ DDL-1b `evento.festival_id` si Alex aprueba). 🚨 DDL.
- Modelos `TipoFestival`, `Festival`. `seed_festivales` (idempotente) siembra los 8 festivales vigencia 2026 en `planeado`.
- DRF: `GET/POST /festivales/api/festivales/`, `GET/PATCH/DELETE /festivales/api/festivales/<id>/`, `GET catálogos`. Regla "máx 15 activos/año" en el serializer/servicio.
- Vinculación: al crear/asociar un `Evento` tipo `FESTIVAL`, setear `evento.festival_id` y `actividad_plan_id=113` → KPI 15 (formulario de evento ya existente; aquí solo se expone el selector de festival).
- Angular: panel de **tarjetas** (grid) + form + detalle, en `/app/festivales`. Cumple regla "paridad + superar Django": badges de estado, contador anual sobre 15, sparkline de actos.
- **Reusa:** `Evento`, cadena `actividad_plan 113→KPI 15`, `get_lugar_incidencia_default`. **Nuevo:** `festival`, `tipo_festival`.
- **Ejecuta:** `backend` (DRF + modelos) + sesión principal (Angular) + Alex (DDL).

### PR-2 — Galería fotográfica · Módulo 2 [INTERNO carga, PÚBLICO opcional lectura]
- **DDL-2**.
- Servicio de subida reusa `mongo_storage.guardar(blob, mime, owner={"tipo":"festival_foto","festival_id":...,"etapa":...})` (`apps/documentos/services/mongo_storage.py:67`). Validación tamaño ~10 MB y mín. 1 foto/etapa → set `festival.documentado=TRUE`.
- DRF: `POST /festivales/api/<id>/fotos/` (multipart), `GET .../fotos/`, `DELETE .../fotos/<fid>/`. Descarga vía endpoint autenticado que descifra el blob (patrón firma Banco con `jwt_or_session_required`).
- Angular: **mosaico + lightbox + descarga**, agrupado por etapa (audición/ejecución).
- **Reusa:** pipeline cripto Mongo, endpoint de descarga autenticado. **Nuevo:** `festival_foto`.
- **Ejecuta:** `backend` + sesión principal + Alex (DDL).

### PR-3 — Aforo · Módulo 3 [INTERNO]
- **DDL-3**. **Bloqueado por la decisión de §4** (define el sync de avance).
- DRF: `POST/PATCH /festivales/api/eventos/<evento_id>/aforo/` (editable solo si `estado='borrador'`), `POST .../aforo/validar/` (requiere rol responsable → confirma; `asistentes_total=0` no permite cerrar el festival como ejecutado).
- Al validar aforo + festival `ejecutado` → dispara `_sincronizar_avance` (+1 al KPI 15 según interpretación elegida en §4). Idempotente/reversible (patrón `apps/entregas/views/organizador.py:55`).
- Angular: form de aforo + **indicador/gráfica** (Chart.js desglose edad/género desde el JSONB).
- **Reusa:** patrón de sync AvanceIndicador. **Nuevo:** `festival_aforo`.
- **Ejecuta:** `backend` + sesión principal + Alex (DDL + decisión §4).

### PR-4 — Jurados + Evaluación de artistas · Módulos 4 y 5 [INTERNO]
- **DDL-4**.
- Jurados: DRF CRUD; resuelve persona vía `obtener_o_crear_persona`; `UNIQUE(festival_id, numero_documento)` evita duplicados; badges de estado; **export PDF** (reportlab, patrón asistencia).
- Evaluación: criterios configurables por festival; **planilla por jurado** (solo el jurado asignado ingresa puntajes — gating por `jurado_id`/usuario, ver D3); **consolidado automático** (promedio o suma según `tipo_agregacion`/config, D2) que recalcula `festival_artista.puntaje_total` + `posicion`; **ranking**; "publicado → no modificable" (gating por estado). **Export PDF + Excel** (patrón Jóvenes 4 hojas).
- Angular: tabla jurados + planilla de evaluación + consolidado/ranking.
- **Reusa:** `Persona`/`Organizacion`, exports PDF/Excel existentes. **Nuevo:** `festival_jurado`, `festival_criterio`, `festival_artista`, `festival_evaluacion`.
- **Ejecuta:** `backend` + sesión principal + Alex (DDL). Es el PR más pesado.

### PR-5 — Publicación web · Módulo 6 [PÚBLICO `/app/p/*`]
- Sin DDL (usa `festival.publicado/slug`).
- DRF público `AllowAny` con `QrTokenPermission` o slug: `GET /api/p/festival/<slug>/` (read-only: galería + aforo agregado + jurados + ranking). Regla: solo publicable si `estado='ejecutado'` + aforo validado.
- Angular ruta pública sin guard en `frontend/src/app/features/publico/publico.routes.ts`: `path: 'festival/:slug'` (junto a banco/captura/etc.). Botón "Publicar en web" en el detalle interno.
- **Reusa:** infraestructura `/app/p/*` AllowAny + `qrTokenInterceptor`. **Nuevo:** vista pública.
- **Ejecuta:** `backend` + sesión principal.

### PR-6 — Seguimiento de meta · tablero [INTERNO]
- Sin DDL. Solo lectura sobre la cadena: cuenta avances del KPI 15 (anual sobre 15, cuatrienal sobre 60), desglose por `tipo_festival`, barra de progreso, tabla resumen, **export informe PDF**. Alerta si avance anual < 50% en 2º semestre.
- **Reusa:** queries sobre `AvanceIndicador`/`Indicador`, exports. **Nuevo:** componente tablero (Chart.js).
- **Ejecuta:** `backend` + sesión principal.

> Cada PR cascadea `feat/festivales-prN → desarrollo → Pruebas → produccion` con el hook pre-push corriendo la suite. Cada PR agrega smoke tests propios (registrar en `scripts/run_smoke_tests.py`).

---

## 6. Mapeo reuse / extiende / nuevo

| Funcionalidad | Reusa (sin tocar) | Extiende | Nuevo |
|---|---|---|---|
| Acto del festival | `Evento`, `actividad_plan 113`, KPI 15 | `tipo_evento` (+`FESTIVAL`); `evento` (+`festival_id`, opcional) | — |
| Suma a la meta | `AvanceIndicador`, `ActividadIndicador`, patrón `_sincronizar_avance` | — | servicio de avance del festival |
| Geo / mapa | `evento.lugar_incidencia`, `get_lugar_incidencia_default` | — | — |
| Personas (jurado/artista) | `Persona`, `PersonaDocumento`, `obtener_o_crear_persona`, `Organizacion` | — | `festival_jurado`, `festival_artista` |
| Fotos/archivos | `mongo_storage.guardar`, descarga autenticada | — | `festival_foto` (punteros) |
| Permisos | `@modulo_required`, `seed_modulos`, hub Actividades, sidebar dinámico | `MODULOS_CATALOGO` (+`festivales`), `ASIGNACION_INICIAL` | — |
| Cabecera festival | — | — | `festival`, `tipo_festival` |
| Aforo | — | — | `festival_aforo` |
| Evaluación | `tipo_agregacion` (semántica SUMA/PROMEDIO) | — | `festival_criterio/artista/evaluacion` |
| Públicos | `/app/p/*` AllowAny, `QrTokenPermission`, `qrTokenInterceptor` | `publico.routes.ts` (+`festival/:slug`) | vista pública read-only |
| Exports | CSV/Excel/PDF (Banco, Jóvenes, asistencia) | — | reportes festival |
| Angular | hub Actividades, patrón list/detail (entregas) | rutas `/app/festivales` | feature `festivales/` |

---

## 7. Decisiones abiertas para Alex

1. **§4 — qué suma a la meta (BLOQUEANTE de PR-3/PR-6):** ¿la meta 60/15 cuenta **festivales** (recomendado: +1 por festival ejecutado, vía un único avance) o **actos/eventos** (cada acto +1)? Define el servicio de avance.
2. **`evento.festival_id` (DDL-1b):** ¿aprobás agregar la columna a `evento` (recomendado, una sola columna nullable) o preferís ligar solo por `festival_aforo`/`festival_foto`? 🚨 toca tabla central.
3. **Jurado como usuario del sistema vs. solo registro:** ¿el jurado **loguea** para ingresar sus puntajes (necesita Usuario/grupo `JuradoFestival` + gating por `jurado.usuario_id`), o un funcionario de Cultura transcribe la planilla en su nombre? Cambia el modelo de auth de PR-4 y la regla "solo el jurado asignado ingresa".
4. **Consolidado de evaluación:** ¿**promedio** simple, **suma**, o **ponderado por `peso`** de criterio? El esquema soporta los tres (`festival_criterio.peso`); hay que fijar el default por festival.
5. **Cierre de evaluación / "publicado no se modifica":** ¿se controla con `festival.estado='cerrado'` (recomendado, sin columna extra) o con un flag dedicado `evaluacion_cerrada`?
6. **Criterios: globales o por festival.** El esquema los pone **por festival** (`festival_criterio.festival_id`) para flexibilidad. ¿Querés un set global por defecto que se clone al crear el festival?
7. **Flags del `tipo_evento FESTIVAL`:** confirmo `permite_inscripcion/caracterizacion/qr=FALSE`, `requiere_actividad_plan=TRUE`. Si en algún festival sí hay inscripción ciudadana por QR, eso sería otro tipo/flujo.
8. **Rol operativo de Cultura:** ¿se asigna el módulo `festivales` a `Coordinador` (kactivo) y/o se crea un `CoordinadorCultura` análogo a `CoordinadorDeportes`?

---

### Notas de implementación (para quien ejecute)
- App nueva aislada `apps/festivales/`, estructura espejo de `apps/entregas/` (`models/`, `api/{views,public,serializers}.py`, `forms/`, `views/organizador.py`, `management/commands/seed_festivales.py`, `tests/test_smoke.py`, `scripts/00N_*.sql`).
- **Nunca `MAX+1`**: todas las PK son `BIGSERIAL`; los INSERT confían en la secuencia.
- DDL se aplica con `connection.cursor().execute(open(script).read())` dentro del contenedor (no hay `psql` en `innova_k`), tras backup < 24 h.
- Sync de avance: copiar literal el patrón idempotente/reversible de `apps/entregas/views/organizador.py:55-110` con marcador `festival=<id>`.

**Cadena BD verificada en vivo (contenedor `innova_k`):** proyecto `2780` (id=1) → meta_proyecto id=20 (meta 100019) → KPI `presu_indicador_meta_proyecto` id=15 (unidad='eventos', meta_magnitud=60, SUMA) → `actividad_indicador` → `actividad_plan` id=113 "Realización de eventos culturales" → **0 eventos ligados hoy** (listo para los festivales).

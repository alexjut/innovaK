# Estratificación IDECA — capa territorial + criterio de scoring del Banco

> **Estado:** PROPUESTA (sin ejecutar). Plan detallado. No se ha tocado código
> ni BD. Requiere aprobaciones marcadas antes de arrancar.
> **Origen:** el alcalde pidió que el Banco de Iniciativas Recreodeportivas
> (proyecto 2784) califique cada sede/escenario según el **estrato
> socioeconómico oficial**, usando como fuente el mapa de IDECA/Catastro.

---

## 1. Objetivo

Traer el **estrato oficial** (fuente Catastro/IDECA) al sistema como **una capa
más** del Mapa de Kennedy —reutilizable, no una integración desechable— y
usarlo en dos frentes:

1. **Scoring del Banco** (nuevo criterio dentro del bloque AUTO de `puntaje.py`).
2. **Visualización** en el Mapa de Kennedy (capa toggleable, como barrios/UPZ/parques).

---

## 2. Decisiones ya tomadas (Alex, esta sesión)

| # | Decisión | Elección |
|---|----------|----------|
| D1 | Motor point-in-polygon | **PostGIS** (habilitar en la BD) — *ver riesgo R1* |
| D2 | Sobre qué coordenada se calcula el estrato | **Ambos**: la **sede/escenario** (para scoring) **y** la **organización** (para validación cruzada declarado-vs-oficial) |
| D3 | Alcance de esta entrega | Plan primero; ejecución por PRs con gate de Pruebas |

---

## 3. Estado real verificado del código (base del plan)

- **Motor de puntaje existe y es config-as-data**: `apps/banco_iniciativas/services/puntaje.py`
  v3 = **AUTO 65 + COMITÉ 35 + BONO 5**. Rúbrica versionada, snapshot en
  `banco_rubrica`. DDL `008_banco_evaluacion.sql` / `009_banco_comite_binario.sql`.
  → El criterio de estrato entra aquí como **rúbrica v4** (versión nueva, no parche).
- **Patrón de capas geo**: `apps/georeferenciacion/views/apis.py`, function-based,
  helper `_as_geojson_list`. Endpoints `/geo/api/kennedy/{contorno,upz,barrios,parques,escuelas}/`.
- **Geometría hoy = JSONB**, servida como GeoJSON. **NO hay PostGIS, GeoDjango ni shapely**
  en el proyecto (verificado en `settings.py`, `requirements*.txt`).
- **Sedes con coordenadas**: `inscripcion_banco_escenario_detalle` → `escuela`
  (241 filas, lat/lng WGS84). Es el punto contra el que se hace el PIP para la sede.
- **Estrato autodeclarado**: `inscripcion_banco_iniciativa.estrato` (SmallInt, **1–4**).
  Es lo que la **org dice tener** — concepto distinto al estrato oficial de la sede.
  El nuevo `estrato_ideca` NO lo reemplaza; queda al lado para la validación cruzada.

---

## 4. Riesgos y decisiones abiertas (leer antes de arrancar)

- **R1 — PostGIS sobre BD compartida (ALTO).** `poblacion_kennedy` (10.100.102.12)
  es compartida con otros sistemas. `CREATE EXTENSION postgis` es superusuario y
  a nivel de toda la BD → radio de impacto fuera de innovaK. **Gate PR-0 obligatorio**:
  visto bueno del dueño de infra/DBA, no solo de Alex. GeoDjango además exige
  GDAL/GEOS/PROJ en el contenedor (Dockerfile → doble confirmación). **Fallback
  documentado**: si infra dice NO, se usa `shapely` en Python puro (el estrato se
  persiste igual; el PIP es batch, no en vivo); el resto del plan no cambia.
- **R2 — Rúbrica v4, techo del bloque AUTO (POLÍTICO). 🚩 GATE antes de PR-7.**
  Dueño: comité/alcalde. Hoy AUTO = 65 (antigüedad 10 + territorialidad 10 +
  capacidad 10 + etario 10 + diferencial 15 + inclusión 10). Meter estrato exige
  decidir la **estructura** (ver §8, 3 opciones) y la **tabla estrato→puntos** con
  su **dirección** (lo esperable: estrato bajo = más puntos, para priorizar
  población vulnerable). El código deja el criterio **placeholder desactivado**
  hasta esa aprobación. **Adelantar la pregunta en paralelo a PR-0/2/3** para que
  no frene el flujo al llegar a PR-7.
- **R3 — Estrato de la organización (D2 "ambos"). 🚩 GATE antes de PR-4.**
  Dueño: comité (aceptación del método). La org tiene `direccion` (texto libre, sin
  lat/lng) y un `barrio` (FK). **Decisión tomada (Javier): aproximar por barrio
  declarado** (mayoría/centroide de sus manzanas), no geocodificar la dirección —
  más robusto, menos partes móviles. Implica que el "estrato oficial de la org" es
  una **aproximación por barrio, no el punto exacto de su sede**. Confirmar con el
  comité que esa aproximación es aceptable antes de PR-4.
- **R4 — Vigencia del dato: Decreto 394 del 2017-07-28.** *(Corregido 2026-07-09:
  la propuesta decía 2019-08-15; es falso.)* El servicio no publica `editingInfo`;
  la vigencia está en `FECHA_ACTO_ADMINISTRATIVO` de cada manzana. Verificado:
  18.927 de 18.929 son el Decreto 394 de 2017; las otras 2 son resoluciones de
  2018. Algunas manzanas salen estrato `0` (sin estrato oficial): limitación **de
  la fuente**, se documenta; no se infiere estrato.
- **R5 — Rangos distintos.** Banco autodeclarado 1–4 vs IDECA 0–6. Normalizar al
  comparar en la validación cruzada.

---

## 5. Plan por PRs

Cada PR en `feat/*` (git worktree en directorio separado, protocolo del proyecto).
Todo DDL = **script preparado, lo aplica Alex tras backup <24h**. Gate de Pruebas
antes de cualquier cascada a producción.

### PR-0 — Gate de viabilidad PostGIS (sin código de negocio) 🔒
- Confirmar con infra/DBA: ¿se puede `CREATE EXTENSION postgis` en `poblacion_kennedy`
  sin afectar otros sistemas? Versión de Postgres, permisos superusuario, si ya está
  instalada parcialmente por otro sistema.
- Probar en local que el contenedor tolera GDAL/GEOS/PROJ.
- **Entregable:** nota go/no-go. Si no-go → activar fallback shapely (afecta solo PR-1 y PR-3).

### PR-1 — Infra PostGIS + GeoDjango 🔒 (doble confirmación)
- DDL: `CREATE EXTENSION IF NOT EXISTS postgis` (ejecuta Alex/infra).
- Dockerfile/compose: libs GDAL/GEOS/PROJ. `django.contrib.gis` en `INSTALLED_APPS`.
- Verificar `manage.py check`, arranque del contenedor y **no regresión** de los
  endpoints geo actuales (siguen sirviendo desde JSONB).

### PR-2 — Modelo `ManzanaEstrato` + sync desde Catastro
- DDL: tabla `manzana_estrato` (`id BIGSERIAL`, `codigo_manzana`, `estrato SMALLINT`,
  `geom geometry(MultiPolygon,4326)`, índice GiST). Script para Alex.
- Modelo GeoDjango `managed=False`.
- Command `sync_estratificacion`: descarga el GeoJSON de la capa ArcGIS REST de
  Catastro (MapServer layer 1, `inSR=4326`, recorte al bbox de Kennedy), upsert por
  `codigo_manzana`. On-demand / cron mensual. Registra la fecha de fuente.

### PR-3 — Asignar estrato a las sedes (PIP) + validación manual ✅ checkpoint
- DDL: campo `estrato_ideca SMALLINT` en `escuela` (reutilizable en cualquier módulo).
- Command `asignar_estrato_sedes`: `ST_Intersects(escuela.punto, manzana.geom)`
  (o shapely si fallback) → escribe `estrato_ideca`.
- **GATE que pediste:** correr contra 2–3 sedes de estrato conocido manualmente y
  validar antes de seguir. Si el PIP no cuadra, se para aquí.

### PR-4 — Estrato de la organización (2ª parte de "ambos")
- DDL: campo `estrato_ideca_org SMALLINT` en `inscripcion_banco_iniciativa`.
- Poblado desde el **barrio declarado** (R3, recomendado) o geocoding (a decidir).
- Habilita la validación cruzada declarado(1–4) vs oficial — **solo dato**, sin scoring.

### PR-5 — Endpoint de la capa
- `/geo/api/kennedy/estratificacion/` con el mismo `_as_geojson_list`
  (props: `codigo_manzana`, `estrato`). Sin lógica especial en el front.

### PR-6 — Frontend Mapa de Kennedy (Angular)
- Casilla "Estratificación" en el panel de capas (sección referencia territorial).
- Coropletas por estrato: paleta 7 colores (sin dato + 1–6). Leyenda.
- Nota: el mapa vive en Angular (`/app/*`); verificar dónde se registran las capas
  de referencia actuales y seguir ese registro.

### PR-7 — Criterio de scoring (config-as-data, PLACEHOLDER)
- Nuevo criterio en `RUBRICA_AUTO` de `puntaje.py`: `C_estrato` con tiers estrato→pts
  **marcados PLACEHOLDER y NO activados**. Snapshot como **rúbrica v4** (versión
  nueva, no parche). Depende de R2 (techo AUTO) — no se activa en producción hasta
  que comité/alcalde aprueben la tabla.

### PR-8 — Testing + cascada
- Tests: sync (mock del servicio), PIP contra fixture de estrato conocido, endpoint
  de la capa, criterio de scoring (placeholder inactivo no altera puntajes).
- Gate de Pruebas → cascada `feat/* → desarrollo → Pruebas → produccion`.

---

## 6. Orden de arranque sugerido

**PR-0 (viabilidad PostGIS) → PR-2/PR-3 (modelo + sync + PIP validado contra 2 sedes)**
antes de tocar frontend o scoring. Justo lo que pediste: validar el point-in-polygon
contra sedes de estrato conocido antes de seguir.

## 8. R2 — Pregunta lista para el comité/alcalde (adelantar en paralelo)

El estrato oficial es **calculable automáticamente**, así que cuenta en el puntaje.
Falta una decisión política de **estructura** (no técnica). Tres opciones:

**Opción A — Criterio nuevo dentro de AUTO, subiendo el techo.**
AUTO pasa de 65 a `65 + N`. Simple y no le quita peso a ningún criterio actual.
Contra: cambia la escala; puntajes de ciclos previos no son comparables sin re-cálculo.

**Opción B — Criterio nuevo dentro de AUTO, redistribuyendo los 65.**
AUTO se queda en 65; se le restan `N` puntos a criterios existentes para dárselos a
estrato. Conserva la escala. Contra: hay que decidir **a qué criterio se le baja el
peso** — políticamente sensible.

**Opción C — Bono automático (recomendada para no reabrir los 65).**
`+N` puntos por operar en territorio de estrato bajo, análogo al bono de género
(+5). No toca la distribución AUTO 65 / COMITÉ 35; solo agrega un modificador
automático y auditable. Es el camino de menor fricción política.

En las tres, el comité debe aprobar además la **tabla estrato → puntos** y su
**dirección** (estrato 1 = más puntos, decreciendo hasta 6; y qué pasa con "sin
estrato"). Sin esa tabla el criterio queda inactivo (placeholder) en el código.

## 9. Resultados de validación (2026-07-08, rama `feat/estratificacion-ideca`)

Ejecutado PR-0, PR-2 y PR-3 **sin tocar `poblacion_kennedy` ni `innova_k`** (todo
en contenedores throwaway). Estado: **PR-0/2/3 en verde. PR-4→7 pendientes.**

**PR-0 — Viabilidad (go).**
- `shapely 2.1.2` instala desde wheel con **GEOS 3.13.1 embebido, sin system libs**;
  point-in-polygon correcto. → El backend default no necesita nada en el contenedor.
- Opción GeoDjango (si infra la prefiere): `apt` instala GDAL 3.10.3/GEOS/PROJ limpio
  en `python:3.10-slim`; `django.contrib.gis` importa OK. Queda como alternativa, **no
  requerida**: el backend PostGIS usa `ST_Contains` por **SQL crudo** (server-side),
  que no exige GDAL en el contenedor.
- **Consecuencia:** PR-1 se reduce a `CREATE EXTENSION` + columna `geom` (DDL, Sección B);
  **no hay que tocar Dockerfile** salvo agregar `shapely` a requirements (ya hecho).

**PR-2 — Código (listo, sin aplicar DDL).**
- Modelo `ManzanaEstrato` (geometry JSONB, managed=False) + `escuela.estrato_ideca`.
- Servicio `services/geo_estrato.py`: `estrato_en_punto()` única puerta, backends
  `shapely`/`postgis` intercambiables por env `ESTRATIFICACION_BACKEND`.
- Commands `sync_estratificacion` y `asignar_estrato_sedes` (dry-run por defecto).
- Endpoint `GET /geo/api/kennedy/estratificacion/`. DDL en `scripts/ddl_estratificacion_ideca.sql`.
- `py_compile` OK en los 7 archivos. Tests del núcleo PIP: **6/6** (incluye STRtree).

**PR-3 — Point-in-polygon contra sedes reales (gate, 8/8).**
- Servicio Catastro confirmado: capa "Manzanas de estrato", campos reales
  `CODIGO_MANZANA` + `ESTRATO` (auto-detectados por el sync), `maxRecordCount=2000`.
- Descarga del bbox Kennedy = **18 929 manzanas en 21.7 s** (payload real del sync).
  Distribución: estrato 0 (sin dato) 2456 · 1: 2748 · 2: 7762 · 3: 5455 · 4: 490 · 5: 18.
- 8 escuelas reales: **mi PIP shapely coincide 8/8 con el motor espacial de Catastro**,
  incluidas 2 sedes que caen fuera de toda manzana (None=None → sin estrato, caso R4).

**Pendiente para aplicar en BD (requiere Alex + backup):** Sección A del DDL
(`manzana_estrato` + `escuela.estrato_ideca`). Solo entonces el sync real y
`asignar_estrato_sedes --write` escriben. Hasta ahí, todo es dry-run/lectura.

## 7. Fuente de datos

Servicio ArcGIS REST de Catastro Bogotá, capa "Manzanas de estrato" (MapServer
layer 1). Campos: `ESTRATO` (0=sin estrato, 1–6), `CODIGO_MANZANA`, geometría de
polígono, más `FECHA_ACTO_ADMINISTRATIVO` / `ACTO_ADMINISTRATIVO` /
`NUMERO_ACTO_ADMINISTRATIVO` (la vigencia real, que se persiste por manzana).
Reproyección on-the-fly con `inSR=4326`. Vigencia: **Decreto 394 del 2017-07-28**.

**Ojo con el bbox.** `BBOX_KENNEDY` es un rectángulo con margen: de las 18.929
manzanas descargadas, solo **4.966 tocan Kennedy**. Las vecinas (Bosa, Puente
Aranda, Fontibón) se conservan porque sirven para asignar estrato a sedes del
borde, pero la capa del mapa se recorta al contorno de la localidad.

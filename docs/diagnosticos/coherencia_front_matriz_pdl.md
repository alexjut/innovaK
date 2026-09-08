# Coherencia del front con la Matriz PDL — diagnóstico

**Fecha:** 2026-09-07 · **Medido contra la BD, no contra los documentos.**

Pregunta que responde: *cuando alguien abre el front, ¿está viendo la Matriz de
Seguimiento PDL, o está viendo otra cosa con el rótulo «oficial»?*

Respuesta corta: **depende de la pantalla, y hoy no hay forma de saberlo desde
la interfaz.** Conviven tres fuentes y ninguna se identifica en pantalla.

---

## 1. Las tres fuentes que hoy conviven

| Fuente | Tablas | Estado medido |
|---|---|---|
| **Matriz PDL de la ALK** — la de verdad | `presu_sector` (13), `presu_objetivo_estrategico` (5), `presu_programa` (22), `presu_presupuesto_meta_vigencia` (312 = 78 metas × 4 vigencias) | Corte **2026-09-01**. Al día. |
| **Espejo SDP** — Datos Abiertos de Planeación | `sdp_meta_oficial` (280 filas) | `synced_at` **2026-07-23**. La fuente abierta está parada. 21 programas · 5 objetivos · 28 proyectos · 70 metas. |
| **Catálogos internos viejos** | `objetivo` (6 filas), `programas` (7 filas) | Datos de prueba de 2025. No son del PDL. |

**La brecha entre la Matriz y el espejo, medida:**

| | Matriz PDL | Espejo SDP | Falta en el espejo |
|---|---:|---:|---:|
| Programas | 22 | 21 | 1 |
| Objetivos | 5 | 5 | 0 |
| Proyectos | 31 | 28 | 3 |
| Metas | 78 | 70 | **8** |

La migración texto → catálogo en la tabla `metas` **sí está hecha**:
`programa_id` poblado 78/78, `sector_id` 77/78.

---

## 2. Pantalla por pantalla

### ✅ Ya leen la Matriz (correctas)

| Pantalla | Lee de |
|---|---|
| `/presupuesto/dashboard` → Top sectores | `presu_sector` vía `metas.sector_id` |
| `/presupuesto/dashboard` → Muro de subgrupos | `presu_sector` + `presu_presupuesto_meta_vigencia` |
| `/presupuesto/dashboard` → Objetivos / Perspectivas *(lo de Anderson)* | `presu_objetivo_estrategico` → `presu_programa` |
| `/presupuesto/sectores` — Avance por sector | `presu_sector` |
| Expediente del proyecto (apropiación, alerta) | `presu_presupuesto_meta_vigencia` |

### ❌ NO leen la Matriz (incoherentes)

| # | Pantalla | Card del hub | Lee de | Qué ve el usuario |
|---|---|---|---|---|
| ~~**C1**~~ | `/presupuesto/objetivos` | «Objetivos — Objetivos estratégicos» | ~~tabla `objetivo`~~ → **`presu_objetivo_estrategico`** | ✅ **Corregido 2026-09-07.** Antes: `objetivo prueba` · `prueba planig programa` · `prueba objetivo` · `prueba`. Ahora: los 5 ejes del PDL con sus 22 programas y 30 proyectos. |
| **C2** | `/presupuesto/plan-oficial` | «Plan oficial» | `sdp_meta_oficial` | El Plan con 21 programas y 70 metas: faltan 1 programa, 3 proyectos y 8 metas |
| **C3** | `/presupuesto/metas` | «Metas» | `sdp_meta_oficial` | 70 de 78 |
| **C4** | `/presupuesto/proyectos` | «Proyectos» | `sdp_meta_oficial` | 28 de 31 |
| **C5** | `/presupuesto/programas` | «Programas» | `sdp_meta_oficial` | 21 de 22 |
| ~~**C6**~~ | Rótulo «corte PDL» del muro y del expediente | — | ~~un solo corte~~ → **tres, uno por fuente** | ✅ **Corregido 2026-09-07.** Antes un rótulo único decía 23-jul al lado de cifras del 01-sep. Ahora: «Corte SECOP», «Matriz PDL · ALK» y «SDP · Datos Abiertos», cada cifra fechada con la suya. |

**C1 es el peor de la lista** y no es de grado: no es que muestre datos viejos,
es que muestra **otro catálogo**. La ruta `/presupuesto/objetivos` no existe en
`presupuesto.routes.ts`, así que cae al catch-all `:entidad`, que la sirve con
`ObjetivosView` → `core_catalogos.Objetivo`. Los objetivos estratégicos reales
del PDL sí están en el sistema y se pintan bien — pero solo dentro del
dashboard, no en la card que dice «Objetivos».

### ⚠️ Correcta, pero sin avisar

`/presupuesto/comparacion-sdp` **debe** leer del espejo: comparar contra lo
oficial es su propósito. Lo que falta es que diga en pantalla que ese lado de la
comparación está congelado desde el 23 de julio. Hoy se lee como si ambas
columnas estuvieran al mismo día.

---

## 3. Dos cadenas partidas

### ~~F1~~ · Formulación ↔ Contrato — ✅ resuelto 2026-09-07

`formulacion` tiene **6 filas**. `formulacion_contrato` tenía **0**.

El expediente ya cuelga las formulaciones **de la meta**
(`_formulaciones_por_meta`), así que se ve *«esta meta tiene la formulación
F-001»*. Lo que no existe en ninguna pantalla es lo contrario: *«este contrato
salió de la formulación F-001»*. El endpoint para engancharlos ya está
(`POST /presupuesto/api/formulaciones/<id>/contratos/`), pero nada en la
interfaz lo llama y la completitud del contrato no tiene campo de formulación
en ninguno de sus cuatro bloques.

Efecto: la cadena **Formulación → Contrato → Etapa → Seguimiento** se ve
completa por tramos y nunca de corrido.

### ~~F2~~ · La carga de matrices sin puerta — ✅ resuelto 2026-09-07

`presu_matriz_carga` está aplicada y en **0 filas**. El motor
(`services/matriz_carga.py`) está completo y probado —hash anti-duplicado,
diff previsualizable, aplicar/descartar, y la regla de que **nunca borra**: lo
que desaparece queda `activo=False` apuntando a la carga que lo retiró— pero
**solo corre por consola**. No hay API ni pantalla, así que hoy nadie fuera de
una terminal puede subir un corte nuevo.

Y hay un límite que importa para el alcance: el motor de carga cubre la
**jerarquía** (sectores, objetivos, programas). Las **cifras y metas** entran
por otro camino (`importar_matriz_pdl_alk`). Si la tarjeta se hace solo sobre el
motor actual, subir un corte donde solo cambiaron cifras diría «sin cambios».

---

## 4. Lo que NO está roto (para no tocarlo)

- **Registrar etapa por subgrupo**: funciona. `/app/mi-area/<área>` → contrato →
  «Completar» en Etapa contractual, con su endpoint (`api_contrato_etapa`) y
  doble candado (módulo + scope por subgrupo).
- **Los cuatro bloques de completitud** (Relaciones · Contratación · Financiero ·
  Seguimiento) y la fórmula plana `completos / aplicables`.
- **Las columnas de texto de `sdp_meta_oficial`** (`total_programado`, etc.):
  copian los nombres de la fuente y las usa el sync nocturno. Renombrarlas
  rompe la trazabilidad del espejo.
- Las columnas de texto redundantes en `metas` (`nomprog`, `codprog`, `sector`,
  `objetivo_estrategico`) al lado de sus FKs: es deuda, no incoherencia. No
  alimentan ninguna pantalla.

---

## 5. Orden de ataque sugerido

| | Qué | Estado |
|---|---|---|
| 1 | **C1** — apuntar «Objetivos» al catálogo del PDL | ✅ **Hecho** (2026-09-07). Ruta propia antes del catch-all + retirada la entrada que llevaba a la tabla de prueba. |
| 2 | **C6** — que el rótulo de corte salga de la fuente que se está mostrando | ✅ **Hecho** (2026-09-07). Tres cortes en el muro y en el cockpit, con el helper compartido `_corte_matriz_pdl`. |
| 3 | **C2–C5** — las cuatro listas «oficiales» a la Matriz | ✅ **Hecho.** Servicio `plan_matriz.py`; el espejo baja a columna de contraste y la jerarquía se endereza a Objetivo → Programa → Proyecto → Meta. |
| 4 | **F2** — la tarjeta de carga (jerarquía **+ cifras**) | ✅ **Hecho.** `/app/presupuesto/matriz`: subir → previsualizar las 4 fases → aplicar o descartar. |
| 5 | **F1** — formulación dentro del contrato | ✅ **Hecho.** Campo en Relaciones + `enlazar_a_contrato` + selector en Mi Área. |

**El plan de coherencia quedó cerrado el 2026-09-07.**

> Y al cerrarlo apareció que el problema era más ancho que estas cinco
> pantallas. El barrido completo —30 defectos confirmados, dos causas
> repetidas— está en
> [`auditoria_fuentes_matriz_pdl.md`](./auditoria_fuentes_matriz_pdl.md).


---

## 6. Bitácora

### 2026-09-07 — C1 y C6 corregidos

**C1 · «Objetivos» apuntaba al catálogo del Banco de Iniciativas.**
La card no tenía ruta propia y caía al catch-all `:entidad`. Se agregó
`objetivos` en `presupuesto.routes.ts` **antes** del catch-all, apuntando a
`ObjetivosPdlComponent`, que consume `/presupuesto/api/objetivos-estrategicos/`
y compone los MISMOS dos componentes que ya usa el cockpit — no recalcula
nada, para que el resumen de un objetivo no pueda decir una cifra acá y otra
allá. Se retiró `objetivos` del catch-all (config, campos editables e icono)
para que no quede ninguna puerta a la tabla de prueba.

De paso, el aplanado de `subgrupo`/`dependencia` —que el backend manda como
`{id, nombre}`— salió del dashboard a `objetivos.types.ts::aplanarObjetivos`:
con dos pantallas leyendo el mismo endpoint, dejarlo en una habría hecho que
la otra mostrara «área ejecutora» vacía por una razón invisible.

**C6 · un solo corte para tres fuentes.**
Helper nuevo `_corte_matriz_pdl` en `muro_subgrupos.py`, que el expediente
importa por la vía que ya existía entre los dos servicios: dos pantallas que
muestran la misma apropiación no pueden fecharla distinto. Publica dos fechas
y no una, porque `corte_oficial` («¿de cuándo son estos datos?») y `cargado_at`
(«¿desde cuándo los tenemos?») contestan preguntas distintas; colapsarlas
obligaría a elegir cuál mentir. `corte_oficial` viaja en `null` mientras el
corte vigente haya entrado por consola —`presu_matriz_carga` nació después—:
deducirlo de la fecha de carga sería inventar.

**Un test que estaba mal, encontrado al pasar.**
`test_no_se_puede_tocar_el_contrato_de_otra_area` fallaba con el scope
funcionando: el PATCH se rechazaba con 403 y la aserción final se caía igual,
porque exigía `etapa_codigo IS NULL` en vez de «no cambió» — y dos contratos
ya tenían etapa registrada desde Mi Área. Ahora compara contra el valor previo
y manda una etapa **distinta** de la que el contrato tiene, sacada del catálogo
vivo: con el código fijo anterior, el test quedaba ciego justo cuando el
contrato ya valía ese mismo código.

**Verificación:** 1490 tests OK (7 skipped) · build con `--base-href=/app/`
comprobado (`<base href="/app/">`) · `/app/` 200 · endpoints 401 sin token.


### 2026-09-07 (cierre) — C2-C5, la tarjeta de carga y la formulación

**Las cuatro listas «oficiales» pasaron a la Matriz** (`plan_matriz.py`). De
70 metas a 78, de 28 proyectos a 30, de 21 programas a 22. El espejo baja a
columna de contraste y las 10 metas que no tienen par en Datos Abiertos se
marcan. La jerarquía se enderezó: hay una FK (`presu_programa.objetivo_id`)
que dice que un objetivo agrupa programas, y la pantalla los anidaba al revés.

La trampa de este cambio era la agregación: en el espejo `total_programado` se
REPLICA en las 4 vigencias y sumarlo infla ×10; en la Matriz `proyectado_pdl`
VARÍA por vigencia en 73 de 78 metas y su suma reproduce las cifras publicadas.
Dos tablas parecidas que se agregan al revés.

**Una inconsistencia que reportó Alex y resultó ser el mismo problema.** El
proyecto 2706 salía «Ejecutada» en el listado y «Crítico» en el expediente. No
era un bug de cálculo: la alerta venía de la Matriz y el semáforo del girado de
SECOP, que no registra giros en esos contratos mientras la Matriz reporta
$1.400.257.732. Y el hueco era mayor: SECOP daba base para calificar **7 de 31**
proyectos y la Matriz para **29** — los otros 24 salían en gris, y ese gris se
leía como «sin problema» cuando era «sin datos».

Decisión de Alex: el semáforo califica con la Matriz, SECOP queda como
anotación cuando discrepa, y los dos juicios se rotulan por lo que miden
(«Metas ejecutadas» vs «Ejecución de plata»). Pueden diferir sin contradecirse:
son plata y unidades.

**La tarjeta de carga** (`/app/presupuesto/matriz`) orquesta las cuatro fases
—jerarquía, cifras, estructura y alertas— sobre el mismo Excel. Los dos
importadores no se reescribieron: llevan meses de correcciones medidas encima
y copiarlos habría creado una segunda implementación que se desincroniza. El
test de aceptación —subir el corte que ya está da diff CERO— pasa, y el
detector se probó al revés en transacciones revertidas.

**La formulación entró al expediente del contrato.** Campo en Relaciones +
`enlazar_a_contrato` (el contrato ya existe; hermana de `enlazar_desde_secop`,
que arranca en el espejo) + selector en Mi Área. El CIA 773/2025 pasó de
«Relaciones 3/3 · 6 pendientes» a «3/4 · 7 pendientes»: el hueco estaba y
ahora se ve.

**Verificación:** 1510 tests OK (7 skipped) · 5 commits cascadeados a
producción · build con `--base-href=/app/` comprobado en cada uno.

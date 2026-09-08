# Auditoría: qué NO sale de la Matriz PDL

**2026-09-07.** Barrido de innovaK buscando dónde se muestra o calcula algo con
una fuente que **no** es la Matriz de Seguimiento PDL, teniendo la Matriz el dato.

Nace de la regla que fijó Alex ese día —**«la base de todo es la Matriz; todo
debe estar coherente con eso»**— y del caso que la disparó: el proyecto 2706,
que se leía «Ejecutada» en una pantalla y «Crítico» en otra.

> El detalle íntegro de cada hallazgo —evidencia completa, veredicto de la
> verificación y el arreglo propuesto con su código— está en
> [`auditoria_fuentes_matriz_pdl.datos.json`](./auditoria_fuentes_matriz_pdl.datos.json).
> Este documento es el mapa; ese archivo es el terreno.

---

## Método, y qué tan confiable es

Cinco barridos independientes con lentes distintas —avance físico, plata,
jerarquía, cortes y fechas, juicios de estado— y **verificación adversarial por
hallazgo**: cada uno se volvió a mirar con voluntad de refutarlo, abriendo el
archivo y contando filas en la base. Lo que no se sostuvo con cifras medidas se
descartó.

| | |
|---|---:|
| Hallazgos brutos | 32 |
| **Confirmados** | **30** |
| Descartados al verificar | 2 |
| Severidad alta / media | 23 / 7 |

**No son 30 problemas distintos: son dos, repetidos.** Por eso el orden de
ataque no es esta lista, es la raíz.

---

## Los dos defectos

### A · El avance físico lee la fuente que cubre 6 de 77 (18 hallazgos)

El avance de metas —unidades, no pesos— se calculaba en **siete lugares
distintos**, cada uno con su SQL, todos sobre `presu_avance_ind_periodo`: los
avances de KPI que se registran a mano acá. **6 de 77 KPI activos, 9 filas, 3
de 47 subgrupos.** La Matriz trae `cumplimiento_pct` para **76 de 78 metas**.

Lo grave no es el hueco: es que el vacío se pintaba de rojo y de 0 %, y eso
**acusa al área de no ejecutar** algo que la propia Alcaldía ya reportó.

### B · Mezcla de fuentes en el mismo recuadro (12 hallazgos)

Un porcentaje que no cierra con las cifras que tiene al lado, un rótulo de
corte que no corresponde al dato que acompaña, o una pantalla titulada «Fuente:
Matriz» que saca su plata del espejo SDP.

---

## Lo que NO es un defecto

La verificación descartó hallazgos por esto. Conviene tenerlo a mano antes de
«arreglar» algo que está bien:

- **`sdp_meta_oficial` como columna de contraste es correcto.** El defecto es
  usarla como BASE, no mostrarla al lado.
- **`/presupuesto/comparacion-sdp` DEBE leer el espejo**: comparar contra lo que
  publica el Distrito es su propósito.
- Las columnas `total_programado` / `valor_programado` / `magnitud_programada`
  conservan los nombres de la fuente a propósito — trazabilidad del espejo, y
  las mapea el sync nocturno.
- **`$0` no es «sin dato»**: un cero medido es un dato y se pinta como cifra.
- **Un vacío no se pinta de rojo**: sin fuente, se deja sin calificar.

---

## Mapa

### A · Avance físico

| # | Hallazgo | Sitio | Sev. |
|---|---|---|---|
| 1 | ✅ El «Avance físico» del muro de áreas sale vacío en 14 de 17 subgrupos, y la tarjeta acusa al… | `presupuesto/services/muro_subgrupos.py:182` | alta |
| 2 | El donut «Metas del plan» del dashboard clasifica 73 de 78 metas como «Sin avance» | `dashboard/services/kpis_presupuesto.py:900` | alta |
| 3 | La página «Avance por sector» pinta 16 de 19 sectores en 0 % y en color de bajo desempeño | `dashboard/services/kpis_presupuesto.py:359` | alta |
| 4 | En Proyecto 360° las barras de 70 de los 77 KPIs se dibujan rojas en 0 % en vez de quedar sin… | `presupuesto/services/avance.py:56` | alta |
| 5 | El gráfico «Top sectores» del dashboard sale con todas las barras en rojo, cinco de ellas en 0… | `dashboard/services/kpis_presupuesto.py:299` | alta |
| 6 | La columna «Avance oficial» del Catálogo de Metas lee el espejo SDP parado y muestra «0 / N»… | `presupuesto/api/views.py:566` | alta |
| 7 | El tile «Avance físico · ponderado» del cockpit habla por todo el PDL con 4 contratos de una… | `dashboard/services/cockpit_presupuesto.py:66` | alta |
| 8 | «Avance por sector» pinta 16 de 19 filas en 0,0 % y las 19 en rojo, leyendo los avances… | `dashboard/services/kpis_presupuesto.py:386` | alta |
| 9 | El gráfico «Top sectores» del dashboard sale con las 8 barras en rojo y deja 5 de los 13… | `dashboard/services/kpis_presupuesto.py:337` | alta |
| 10 | La columna «Avance oficial» del catálogo de Metas lee el espejo SDP parado y suma las cuatro… | `presupuesto/api/views.py:566` | alta |
| 11 | «Avance por sector» se subtitula «alineado con el Visor SDP-PDL» pero calcula con los avances… | `front/presupuesto/sectores.component.ts:36` | alta |
| 12 | En el mismo panel lateral del cockpit conviven dos veredictos opuestos sobre las mismas 78… | `front/presupuesto/presupuesto-dashboard.component.ts:188` | alta |
| 13 | «Avance por sector» pinta de rojo 16 de 19 sectores con un 0,0 % que no es un cero medido: el… | `dashboard/services/kpis_presupuesto.py:359` | alta |
| 14 | ✅ El muro de subgrupos deja «Avance físico: Sin avance cargado» en 43 de 46 tarjetas y lo lista… | `presupuesto/services/muro_subgrupos.py:182` | alta |
| 15 | El detalle de un KPI muestra «0 % Cumplimiento» en rojo cuando lo que pasa es que nadie… | `front/presupuesto/presupuesto-detail.component.ts:41` | alta |
| 16 | Las tarjetas del Plan oficial y de las listas «del Plan» ponen plata acumulada 2025+2026 al… | `front/presupuesto/plan-oficial.component.ts:85` | media |
| 17 | La línea de contraste rotulada «Datos Abiertos SDP» de la tarjeta de meta imprime el entregado… | `presupuesto/services/plan_matriz.py:78` | media |
| 18 | En «Plan oficial» y «Metas del Plan» la baldosa de alerta pinta el valor crudo de la columna y… | `front/presupuesto/plan-oficial.component.ts:88` | media |

### B · Mezcla de fuentes y jerarquía

| # | Hallazgo | Sitio | Sev. |
|---|---|---|---|
| 19 | La fila de KPI que encabeza el cockpit encadena tres fuentes: Apropiación de la Matriz,… | `presupuesto/services/muro_subgrupos.py:1008` | alta |
| 20 | «Ejecución financiera 29,7 % · comprometido / programado» arma el numerador con dos fuentes y… | `front/presupuesto/objetivos/objetivos.types.ts:138` | alta |
| 21 | El tile «Contratado» de Mi Área muestra $0 en 12 de las 16 áreas que sí tienen plata… | `presupuesto/services/panel_area.py:225` | alta |
| 22 | En la jerarquía de perspectivas la tarjeta padre muestra proyectado de SDP y sus programas… | `front/presupuesto/objetivos/perspectivas-explorador.component.ts:138` | alta |
| 23 | El detalle de programa muestra Asignado / Comprometido / Disponible en $0 porque suma sobre… | `presupuesto/services/metrics.py:190` | alta |
| 24 | La página de Objetivos se rotula «Fuente: Matriz de Seguimiento PDL» pero su «Presupuesto… | `front/presupuesto/objetivos/objetivos-resumen.component.ts:165` | alta |
| 25 | El selector de vigencia del cockpit gobierna solo 1 de los 4 tiles: al elegir 2026 el Avance… | `front/presupuesto/presupuesto-dashboard.component.ts:695` | alta |
| 26 | La fila de cada programa dice «N metas» pero cuenta PROYECTOS con alerta: la pantalla suma 30… | `front/presupuesto/objetivos/perspectivas-explorador.component.html:112` | alta |
| 27 | El panel de subgrupo muestra «Valor contratado $0» en las mismas 12 áreas y además contradice… | `presupuesto/services/panel_subgrupo.py:150` | media |
| 28 | Los insights de Festivales muestran Asignado, Ejecutado y Disponible en $0 porque leen dos… | `festivales/api/views.py:507` | media |
| 29 | El expediente del proyecto lee el Programa del PDL de la tabla vieja `programas`, y 26 de 31… | `presupuesto/services/expediente_proyecto.py:400` | media |
| 30 | La vista 360° del proyecto omite el programa en 26 de 31 proyectos: el serializer resuelve… | `presupuesto/api/serializers.py:63` | media |


---

## Detalle · A · Avance físico

### 1. El «Avance físico» del muro de áreas sale vacío en 14 de 17 subgrupos, y la tarjeta acusa al área de no reportar

> ✅ **Cerrado el 2026-09-07** — ver la bitácora al final.

`apps/presupuesto/services/muro_subgrupos.py:182` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto (muro de áreas) la línea «Avance físico» dice «Sin avance cargado» en 14 de las 17 tarjetas, y debajo la tarjeta lista un pendiente que dice «Indicadores sin ningún avance reportado · Por eso el avance sale vacío y no en 0%» — o sea culpa al área de no haber reportado algo que la propia Alcaldía ya reportó en la Matriz. Es además una mezcla dentro del mismo recuadro: la plata de esa misma tarjeta…

**Lee** `presu_avance_ind_periodo.magnitud_aportada / presu_indicador_meta_proyecto.meta_magnitud…` · **lo tiene** `presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): magnitud_contratada, magnitud_ejecutada y…`

**Cobertura:** `presu_avance_ind_periodo`: 9 filas (todas activas), 6 de 77 indicadores activos, 3 de 17 subgrupos con avance calculable → 14 de 17 tarjetas… → `presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk'): 76 de 78 metas con `cumplimiento_pct`, `magnitud_ejecutada` y `magnitud_contratada` → 17…

**Arreglo:** Archivo: `/home/innova/Proyectos/innovaK/apps/presupuesto/services/muro_subgrupos.py`. 1. En `_avance_por_subgrupo` (líneas 182-230), cambiar la BASE del avance físico a la Matriz, agregando el cruce por meta y quedándose con la vigencia más reciente que tenga cumplimiento (nunca sumar porcentajes de años distintos). El join está verificado y da 17/17: ```sql FROM meta_proyecto mp JOIN proyecto p ON p.id = mp.proyecto_id LEFT JOIN metas m ON m.codigo =…

---

### 2. El donut «Metas del plan» del dashboard clasifica 73 de 78 metas como «Sin avance»

`apps/dashboard/services/kpis_presupuesto.py:900` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/dashboard el panel «Metas del plan» muestra Cumplidas 0, En progreso 5, En riesgo 0 y Sin avance 73, con el donut casi entero en gris. El gris se lee como «el Plan no arrancó», cuando la Matriz dice que 21 metas ya están al 100 % o más y otras 15 van en camino. El mismo cero viaja al orden de la lista de /app/presupuesto/metas, que ordena por ese porcentaje.

**Lee** `metas_con_progreso(): SUM(presu_avance_ind_periodo.magnitud_aportada) /…` · **lo tiene** `presu_presupuesto_meta_vigencia (matriz_pdl_alk).cumplimiento_pct por codigo_meta`

**Cobertura:** presu_avance_ind_periodo: 5 de 78 metas (6 %) tienen algún avance registrado. Las otras 73 salen con porcentaje 0,0 y estado 'sin_avance'. Medido… → presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): 312 filas meta×vigencia, 78 codigo_meta distintos, 76 metas con cumplimiento_pct (97 %).…

**Arreglo:** Archivo: apps/dashboard/services/kpis_presupuesto.py, función metas_con_progreso() (línea 900). 1) Agregar al SQL un LEFT JOIN lateral a la Matriz por codigo_meta —la llave es m.codigo_meta (varchar), no m.codigo— tomando el cumplimiento de la VIGENCIA MÁS RECIENTE con dato, no la suma ni el promedio. No escribir ese criterio de nuevo: ya existe y está razonado en apps/presupuesto/services/plan_matriz.py::_SQL_CIFRAS_META, que hace exactamente…

---

### 3. La página «Avance por sector» pinta 16 de 19 sectores en 0 % y en color de bajo desempeño

`apps/dashboard/services/kpis_presupuesto.py:359` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/sectores («Avance por sector») 16 de 19 barras marcan 0 % y las 19 se pintan con la clase 'bajo' porque nivel(pct) manda todo lo <50 a bajo (sectores.component.ts:138). Un vacío queda pintado como bajo desempeño de 16 áreas, que es justo lo que la regla del muro prohíbe. La tabla de abajo repite el mismo 0 % como si fuera una medición.

**Lee** `avance_por_subgrupo(): SUM(presu_avance_ind_periodo.magnitud_aportada) /…` · **lo tiene** `presu_presupuesto_meta_vigencia (matriz_pdl_alk).cumplimiento_pct / magnitud_ejecutada de las metas de cada…`

**Cobertura:** `presu_avance_ind_periodo` (fuente que usa hoy `avance_por_subgrupo`, apps/dashboard/services/kpis_presupuesto.py:359-421): **9 filas activas que… → `presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk'): 312 filas, 78 metas × 4 vigencias. **76 de las 78 metas traen `cumplimiento_pct` y…

**Arreglo:** **Archivo:** `apps/dashboard/services/kpis_presupuesto.py`, función `avance_por_subgrupo()` (línea 359). 1. Cambiar el numerador: en vez del CTE `kpi` que suma `presu_avance_ind_periodo.magnitud_aportada`, agregar por subgrupo desde la Matriz, cruzando `proyecto → meta_proyecto → metas.codigo_meta ⇄ presu_presupuesto_meta_vigencia.codigo_meta` con `fuente='matriz_pdl_alk'`, sumando `magnitud_ejecutada` y `magnitud_contratada`. 2. **Usar el par de la…

---

### 4. En Proyecto 360° las barras de 70 de los 77 KPIs se dibujan rojas en 0 % en vez de quedar sin calificar

`apps/presupuesto/services/avance.py:56` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/proyectos/<id> (Proyecto 360°) cada KPI muestra «Avance: 0» y una barra roja al 0 % — kpiClass() manda todo lo <50 a 'red' (proyecto-360.component.ts:775). El null que la UI sabe ocultar nunca llega, porque el servicio devuelve 0.0. La misma cifra alimenta «avance_promedio» del DashboardPresupuestoView (api/views.py:943), que promedia esos ceros y publica un «% avance ponderado KPIs» que no…

**Lee** `calcular_avance(): AvanceIndicador (presu_avance_ind_periodo) sobre indicador.meta_magnitud; devuelve pct =…` · **lo tiene** `presu_presupuesto_meta_vigencia (matriz_pdl_alk).cumplimiento_pct y magnitud_ejecutada de la meta a la que…`

**Cobertura:** `presu_avance_ind_periodo`: 6 de los 76 KPIs activos con objetivo > 0 (7,9 %). Los otros 70 no tienen ni una fila de avance activa; el servicio igual… → `presu_presupuesto_meta_vigencia` (fuente `matriz_pdl_alk`): 76 de 78 metas con `cumplimiento_pct` y `magnitud_ejecutada` (vigencia 2025). Los 70…

**Arreglo:** Tres cambios; el primero es el que arregla todas las pantallas de una, porque `calcular_avance()` ya es la fuente única (la usan el 360°, `IndicadorListSerializer` y el dashboard). 1. **`apps/presupuesto/services/avance.py`** (núcleo, líneas 46-65). Agregar un campo `fuente: str` al dataclass `Avance` y un fallback a la Matriz cuando `qs.count() == 0`: - Resolver `indicador.meta_proyecto.meta.codigo_meta` y buscar en `presu_presupuesto_meta_vigencia` con…

---

### 5. El gráfico «Top sectores» del dashboard sale con todas las barras en rojo, cinco de ellas en 0 %

`apps/dashboard/services/kpis_presupuesto.py:299` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/dashboard la barra horizontal «% Avance» por sector sale entera en rojo: el color se asigna por umbral (≥80 verde, ≥50 amarillo, resto rojo) en presupuesto-dashboard.component.ts:906-909, y ninguna barra llega a 50. Cinco sectores del PDL aparecen exactamente en 0 %, lo que se lee como que esos sectores no han ejecutado nada del Plan.

**Lee** `top_sectores_avance(): SUM(presu_avance_ind_periodo.magnitud_aportada) /…` · **lo tiene** `presu_presupuesto_meta_vigencia (matriz_pdl_alk).cumplimiento_pct de las metas de cada sector del PDL`

**Cobertura:** `presu_avance_ind_periodo`: **6 de 77 KPIs activos** tienen al menos una fila de avance (7,8 %). Por sector: solo **3 de 13 sectores** tienen algún… → `presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk'): **76 de 78 metas** tienen `cumplimiento_pct` (97,4 %), todas de vigencia 2025. Por…

**Arreglo:** Archivo: `apps/dashboard/services/kpis_presupuesto.py`, función `top_sectores_avance()` (líneas 299-355). 1. Reemplazar el `LEFT JOIN presu_avance_ind_periodo` + `SUM(av.magnitud_aportada)/SUM(imp.meta_magnitud)` por la Matriz. La llave de cruce que funciona (medida) es `(metas.codigo_meta, metas.proyecto_codigo)` contra `(v.codigo_meta, v.proyecto_codigo)` con `v.fuente='matriz_pdl_alk'`; el sector sigue saliendo de `metas.sector_id → presu_sector`, que…

---

### 6. La columna «Avance oficial» del Catálogo de Metas lee el espejo SDP parado y muestra «0 / N» en 32 metas que la Matriz reporta ejecutadas

`apps/presupuesto/api/views.py:566` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/metas la única columna de avance de la pantalla se llama «Avance oficial» y muestra «0 / 30.000», «0 / 10.000», «0 / 4.000»… o un guion. El usuario lee el catálogo completo del Plan y concluye que no se ha entregado nada, cuando la Matriz —la base— sí registra magnitud ejecutada para esas mismas metas. No hay columna de la Matriz al lado que permita el contraste.

**Lee** `MetaListCreateView.get(): SUM(sdp_meta_oficial.magnitud_entregada) /…` · **lo tiene** `presu_presupuesto_meta_vigencia (matriz_pdl_alk).magnitud_ejecutada y magnitud_contratada por codigo_meta`

**Cobertura:** sdp_meta_oficial (espejo parado, max(synced_at) = 2026-07-23, 280 filas / 70 plan_meta_producto_id): de las 78 metas del catálogo, 68 cruzan y traen… → presu_presupuesto_meta_vigencia con fuente='matriz_pdl_alk' (312 filas meta×vigencia, 78 codigo_meta distintos): 76 de las 78 metas del catálogo…

**Arreglo:** 1) Backend — apps/presupuesto/api/views.py, MetasCatalogoView.get() (líneas 549-592): agregar un segundo LEFT JOIN a presu_presupuesto_meta_vigencia con fuente='matriz_pdl_alk' agregado por codigo_meta sobre metas.codigo_meta, y construir con eso la columna base de avance (magnitud_ejecutada / magnitud_contratada, más cumplimiento_pct para el semáforo). NO escribir una agregación nueva: apps/presupuesto/services/plan_matriz.py:52-69 ya la tiene resuelta,…

---

### 7. El tile «Avance físico · ponderado» del cockpit habla por todo el PDL con 4 contratos de una sola área

`apps/dashboard/services/cockpit_presupuesto.py:66` · cobertura · severidad **alta**

**Se ve así.** El cuarto tile de la fila de plata del cockpit dice «72,2 % · Avance físico ponderado» al lado de un girado que es el 1,3 % de lo apropiado. La lectura obvia —«el Plan va ejecutado en tres cuartas partes»— la sostienen cuatro contratos de Infraestructura, uno de ellos de la vigencia 2015. Ningún rótulo dice sobre cuántos contratos se calculó, a diferencia de los tiles de Comprometido y Girado que sí llevan su…

**Lee** `SUM(contrato.valor * contrato.ejecucion) / SUM(contrato.valor) sobre los contratos que tienen las dos…` · **lo tiene** `presu_presupuesto_meta_vigencia: la ejecución de plata verificable es girado/comprometido de la Matriz (45,0…`

**Cobertura:** 4 de 25 contratos tienen `ejecucion` no nula — son los únicos que entran al ponderado: · 807/2025 · $4.276.732.038 · 80 % · proyecto 2574 ·… → `presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk', 312 filas): `magnitud_contratada`, `magnitud_ejecutada` y `cumplimiento_pct` están los…

**Arreglo:** Dos cambios, uno por lado. El principio: el tile titular del cockpit se calcula con la Matriz, y el ponderado por contratos sobrevive solo donde declare su base. 1) `apps/dashboard/services/cockpit_presupuesto.py` — en `ejecucion_financiera()`: · Agregar al SELECT de la línea 53 el conteo de la base: `COUNT(CASE WHEN ejecucion IS NOT NULL AND valor IS NOT NULL THEN 1 END)`, y devolver junto a `pct_ejecucion` (línea 140) un `"ejecucion_cobertura": {"con":…

---

### 8. «Avance por sector» pinta 16 de 19 filas en 0,0 % y las 19 en rojo, leyendo los avances internos (6 de 77 KPIs) teniendo la Matriz cumplimiento para las 78 metas

`apps/dashboard/services/kpis_presupuesto.py:386` · cobertura · severidad **alta**

**Se ve así.** La página `/presupuesto/sectores` («Avance por sector») muestra una lista donde 16 de 19 sectores dicen 0 % y las 19 barras están pintadas de rojo (`nivel()` devuelve 'bajo' → `#dc2626` para todo pct<50, `sectores.component.ts:139-141`). Un área que la Matriz reporta con la meta cumplida al 120 % aparece en rojo con 0 %. Es exactamente el caso de «un vacío pintado de rojo»: no hay con qué calificar y se está…

**Lee** ``avance_por_subgrupo()` calcula el % sumando `presu_avance_ind_periodo.magnitud_aportada` sobre…` · **lo tiene** ``presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk'): `cumplimiento_pct`, `magnitud_contratada` y…`

**Cobertura:** presu_avance_ind_periodo: 6 de 77 KPIs activos tienen avance registrado. En el listado de la pantalla eso son 3 de 19 filas con dato (Infraestructura… → presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): cumplimiento_pct no nulo para 76 metas distintas y magnitud_contratada/magnitud_ejecutada…

**Arreglo:** Backend — apps/dashboard/services/kpis_presupuesto.py, función avance_por_subgrupo() (líneas 359-425): cambiar la base del porcentaje a la Matriz. Cruzar proyecto -> meta_proyecto -> metas.codigo_meta contra presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'), tomando la ÚLTIMA vigencia con dato con el patrón que ya usa el repo: (ARRAY_AGG(cumplimiento_pct ORDER BY vigencia DESC) FILTER (WHERE cumplimiento_pct IS NOT NULL))[1] — está en…

---

### 9. El gráfico «Top sectores» del dashboard sale con las 8 barras en rojo y deja 5 de los 13 sectores del PDL fuera del ranking

`apps/dashboard/services/kpis_presupuesto.py:337` · cobertura · severidad **alta**

**Se ve así.** En `/presupuesto/dashboard` la barra horizontal «Top sectores» muestra 8 barras y las 8 están en rojo (`presupuesto-dashboard.component.ts:905-907`: `porcentaje >= 80 ? verde : >= 50 ? amarillo : #DC2626`). Peor: como el orden es por avance interno y 5 sectores empatan en cero, cuáles entran al «top 8» es arbitrario, y AMBIENTE, SALUD, SEGURIDAD·CONVIVENCIA·JUSTICIA, AMBIENTE/HÁBITAT y DESARROLLO ECONÓMICO —que…

**Lee** ``top_sectores_avance()` ya agrupa bien por el catálogo (`presu_sector` vía `metas.sector_id`), pero el NÚMERO…` · **lo tiene** ``presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk').`cumplimiento_pct` por meta, agregable por…`

**Cobertura:** `presu_avance_ind_periodo`: 6 de 77 KPIs activos tienen algún avance registrado (71 sin ninguno). En el gráfico eso deja solo 3 de 13 sectores con un… → `presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk'): 312 filas, 78 metas distintas, **76 con `cumplimiento_pct`**. Cruzadas por `codigo_meta`…

**Arreglo:** Archivo: `/home/innova/Proyectos/innovaK/apps/dashboard/services/kpis_presupuesto.py`, función `top_sectores_avance()` (líneas 299-356). 1. Cambiar la fuente del número. Reemplazar el `LEFT JOIN presu_avance_ind_periodo av` + `SUM(av.magnitud_aportada)` por un CTE de cumplimiento de la Matriz, con el mismo patrón que ya usan `plan_matriz.py:55-67` y `expediente_proyecto.py:280-293` (última vigencia con dato por meta, NO promedio entre años): ```sql WITH…

---

### 10. La columna «Avance oficial» del catálogo de Metas lee el espejo SDP parado y suma las cuatro vigencias de un valor que el espejo replica: la meta 26101 sale con 154.804 entregadas cuando la fuente publica 38.701

`apps/presupuesto/api/views.py:566` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/metas la columna «Avance oficial» muestra «154.804 / 24.700» para la meta 26101 —un 627 % que ningún acto administrativo respalda— y «23.304 / 23.304» para la 26103, que es de anualización «Constante» y cuyo dato real es 5.826/5.826. Otras 10 metas salen con «—» aunque la Matriz sí las califica. No hay ninguna fecha de corte junto a la columna, así que el usuario no puede saber que «oficial»…

**Lee** `sdp_meta_oficial con SUM(magnitud_programada) y SUM(magnitud_entregada) agrupado por plan_meta_producto_id…` · **lo tiene** `presu_presupuesto_meta_vigencia.cumplimiento_pct y .magnitud_ejecutada / .magnitud_contratada…`

**Cobertura:** `sdp_meta_oficial` (espejo SDP parado, synced_at 2026-07-23): imprime cifra para **68 de las 78** metas del catálogo, y «—» para 10. Y de esas 68,… → `presu_presupuesto_meta_vigencia` (fuente `matriz_pdl_alk`, corte 2026-09-02): 312 filas sobre 78 metas, con `cumplimiento_pct`, `magnitud_ejecutada`…

**Arreglo:** **a) `apps/presupuesto/api/views.py:558-570` — que la base sea la Matriz.** Agregar un `LEFT JOIN` a `presu_presupuesto_meta_vigencia` sobre `codigo_meta` con `fuente='matriz_pdl_alk'`, agregando `SUM(magnitud_ejecutada) / SUM(magnitud_contratada)` (las vigencias sin ejecutar vienen NULL, así que suman limpio: en 26101 solo 2025 trae dato), y emitir ese par como el avance. Cubre 76 en vez de 68 y sale del corte del 2026-09-02. **b) Mismo archivo —…

---

### 11. «Avance por sector» se subtitula «alineado con el Visor SDP-PDL» pero calcula con los avances internos de innovaK, que cubren 6 de 77 KPIs: 16 de 19 sectores salen en 0,0 %

`frontend/src/app/features/presupuesto/sectores.component.ts:36` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/sectores el encabezado promete alineación con el Visor SDP-PDL y luego pinta 16 barras vacías con «0,0 %»: Seguridad 0 % sobre una meta de 247, Ambiente 0 % sobre 26.493, Mujer 0 % sobre 11.870, Salud 0 % sobre 1.820, Deporte 0 % sobre 8.160. Un cero no distingue «el área no ejecutó» de «nadie registró el avance en innovaK», y bajo un rótulo que invoca al Distrito se lee como que el Distrito…

**Lee** `avance_por_subgrupo() (apps/dashboard/services/kpis_presupuesto.py:359) suma…` · **lo tiene** `presu_presupuesto_meta_vigencia.cumplimiento_pct y .magnitud_ejecutada / .magnitud_contratada…`

**Cobertura:** 6 de 77 KPIs activos tienen avance registrado (9 filas en presu_avance_ind_periodo, 6 origen EVENTO y 3 MANUAL) → solo 3 de 19 sectores salen… → 76 de 78 metas con cumplimiento_pct y 76 con magnitud_ejecutada (312 filas meta×vigencia, fuente='matriz_pdl_alk') → 17 de 19 sectores quedarían…

**Arreglo:** Dos archivos. 1) apps/dashboard/services/kpis_presupuesto.py — `avance_por_subgrupo()` (línea 359). Hoy el CTE `kpi` calcula avance/meta desde `presu_avance_ind_periodo` sobre `presu_indicador_meta_proyecto.meta_magnitud`. Cambiar la BASE a la Matriz: unir `presu_presupuesto_meta_vigencia v` (fuente='matriz_pdl_alk') por `v.codigo_meta = metas.codigo_meta` → `meta_proyecto.meta_id = metas.codigo` → `proyecto.id` → `proyecto.subgrupo_id`, y agregar por…

---

### 12. En el mismo panel lateral del cockpit conviven dos veredictos opuestos sobre las mismas 78 metas: «Alertas» (Matriz) dice 21 ejecutadas, «Metas del plan» dice 73 sin avance

`frontend/src/app/features/presupuesto/presupuesto-dashboard.component.ts:188` · mezcla · severidad **alta**

**Se ve así.** En /app/presupuesto/dashboard, dentro de la misma barra lateral y a un centímetro de distancia: el panel «Alertas que requieren atención» muestra 76 metas con 41 críticas y 21 ejecutadas; el panel «Metas del plan», inmediatamente debajo, muestra «Cumplidas 0 · En progreso 5 · En riesgo 0 · Sin avance 73» y un donut casi todo gris. Ninguno de los dos rótulos dice qué mide, así que se leen como la misma pregunta con…

**Lee** `presu_avance_ind_periodo, vía apps/dashboard/services/kpis_presupuesto.py:900 metas_con_progreso() →…` · **lo tiene** `presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): columna `alerta` para 76 de 78 metas y…`

**Cobertura:** presu_avance_ind_periodo: 9 filas activas que tocan 6 de los 77 indicadores activos. Corriendo metas_con_progreso() contra la BD real (working tree… → presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk', 312 filas): 78 codigo_meta distintos, de los cuales 76 cruzan con el catálogo por…

**Arreglo:** 1) apps/dashboard/services/kpis_presupuesto.py:900 metas_con_progreso() — REUSAR, no duplicar, el helper _cumplimiento_por_meta(cursor) que el commit 1afa90e ya dejó hoy en apps/presupuesto/services/expediente_proyecto.py (lee la vigencia MÁS RECIENTE, no la suma, y ya convierte el tanto-por-uno de la Matriz a porcentaje). Agregar m.codigo_meta al SELECT y al GROUP BY del SQL (hoy solo agrupa por m.codigo, el interno entero; la llave contra la Matriz es…

---

### 13. «Avance por sector» pinta de rojo 16 de 19 sectores con un 0,0 % que no es un cero medido: el COALESCE convierte «no reportado» en «cero avance»

`apps/dashboard/services/kpis_presupuesto.py:359` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/sectores, Seguridad (4 proyectos, 13 KPIs), Ambiente, Mujer, Participación, Deporte, Salud y otros 10 sectores salen con una barra roja completa y «0 %» de cumplimiento. Es la lectura más dura que puede dar el tablero —el área no ejecutó nada— y lo que en realidad pasa es que sus avances no se registran a mano en innovaK; la Matriz sí trae su cumplimiento. Además rompe la regla de que un vacío no…

**Lee** `presu_avance_ind_periodo, con `COALESCE((SELECT SUM(av.magnitud_aportada) …), 0)` dentro de…` · **lo tiene** `presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): cumplimiento_pct, magnitud_contratada y…`

**Cobertura:** `presu_avance_ind_periodo`: 6 de 80 KPIs activos tienen alguna fila de avance; solo 3 de los 18 subgrupos con proyecto muestran algo distinto de 0… → `presu_presupuesto_meta_vigencia` fuente `matriz_pdl_alk`: 76 de 78 metas con `cumplimiento_pct` y `magnitud_ejecutada` (vigencia 2025; 2026-2028 en…

**Arreglo:** Tres cambios, y el orden importa: el (1) solo por sí mismo ya quita el rojo falso. 1. `apps/dashboard/services/kpis_presupuesto.py:415` — dejar de fabricar el cero. Copiar la invariante que ya está escrita en `apps/presupuesto/services/muro_subgrupos.py:225`: emitir `porcentaje: None` cuando ningún KPI del subgrupo tiene avance reportado o `meta_total` es 0, en vez de `0.0`. Para saberlo hace falta contar aparte los KPIs con avance (`COUNT(DISTINCT CASE…

---

### 14. El muro de subgrupos deja «Avance físico: Sin avance cargado» en 43 de 46 tarjetas y lo lista como falta del área, en la misma tarjeta que ya se califica con la Matriz

> ✅ **Cerrado el 2026-09-07** — ver la bitácora al final.

`apps/presupuesto/services/muro_subgrupos.py:182` · cobertura · severidad **alta**

**Se ve así.** En el muro de /app/presupuesto/dashboard, una tarjeta como Seguridad muestra el bloque de plata rotulado «Matriz de Seguimiento PDL · ALK» con su comprometido y su girado, y justo debajo «Avance físico — Sin avance cargado · 0 de 13 indicadores con avance», rematado en «Qué falta: 13 indicadores sin ningún avance reportado». La tarjeta le atribuye al área un incumplimiento de reporte usando una fuente que casi nadie…

**Lee** `presu_avance_ind_periodo, vía _avance_por_subgrupo(); el resultado alimenta `avance`, `avance_detalle` y el…` · **lo tiene** `presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): cumplimiento_pct / magnitud_contratada /…`

**Cobertura:** presu_avance_ind_periodo: 6 de 77 indicadores activos con alguna fila de avance (9 filas). En pantalla: 3 de 46 tarjetas del muro con cifra de avance… → presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): cumplimiento_pct + magnitud_contratada + magnitud_ejecutada para 76 de 78 metas y 30 de 30…

**Arreglo:** 1) apps/presupuesto/services/muro_subgrupos.py, dentro del `with connection.cursor()` de ~l.775-793 donde ya se importan perezosamente los helpers del expediente: agregar `_cumplimiento_por_meta` a ese import desde apps.presupuesto.services.expediente_proyecto (l.254) — NO reescribir la query, es la misma pregunta y dos copias se desincronizan, que es el motivo escrito en el comentario de l.780. 2) Agregar un `_avance_matriz_por_subgrupo(cursor)` al lado…

---

### 15. El detalle de un KPI muestra «0 % Cumplimiento» en rojo cuando lo que pasa es que nadie registró avances: 71 de 77 KPIs

`frontend/src/app/features/presupuesto/presupuesto-detail.component.ts:41` · cobertura · severidad **alta**

**Se ve así.** Al abrir /app/presupuesto/indicadores/<id>, la tercera baldosa dice «0 % · Cumplimiento» sobre fondo rojo y la barra sale roja y vacía, aunque la Alcaldía ya reportó cumplimiento para esa meta en su Matriz. El mismo KPI, visto desde el expediente del proyecto, muestra el porcentaje de la Matriz: dos pantallas del mismo sistema dan dos veredictos del mismo indicador.

**Lee** `presu_avance_ind_periodo, vía apps/presupuesto/services/avance.py:56 calcular_avance(), que devuelve pct=0.0…` · **lo tiene** `presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): cumplimiento_pct, magnitud_contratada y…`

**Cobertura:** `presu_avance_ind_periodo`: 6 de 77 KPIs activos (9 filas en total). 71 KPIs sin una sola fila. → `presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk'): `cumplimiento_pct` para 76 metas → cubre 75 de los 77 KPIs (los 71 hoy en rojo…

**Arreglo:** Tres cambios, el primero es el que apaga el rojo falso en las tres pantallas de una vez: 1. `/home/innova/Proyectos/innovaK/apps/presupuesto/api/serializers.py:202` — `get_avance_pct` devuelve `None` cuando `av.aportes == 0`. Distingue «medimos 0» de «nadie midió» sin tocar `calcular_avance()` (que lo consumen cockpit y tests: `apps/presupuesto/tests/test_api.py:77`). Si se prefiere en la fuente única, es `apps/presupuesto/services/avance.py:56`: `pct =…

---

### 16. Las tarjetas del Plan oficial y de las listas «del Plan» ponen plata acumulada 2025+2026 al lado de un «Avance de metas» que solo existe para 2025, y no rotulan ninguna de las dos vigencias

`frontend/src/app/features/presupuesto/plan-oficial.component.ts:85` · mezcla · severidad **media**

**Se ve así.** En /app/presupuesto/plan-oficial y en /app/presupuesto/oficial/metas cada tarjeta muestra cuatro recuadros seguidos: «Apropiación POAI», «Comprometido», «Girado» y «Avance de metas». Los tres primeros son el acumulado de dos años; el cuarto es el veredicto de uno solo. Nada en la tarjeta dice a qué período corresponde cada cosa, así que una meta con «Ejecutada» al lado de la plata de 2026 se lee como que ya cumplió…

**Lee** `plan_matriz._SQL_CIFRAS_META: SUM() sobre todas las vigencias para apropiacion_poai/comprometido/girado, y…` · **lo tiene** `presu_presupuesto_meta_vigencia.vigencia junto con .alerta y .cumplimiento_pct (solo poblados en 2025) frente…`

**Cobertura:** Defecto de MEZCLA, no de cobertura — ambas cifras salen de la Matriz. La densidad por año es lo que difiere: el recuadro «Avance de metas» (alerta)… → Los tres recuadros de plata cubren 78 de 78 metas y suman DOS vigencias: apropiación 2025 $187.520.585.000 + 2026 $188.937.712.000 =…

**Arreglo:** Tres cambios, reusando el rótulo que el propio proyecto ya escribió en otras dos pantallas. 1) apps/presupuesto/services/plan_matriz.py, _SQL_CIFRAS_META (líneas 51-70): hoy expone vig_desde/vig_hasta de la plata pero NO de qué año salió la alerta. Agregar la columna que falta: (ARRAY_AGG(vigencia ORDER BY vigencia DESC) FILTER (WHERE alerta IS NOT NULL))[1] AS alerta_vigencia y publicarla como "alerta_vigencia" en el dict de _metas_crudas (junto a…

---

### 17. La línea de contraste rotulada «Datos Abiertos SDP» de la tarjeta de meta imprime el entregado sumado sobre las cuatro vigencias, que es cuatro veces lo que el Distrito publica

`apps/presupuesto/services/plan_matriz.py:78` · mezcla · severidad **media**

**Se ve así.** En /app/presupuesto/oficial/metas, bajo el rótulo «Datos Abiertos SDP», la tarjeta de la meta 26101 dice «24.700 programado · 154.804 entregado». El usuario que abra el portal del Distrito para contrastar encontrará 38.701, no 154.804, y concluirá que innovaK está inventando cifras del Distrito. El rótulo promete literalidad de la fuente y el número no está en la fuente.

**Lee** `_SQL_ESPEJO_META: SUM(magnitud_entregada) sobre sdp_meta_oficial. El comentario inmediatamente arriba (líneas…` · **lo tiene** `presu_presupuesto_meta_vigencia.magnitud_ejecutada y .cumplimiento_pct (76 metas, corte 2026-09-02) — el dato…`

**Cobertura:** La línea afectada aparece en las 70 metas que tienen par en el espejo, pero la cifra sale mal solo donde hay entregado: 8 de 70 metas del espejo (las… → presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk') cubre 78 metas: 76 con cumplimiento_pct y 76 con magnitud_ejecutada. Para la 26101 trae…

**Arreglo:** En apps/presupuesto/services/plan_matriz.py, `_SQL_ESPEJO_META` (líneas 75-82), aplicar la misma regla que ya está implementada en apps/dashboard/services/kpis_presupuesto.py:481-500: SELECT plan_meta_producto_id, CASE WHEN MAX(tipo_anualizacion) = 'Constante' THEN MAX(magnitud_programada) ELSE SUM(magnitud_programada) END AS programado, MAX(magnitud_entregada) AS entregado, MAX(tipo_anualizacion) AS tipo_anualizacion FROM sdp_meta_oficial GROUP BY…

---

### 18. En «Plan oficial» y «Metas del Plan» la baldosa de alerta pinta el valor crudo de la columna y su corte (solo 2025) no coincide con las tres cifras de plata que tiene al lado (2025+2026)

`frontend/src/app/features/presupuesto/plan-oficial.component.ts:88` · mezcla · severidad **media**

**Se ve así.** Cada tarjeta de /app/presupuesto/plan-oficial y /app/presupuesto/metas muestra «Apropiación POAI $1.842 M · Comprometido $917 M · Girado $0 M · Avance de metas: Crítico». Los tres montos son la suma de dos años y el «Crítico» es el juicio de uno solo, sin que nada en pantalla lo diga; el usuario lee el rojo como el veredicto sobre esa plata. Y «Crítico» a secas es la misma palabra que el semáforo de plata usa para…

**Lee** `presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'), pero mezclando dos cortes en la misma fila de…` · **lo tiene** `La misma tabla ya manda lo que falta y la pantalla lo descarta: `apropiacion_vigencia_desde` /…`

**Cobertura:** La baldosa pinta un solo dato crudo: `alerta` de la vigencia más reciente con dato, que hoy es 2025 en el 100 % de los casos — 76 de las 78 metas… → La misma tabla ya manda, en la misma fila del endpoint y sin pintarse: `apropiacion_vigencia_desde`/`_hasta` (2025 y 2026 en las 78 metas),…

**Arreglo:** 1) `frontend/src/app/features/presupuesto/plan-oficial.component.ts:88` y `frontend/src/app/features/presupuesto/oficial-lista.component.ts:87`: pasar la alerta por la etiqueta compartida en vez de imprimirla cruda — importar `ALERTAS` de `./objetivos/objetivos.types` (en plan-oficial) / `./objetivos/objetivos.types` (en oficial-lista) y copiar el helper de `expediente-proyecto.component.ts:391`: `etiquetaAlerta(a) { return ALERTAS.find(x => x.valor ===…

---

## Detalle · B · Mezcla de fuentes y jerarquía

### 19. La fila de KPI que encabeza el cockpit encadena tres fuentes: Apropiación de la Matriz, Comprometido de innovaK y Girado de SECOP

`apps/presupuesto/services/muro_subgrupos.py:1008` · mezcla · severidad **alta**

**Se ve así.** En /app/presupuesto/dashboard los cuatro tiles de arriba se leen como la cadena del PDL: «Apropiación $376.458 M · 2025-2026», «Comprometido $41.264 M · 25 de 25 contratos», «Girado $4.769 M · 24 de 25 contratos». El primero es la Matriz y los otros dos son otro universo, así que la Alcaldía aparece habiendo comprometido el 11 % y girado el 1,3 % de lo que apropió, cuando su propia Matriz dice 59,7 % y 26,9 %. Los…

**Lee** `comprometido = SUM(contrato.valor) de innovaK (25 contratos) · girado = SUM(secop_plan_pago.valor_neto) de…` · **lo tiene** `presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk'): apropiacion_poai, comprometido y girado, los tres…`

**Cobertura:** Comprometido: `contrato.valor` de innovaK — 25 contratos, los 25 con valor, atribuidos a solo 4 subgrupos (Cultura 15, Infraestructura 4, Seguridad… → `presu_presupuesto_meta_vigencia` con `fuente='matriz_pdl_alk'`: 312 filas, de las cuales 156 traen comprometido Y girado no nulos — 78 metas, 30…

**Arreglo:** Backend — `apps/presupuesto/services/muro_subgrupos.py`: 1. Agregar `_ejecucion_matriz(cursor)` como hermana de `_apropiacion()` (línea 233), con el MISMO WHERE para que el par cierre: `SELECT SUM(comprometido), SUM(girado), COUNT(*) FILTER (WHERE comprometido IS NOT NULL), COUNT(DISTINCT codigo_meta), COUNT(DISTINCT proyecto_codigo), MIN(vigencia), MAX(vigencia) FROM presu_presupuesto_meta_vigencia WHERE fuente='matriz_pdl_alk'`. Devolver `None` si no…

---

### 20. «Ejecución financiera 29,7 % · comprometido / programado» arma el numerador con dos fuentes y el denominador con una tercera

`frontend/src/app/features/presupuesto/objetivos/objetivos.types.ts:138` · mezcla · severidad **alta**

**Se ve así.** En la barra lateral de /app/presupuesto/dashboard y en /app/presupuesto/objetivos, «Ejecución financiera» dice 29,7 % con el subtítulo «comprometido / programado». El numerador viene de innovaK en 7 proyectos y de la Matriz en 23, y el denominador del espejo de SDP. El porcentaje no cierra con ninguna pareja real: el mismo panel muestra «Presupuesto programado $667.578 M» arriba y el tile de la página dice…

**Lee** `comprometidoDe(): si el proyecto tiene ≥1 contrato en innovaK usa p.comprometido (SUM contrato.valor); si no,…` · **lo tiene** `presu_presupuesto_meta_vigencia.comprometido para los 30 proyectos, y apropiacion_poai como denominador de la…`

**Cobertura:** Numerador MIXTO sobre 30 proyectos: innovaK (SUM contrato.valor) en 7 y Matriz en 23. Denominador de una TERCERA fuente:… → presu_presupuesto_meta_vigencia (fuente='matriz_pdl_alk') tiene comprometido para 30/30 proyectos ($224.853.665.855) y apropiacion_poai para 30/30…

**Arreglo:** 1) frontend/src/app/features/presupuesto/objetivos/objetivos-resumen.component.ts:165-166 — `presupuestoProgramado` (Σ programado_oficial, SDP) pasa a ser la apropiación de la Matriz: Σ (p.apropiacion_oficial ?? 0) sobre proyectosUnicos(); da $376.458.297.000, idéntico al ledger.apropiacion del mismo tablero. Cambiar el rótulo «Presupuesto programado» por «Apropiación» y el sub «total PDL cargado» por el rango real, que ya viaja en…

---

### 21. El tile «Contratado» de Mi Área muestra $0 en 12 de las 16 áreas que sí tienen plata comprometida en la Matriz

`apps/presupuesto/services/panel_area.py:225` · cobertura · severidad **alta**

**Se ve así.** «Contratado» es el ÚNICO número de plata del panel /app/mi-area/<área>. Salud, Mujer, Deporte, Ambiente, Participación, Reactivación Económica, Espacio Público, Subsidio tipo C, CPS y Planta, Buen trato, Paz y Memoria e Innovación lo ven en $0 con el resto del panel lleno de proyectos y actividades. Un área que apropió $18.450 M y comprometió $9.858 M abre su panel y lee «Contratado $0», que se entiende como «acá no…

**Lee** `sum(contrato.valor) de los contratos del área por la unión contrato_proyecto + contrato_actividad_plan (25…` · **lo tiene** `presu_presupuesto_meta_vigencia: comprometido, girado y apropiacion_poai por proyecto — los 16 subgrupos con…`

**Cobertura:** 4 de las 18 áreas que tienen panel. La unión `contrato_proyecto` + `contrato_actividad_plan(activo)` alcanza 25 contratos en toda la base… → 17 de las 18 áreas tienen filas en `presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk': 312 filas meta×vigencia, 30 proyectos, 78 metas,…

**Arreglo:** Dos archivos, y las cifras van SEPARADAS por fuente (no sustituir una por otra: Educación tiene $23.168.769.452 contratado contra $18.225.782.000 comprometido en la Matriz — son mediciones distintas). 1) `apps/presupuesto/services/panel_area.py`, paso 9 (línea ~216): agregar la plata de la Matriz al dict `tiles`. Una consulta sobre los `proyecto_ids` del área: SELECT COALESCE(sum(apropiacion_poai),0), COALESCE(sum(comprometido),0), COALESCE(sum(girado),0)…

---

### 22. En la jerarquía de perspectivas la tarjeta padre muestra proyectado de SDP y sus programas hijos apropiación de la Matriz, sin rótulo que los distinga

`frontend/src/app/features/presupuesto/objetivos/perspectivas-explorador.component.ts:138` · mezcla · severidad **alta**

**Se ve así.** En /app/presupuesto/dashboard, cada tarjeta de perspectiva lleva una cifra de plata abajo a la derecha y, al abrirla, cada programa lleva otra en el mismo lugar y con el mismo estilo. Los hijos suman poco más de la mitad del padre y no hay ninguna etiqueta que diga que uno es el proyectado del cuatrienio y el otro la apropiación 2025-2026: se lee como que a la perspectiva le faltan programas o que la mitad de la…

**Lee** `tarjeta de perspectiva = suma de programado_oficial (sdp_meta_oficial.total_programado); fila de programa =…` · **lo tiene** `presu_presupuesto_meta_vigencia.apropiacion_poai, que es lo que el backend ya suma en el resumen de cada…`

**Cobertura:** `sdp_meta_oficial.total_programado` (lo que usa la tarjeta hoy): 28 de los 31 proyectos del expediente; 28 de los 30 que cuelgan de la jerarquía de… → `presu_presupuesto_meta_vigencia.apropiacion_poai` (fuente='matriz_pdl_alk'): 30 de los 31 proyectos; **30 de 30** dentro de la jerarquía de…

**Arreglo:** 1. `/home/innova/Proyectos/innovaK/frontend/src/app/features/presupuesto/objetivos/perspectivas-explorador.component.ts:138` — reemplazar la suma de SDP por la cifra de la Matriz que el backend ya calcula para ese mismo objetivo: `presupuestoProgramado: proyectos.reduce((s, p) => s + (p.programado_oficial ?? 0), 0)` → `apropiacion: o.resumen.apropiacion_total` (`objetivos_estrategicos()` ya lo emite; el `computed` recibe `o` como primer parámetro del…

---

### 23. El detalle de programa muestra Asignado / Comprometido / Disponible en $0 porque suma sobre programa_cdp y crp, ambas vacías

`apps/presupuesto/services/metrics.py:190` · cobertura · severidad **alta**

**Se ve así.** En /app/presupuesto/programas/<id> los tres tiles de plata salen siempre en $0 y el «Disponible» en $0, aunque el programa liste sus proyectos justo debajo con enlace al 360°. El de «Más Cultura Local», con dos proyectos reales, se lee como un programa sin un peso, y el Disponible en cero además sugiere que ya se gastó todo.

**Lee** `programa_cdp.valor_asignado (o cdp.valor) para el asignado y crp.valor_crp para el comprometido — las dos…` · **lo tiene** `presu_presupuesto_meta_vigencia, agregable por programa a través de los proyectos que le cuelgan`

**Cobertura:** 0. `programa_cdp` = 0 filas y `crp` = 0 filas (COUNT(*) en la BD), así que la fuente actual no cubre ningún programa ni ningún proyecto: 0 de 7… → `presu_presupuesto_meta_vigencia` (fuente='matriz_pdl_alk'): 312 filas sobre 30 proyectos distintos, y los 30 cruzan con la tabla `proyecto` de…

**Arreglo:** Tres cambios, y el tercero es obligatorio para no cambiar un defecto (A) por uno (B). 1. **`apps/presupuesto/services/metrics.py`** — reemplazar la fuente en `resumen_programa()` (línea 190) y en la agregación de `resumen_inversion()` (~120-180): en vez de `ProgramaCdp`/`Crp`, sumar `apropiacion_poai`, `comprometido` y `girado` de `presu_presupuesto_meta_vigencia WHERE fuente='matriz_pdl_alk'`, uniendo a `proyecto` por `proyecto.codigo::int =…

---

### 24. La página de Objetivos se rotula «Fuente: Matriz de Seguimiento PDL» pero su «Presupuesto programado» sale del espejo SDP parado, y la «Ejecución financiera» divide un numerador mezclado por ese denominador

`frontend/src/app/features/presupuesto/objetivos/objetivos-resumen.component.ts:165` · mezcla · severidad **alta**

**Se ve así.** En /app/presupuesto/objetivos el subtítulo dice «Fuente: Matriz de Seguimiento PDL de la Alcaldía Local» (objetivos-pdl.component.ts:37) y justo debajo el KPI «Presupuesto programado $667.578 M · total PDL cargado» no viene de la Matriz sino del espejo congelado hace mes y medio. Al lado, «Ejecución financiera 29,7 % · comprometido / programado» es un porcentaje que no cierra con ninguna de las dos fuentes. El mismo…

**Lee** ``programado_oficial` = sdp_meta_oficial.total_programado (synced_at 2026-07-23, 28 de 30 proyectos). El…` · **lo tiene** `presu_presupuesto_meta_vigencia.proyectado_pdl (30 proyectos, 78 metas) y .apropiacion_poai / .comprometido…`

**Cobertura:** `sdp_meta_oficial.total_programado`: 28 de los 30 proyectos del árbol de objetivos (espejo parado, synced_at 2026-07-23). Los 2 faltantes (2556,… → `presu_presupuesto_meta_vigencia` con fuente='matriz_pdl_alk' cubre 30 de 30 proyectos en las tres columnas que hacen falta: `proyectado_pdl`…

**Arreglo:** 1) `frontend/src/app/features/presupuesto/objetivos/objetivos-resumen.component.ts` - Línea 165: cambiar el KPI «Presupuesto programado» por **Apropiación**, sumando `p.apropiacion_oficial` (30/30, $376.458 M) en vez de `p.programado_oficial`, y poner de sublabel el rango de vigencias derivado de `apropiacion_vigencia_desde`/`apropiacion_vigencia_hasta` (2025-2026) — exactamente como ya lo hace el tile del cockpit…

---

### 25. El selector de vigencia del cockpit gobierna solo 1 de los 4 tiles: al elegir 2026 el Avance físico cae a 0 % mientras Apropiación, Comprometido y Girado siguen mostrando todas las vigencias

`frontend/src/app/features/presupuesto/presupuesto-dashboard.component.ts:695` · mezcla · severidad **alta**

**Se ve así.** En /app/presupuesto/dashboard el usuario pulsa el chip «2026» y la cabecera queda marcando esa vigencia. Tres de los cuatro tiles no se mueven: Apropiación sigue en $376.458 M con el subtítulo «2025-2026» (que contradice al chip que dice 2026), Comprometido sigue en $41.264 M «25 de 25 contratos» —contratos cuyas vigencias son 2025, 2024 y 2015— y Girado sigue en $4.769 M. El único que reacciona es Avance físico,…

**Lee** ``setVigencia()` solo recarga /dashboard/api/presupuesto/ejecucion-financiera/?vigencia=N. Los tiles de…` · **lo tiene** `presu_presupuesto_meta_vigencia.vigencia — la Matriz trae apropiacion_poai, comprometido y girado…`

**Cobertura:** El chip de vigencia alcanza UNA sola tabla: `contrato`, vía `ejecucion_financiera(vigencia)` → `WHERE contrato_vigencia = %s`. Son 25 filas en total,… → `presu_presupuesto_meta_vigencia` con `fuente='matriz_pdl_alk'` trae las tres cifras desagregadas por año, 78 metas por vigencia: 2025 → apropiación…

**Arreglo:** Que el chip gobierne los cuatro tiles, propagando la vigencia hasta el ledger; y que el vacío de 2026 se declare vacío en vez de 0 % ámbar. 1. `apps/presupuesto/services/muro_subgrupos.py:674` — `muro_subgrupos(hoy=None)` pasa a `muro_subgrupos(hoy=None, vigencia=None)` y propaga el año a los tres lugares que arman el ledger: - `_apropiacion(cursor)` (:233, SELECT en :262): agregar `AND (%s::int IS NULL OR vigencia = %s)`. Con vigencia fija, `vig_min ==…

---

### 26. La fila de cada programa dice «N metas» pero cuenta PROYECTOS con alerta: la pantalla suma 30 donde el donut de la misma página dice 76

`frontend/src/app/features/presupuesto/objetivos/perspectivas-explorador.component.html:112` · mezcla · severidad **alta**

**Se ve así.** En el explorador jerárquico de /app/presupuesto/dashboard, el programa «4 - Servicios centrados en la justicia» dice «1 de 1 proyectos · 1 meta» cuando tiene 7 metas con alerta; «14 - Bogotá deportiva…» dice «2 metas» y tiene 8. Quien abre el programa esperando una meta se encuentra siete, y quien no lo abre se lleva la idea de que el programa es diez veces más pequeño de lo que es.

**Lee** ``resumen.n_con_alerta`, que en apps/presupuesto/services/expediente_proyecto.py:1125 es `len([p for p in…` · **lo tiene** `El desglose por meta ya viaja en `alerta_conteo` de cada proyecto (expediente_proyecto.py:1004, poblado desde…`

**Cobertura:** `resumen.n_con_alerta` = proyectos con alerta. En los 22 programas suma 30, y 16 de los 22 muestran una cifra distinta de la real. Expandir el… → `alerta_conteo` —ya presente en cada proyecto (expediente_proyecto.py:990, poblado por `_alerta_por_proyecto` desde presu_presupuesto_meta_vigencia,…

**Arreglo:** Que el número salga de la misma fuente que el donut, calculado UNA vez en el backend. (1) apps/presupuesto/services/expediente_proyecto.py, en `_resumen()` (~línea 1137), agregar junto a los conteos de proyecto: `metas_alerta = sum(sum((p.get("alerta_conteo") or {}).values()) for p in proyectos)` y `metas_criticas = sum((p.get("alerta_conteo") or {}).get("Crítico", 0) for p in proyectos)`, y exponerlos en el dict como `"n_metas_alerta"` y…

---

### 27. El panel de subgrupo muestra «Valor contratado $0» en las mismas 12 áreas y además contradice a Mi Área en Seguridad

`apps/presupuesto/services/panel_subgrupo.py:150` · cobertura · severidad **media**

**Se ve así.** El tile «Valor contratado» de /app/subgrupo/<id> repite el $0 de las 12 áreas sin contratos en innovaK, y encima Seguridad muestra $0 acá mientras /app/mi-area/seguridad muestra $6.944.742.446 para el mismo subgrupo el mismo día. El usuario ve dos cifras distintas de su propia área según por qué pantalla entró, y ninguna de las dos es la de la Matriz.

**Lee** `sum(contrato.valor) sólo por la vía contrato_proyecto (no usa la unión con contrato_actividad_plan que ya…` · **lo tiene** `presu_presupuesto_meta_vigencia.comprometido por proyecto del subgrupo`

**Cobertura:** `contrato_proyecto` (lo que lee `panel_subgrupo`): 3 de 47 subgrupos con valor > 0 — Cultura $713.221.534, Educación $23.168.769.452, Infraestructura… → `presu_presupuesto_meta_vigencia.comprometido` (fuente='matriz_pdl_alk', 312 filas): 16 de 47 subgrupos con valor > 0, sobre 30 proyectos distintos,…

**Arreglo:** Son dos arreglos separados; conviene no confundirlos. **(1) La contradicción — `apps/presupuesto/services/panel_subgrupo.py:131-136`.** Portar la unión de `panel_area.py:161-163`. Como este servicio no calcula actividades por proyecto, hay que traer el segundo camino explícito: ```python from apps.presupuesto.models.core import ActividadPlan from apps.presupuesto.models.sql import ContratoActividadPlan via_proyecto = set(ContratoProyecto.objects…

---

### 28. Los insights de Festivales muestran Asignado, Ejecutado y Disponible en $0 porque leen dos tablas vacías

`apps/festivales/api/views.py:507` · cobertura · severidad **media**

**Se ve así.** En /app/festivales/insights el bloque de presupuesto dice «Asignado $0 · Ejecutado $0 · Disponible $0» y el gráfico de barras dibuja tres barras en cero, junto a los KPIs de la Meta 4 que sí traen datos. Cultura lee que su proyecto no tiene un peso asignado cuando la Matriz le reporta $12.392.980.000 apropiados y $7.794.984.904 comprometidos.

**Lee** `resumen_inversion() → programa_cdp (0 filas) para el asignado y crp (0 filas) para el comprometido` · **lo tiene** `presu_presupuesto_meta_vigencia del proyecto 2780: apropiacion_poai, comprometido y girado`

**Cobertura:** Cero. `programa_cdp` y `crp` tienen 0 filas en toda la BD, así que la fuente actual no cubre ningún proyecto: para el 2780 devuelve asignado_total=0,… → 16 filas meta×vigencia para proyecto_codigo=2780 (4 metas × 4 vigencias), de las cuales 8 traen plata (2025 y 2026; 2027-2028 en NULL). Acumulado:…

**Arreglo:** 1) apps/festivales/api/views.py, bloque de las líneas 503-514: sacar la llamada a `resumen_inversion` y leer `presu_presupuesto_meta_vigencia` con `fuente='matriz_pdl_alk'` y `proyecto_codigo=2780`, FILTRANDO por la vigencia `vig` que ya calcula la vista, para que la plata corresponda al mismo corte que los KPIs y el aforo. Devolver `apropiado` (SUM apropiacion_poai), `comprometido`, `girado`, `disponible = apropiado - comprometido`, más `vigencia` y un…

---

### 29. El expediente del proyecto lee el Programa del PDL de la tabla vieja `programas`, y 26 de 31 proyectos salen «Sin programa asociado»

`apps/presupuesto/services/expediente_proyecto.py:400` · cobertura · severidad **media**

**Se ve así.** En la ficha del proyecto, el campo «Programa del PDL» dice «Sin programa asociado» en 26 de 31 proyectos. Y es peor dentro del explorador de perspectivas (`perspectivas-explorador.component.ts`, que embebe este mismo componente): el usuario acaba de navegar Objetivo → Programa → Proyecto usando el catálogo, abre el proyecto, y la ficha le dice que no tiene programa. Los 2 proyectos de Cultura que sí muestran algo…

**Lee** ``_SQL_PROYECTOS` hace `LEFT JOIN programas pr ON pr.id = p.programa_id` — la tabla vieja de 7 filas (3 de…` · **lo tiene** ``metas.programa_id` → `presu_programa` (22 programas del Plan, DDL 024), la misma vía que YA usa…`

**Cobertura:** 5 de 31 proyectos (tabla vieja `programas`, 7 filas, 3 de ellas 'prueba'). Y de esos 5, dos son FALSOS: 2780 y 2788 muestran 'Más Cultura Local',… → 30 de 31 proyectos (`metas.programa_id` → `presu_programa` → `presu_objetivo_estrategico`, respetando `activo`, con `meta_proyecto` como respaldo…

**Arreglo:** Archivo: /home/innova/Proyectos/innovaK/apps/presupuesto/services/expediente_proyecto.py, `_SQL_PROYECTOS` (líneas 393-405). Quitar `LEFT JOIN programas pr ON pr.id = p.programa_id` y resolver el programa por el catálogo, con el MISMO camino que ya usa `objetivos_estrategicos()` (línea 1090) para que la ficha y el explorador nunca digan dos programas distintos del mismo proyecto: LEFT JOIN LATERAL ( SELECT pg.id, pg.codigo || ' - ' || pg.nombre AS nombre…

---

### 30. La vista 360° del proyecto omite el programa en 26 de 31 proyectos: el serializer resuelve `programa` por la FK a la tabla vieja `programas`

`apps/presupuesto/api/serializers.py:63` · cobertura · severidad **media**

**Se ve así.** En `/presupuesto/proyectos/:id` el subtítulo de la cabecera es `código · Programa · Subgrupo · Dependencia` (`proyecto-360.component.ts:56`), pero el `@if (p.programa)` no se cumple en 26 de 31 proyectos: el programa simplemente desaparece del encabezado sin decir por qué, y el usuario ve un proyecto que aparenta no pertenecer a ningún programa del Plan. En los 2 de Cultura donde sí aparece, dice «Más Cultura…

**Lee** ``ProyectoDetailSerializer.get_programa()` devuelve `None` si `obj.programa_id` es nulo y, si no,…` · **lo tiene** ``metas.programa_id` → `presu_programa` (22 programas del Plan, con su `codigo` y su `objetivo_id`).`

**Cobertura:** 5 de 31 proyectos (FK `proyecto.programa_id` → tabla vieja `programas`, 7 filas de las cuales 3 se llaman «prueba»). Y de esos 5, 2 (Cultura… → 30 de 31 proyectos, sin ambigüedad (`metas.programa_id → presu_programa` activo, uniendo `metas.proyecto_codigo` con…

**Arreglo:** 1) `apps/presupuesto/api/serializers.py`: resolver el programa desde el catálogo del Plan en vez de la FK vieja, con la misma unión que ya usa `apps/presupuesto/services/plan_matriz.py:101` (`LEFT JOIN presu_programa p ON p.id = m.programa_id AND p.activo`), enlazando `metas.proyecto_codigo::text = regexp_replace(proyecto.codigo,'^0+','')`. - `ProyectoDetailSerializer.get_programa()` (líneas 63-66): devolver `{"id": pg.id, "codigo": pg.codigo, "nombre":…

---

## Anexo · Especificación de `avance-por-sector`

Un segundo barrido debía producir la especificación de migración sitio por
sitio. **Murió por límite de sesión: de 8 agentes terminó 1.** Ésta es la única
que llegó, y trae un hallazgo que la auditoría no había visto.

**apps/dashboard/services/kpis_presupuesto.py:359 — `avance_por_subgrupo()`, servida por `AvancePorSectorView` (apps/dashboard/api/views.py:51) en `GET /dashboard/api/v2/presupuesto/avance-por-sector/` (apps/dashboard/urls.py:69). Pinta /app/presupuesto/sectores. SÍ debe migrar: acá el defecto es doble, porque además de…**

- **Función:** `apps/dashboard/services/kpis_presupuesto.py::avance_por_subgrupo()` (línea 359). OJO con el nombre: hay otras dos parecidas y NO son ésta — `apps/presupuesto/services/muro_subgrupos.py::_avance_por_subgrupo()` (línea 182, el muro) y la que va a publicar el helper nuevo. Al importar el helper hay…
- **Calcula hoy:** Un solo SQL (líneas 378-411). CTE `kpi` cuelga `proyecto → meta_proyecto → presu_indicador_meta_proyecto (activo)` y por cada indicador pre-suma su avance con un escalar sobre `presu_avance_ind_periodo (activo)` — el pre-sumado está bien puesto, evita el fan-out que documenta muro_subgrupos. Después agrega por `subgrupo`, con `proj` (conteo de `proyecto`) y `ev` (conteo de `evento activo`), y `HAVING` deja pasar al subgrupo que tenga proyectos O eventos. El % sale en Python (línea 416): `porcentaje = Σ magnitud_aportada / Σ meta_magnitud * 100`, con `0.0` cuando el denominador es 0. Dos defectos, no uno: 1. FUENTE. El numerador es `presu_avance_ind_periodo`, que en este corte llega a 3…
- **Cobertura hoy:** Medido corriendo el SQL textual del servicio contra la BD (2026-09-07): - Devuelve **19 filas** (subgrupos con proyectos o eventos). - **3 de 19** traen un % distinto de cero: Educación 47,5 · Infraestructura 1,7 · Cultura 0,7. - **16 de 19 salen en 0,0 % y en rojo.** De esas 16, dos (Relacionamiento Interinstitucional, Desarrollo Estratégico y Mejora) ni siquiera tienen metas: son vacíos puros pintados de crítico. - KPIs con avance interno: **6 de 77**, repartidos en 3 subgrupos (Cultura 2/5,…
- **Helper que le sirve:** `avance_por_subgrupo()` del helper — la que devuelve `{subgrupo_id: {pct, n_metas}}` — porque mi eje de agregación ES el `subgrupo_id` y el helper ya recorre la cadena que yo necesito: `proyecto.subgrupo_id → meta_proyecto → metas.codigo_meta ↔ presu_presupuesto_meta_vigencia.codigo_meta`, con el promedio simple y la vigencia más reciente ya resueltos adentro. NO me sirve `avance_por_sector()`: ese agrupa por `metas.sector_id → presu_sector`, que es la taxonomía del PDL. Mi pantalla dice «sector» pero agrupa por el **subgrupo del proyecto**, que es la organización del área (Cultura, Deporte,…
- **Riesgo:** 1. **Educación baja de 47,5 % a 0,0 % y es el número correcto.** Es la única fila que empeora. Sus 2 metas: la Matriz cubre «Dotar 74 sedes educativas» (contratada 20, ejecutada 0 → 0 %) y no cubre la de becas (`codigo_meta` NULL), que es de donde salía todo el 47,5 % interno. El promedio de la Matriz es sobre las metas que la Matriz mide, igual que en `expediente_proyecto`; el 47,5 sigue visible…

> El hallazgo extra: esa pantalla no solo lee la fuente equivocada, **además
> agrega mal** — suma unidades que no se suman (Ambiente da denominador 26.493
> mezclando árboles, m² y personas). Las 3 barras que hoy no están en cero
> tampoco son un número interpretable.

Las otras 6 especificaciones quedan por hacer. El código propuesto completo de
ésta está en el anexo JSON.

---

## Bitácora

### 2026-09-07 — cerrado el primer tramo

**Un solo módulo para el avance físico**: `apps/presupuesto/services/avance_matriz.py`.
Cinco agregaciones sobre una consulta base, contando metas distintas para
evitar el fan-out. Cobertura que gana:

| | antes | después |
|---|---:|---:|
| por subgrupo | 3 de 17 | **17 de 17** |
| por sector | 3 de 19 | **13 de 13** |
| por KPI | 6 de 77 | **75 de 77** |
| por proyecto | pocos | **30 de 30** |

**Migrados:** el expediente del proyecto (donut y metas) y el muro de áreas
(hallazgo 1). El muro pasó de 3 tarjetas con avance a 17, y de **14 tarjetas
acusando** «Indicadores sin ningún avance reportado» a **cero** — el pendiente
no desapareció, cambió de sentido: cuando la Matriz mide, lo que falta es
registrarlo acá para seguirlo entre cortes.

El cálculo interno no se tiró: viaja como `pct_interno` y se muestra al lado.
En los 3 subgrupos con las dos cifras difieren siempre (Cultura 0,7 % contra
109 %), y esa diferencia es conciliación pendiente.

**Quedan 6 lectores** por enchufar al helper: Avance por sector, Top sectores,
donut «Metas del plan», KPI del Proyecto 360°, catálogo de Metas y el tile
ponderado del cockpit. Más los 12 hallazgos del grupo B, que son caso
por caso.

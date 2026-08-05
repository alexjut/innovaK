# Estado de innovaK

**Al 2026-08-05.** Un solo archivo, en la raíz, sobre la rama `produccion`.

> **Para retomar:** lo que sigue abierto está en §3, ordenado. Lo más grande hoy
> es §3.6 (el ciclo actividad–evento–contrato) y §3.7 (metas y proyectos
> oficiales). Lo que depende de terceros: §3.2 (31 sedes, espera al área) y
> §3.5 (festivales, espera a Cultura).

Antes había un `ESTADO.md` por worktree y se contradecían entre sí: el de
`home-publico` seguía diciendo *"nada commiteado"* varios días después de que su
código estuviera en producción. Un estado que miente es peor que no tenerlo, así
que ahora hay uno solo y vive donde vive el código desplegado.

Para el detalle histórico de cada entrega, la bitácora está en `CLAUDE.md` §11.
Para el estado de un módulo, su propio `README.md` (p. ej.
`apps/georeferenciacion/README.md`).

---

## 1. Cómo se trabaja: ramas, no worktrees

El flujo es el de `CLAUDE.md` §5 — `feat/*` → `desarrollo` → `Pruebas` →
`produccion` — sobre **ramas normales en el árbol principal**.

Entre julio y agosto de 2026 se usaron worktrees de git (`.claude/worktrees/`).
Se retiraron el 2026-08-03. No fallaron técnicamente: fallaron por falta de
cierre. Cada uno costaba ~100 MB de copia del árbol y **ninguno se borró al
cascadear**, así que se acumularon 4 vivos + 5 zombis que git ya ni reconocía —
496 MB y cuatro ramas que parecían trabajo pendiente sin serlo.

Costos concretos que se pagaron y no se recuperan trabajando sobre ramas:

- El contenedor `innova_k` monta el árbol principal, no el worktree. Correr
  tests o comandos con el código de un worktree exigía levantar un contenedor
  efímero con `--add-host` y montajes a mano.
- Cada worktree tenía su propio `ESTADO.md` sin trackear. Al mergear no se
  actualizaban, y quedaban afirmando cosas falsas.
- Ver cuatro ramas en `git branch` sugiere trabajo en vuelo. Las cuatro estaban
  100 % mergeadas en `produccion`.

Si vuelve a hacer falta aislamiento real (dos cambios incompatibles sobre los
mismos archivos, a la vez), la regla es: **el worktree se borra en el mismo
paso en que se cascadea la rama**, no después.

---

## 2. Qué está vivo en producción

Las tres troncales están sincronizadas y con el mismo árbol. Todo lo que estaba
en worktrees ya entró:

| Entrega | Dónde |
|---|---|
| Home público en la raíz (`/app/` sin sesión → bienvenida, mapa, encuestas abiertas) | `features/publico/home-publico.component.ts` |
| Censo de escuelas de julio 2026 + resolución territorial | `apps/georeferenciacion/` |
| UX y accesibilidad del mapa público (las 5 fases del plan) | `features/mapa/` |
| Diagnóstico IA NL→consulta de beneficiarios | `docs/propuestas/ia_nl2sql_diagnostico.md` |

---

## 3. Qué queda abierto

### 3.1 Scope por subgrupo en la consulta IA — CERRADO (era falso positivo)

Este punto decía que el motor de consulta de beneficiarios no aplicaba scope y
que cualquiera con el módulo `dashboard_ia` veía el universo completo. **Es
falso, y la verificación que lo respaldaba estaba mal hecha**: se buscó el
símbolo `aplicar_subgrupo` en `apps/dashboard/`, que nunca iba a aparecer ahí.

`Persona` no tiene `subgrupo_id`. El alcance viaja por `Evento.subgrupo_id`, así
que las funciones son otras: `participaciones_visibles` y
`personas_beneficiarias_visibles` (`apps/login/services/scope.py`), ambas
fail-closed. Se enhebra `request.user` en las tres rutas —
`SafeQueryBuilder.build` (`views.py:167`), `analizar` y `analitica`
(`views.py:133,146`).

Lo cerró el commit `01c573c` del **2026-07-14** ("fix(dashboard_ia): scope RBAC
por subgrupo en el motor de consulta de beneficiarios"), que está en `produccion`
y trajo 11 tests en `apps/login/tests/test_rbac_dashboard_ia_scope.py` cubriendo
los 5 roles. `dash_apps.py` (Dash legacy) llama sin `user`, pero no está
enrutado y queda fail-closed: devuelve vacío, no el universo.

Lección: verificar un hueco de RBAC grepeando **un nombre de función** da falsos
positivos. Lo que hay que buscar es el camino del dato.

### 3.2 Los tres CSV con el área de escuelas

Entregados y revisados el 2026-08-03, en `/home/innova/Proyectos/`
(`REVISION_*.csv` + `LEEME_reporte_escuelas_area.txt`). Cada fila trae una
columna *"Qué necesitamos de ustedes"*.

**Viven fuera del repo a propósito**: llevan direcciones reales. El repo es
público y eso es habeas data (Ley 1581). No se mueven adentro.

Falta la respuesta del área sobre las sedes sin ubicación. **Eran 43; hoy son
31**, y las que bajaron no las resolvió el área: las resolvió arreglar el
geocodificador (ver §3.4).

Las 31 que quedan no se arreglan con código:

- **25 no tienen ningún dato** — ni dirección, ni barrio, ni código de barrio.
  Solo el nombre.
- **5 son nombres de lugar, no direcciones**: salones comunales y conjuntos. Se
  buscaron en internet y no aparecen; son equipamientos de junta de acción
  comunal, sin ficha pública. Solo el área sabe dónde quedan.
- **1 no existe en Catastro** con la dirección registrada.

Todas se pintan en la sede de la Alcaldía, marcadas y desapiladas, y se listan
en el panel del mapa con lo que le falta a cada una.

### 3.4 Lo que sí se arregló (2026-08-03)

De las 18 sedes que tenían dirección sin resolver, **12 quedaron ubicadas**. No
era problema de las direcciones:

- El guardia de la localidad filtraba por `placa_domiciliaria.en_kennedy`, que
  estaba desalineada con el contorno oficial (~2 % de las placas, todo en el
  borde — y la Carrera 68 es el límite oriental). Se realinearon **33.207
  placas**. Eso además arregla el autocompletado de direcciones de TODOS los
  formularios, que filtra por esa misma columna.
- El primer candidato que resolvía fuera terminaba la búsqueda, así que el
  segundo —el que mueve el SUR a la placa, como escribe Catastro— no se probaba.
- `CLLE` no estaba entre las abreviaturas, y la vía pegada al número (`CRA75`)
  descartaba la dirección entera.

De las 12: 4 con placa exacta, 7 por tramo de vía (marcadas para afinar el
número) y 1 fuera de la localidad, escrita con su propia dirección sin corregir
(decisión de Alex: *"son datos y hay que ponerlos"*).

**Pista pendiente para el área:** la sede que quedó fuera tiene registrada una
carrera cuya placa no cae en Kennedy; la misma placa en una carrera vecina sí
existe y sí está en la localidad. Parece un dígito mal digitado, pero no se
tocó — el dato se cambia cuando el área lo confirme, no antes.

### 3.5 Festivales de Cultura — conectados, pero a medias (2026-08-05)

La cadena ya funciona de punta a punta y el tablero muestra datos reales, no un
número inventado. Lo aplicado el 2026-08-05 (scripts `018`–`019`):

- Borrado el festival de prueba id=11. Quedan **8**.
- Creados los actos **89, 90 y 91** — uno por cada festival publicado, con el
  **punto propio de cada festival**, no la sede de la Alcaldía.
- Los 3 pasaron a `ejecutado` y el **KPI 15 quedó en 3 de 60**.

Antes, el tile decía `9 · 0 / 15` y ese 15 era un literal en la vista: resultó
ser la meta del **KPI 12 (organizaciones)**, otra meta distinta. Hoy sale del
KPI real y, si no hay nada conectado, dice "Sin conectar" en vez de comparar
contra una cifra que no existe.

**Lo que falta, y es de Cultura, no de código:**

| | |
|---|---|
| 5 festivales sin fecha ni actos | Rock Techotiba, Hip Hop, Libertad Religiosa, Góspel, Festival de Festivales. Sin fecha no se les puede crear acto |
| responsable | solo lo tiene *Popular y Carranga*; faltan 7 |
| `fecha_fin` de *Kennedy Territorio Salsa* | dice 12-jul y el festival fue de **un día** (11-jul) |
| fotos / aforo | 0 en los 8. Ninguno cuenta como documentado |
| encuesta de percepción | **sí funciona**: 8 respuestas (7 en Salsa, 1 en Popular y Carranga) |

**La pregunta grande, para llevar a Cultura:** la meta 2026 es **60 eventos** y
hay 8 festivales de un día. Por esta vía se llega a 8, no a 60. O los festivales
tienen actos internos que cuentan por separado, o el KPI 15 se alimenta también
de eventos culturales que no son festivales — la actividad del plan se llama
*"Realización de eventos culturales"*, no *"festivales"*. Sin resolver eso, el
tablero va a mostrar un incumplimiento que quizá sea un problema de registro.

Reversible: devolver un festival a `planeado` borra su avance automáticamente.

### 3.6 El ciclo completo: actividad, evento y contrato sin ordenar

Pendiente abierto por Alex el 2026-08-05. Medido en producción ese día:

| | |
|---|---|
| `ActividadPlan` | 54 |
| `Evento` | 54 |
| Eventos **con** `actividad_plan` | **22 de 54** |
| Vinculaciones contrato↔actividad activas | 14 |
| `ActividadPlan` **sin** contrato | **42 de 54** |

Dos huecos concretos, no teóricos:

- **32 eventos no cuelgan de ninguna actividad del plan**, así que no aportan a
  ningún KPI por más que se ejecuten. Es el mismo defecto que tenían los
  festivales, multiplicado.
- **42 actividades del plan no tienen contrato**, o sea que la parte financiera
  de la cadena está sin registrar para la mayoría.

**Y hay un problema de nombres que confunde a todo el mundo, con razón:** dos
cosas distintas se llaman "actividades" en la misma app.

- `/app/actividades` → son **Eventos** (se renombraron a "actividades" en la UI
  en 2026-04-25, pero el modelo sigue siendo `Evento`).
- `/app/presupuesto/actividades` → son **ActividadPlan**, las del plan SIPSE.

Un evento es la ejecución concreta; una actividad del plan es la línea
presupuestal a la que esa ejecución aporta; el contrato es lo que la financia.
No son lo mismo, pero la interfaz los llama igual. Ordenar esto es primero
decidir el vocabulario y después alinearlo en UI, rutas y documentación.

### 3.7 Metas y proyectos oficiales (SIPSE / SIPLAN)

La cadena existe en el modelo pero está **desconectada de la fuente oficial**:
falta enganchar `metas.codigo_meta` e ingerir los datos que vienen de SIPSE y
SIPLAN. No es trabajo nuevo de diseño — el plan ya está escrito en
[`docs/propuestas/alineacion_sdp_pdl_plan.md`](docs/propuestas/alineacion_sdp_pdl_plan.md),
con el marco oficial en [`docs/referencia/SIPSE.md`](docs/referencia/SIPSE.md).

⚠️ **Ojo antes de retomarlo:** ese trabajo involucra CSV con datos personales y
este repo es público. Nada de direcciones ni documentos adentro (Ley 1581).

### 3.3 Decisiones ya tomadas (2026-08-03)

- **`QR_TOKEN_ENFORCE` se queda en modo suave.** Decisión de Alex: sin token se
  registra un warning y no se bloquea, para no invalidar los QR ya impresos.
  `QR_TOKEN_ENFORCE` no está en `.env` (default `False` en `settings.py:337`).
  Activar la fase 2 sigue siendo posible, pero exige reimprimir los QR vigentes
  **antes**; no es un pendiente abierto sino una decisión consciente.

- **Las actividades sin ubicación se quedan donde están, marcadas.** Son **18**,
  no 13 (verificado contra la BD el 2026-08-03), y **ninguna tiene de dónde
  sacar una ubicación real**: `descripcion` vacía en las 18 y sin territorio en
  su `actividad_plan`. Doce son metas del subgrupo 38 con fecha `2025-01-01` —
  metas de vigencia, no hechos ocurridos en un lugar. Ponerles un punto
  "cercano" sería inventarlo, que es justo lo que prohíbe la regla de que las
  direcciones deben existir.

  Lo que sí está resuelto es que no mientan: se desapilan en abanico, se pintan
  con borde punteado y relleno pálido, y el popup abre diciendo *"Ubicación no
  registrada"* (`mapa.component.ts:1771+`). Y la raíz está cerrada hacia
  adelante: `evento-form.component.ts` ya captura la dirección con
  `app-direccion-picker` (autocompletado Catastro + pin), así que las
  actividades nuevas nacen con lat/lon propio.

- **Deuda L4 — hecha.** `apps/kordial` y `apps/VitalK` ya no existen en disco ni
  quedan referencias en el código. No hace falta el `sudo rm`.

---

## 4. Verificación al cierre del 2026-08-03

- Tres troncales con árbol idéntico, sincronizadas con `origin`.
- `.claude/worktrees/` borrado (496 MB, 9 carpetas) — **con una salvedad, ver
  abajo**.
- Ramas locales: solo las tres troncales.
- Suite de smoke tests corrida por el hook `pre-push`.

**El borrado quedó a medias, y se terminó el mismo día.** Este punto decía
"borrado por completo" y no era exacto: sobrevivieron 8 carpetas con **24 MB en
2.643 archivos `.pyc`, todos de root**. El contenedor corre como root y deja los
`__pycache__`; al borrar las carpetas desde el host esos archivos no se pudieron
eliminar y quedaron los esqueletos de directorios. Es el mismo patrón que dejó
`apps/kordial` y `apps/VitalK` (deuda L4).

No hacía falta `sudo`: el contenedor monta el árbol y ya es root, así que
`docker exec innova_k rm -rf /app/.claude/worktrees` los limpió. `.claude/`
quedó en 664 KB.

**Se verificó que no se perdió trabajo** antes de borrar. En el object store
quedaban commits colgados de las ramas retiradas; casi todos son `git stash`
viejos. De los que sí eran trabajo real, `git cherry` marcaba dos como ausentes
de `produccion` — pero su contenido sí está, con otro hash: el gate
`es_coordinador` / `puede_crear_en_area` vive en `apps/login/services/permisos.py`
con su test `test_rbac_pra_crear_actividad.py`, y el DDL del lote 4 del Banco en
`apps/banco_iniciativas/scripts/004_banco_qa_lote4.sql`. Un `+` de `git cherry`
significa "este parche exacto no está", no "este trabajo falta": un commit
rehecho o remergeado cambia de hash sin perder nada.

**Repaso de los pendientes (misma fecha, más tarde).** De los cinco puntos que
esta sección daba por abiertos, dos estaban cerrados hacía semanas (§3.1 desde
el 2026-07-14, L4 borrado del disco) y dos eran decisiones, no trabajo. El único
que sigue dependiendo de un tercero es la respuesta del área sobre las 43 sedes
(§3.2). Un estado que da por abierto lo que ya está hecho cuesta lo mismo que
uno que da por hecho lo que falta: manda el código, no el documento.

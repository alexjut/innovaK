# Estado de innovaK

**Al 2026-08-05.** Un solo archivo, en la raíz, sobre la rama `produccion`.

> **📍 Empieza por [`docs/RUMBO.md`](./docs/RUMBO.md)** (2026-08-05): la auditoría
> completa —fuentes, código muerto, cadena, docs, a11y, mapa y deuda— con el
> orden de ataque y qué depende de quién. Este archivo sigue siendo el detalle
> por frente; RUMBO es el mapa.
>
> **Para retomar:** lo que sigue abierto está en §3, ordenado. Lo más grande hoy
> es §3.6 (el ciclo actividad–evento–contrato) y §3.7 (metas y proyectos
> oficiales). Lo que depende de terceros: §3.2 (31 sedes, espera al área),
> §3.5 (festivales, espera a Cultura) y §3.8 (Educación y CAI: falta que SED
> concilie 74 vs 75 sedes y que Seguridad diga dónde están los CAI móviles).

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
| Módulo Educación: 48 colegios / 79 sedes / 95.909 alumnos + entregas de insumos (2026-08-05) | `apps/educacion/`, `features/educacion/` |
| Capa CAI en el mapa: 15 CAI de Kennedy, fijo vs móvil diferenciados (2026-08-05) | `apps/georeferenciacion/`, `features/mapa/` |

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

### 3.8 Educación y CAI — entregado el 2026-08-05, con dos cabos sueltos

Rama `feat/educacion-colegios-cai`. Aplicado en `poblacion_kennedy` y en vivo.

**Colegios distritales.** Módulo nuevo `apps/educacion` + `/app/educacion`.
La fuente es la capa oficial de la Secretaría de Educación publicada por
IDECA (`educacion/infraestructuraeducativa/MapServer/0`, corte 2025-12-31),
cruzada por `DANE12_SED` con la de matrícula (`educacion/matricula/MapServer/1`,
corte 2025-04-30). Cargado con `manage.py sync_colegios`:

| | colegios | sedes |
|---|---|---|
| Distritales | 44 | 75 |
| Distrital – administración contratada | 4 | 4 |
| **Total oficial** | **48** | **79** |

95.909 alumnos. Las 79 sedes tienen coordenada (cero sin ubicar, a diferencia
de las escuelas de formación). 4 sedes no traen matrícula en la capa oficial:
CIUDAD FLORALIA (Carlos Arango Vélez), SEDE B - ELOÍSA GARZÓN (Marsella), la
sede principal de Jaime Hernando Garzón Forero y SEDE B - GABRIEL BETANCOURT
MEJÍA.

**🔴 Cabo suelto 1 — el 74 contra el 75.** Al área le dijeron que eran 74
sedes; la fuente oficial dice 75 distritales. La diferencia es de UNA y hay
que conciliarla con SED fila por fila (el DANE de sede está cargado, así que
se compara contra cualquier archivo que manden, no por conteo).

**Entregas de insumos.** Tabla `entrega_insumo_colegio`: una fila = un insumo
en una sede, con el contrato que lo pagó, cantidad, valor, beneficiarios,
acta y fecha. El insumo sale del catálogo compartido `implemento`, al que se
le agregó la categoría `educativo` con 10 ítems. **No confundir con
`entrega_insumo` (apps.entregas), que es a una PERSONA con cédula y firma.**
Hoy la tabla está vacía: espera el archivo de liquidación de los contratos
2025.

**CAI.** Capa nueva en el mapa, fuente Secretaría de Seguridad
(`oaiee.scj.gov.co/.../EquipamientoPMSDSCJ/MapServer/22`), cargada con
`manage.py sync_cai`. **15 CAI en Kennedy**, todos fijos.

**🔴 Cabo suelto 2 — los CAI móviles no existen en la fuente.** La capa sí
conoce la distinción (su dominio de localidad trae el código `00 = MOVILES`),
pero devuelve cero móviles en toda Bogotá. La columna `tipo` (FIJO/MOVIL) y
el ícono diferenciado ya están; el sync solo pisa las filas `fuente='SCJ'`,
así que Seguridad puede cargar los móviles a mano sin que se los borre. Falta
que Seguridad diga cuáles son y dónde.

De paso: SCJ publica `SistemaVideoVigilancia/CamarasTerritorio`, pero solo
**agregado** (cámaras por localidad / UPZ / sector / cuadrante), no el punto
de cada cámara. Si algún día piden el mapa de cámaras, eso es lo que hay.

---

### 3.9 Panel de área: un solo panel para las 15 (2026-08-05)

Rama `feat/educacion-colegios-cai`. En vivo en `/app/area/<id>`.

**El problema que resolvió.** El panel anterior (`/app/subgrupo/<id>`) derivaba
todo de `evento.subgrupo_id`. Funcionaba para las áreas que capturan eventos y
dejaba en blanco a las que no. Medido: **Deporte tiene 24 actividades del plan
y UN evento**; Educación e Infraestructura tienen proyecto, contratos y módulo
propio, y **cero eventos**. Sus paneles salían vacíos teniendo trabajo.

**El ancla ya existía y no hizo falta DDL.** Los 11 proyectos tienen
`subgrupo_id` y toda actividad del plan cuelga de un proyecto: el área de una
actividad se sabe sin preguntarle a ningún evento. `panel_area.py` arma desde
ahí `Área → Proyectos → Metas/KPI → Actividades → Contratos + Eventos`.

**Registro de módulos en dos capas** (`modulos_area.py`), para no escribir 15
componentes:
- **Propios**: Cultura → festivales + escuelas; Educación → Jóvenes a la E +
  colegios (es el MISMO proyecto 0002377, por eso van juntos); Infraestructura
  → obras; Seguridad → CAI; Participación → votaciones.
- **Transversales**, que aparecen solos donde hay datos: Banco de Iniciativas,
  cursos y capacitaciones, entregas, caracterizaciones. El Banco **no es de
  Deporte**: Seguridad también tiene una convocatoria, y la primera versión de
  este archivo lo tenía mal cableado.

**🔴 Lo que el panel dejó a la vista.** Cada área muestra sus sueltos:

| Área | act. sin meta | act. sin plata | contratos fuera del plan |
|---|---|---|---|
| Cultura | 10/15 | 15/15 | **15/15 ($713 M)** |
| Deporte | 23/24 | 24/24 | 0/0 |
| Seguridad | 0/12 | 0/12 | 0/0 |
| Educación | 1/1 | 1/1 | 0/0 |
| Infraestructura | — | — | 4/4 |

Global: **20 de 24 contratos no llegan a ninguna actividad**, 36 de 54
actividades sin KPI, 32 de 54 eventos sin actividad, 7 avances, **0
beneficiarios registrados**. Decisión de Alex: el dato histórico NO se migra
— cada área engancha sus contratos desde la pantalla nueva
(`POST /presupuesto/api/areas/<id>/contratos/vincular/`).

**Cada área tiene su lugar, y se entra por "Mi área".** Un módulo puede vivir
DENTRO del área (`"ruta": "/mi-area/{slug}/cai"`) en vez de en una pantalla
global: los CAI son de Seguridad, y mandar su tarjeta a `/mapa` la dejaba
buscando su capa entre las de todas las demás áreas. La capa sigue en el mapa
público porque eso es información para el ciudadano, no herramienta del área.

**La URL usa el nombre, no el id.** `/app/mi-area/educacion/colegios`, no
`/app/mi-area/8/colegios`. Se lee, se comparte sin explicar nada, y queda
alineada con la miga de pan: `Inicio › Mi área › Educación › Colegios` dice
exactamente lo mismo que la barra de direcciones, segmento por segmento.

El slug se DERIVA del nombre y no hizo falta columna: verificado sobre los 45
subgrupos, 45 slugs distintos, cero colisiones. La contra es que renombrar un
área cambia su URL, así que el backend **también acepta el id** y ningún
enlace viejo se rompe. `/app/subgrupo` queda como redirect a `/app/mi-area`
—está en marcadores y en el onboarding.

**El home lleva solo lo transversal.** Regla fijada el 2026-08-05: un módulo
de un área concreta NO va de primer nivel — se llega por "Mi área". Festivales
e Infraestructura salieron del home y del sidebar (desactivadas, no borradas;
`/app/festivales` y `/app/infraestructura` siguen respondiendo 200). Si cada
área pusiera la suya, el home terminaría con quince cards y ninguna jerarquía.
Votaciones se queda como excepción deliberada: cuelga de Participación en el
registro, pero es un sistema aparte con su propio flujo de QR.

El home queda en 7: Mi área · Actividades · Presupuesto · Mapa Kennedy ·
Votaciones · Consulta IA · Administración.

De paso, `seed_hub_cards` no sabía desactivar: una card retirada del catálogo
se quedaba viva en la tabla para siempre y el archivo no era la fuente de
verdad que decía ser. Ahora da de baja lo que ya no está.

**🔴 CORRECCIÓN (auditoría de la misma tarde).** Este documento afirmó que
había "0 beneficiarios registrados". **Es falso y el diagnóstico era erróneo.**
El 0 es el resultado de una query, no el estado de la base:

    apps/dashboard/services/cockpit_presupuesto.py:293
    actividad_plan → evento → participante_evento

Esa query no puede dar otra cosa que vacío, porque los datos están en
disyunción perfecta:

| | eventos | con actividad_plan | con inscritos | personas |
|---|---|---|---|---|
| `GENERICO` (Novenas, Recorridos) | 32 | **0** | 28 | **2.545** |
| El resto (curso, festival, banco…) | 22 | **22** | 0 | 0 |

**Los 28 eventos que tienen gente no cuelgan del plan; los 22 que cuelgan del
plan no tienen gente.** No falta captura: faltan 32 `actividad_plan_id`.

Y hay un segundo universo que la cadena tampoco ve: `beneficiario` tiene
**3.605** filas y `contrato_beneficiario` **2.950**. La intersección entre
`participante.persona_id` y `beneficiario.persona_id` es **exactamente 0**:
son dos cargas que nunca se cruzaron. Además `contrato_beneficiario.beneficiario_id`
está **100 % NULL** aunque los 2.892 documentos cruzan uno a uno con
`beneficiario` — es un UPDATE de una pasada, no un problema de datos.

**Los tres pasos que mueven el tablero de 0 a ~2.545** (horas, no semanas):
1. Poner `actividad_plan_id` a los 32 eventos GENERICO — es decisión del área,
   no código.
2. Cerrar `contrato_beneficiario.beneficiario_id` con el match por documento.
3. Llamar `asegurar_beneficiario_persona` desde `inscribir_persona`: es el
   único flujo de captura que NO lo llama, y es justo el que tiene las 2.545
   personas.

Lección: "0" en un tablero puede ser un JOIN vacío y no un dato faltante. Se
tomó por dato faltante durante toda una jornada.

---

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

---

### 3.10 Educación posmedia — cadena completa (2026-08-12/13)

Ramas `feat/jovenes-cargue-beneficiarios` y `feat/educacion-instituciones-mapa`,
cascadeadas. La cadena del proyecto 0002377 quedó cerrada punta a punta:

```
Proyecto 2805 ── Meta 8 (sector Educación) ── KPI 30 acceso 175/año ← 174
                                           └─ KPI 31 permanencia 175/año ← 0
   └── Contrato CIA-773-2025 · $23.168.769.452 ── Actividad 105 ── Evento 94
         └── 174 beneficiarios ── 34 instituciones (23 ubicadas) · 69 programas
```

**Panel del área: cero sueltos.** Es la primera área que lo logra.

**Cómo se llena lo que falta:** `docs/operacion/donde_se_llena_cada_dato.md`.

**🔴 Lo que sigue abierto y depende de terceros**

| Qué | De quién |
|---|---|
| CDPs (número, fecha, valor) — **SECOP no los trae**, verificado sobre sus 84 campos | Área / Hacienda |
| Acceso vs. permanencia por persona | Área |
| Archivo de liquidación 2025 (dotación a colegios) | Área |
| 11 instituciones sin ubicar (57 beneficiarios sin punto) | Área |

**Decisiones que quedaron tomadas**

- La unicidad de `entrega_beca` es de MATRÍCULA, no de persona: `(vigencia,
  documento, snies_ies, snies_programa)` con `NULLS NOT DISTINCT`.
- Una persona entra UNA vez por cargue, y **cuál de sus matrículas lo elige quien
  carga** — el servicio se niega a procesar si falta esa elección.
- El avance se **recalcula** por `(indicador, vigencia)` con `COUNT(DISTINCT
  persona)`; nunca toca los avances `MANUAL`.
- El acumulado del cuatrienio NO es la suma de las vigencias.
- El KPI lleva el aporte del AÑO; el cuatrienio va en el nombre de la meta
  (patrón Cultura).
- `GestorEducacion` mantiene el catálogo. **Sin prefijo `Coordinador`**, que
  otorgaría creación de actividades y contratos por RBAC.

**Tres defectos que aparecieron al hacerlo, y no los buscaba nadie**

1. El marcador de avance emparejaba por prefijo (`entrega_beca=1` encontraba a
   la 11): borraba filas ajenas al revertir. Cinco módulos afectados.
2. El `DISTINCT` de personas arrastraba el `Meta.ordering` del modelo y contaba
   MATRÍCULAS. Daba bien de casualidad, con una matrícula por persona.
3. `ui-badge--danger/--warning/--neutral` se usaban 33 veces en la app y no
   existían en ningún partial: se pintaban sin color.

---

### 3.11 Matriz PDL de la ALK — cargada, y la plata todavía no (2026-09-01)

La fuente oficial abierta de Planeación —el espejo `sdp_meta_oficial`— **está
parada desde el 2026-02-18**. La ALK siguió reprogramando metas igual y las
manda a mano en `Matriz de seguimiento PDL 2025-2028.xlsx`. Para eso existe
`apps/presupuesto/management/commands/importar_matriz_pdl_alk.py` (seco por
defecto, firmado, idempotente; commit `847ebbb`).

**Lo que quedó cargado y verificado en BD**, todo auditado en `auditoria_dato`
con la observación «Matriz PDL ALK» y firmado por `alexjut`:

| | |
|---|---|
| 18 | proyectos creados |
| 56 | indicadores/metas nuevos |
| 22 | metas completadas con metadatos SEGPLAN (solo columnas que estaban en NULL) |

**Cobertura PDL: de 12/28 proyectos a 28/28, `faltan: 0`.** El cockpit
(`/app/presupuesto/dashboard`) ya lo refleja: `comparacion_sdp` pasó de ~21
filas a 76, y 31 proyectos en la base.

**Ambiente dejó de atribuirse por sector y pasa por proyecto** —la vía
precisa— **por la misma cifra exacta** ($17.760.050.000). Que no se moviera al
cambiar de vía confirma que las dos rutas concuerdan. Hoy ningún subgrupo usa
ya el fallback por sector.

#### La plata: cargada, y «Programado» salió de la pantalla

**El mismo día se cerró el hueco.** DDL `020_presupuesto_meta_vigencia.sql`
aplicado (aditivo, rollback de un `DROP`) y **312 filas meta×vigencia**
cargadas desde el Excel con las cuatro columnas: proyectado PDL, apropiación
POAI, comprometido y girado.

**Por qué una tabla nueva y no `sdp_meta_oficial`.** Su UNIQUE es `(vigencia,
proyecto, indicador)` **sin `fuente`**, así que escribir ahí no agrega una
fuente en paralelo: PISA la fila oficial. Ya se intentó y rompió 10 tests. En
la tabla nueva `fuente` va **dentro** del UNIQUE. Esa lección quedó escrita en
el schema, no en un comentario.

**Por qué la apropiación y no el proyectado.** El «Presupuesto proyectado PDL»
es la meta aspiracional del cuatrienio; la **Apropiación POAI inicial** es lo
que de verdad se asigna para ejecutar. La cadena real es

    Apropiación → Comprometido → Girado

y el cockpit venía encabezando con el proyectado. Con la cifra correcta, el %
de ejecución cambia de sentido: **11,0 % comprometido y 1,3 % girado** sobre lo
apropiado, contra 6,2 % y 0,7 % que daba antes — que mezclaba cuatro años de
meta con dos de plata real.

**Dos cosas que solo aparecieron al medir:**

1. **La apropiación es MAYOR que el proyectado, no menor.** 2025 apropió
   $187.520 M contra $163.049 M proyectados (+15 %); 2026, +12 %. Se financió
   por encima del PDL.
2. **Dice «2025-2026», no «2025-2028», y es a propósito.** El POAI se apropia
   año a año: 2027 y 2028 vienen VACÍAS en la matriz. Rotular la suma como
   cuatrienio haría ver $376 mil M contra $667 mil M como si fuéramos a la
   mitad, cuando lo que pasa es que faltan dos años por apropiar. El rango se
   calcula del dato: cuando llegue la matriz con 2027, el rótulo se mueve solo.

#### «Programado» ya no aparece en la interfaz — y qué se dejó, y por qué

La palabra era ambigua: nombraba tres cosas distintas y por eso se esperaba ver
la apropiación donde había una proyección. Se separaron:

**Los rótulos nuevos NO se inventaron: son los encabezados literales de la
matriz.** Es la diferencia entre que un área reconozca su propia cifra o tenga
que traducirla. «Meta programada» ya coincidía por casualidad; los otros se
alinearon después de leer los encabezados del Excel uno por uno.

| Antes | Ahora | De dónde sale / qué es |
|---|---|---|
| Programado *(plata PDL)* | **Presupuesto proyectado PDL** | Encabezado literal del Excel. Meta aspiracional del cuatrienio; ya no encabeza. |
| Programado *(magnitud)* | **Meta programada** | Encabezado literal del Excel. Unidades, no pesos: «700 estudiantes». No se apropia gente. |
| Programado *(pagos)* | **Pago programado** | NO está en la matriz: es el plan de pagos del contrato, por período. |
| Programado *(contrato)* | **Programado (CDP)** | NO está en la matriz: es el respaldo del CDP. Ni PDL ni POAI. |

Y la cifra que encabeza se llama **«Apropiación POAI inicial»**, que es como la
nombra la matriz — no «Apropiación» a secas.

**Lo que NO se tocó, y es deliberado: las columnas de `sdp_meta_oficial`.**
`total_programado`, `valor_programado` y `magnitud_programada` **copian
literalmente los nombres de la fuente oficial** — `TotalProgramado`,
`ActividadValorProgramadoTotal`, `ActividadMagnitudProgramadaTotal`— y así los
mapea `ingest_sdp_datos_abiertos`. Renombrarlas rompería el sync que corre cada
noche y, peor, borraría la trazabilidad: el sentido de un espejo es poder
contrastarlo contra su origen campo por campo. Además no cambiaría nada de
fondo — Planeación va a seguir llamándolo «Programado» aunque nosotros no.

La palabra desapareció de donde confundía (la pantalla). Donde describe de
dónde vino un dato, se queda.

#### Pendientes de decisión de Alex

1. **Subgrupo del proyecto 2740** (comunidades étnicas: rom, negras, raizales,
   indígenas). Ningún subgrupo existente nombra «asuntos étnicos»; quedó en
   Participación por descarte y marcado «⚠ revisar» por el propio importador.
2. **10 indicadores donde la ALK reprogramó 2026 pero el KPI vivo quedó con
   otra magnitud.** El importador los REPORTA y no los toca: cambiar la meta de
   un área en curso sin que nadie lo vea es el error que ya costó una fila mal
   enganchada. Hay que decidir uno por uno.
3. **Los proyectos 2556 (Mujeres sin Barreras) y 2643 (Ecomanos en Acción) no
   tienen par en el espejo oficial.** No son basura: son reales, están
   auditados, y no cruzan porque la fuente oficial se quedó atrás. Se
   resuelven solos cuando Planeación se ponga al día.
4. **Las vigencias 2027-2028 no tienen apropiación** porque el POAI se apropia
   año a año. No es un vacío que haya que llenar: llegará con la matriz del año
   que viene y el rótulo se ajusta solo.

*(El DDL de la plata, que era el punto 4, se aplicó y se cargó el mismo día.)*

#### Los tests: 15 en rojo, ninguno era un defecto

La base creció y las cifras escritas a mano se quedaron viejas. Donde el
número era el punto se re-midió; donde no, se cambió por la invariante que de
verdad se cuidaba —contar contra la BD en vez de contra una constante—. El
caso que más enseña es el de fan-out: comparaba contra el «43» de
Infraestructura (hoy 1144) y fallaba **sin que nada se hubiera roto**, porque
un número congelado no distingue *«volvió el fan-out»* de *«entraron
indicadores nuevos»*, que es justo lo que tiene que distinguir. Ahora calcula
el denominador aparte y lo compara.

Aparte, ocho metas cuyo objetivo es **1** («1 casa LGBTI», «1 sede
administrativa», «una (1) iniciativa» por comunidad étnica) rompían la
tolerancia: SDP las anualiza en 0,30 y 0,30 × 4 = **1,20**. Es redondeo de la
fuente —el cuarto exacto sería 0,25—, no doble conteo. Con denominador 1 ese
redondeo se come toda la tolerancia relativa, así que se aceptó además media
unidad absoluta: nadie entrega media casa. Sumar una «Constante» de 1 sigue
dando 4,0 y sigue cayendo.

**1488 tests OK, 7 skipped.**

### 3.12 CRP de BogData y la coherencia con la Matriz (2026-09-07/09)

Dos frentes de la misma semana. El primero fue hacer que el front de Anderson
diga lo mismo que la Matriz —regla de Alex: *«la base de todo es la matriz»*—
y el segundo, ingerir el CRP de BogData, que es lo que SECOP no da.

#### La coherencia: una sola implementación del avance físico

El proyecto 2706 aparecía «Ejecutada» en una pantalla y «Crítico» en otra. No
era un dato malo: eran siete lectores calculando el avance cada uno por su
lado. Ahora sale entero de `apps/presupuesto/services/avance_matriz.py`, una
consulta base y cinco agregaciones, con caché de proceso de 30 s porque se lo
llama en bucles de hasta 200.

Reglas que quedaron fijadas ahí y conviene no volver a discutir:

- **Promedio simple de metas, nunca razón de magnitudes.** Las unidades no se
  suman: motos, sedes y personas no hacen un denominador.
- `cumplimiento_pct` viene en **tanto por uno** desde la Matriz. Se convierte
  UNA vez, en el servicio.
- Se cuentan **metas distintas**, no filas del join, o el fan-out infla.
- `None` y `0` no son lo mismo: *un vacío no se pinta de rojo*, *$0 no es sin
  dato*.

#### El CRP: 2.630 filas, y una revisión que valió la pena

Cargado el 2026-09-08 con `cargar_crp` (seco por defecto, firmado, idempotente
por la PK natural del reporte). DDL 026 y 027 aplicados. El archivo fuente
—`CRP 07092026.xlsx`— **está sin versionar en la raíz del repo**.

Dos errores de la especificación los cazaron los tests, no la lectura:
`valor_neto = valor_crp − anulaciones` (sin reintegros, confirmado contra los
totales del propio archivo) y el offset del proyecto en el rubro, que la
especificación daba en `[16:20]` y devuelve `7110` en vez de `2711`.

La revisión adversarial dio **19 hallazgos**: 4 los cubrió el arreglo de
`metrics`, **6 no sobrevivieron a la verificación** y **9 eran reales**. Los
seis refutados están escritos con su motivo medido en
`docs/diagnosticos/review_crp_bogdata.md`, porque son lecturas razonables del
código que volverán a proponerse.

Los dos que importaban:

1. **No había permiso de escritura.** Subir el CRP o aplicar la Matriz no
   editan una fila: reemplazan el libro entero. El endpoint solo pedía
   `presupuesto_proyectos`, que también tiene el rol de un solo contrato.
   Reproducido con su token real: el comprometido de la localidad caía a
   $56 M, sin vuelta atrás desde la pantalla. Ahora la escritura exige
   `presupuesto_cdp`.
2. **El upsert congelaba 37 de 50 columnas** y las tres derivadas sí se
   movían: la fila del corte siguiente quedaba con el proyecto nuevo y el
   rubro viejo. El SQL ahora se deriva de una lista única de columnas, así que
   el SET es el INSERT menos la llave por construcción y no por disciplina.

#### El comprometido es el del cuatrienio, no el del estado de cuenta

Decisión de Alex el 2026-09-09: *«las vigencias pasadas no las contemos… solo
el cuatrienio 2025-2028»*.

| | |
|---|---|
| Estado de cuenta completo (BogData) | $226.744.982.139 |
| **Comprometido del PDL 2025-2028** | **$184.839.187.185** |
| Anterior al PDL, separado y visible | $41.905.794.954 |

**El corte va por el AÑO DEL COMPROMISO, no por `es_obligacion_por_pagar`**, y
esa distinción es la que hay que conservar: de los $135.078 M de obligaciones
por pagar, **$93.209 M son de compromisos de 2025** —dentro del Plan— y solo
$41.906 M vienen de 2024 hacia atrás, hasta 2013. Cortar por la bandera se
lleva los $93.209 M junto con el resto. Las 140 filas sin año parseable se
quedan DENTRO: son del ejercicio en curso.

#### El gate de escritura, y por qué está donde está — CERRADO (2026-09-10)

`javier.prieto`, `anderson.rojas` y `alexander.gil` quedaron promovidos a
superusuario. Estaban en el grupo Admin con los 19 módulos pero no eran
superusuarios, y `subgrupos_visibles` solo devuelve `None` —o sea, «ve todo»—
para un superusuario: los tres quedaban acotados a su subgrupo aunque
administraran el sistema. **Con eso hay siete cuentas de alcance global**
(las cuatro de antes más estas tres).

Y el gate de escritura pasó de `presupuesto_cdp` al **alcance**, que es el
criterio exacto: quien solo ve una parte de la localidad no puede reemplazar
el libro de toda —es la misma frase leída como permiso, y no depende de qué
módulos tenga asignado un rol—. Entre el 09 y el 10 estuvo en el módulo, que
distinguía lo mismo por casualidad, para no dejar a esas tres cuentas sin
poder cargar.

Verificado en vivo: los cuatro con alcance global reciben 400 en el POST (o
sea, pasan el permiso y el endpoint se queja del archivo que no se mandó) y
`miguel.arias` —`Lider_contrato`, el rol provisionado para un solo contrato—
recibe 403. Los cinco siguen leyendo el historial en 200: **el gate es de
escritura, no de lectura**.

El enmascarado de la cédula sigue siendo por módulo (`presupuesto_cdp`) y no
por alcance, a propósito: es sensibilidad del dato, no territorio.

#### Lo demás que queda abierto

- **Los 23 registros de CRP por $11.200 M cuya atribución a proyecto se
  recupera por el contrato** aplican desde el próximo corte: el arreglo corre
  en la carga y septiembre ya está aplicado. Si urge antes, el camino
  sancionado es reguardar el Excel (bytes distintos, dato idéntico → hash
  distinto) y volver a subirlo.
- Los diez confirmados de `review_crp_bogdata.md` que no se han tocado, entre
  ellos los tres frentes de `tercero_sap` (el NIT distrital 899999061 que
  colapsa siete entidades bajo $34.771 M, el rendimiento del upsert de
  terceros, y el `COMMIT;` embebido del DDL 026).
- Las doce mezclas de plata de `docs/diagnosticos/auditoria_fuentes_matriz_pdl.md`.
- Cinco discrepancias SECOP contra Matriz que necesitan decisión de negocio
  (2780: 99,2 % contra 28,4 %; 2790: 76,4 % contra 0,6 %).

**1566 tests OK, 7 skipped.** Cascadeado a las tres troncales
(`produccion=567f0a0`), contenedor reiniciado, `/app/` 200.

### 3.13 El mapa de fuentes, las cinco discrepancias y el CRP endurecido (2026-09-10)

Rama `fix/crp-endurecimiento-corte-octubre`, salida de `desarrollo`.

#### Las cinco discrepancias eran tres cosas

El mapa completo —qué aporta cada fuente y quién manda para cada dato— quedó en
[`docs/diagnosticos/mapa_fuentes_matriz_secop_bogdata.md`](docs/diagnosticos/mapa_fuentes_matriz_secop_bogdata.md).
Lo que hay que retener:

**Tres de las cinco no existían.** SECOP marcaba 0,0 % en 2377, 2574 y 2706, y
ese cero no era una medición: `valor_pagado` no llega nunca en NULL —3.123 de
3.123 filas del espejo lo traen—, así que «no giró» y «nadie cargó el pago» son
el mismo cero. **152 contratos de 2025 en adelante, por $70.204 M, están en
cero**, y entre ellos el CIA-773-2025, que BogData reporta con **$8.818.769.452
girados**. Aplicada la regla: sin fuente no se califica ni se anota. `_semaforo`
dejó de anotar esos tres y, sin Matriz, devuelve `incompleto` con base
`secop_sin_giros` en vez de pintar de rojo a un área por un campo que su
contratista no diligenció.

**2780 es cobertura.** SECOP ve 15 contratos por $713.221.534, o sea el **9,1 %**
de los $7.794.984.904 que la Matriz da por comprometidos, y sobre esa novena
parte casi todo está pagado. Las dos cifras eran ciertas sobre universos
distintos. La anotación ahora dice cuánto alcanza a ver el espejo antes de decir
qué porcentaje reporta. Numerador `Σ contrato.valor` del proyecto —la misma base
sobre la que se calcula el % de SECOP— y denominador el comprometido de la
Matriz.

**2790 es vigencia, y cierra.** Sus 2 contratos cruzan con SECOP y cubren el
84,1 % del comprometido, así que no es cobertura. Los tres CRP de COP-816-2025 y
CON-993-2025 son de **ejercicio 2026 con año de compromiso 2025**, rubro
**O230689 «Obligaciones por pagar Inversión vigencia anterior»**: el dinero se
giró, como obligación por pagar. La Matriz mide el giro contra la apropiación de
cada vigencia y SECOP el pago acumulado del contrato. Homologada la vigencia,
las tres fuentes concuerdan. **No se escribió al área**: no hay discrepancia que
reportar, solo una pregunta abierta sobre si la Matriz reflejará esos giros en
alguna vigencia.

#### Los cuatro arreglos del CRP, antes del corte de octubre

Los cuatro fallaban **solo en el segundo corte**, y ninguno con un mensaje de
error.

| # | Qué hacía | Qué hace ahora |
|---|---|---|
| 12 | `uq_crp_interno_posicion` era único sobre dos columnas nullables, y dos NULL no chocan: una fila sin llave se insertaba de nuevo cada mes | `validar()` la rechaza con el número de fila del Excel; **DDL 028** pone las dos columnas NOT NULL |
| 3 | Siete entidades distritales comparten el NIT de Bogotá D.C. y colapsaban en un tercero: $34.771 M a nombre de quien no los recibió | `bp_sap` entra en la llave (DDL 028) y la lista muestra el nombre de la fila. Integración Social recupera sus **$31.127.780.186** |
| 6 | `_upsert_terceros` emitía 8.472 sentencias y sostenía 1.412 bloqueos `FOR UPDATE`: dos cargas simultáneas se trababan | **una** sentencia con las claves ordenadas. Medido: 11.210 → 2.741 sentencias, 1,74 s → 0,5 s |
| 7 | El `corte` se filtraba por la fecha del join y el upsert pisa `carga_id`: pedir un corte viejo daba ceros que parecían medidos | Se resuelve contra `crp_carga`: 400 si no existe, **409** si no es el último, con el motivo escrito |

**DDL 028** (`028_crp_llaves_naturales.sql` + rollback) aplicado con backup del
día. Aditivo en datos: no borra ni reescribe ninguna fila.

Verificado con el archivo real en transacción revertida: 2.630 filas,
$226.744.982.139 de neto, las siete entidades separadas con su nombre y su
plata, y `proyecto_por_contrato = 23` —los 23 registros por $11.200 M que entran
solos en octubre—.

**1582 tests OK, 7 skipped** (16 nuevos). Contenedor reiniciado, `/app/` 200,
los dos endpoints de CRP en 401 sin credenciales.

#### Ramas

Locales **38 → 6**: las 33 fusionadas al 100 % en `produccion` borradas una por
una. Se conservan las tres troncales y las dos con trabajo propio:
`feat/fase-c-carga-matriz` (3 commits) y `feat/brain-spec-kit` (1 commit de
documentación). **No se tocó ninguna rama remota** —eso es un push— ni los
archivos del frontend que otra persona tiene modificados en el árbol
compartido.

### 3.14 Una sola fuente para la plata: las siete fases (2026-09-10)

Rama `fix/crp-endurecimiento-corte-octubre`. Siete commits, todos en vivo.

El defecto de fondo: **el sistema no tenía UNA forma de responder «cuánta plata
tiene esto»**. Convivían seis registros y cada recuadro eligió el suyo sin
declararlo. Es la misma forma que tenía el avance físico antes de
`avance_matriz`, y se cerró igual.

| Fase | Qué se cerró | Medido |
|---|---|---|
| 1 | Nace `plata_matriz`, única implementación, con el contraste adentro | — |
| 2 | El tablero encabeza con la Matriz y el selector de año lo mueve entero | 11,0 % → **59,7 %** comprometido |
| 3 | Los dos paneles de área | 3 → **16** áreas con cifra |
| 4 | Objetivos deja de contradecirse | $667.578 M → **$376.458 M**; 29,7 % → **59,7 %** |
| 5 | Festivales | «Asignado $0» → **$12.392.980.000** apropiado |
| 6 | El programa del proyecto sale del Plan | 5 → **30 de 31** fichas |
| 7 | El rótulo deja de nombrar una cosa y contar otra | la fila suma 30 → **76** metas |

**Cuatro reglas quedaron fijadas en `plata_matriz`** y no conviene volver a
discutirlas: la plata SE SUMA (a diferencia del cumplimiento, que se promedia
porque motos y personas no hacen un denominador); `None` nunca es `0`; la
vigencia filtra y sin ella se acumula; y ninguna cifra viaja sin su cobertura.

**Tres cosas que solo aparecieron al medir:**

- **BogData atribuye a un proyecto solo $86.603.918.854 de los $184.839.187.185
  del Plan.** Las obligaciones por pagar de vigencias anteriores traen un rubro
  que no identifica proyecto ($92.160.547.878 en 1.056 filas). Sumando las
  filas visibles, la diferencia contra la Matriz salía $138.249 M en vez de los
  $40.014 M reales, y ese exceso no es un desacuerdo: es plata que BogData no
  alcanza a atribuir. El total sale de `metrics`, las filas suman aparte, y la
  respuesta declara las dos cosas.
- **El selector de año nunca movió nada, y no por falta de plomería.** El bucle
  de contratos desempaqueta cada fila en una variable llamada `vigencia`, que
  pisaba el parámetro de la función: al terminar, valía la del ÚLTIMO contrato.
  El tablero filtraba por 2025 pasara lo que pasara, sin un solo error a la
  vista, y hasta el «Todas» mostraba $187.521 M en vez de $376.458 M.
- **La pantalla de Programas corre sobre una tabla vieja de 7 filas**, 3 de
  ellas llamadas «prueba», y reparte proyectos por una FK que solo 5 de 31
  tienen. Es un CRUD editable a mano, distinto de los programas del Plan, que
  llegan de la Matriz y ya tienen su pantalla en Objetivos. Repuntarla al
  catálogo convertiría un catálogo libre en uno oficial editable a mano. **Si
  esa pantalla ya no tiene razón de ser, borrarla es decisión de Alex.**

**Verificación:** 1622 tests OK (7 skipped) · build con `--base-href=/app/`
comprobado en cada publicación · `/app/` 200.

**Lo que queda:**

- **La meta agrupada de posmedia.** Las metas 23771 y 23772 del proyecto 2377
  están Ejecutadas al 100 % y no existen como fila propia: las cubre una meta
  agrupada sin código SEGPLAN. Todo lo que camina el catálogo las pierde — 76
  metas de 78, 21 ejecutadas de 23, la perspectiva «potencial» en 5 de 7 — y en
  la peor dirección, porque las dos que desaparecen son las dos que están
  terminadas. O se crean las dos y se retira la agrupada (toca datos), o se
  enseña a las pantallas a desdoblarla (no toca datos, la rareza sigue viva).
- La pestaña de **Fuentes**: los dos endpoints están desde la fase 1, falta la
  pantalla.
- El proyecto de código **7895**, sin metas en el catálogo: confirmar si es
  basura o un proyecto mal codificado.
- N+1 preexistente: la tabla paginada de proyectos abre 31 consultas por página
  para resolver la dependencia de cada uno.

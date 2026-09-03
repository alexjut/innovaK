# Matriz PDL → modelo: el mapeo (Fase A)

Entregable de la **Fase A** del plan «Matriz PDL como fuente de verdad».
Medido contra el archivo real y contra la base en vivo el **2026-09-03**.

| | |
|---|---|
| Archivo | `Matriz de seguimiento PDL 2025-2028.xlsx` (raíz del repo, 104.830 bytes) |
| SHA-256 | `814832b0cb118d042ef2d8c72d003c337eb5d63d5e4b4735fd68a323f4f2fc6e` |
| Corte oficial | 2026-07-23 (el que reporta el backend como `corte_pdl_oficial`) |
| Hojas | `Programacion PDL 2025 - 2028` · `Seguimiento` · `Alertas` |

> **El archivo estaba sin trackear y sin ignorar** (`??` en `git status`), o sea a un
> `git add -A` de entrar a un repo público. Se agregó a `.gitignore` el 2026-09-03: el
> original pertenece a su **carga** —guardado con su hash, como pide la Fase C—, no a
> git. Revertirlo es una línea si se decide otra cosa.
>
> (El indexador de código tampoco lo lee, pero eso lo decide su propia skip-list por
> sufijo — `ignored-suffix` —, que no tiene nada que ver con git.)
>
> El hash de arriba es el que la Fase C tiene que rechazar como duplicado.

---

## 1 · Qué trae cada hoja, y con qué grano

**Las dos hojas de datos tienen el MISMO grano: proyecto × indicador. 78 filas cada una,
y cruzan al 100 % sin huérfanos en ninguna dirección.** Eso es la mejor noticia de la
Fase A: no hay que reconciliar dos universos, hay que unirlos por una llave.

| Hoja | Filas | Grano | Qué aporta que la otra no |
|---|---|---|---|
| `Programacion PDL 2025 - 2028` | 78 | proyecto × indicador | **magnitudes** (metas por vigencia), ponderaciones, línea de inversión, concepto de gasto, componente, tipo de anualización, **sector** |
| `Seguimiento` | 78 | proyecto × indicador | **la jerarquía** (objetivo → programa) y **toda la plata** (proyectado, apropiación POAI, comprometido, girado, por vigencia) |
| `Alertas` | — | meta | la clasificación de cumplimiento 2025 ya resuelta por la ALK |

Cardinalidades de la jerarquía, contadas del archivo:

```
5 objetivos estratégicos → 22 programas → 30 proyectos → 78 metas/indicadores
```

La hoja `Alertas` trae además su propio cuadre, y cierra: **78 metas = 41 críticas + 8 en
ejecución según cronograma + 23 ejecutadas + 4 desiertas + 2 sin magnitud.**

> Ojo con la lectura de ese 41: son **metas**, no proyectos. El dashboard aplica «peor
> alerta gana» y por eso muestra **18 proyectos** críticos. Las dos cifras son correctas
> y miden cosas distintas.

---

## 2 · Tres trampas medidas, antes de modelar

### 2.1 · `Codigo cocatenado` es POSICIONAL — no sirve de llave

La columna F de `Seguimiento` parece la llave natural del par proyecto-meta, y es
única en las 78 filas. **Pero no es proyecto + código de indicador: es proyecto +
posición secuencial (1..7) dentro del proyecto.**

| Codigo cocatenado | proyecto | cód. indicador | sufijo real |
|---|---|---|---|
| `23772` | 2377 | 51 | `2` |
| `23771` | 2377 | 52 | `1` |
| `23773` | 2377 | 50 | `3` |

Coincide con el código de indicador en **3 de 78 filas**, por casualidad — el mismo modo
de falla intermitente que ya dio el `id` vs `codigo` de proyecto. Si la ALK reordena las
filas de un proyecto en el próximo corte, esa columna reasigna sus valores y la carga
cambiaría de meta sin que nada avise.

**La llave estable es el par `(cód. proyecto, cód. indicador)`**: 78 pares en cada hoja,
conjuntos idénticos, verificado. `Codigo cocatenado` se guarda como dato de la fuente,
nunca como identificador.

### 2.2 · Los códigos de proyecto de la matriz vienen SIN ceros a la izquierda

La matriz guarda `2377`; innovaK guarda `0002377`. Hoy solo dos proyectos de innovaK
traen ceros (`0002377` y `000007895`), así que el JOIN sin normalizar falla en pocos
casos — y por eso no se ve. Es exactamente el defecto que ya obligó a normalizar la
cobertura PDL. **Normalizar en la entrada, no en la consulta.**

### 2.3 · El sector está sucio EN LA PROPIA MATRIZ

No es solo `EDUCACIÓN` contra `Educación`: la matriz trae **13 valores de sector para
11 sectores reales**, y dos de ellos son compuestos.

| Valor en la matriz | Filas | Problema |
|---|---|---|
| `AMBIENTE` / `AMBIENTE/HÁBITAT` | 5 / 5 | dos etiquetas, ¿un sector o dos? |
| `MUJERES` / `MUJERES/INTEGRACIÓN SOCIAL` | 1 / 3 | ídem, y cruza con `INTEGRACIÓN SOCIAL` (8) |
| `GOBIERNO`, `SEGURIDAD, CONVIVENCIA Y JUSTICIA`, … | 13, 13, … | mayúsculas y comas |

Un catálogo `Sector` con `nombre_oficial` + `alias` resuelve el plegado de mayúsculas y
tildes, **pero no resuelve los compuestos**: `AMBIENTE/HÁBITAT` no es un alias de
`AMBIENTE`, es una fila que pertenece a dos sectores o a uno nuevo. Eso es una decisión
de la ALK, no un `LOWER()`.

---

## 3 · Los tres universos de proyectos, anidados

Están anidados, y eso simplifica todo:

```
SDP oficial (28)  ⊂  Matriz ALK (30)  ⊂  innovaK (31)
```

| | Cuántos | Cuáles |
|---|---|---|
| **SDP oficial** | 28 | de `sdp_meta_oficial` |
| **La matriz agrega 2** | 30 | `2556 Kennedy Mujeres sin Barreras` · `2643 Kennedy Ecomanos en Acción` |
| **innovaK agrega 1** | 31 | `000007895` — el registro de prueba confirmado |

**Corrige el plan: no son «los 3 proyectos no oficiales», es UNO.** El `innovak_sin_par_oficial: 3`
que reporta el muro se mide contra los 28 de SDP; contra la matriz, que es la fuente que
este plan entroniza, sobra uno solo y es el de prueba.

Consecuencia para el modelo: si `oficial = true` significa «viene de la matriz», pasan a
oficiales **30**, no 28 — y la cobertura PDL deja de ser un cruce de códigos para ser una
columna. Ningún proyecto se pierde al cambiar de fuente.

---

## 4 · El mapeo, columna por columna

Leyenda de estado: **✅ existe** · **🔶 existe pero como texto plano** · **🔴 no existe**

### 4.1 · Jerarquía (hoja `Seguimiento`)

| Columna del Excel | Dónde vive hoy | Estado |
|---|---|---|
| A `Objetivo Estrategico` | `metas.objetivo_estrategico` (str) · `sdp_meta_oficial.objetivo` | 🔶 texto en 2 tablas; la tabla `objetivo` (6 filas) **no es ésta** — 4 de sus 6 filas se llaman «prueba» |
| B `Programa` | `metas.codprog` / `metas.nomprog` · `sdp_meta_oficial.programa` | 🔶 texto. `proyecto.programa_id` apunta a `programas` (7 filas, 5 de 31 proyectos): **no es el programa del PDL** |
| C `Linea de Inversión` | `metas.linea` | 🔶 |
| D `Concepto` | `metas.concepto` | 🔶 |
| E `Componente` | `metas.componente` | 🔶 |
| F `Codigo cocatenado` | — | 🔴 y **no debe ser llave** (§2.1) |
| G `N° Proyecto de inversión` | `proyecto.codigo` · `metas.codproy` | ✅ normalizar ceros |
| H `Proyecto de Inversión` | `proyecto.nombre` · `metas.nomproy` | ✅ viene como `2377-Nombre`: hay que partirlo |
| I `Metas del Plan de Desarrollo Local` | `metas.nombre` / `metas.descripcion` | ✅ |
| J `Codigo indicador` | `metas.codind` · `metas.nomind` | ✅ mitad de la llave estable |

### 4.2 · Plata, por vigencia (hoja `Seguimiento`, 4 bloques)

Las cuatro columnas de plata se repiten por vigencia (2025 · 2026 · 2027 · 2028) y ya
tienen destino:

| Columna del Excel | Campo | Estado |
|---|---|---|
| `Presupuesto proyectado PDL {año}` | `presu_presupuesto_meta_vigencia.proyectado_pdl` | ✅ |
| `Apropiación POAI inicial {año}` | `…​.apropiacion_poai` | ✅ |
| `Presupuesto Comprometido {año}` | `…​.comprometido` | ✅ |
| `Presupuesto Girado {año}` | `…​.girado` | ✅ |
| `% ejecución presupuestal {año}` | — | 🔴 **no se guarda, y está bien**: es derivable |
| Columnas `… Total` (AY–BJ) | — | 🔴 **no guardar**: son sumas del propio Excel |

> El orden de columnas del Excel es irregular: el bloque de plata de 2027 (AE–AI) viene
> **antes** que sus columnas de meta (AJ–AN), al revés que 2025, 2026 y 2028. El lector
> tiene que ubicar por encabezado, nunca por posición. El importador actual ya lo hace
> (`_columnas_plata`).

### 4.3 · Magnitudes (hoja `Programacion`)

| Columna del Excel | Dónde vive hoy | Estado |
|---|---|---|
| K `PONDERACIÓN PROYECTO` | — | 🔴 |
| L `Meta proyecto 2025-2028 (PDL)` | `metas.nombre` | ✅ |
| M `COMPONENTE PROYECTO` | `metas.componente` | 🔶 |
| N `PONDERACIÓN META INTERNA PROYECTO` | — | 🔴 |
| O `Tipo de anualización meta` | `metas.anualizacion` · `sdp_meta_oficial.tipo_anualizacion` | ✅ decide la agregación — ya hay un fix suyo en el historial |
| P–S `Magnitud Meta Reprogramacion {año}` | — | 🔴 la magnitud **por vigencia** no tiene columna propia |
| T `Meta 2025-2028` | `metas.*` (total) | ✅ |
| C `Sector` | `metas.sector` (str) | 🔶 sin catálogo (§2.3) |

### 4.4 · Alertas (hoja `Alertas`)

| Dato | Campo | Estado |
|---|---|---|
| Clasificación de cumplimiento | `presu_presupuesto_meta_vigencia.alerta` | ✅ **ya cargada** |
| Contratada / ejecutada | `…​.magnitud_contratada` / `…​.magnitud_ejecutada` | ✅ |
| % cumplimiento | `…​.cumplimiento_pct` | ✅ |

> **El DDL 021 no hace falta.** El comentario que sigue en el código sin commitear dice
> que la alerta «nace `null` hasta que se cargue la hoja Alertas — DDL 021, sin aplicar
> todavía». Está poblada en **30 de 31 proyectos** con las cinco categorías reales. Ese
> comentario va a mandar a alguien a aplicar una migración que ya no corresponde.

---

## 5 · Lo que la Fase B YA no tiene que construir

El plan dimensiona la Fase B como si el modelo estuviera vacío. No lo está: **el DDL 020
ya es, campo por campo, la entidad `ApropiacionVigencia` del plan** — y de paso incluye
las alertas.

`presu_presupuesto_meta_vigencia`, **312 filas** (78 metas × 4 vigencias):

```
codigo_meta · proyecto_codigo · vigencia
proyectado_pdl · apropiacion_poai · comprometido · girado
alerta · magnitud_contratada · magnitud_ejecutada · cumplimiento_pct
fuente · archivo_origen · cargado_por · created_at · updated_at
```

Y el importador `importar_matriz_pdl_alk` (578 líneas) ya hace seco por defecto, es
idempotente, ubica columnas por encabezado, hace *backfill* solo de `NULL` sin pisar lo
escrito, reporta divergencias sin tocarlas y deja **una** entrada en `auditoria_dato`.

**Lo que falta de verdad, entonces, es más chico y más concreto:**

| Falta | Por qué |
|---|---|
| `MatrizPDLCarga` (hash, estado, diff, archivo) | hoy la carga es un comando de consola: no hay entidad, ni dedupe por hash, ni `borrador`/`aplicada` |
| `ObjetivoEstrategico` y `Programa` como tablas | hoy son texto en `metas` y en `sdp_meta_oficial`; la tabla `objetivo` está contaminada con filas «prueba» y `programas` es otra cosa |
| Catálogo `Sector` con alias | y una decisión sobre los compuestos (§2.3) |
| `activo` / `carga_origen` / `carga_retiro` | la regla «la carga nunca borra» no tiene dónde escribirse |
| Magnitud por vigencia | columnas P–S de `Programacion` no tienen destino |
| Las 3 pantallas (subir · previsualizar · aplicar) | el flujo web de la Fase C |

---

## 6 · Las cuatro decisiones de Alex — dos ya las contestó el archivo

**1 · ¿La apropiación viene por meta o por proyecto?** → **Por meta.** El grano de
`Seguimiento` es proyecto × indicador, con una columna de apropiación por vigencia. La FK
va al nivel meta/indicador, que es lo que `presu_presupuesto_meta_vigencia` ya hace
(78 × 4 = 312). Agregar a proyecto es una suma, no un campo.

**3 · ¿Los proyectos no oficiales siguen visibles?** → La pregunta se encoge: **es uno
solo y es el registro de prueba `000007895`** (§3). No es «qué hacemos con los proyectos
propios del área», es «cuándo se borra el de prueba», y eso espera respuesta del Despacho
sobre su CDP 1486.

**5 · Los sectores compuestos** → **DECIDIDO por Alex (2026-09-03): se agregan como
sectores propios.** *«Hay que agregar esos sectores; nuestra luz es esa matriz con
SEGPLAN.»* El catálogo `Sector` nace con los **13 valores que trae la matriz**,
`AMBIENTE/HÁBITAT` y `MUJERES/INTEGRACIÓN SOCIAL` incluidos: no se pliegan a `AMBIENTE`
ni a `MUJERES`, porque la fuente dice que son otra cosa y la fuente manda.

Los `alias` quedan solo para lo que es la MISMA cosa escrita distinto — el
`Educación` interno de innovaK contra el `EDUCACIÓN` de la matriz —, nunca para unir dos
sectores que la matriz separa.

Y la autoridad es una sola, no dos que haya que reconciliar: la columna I se llama
literalmente **«Cód. Proyecto de Inversión SEGPLAN»**, así que el identificador de la
matriz *es* el de SEGPLAN.

**Qué arregla y qué no en «Top sectores»:** desaparecen los duplicados por mayúsculas
(`Educación` / `EDUCACIÓN`) y las filas que en realidad eran **subgrupos** colándose como
sectores (`Cultura` y `Deporte` son subgrupos del sector `CULTURA, RECREACIÓN Y
DEPORTE`). Lo que **sigue** siendo dos filas es `AMBIENTE` y `AMBIENTE/HÁBITAT` — ya no
como defecto, sino porque así lo define la fuente.

**1b · `oficial = true` significa «viene de la matriz» → 30 proyectos.**
DECIDIDO por Alex (2026-09-03). La cobertura PDL pasa de ser un cruce de códigos a ser
una columna, `2556` y `2643` dejan de salir como «sin par oficial», y el tablero pasa de
mostrar **28/28 a 30/30**. Hay que avisarlo cuando cambie: no es que aparecieron dos
proyectos, es que cambió la definición de oficial.

**Siguen abiertas, y el archivo no las contesta:**

**2 · ¿`contrato_actividad_plan` referencia metas de la matriz o actividades internas?**
Hay que mirar los datos de esa tabla, no la matriz. Queda para la Fase B.

**4 · ¿Quién aplica las cargas?** Decisión de gobierno, no de dato.

**Y una quinta que apareció al medir:** los sectores compuestos `AMBIENTE/HÁBITAT` y
`MUJERES/INTEGRACIÓN SOCIAL` — ¿un sector nuevo, o la fila pertenece a dos? Bloquea el
catálogo `Sector`, y por lo tanto el arreglo de «Top sectores».

---

## 7 · Cómo se verificó

Todo lo de arriba sale de leer el `.xlsx` con `openpyxl` y de consultar la base en vivo;
nada se copió del documento anterior. Las afirmaciones que valen revisar antes de creer:

- grano y cruce de las hojas: 78 pares `(proyecto, indicador)` en cada una, conjuntos idénticos;
- `Codigo cocatenado`: sufijo `1..7`, coincide con el indicador en 3 de 78;
- universos: 28 ⊂ 30 ⊂ 31, con los dos que agrega la matriz nombrados en §3;
- `presu_presupuesto_meta_vigencia`: 312 filas y las 17 columnas listadas;
- `objetivo` tiene 6 filas y `programas` 7, con 5 de 31 proyectos enganchados.

Ver `docs/operacion/dashboard_presupuesto_estado_2026-08-24.md` para el estado de la
pantalla, y el inventario del 2026-09-03 para qué bloque muestra qué.

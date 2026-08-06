# Rumbo — qué tenemos, qué está roto y en qué orden se arregla

**Auditoría del 2026-08-05.** Ocho revisiones en paralelo sobre fuentes de datos,
código muerto del backend, frontend, la cadena presupuestal, documentación,
accesibilidad, el mapa y la deuda técnica. Todo medido contra el código y contra
`poblacion_kennedy` en vivo, no contra lo que dicen los documentos.

> **Cómo leer esto.** El orden no es por área ni por gusto: es por qué desbloquea
> qué. Lo de arriba se hace primero porque lo de abajo depende de ello o porque
> el daño es desproporcionado frente al esfuerzo. Cada ítem dice **de quién es**:
> hay cosas que resuelve el código y cosas que solo puede decidir un área.

---

## 0. Lo que hay que decidir hoy, no esta semana

### 0.1 🔴 4.582 cédulas en un repositorio público

| Archivo | Personas | Contenido |
|---|---|---|
| `personas_con_documento.csv` | **4.382** | nombre1, nombre2, apellido1, apellido2, tipo_documento, **numero_documento** |
| `ultimos_200.csv` | 200 | los mismos campos |
| `personas_esta_semana.csv` | 0 | solo el encabezado |

Entraron en **un solo commit** (`116bfd7`, 2026-04-16) y están en las cuatro
ramas del remoto. `github.com/alexjut/innovaK` responde **200 a un `curl`
anónimo**: el repositorio es público. Nombre completo más cédula es exactamente
el par que protege la Ley 1581 de 2012.

Agravante: `docs/infra/despliegue_kubernetes.md:14` afirma que el repositorio es
privado, y todo el modelo de amenazas de ese documento se razonó sobre esa
premisa falsa.

**Las opciones, con su consecuencia real:**

| | Costo | Qué logra | Qué no logra |
|---|---|---|---|
| **A. Poner el repo en privado** | 30 segundos | Corta la exposición pública **ya**. Convierte una exposición ilimitada en una controlada, que es lo que más pesa jurídicamente | No borra el dato; los forks que existan siguen afuera |
| **B. `git rm` + commit** | 10 min | Limpia la vista web | **Nada más.** `git log -p` sigue entregando las 4.382 cédulas |
| **C. Purgar el historial** (`git filter-repo`) | 2-4 h | Purga real | Reescribe **1.171 commits**, obliga a re-clonar a todos, **rompe los hashes citados en `CLAUDE.md`, `ESTADO.md` y `docs/_historico/`**, y contradice la regla propia del proyecto de nunca hacer force-push |
| **D. Repositorio nuevo**, el viejo se archiva privado | ~1 h | Lo más limpio sin force-push | Se pierde el historial navegable |

### ✅ Hecho el 2026-08-05 — y lo que sigue faltando

Se verificó primero que el dato no se perdía: **las 4.382 personas del CSV y sus
documentos están las 4.382 en `poblacion_kennedy`**. El archivo no era fuente de
nada. Se hizo `git rm` de los tres y se bloqueó `/*.csv` en `.gitignore`.

**🔴 Eso es la opción B, y B por sí sola no resuelve el problema legal.** Las
4.382 cédulas **siguen en el historial**: `git clone` + `git log -p` las entrega
igual, y GitHub conserva los blobs accesibles por URL de SHA. Falta decidir
entre:

- **A. Poner el repo en privado** — 30 segundos, corta la exposición pública ya.
  Es lo que más pesa jurídicamente y no rompe nada.
- **C. Purgar el historial** — reescribe 1.171 commits, obliga a re-clonar y
  deja muertos los hashes citados en `CLAUDE.md`, `ESTADO.md` y `_historico/`.
- **D. Repositorio nuevo**, el viejo archivado en privado.

**A sigue siendo lo primero**, y ahora es lo único que falta para detener la
exposición.

Y en los cuatro casos: agregar `*.csv` de la raíz al `.gitignore`, y anotar en
`docs/README.md` la excepción que hoy falta — la regla *"si un documento deja de
ser vigente se mueve a `_historico/`, **no se borra**"* empuja a archivar cédulas
en vez de eliminarlas.

**De quién es:** de Alex. No se toca sin su decisión.

### 0.2 Tres tokens HMAC publicados — ✅ el código, el 2026-08-06

Estaban en `docs/manuales_modulos/cultura.md`. Detectados el 2026-07-16 y
quietos hasta hoy por una razón real: **se derivaban de `SECRET_KEY`**, así que
quemarlos exigía rotarla, y eso tumba las sesiones de Redis y los enlaces de
restablecimiento de contraseña de todo el mundo. `SECRET_KEY_FALLBACKS` tampoco
servía: habría dejado válidos precisamente los tokens filtrados.

**Lo que se hizo:**

- Clave propia **`QR_TOKEN_SECRET`**, con fallback a `SECRET_KEY` para que
  desplegar no rompa en el acto. Los QR se rotan ahora sin arrastrar nada más.
- **`QR_TOKEN_SECRETS_LEGACY`**: claves viejas que se aceptan al **validar** y
  nunca al **firmar**. Esa asimetría es la que deja rotar sin matar el material
  ya impreso; los tokens de clave vieja entran, pero quedan marcados en el log
  como "falta reimprimir".
- Los 3 valores fuera del manual, reemplazados por una nota de dónde se
  obtiene el enlace de verdad. Barrido de todo el repo —rastreado y no
  rastreado—: no aparecían en ningún otro archivo.

**Sigue abierto, y son dos cosas distintas:** poner `QR_TOKEN_SECRET` en el
`.env` del servidor (mientras no esté, el fallback mantiene los tres tokens
filtrados **vivos**), y purgar el historial de git, donde los valores siguen
siendo alcanzables.

### 0.3 QR_TOKEN_ENFORCE — ahora se puede activar sin romper territorio

Seguía en `False`, o sea que los formularios públicos con QR **no validan
token**. El obstáculo no era técnico: el material impreso está pegado en
territorio y un corte duro deja al ciudadano con un afiche muerto.

Desde el 2026-08-06 hay **modo dual**, así que el corte deja de ser binario:

| `QR_TOKEN_ENFORCE` | `QR_TOKEN_LEGACY_HASTA` | qué pasa |
|---|---|---|
| `False` | — | **suave**: todo entra, se registra (es el estado de hoy) |
| `True` | fecha futura | **dual**: token válido entra; sin token entra y queda marcado como legacy |
| `True` | vacía o vencida | **duro**: solo token válido |

`ENFORCE=true` ya se puede activar **el mismo día**, sin riesgo, poniendo una
fecha de gracia que cubra la reimpresión. El legacy se apaga **solo** cuando
vence — no hace falta otro despliegue. Una fecha ilegible se trata como ventana
**cerrada**, para que un error de tipeo en el `.env` no se convierta en una
puerta abierta silenciosa.

---

## 1. Lo que tenemos (inventario, con números reales)

### 1.1 Fuentes de datos externas

**Once fuentes remotas, ninguna automatizada.** El cron está escrito
(`scripts/cron_sync_oficial.sh`), documentado y listo — y **nunca se instaló**:
`crontab -l` solo tiene el backup de las 2 AM. La carpeta `logs/` a la que el
script dice escribir no existe. Se sincroniza a mano, cuando alguien se acuerda.

| Fuente | Tabla | Filas | Corte del dato | Estado |
|---|---|---|---|---|
| Estratificación (IDECA) | `manzana_estrato` | 18.929 | Decreto 394/2017 | 🟡 faltan **26.122** manzanas: se cargó solo el bbox de Kennedy |
| Placas domiciliarias | `placa_domiciliaria` | 1.771.088 | — | 🟡 1.784 nuevas sin traer |
| Sectores catastrales | `sector_catastral` | 1.230 | **NULL** | 🟡 no sabemos de cuándo es |
| Barrios legalizados | `barrio_legalizado` | 1.709 | **NULL** | 🟡 ídem |
| Colegios (SED/IDECA) | `colegio_sede` | 79 | 2025-12-31 | ✅ |
| Matrícula (SED) | `colegio_sede.matricula_total` | 75 | 2025-04-30 | 🟡 lo más nuevo que publica SED, pero son 15 meses |
| CAI (SCJ) | `cai` | 15 | NULL | ✅ |
| SDP–PDL | `sdp_meta_oficial` | 280 | **fuente parada desde 2026-02-18** | 🔴 escalar a Planeación |
| SECOP II | `secop_contrato` | 3.050 | último 2026-06-02 | 🔴 **la fuente va en 2026-08-03: dos meses de contratación afuera** |
| Malla vial (IDU) | `tramo_vial_contrato.geom` | 30 | — | ✅ bajo demanda |
| Presupuesto PP (CKAN) | — | — | — | solo preview, no persiste |

**Los diez endpoints responden 200.** Ninguna fuente está rota; están
desactualizadas o sin automatizar.

**Cuatro cargas frágiles, sin forma de refrescarse:**
1. 🔴 **`escuela` (424 filas)** — `cargar_censo_escuelas.py` lee de `/tmp`, y
   **los archivos ya no están ahí ni estuvieron nunca en el repo**. El censo de
   julio de Cultura y Deportes no se puede volver a correr hoy.
2. `parque` (554) y `upz.geometry` (12) — importadores archivados, dependen de
   geojson del repo. IDECA publica las tres por servicio: son candidatas a
   entrar al registro de capas.
3. `barrio.geometry` — **155 de 325**.
4. Contorno de Kennedy — se lee de disco en cada request.

**Tres convenciones de seguridad conviviendo** en los comandos de sync, y
difieren en lo más peligroso: qué pasa si los corres sin flags. Siete escriben
por defecto (`--dry-run` para no hacerlo), nueve son secos por defecto
(`--write`/`--apply`). **`sync_estratificacion` y `sync_capa estratificacion`
escriben la misma tabla con defaults opuestos.** Y el orquestador
`sync_fuentes_oficiales` —el que iría al cron— no tiene `--dry-run` y solo cubre
2 de las 11 fuentes.

**Solo 1 de 12 fuentes declara su licencia.** IDECA y datos.gov.co son CC BY 4.0:
la atribución es obligatoria.

### 1.2 La cadena, medida

```
Proyecto 11 → Meta 23 → KPI 20 → ActividadPlan 54 → Contrato 24 → Evento 54 → Persona
```

| Eslabón | |
|---|---|
| Contratos ligados a una actividad del plan | **4 de 24** |
| Actividades con KPI | 18 de 54 |
| Eventos colgando de una actividad | 22 de 54 |
| Avances registrados | 7 |

---

## 2. Los tres hallazgos que cambian lo que hay que hacer

### 2.1 No hay "0 beneficiarios". Hay 2.545 personas desconectadas

`ESTADO.md` afirmaba "0 beneficiarios registrados". **El diagnóstico era
equivocado.** Ese 0 es el resultado de un JOIN vacío
(`cockpit_presupuesto.py:293`), no el estado de la base:

| | eventos | con `actividad_plan` | con inscritos | personas |
|---|---|---|---|---|
| `GENERICO` (Novenas, Recorridos) | 32 | **0** | 28 | **2.545** |
| El resto (curso, festival, banco…) | 22 | **22** | 0 | 0 |

Los eventos que tienen gente no cuelgan del plan; los que cuelgan del plan no
tienen gente. La query no puede dar otra cosa.

Y hay un segundo universo que la cadena tampoco ve: **`beneficiario` tiene 3.605
filas** y `contrato_beneficiario` 2.950. La intersección entre
`participante.persona_id` y `beneficiario.persona_id` es **exactamente 0**: son
dos cargas que nunca se cruzaron. Además `contrato_beneficiario.beneficiario_id`
está **100 % NULL** aunque los 2.892 documentos cruzan uno a uno.

**Medido el 2026-08-05 al ejecutarlo:** enganchar los 32 eventos GENERICO
(**A3**) lleva la query del cockpit de **0 a 2.545** por sí solo. No necesita
nada más: el cockpit cuenta participantes, no beneficiarios.

**🔴 Corrección a este mismo documento — y la corrección de la corrección
(2026-08-06).** La primera versión decía que A5 "unifica los dos universos"
dando a entender que valía 2.545. La segunda lo corrigió a **136**, diciendo
que *"solo 137 de 2.693 tienen número de documento"*. **Ese 137 también estaba
mal, y por mucho.**

Medido de nuevo el 2026-08-06 sobre los 2.545 inscritos en eventos `GENERICO`:

| | personas |
|---|---|
| Inscritas en los 32 eventos GENERICO | **2.545** |
| **Con documento registrado** | **1.888** |
| Sin ninguna forma de identificarlas | 657 |

**Por qué se contaron 137.** El documento de una persona puede llegar por dos
caminos y **solo uno está poblado**: la tabla `persona_documento` (vía FK
`persona.persona_documento`) tiene **2** de estas personas; la columna
denormalizada `persona.documento` tiene **1.887**. El conteo anterior —y el
backfill de A5— miraron la vía FK, que es la "correcta" según el modelo y la
que está vacía. Ninguna de las dos columnas se llama `numero_documento` en
`persona`: esa columna **no existe**, así que la consulta que la usara fallaba
o se resolvía por otro lado.

**Qué queda de verdad, ya cruzado contra `beneficiario` (3.741 filas):**

| | |
|---|---|
| Identificables | 1.888 |
| Ya son beneficiario (por `persona_id`) | 1 |
| Ya son beneficiario (cruzando por documento) | 37 |
| **Faltarían por crear** | **~1.851** |

Con dos salvedades que hay que decidir antes de escribir nada: de los 1.888,
**1.879 tienen forma de documento** (6 a 12 dígitos) y los otros 9 son basura
—hay largos de 1 y de 23 caracteres, y 4 con letras o signos—; y esos 1.879
colapsan en **1.713 documentos distintos**, o sea que hay **166 filas de
`persona` repetidas dentro del propio grupo**.

**El problema de duplicados es mucho mayor de lo que decía este documento.** La
versión anterior hablaba de *"una que falló por documento duplicado: dos filas
de `persona` comparten el 1030547250"*. Medido sobre toda la tabla: **380
documentos repetidos, en 1.244 filas de `persona`**. No es un caso aislado, es
un patrón.

**De qué subgrupos salieron los 2.545:**

| Subgrupo | eventos | personas | con documento |
|---|---|---|---|
| Relacionamiento Interinstitucional (las 17 Novenas + 1 recorrido) | 18 | 2.408 | 1.858 |
| Desarrollo Estratégico y Mejora (14 Recorridos) | 14 | 137 | 30 |

*(El «137» de la versión anterior es exactamente el total del segundo subgrupo.
Coincidencia o no, el número correcto de identificables es 1.888.)*

**🔴 Y acá está el muro real de A3, que no era el que decía este documento.**
Enganchar los 32 eventos al plan exige que exista una actividad del plan a la
cual engancharlos, y **no existe**:

| Subgrupo | actividades en el plan |
|---|---|
| Relacionamiento Interinstitucional | **1** |
| Desarrollo Estratégico y Mejora | **0 — no aparece en el plan** |

O sea: las 2.408 personas de las Novenas tienen **una sola** actividad
candidata (habría que confirmar que es la correcta, y eso lo dice el área), y
las 137 de los Recorridos **no tienen ninguna**: su subgrupo no tiene plan.
A3 no está bloqueado solo por "a qué actividad mapea cada evento" — para la
mitad está bloqueado porque **primero hay que crear la actividad del plan**.

### 2.2 El 93 % del mapa de eventos es ficción

De 54 eventos: **32 sin `lugar_incidencia`**, **18 apilados en la sede de la
Alcaldía**, **4 con ubicación real**. En la capa que se sirve al ciudadano, 13
de 16 eventos están en la Alcaldía.

Y hay un bug que lo perpetúa: `apps/login/api/views.py:1487-1495` solo entra a
la rama geográfica si **falta** `lugar_incidencia_id`. Como el formulario ahora
sí lo manda, **mover el pin y guardar no hace nada**: la coordenada nueva se
descarta.

> **✅ Arreglado el 2026-08-05 (B6).** Si llegan lat/lng, mandan. Y la
> ubicación pasó a ser obligatoria al crear, que es lo que hacía indoloro el
> hueco: el anclaje automático en la Alcaldía convertía "no sé dónde es" en un
> punto que parecía dato. Lo que queda es **corregir las 50 ya cargadas**, y eso
> lo hace cada área desde la pantalla — ahora sí guarda.

Basura acumulada: **236 de 310 `geo_referenciacion` huérfanas**, **69 de 74
`lugar_incidencia`** sin evento.

### 2.3 `templates/` vive por un solo archivo

Quedan tres plantillas. La única que se renderiza de verdad es
`templates/votaciones/scan.html` — el kiosko público de votación por QR, el
**único `render()` de todo el backend**. `base.html` (424 líneas, sidebar de 26
enlaces, topbar, Alpine, HTMX, Chart.js) existe solo porque `scan.html` la
extiende… y se sirve **únicamente a un votante anónimo**, para quien el sidebar
entero está apagado por permisos.

**Migrar esa pantalla a Angular desata en cascada:** `base.html`,
`breadcrumb.html`, `breadcrumbs.py` (166 líneas que corren en cada request y
nunca producen salida), tres context processors, todo el pipeline de
webpack/SCSS, el `node_modules/` de la raíz (31 MB) y ~24 vistas puente.

---

## 3. El orden

### Bloque A — hoy, y son horas

| # | Qué | De quién | Desbloquea |
|---|---|---|---|
| A1 | **Decidir sobre los CSV con cédulas** (§0.1) | Alex | Poder hablar del repo sin exposición abierta |
| A2 | ~~`presupuesto/views/__init__.py` corría `django.setup()` en cada arranque~~ **HECHO 2026-08-05** | — | Arranque limpio |
| A3 | 🔴 **BLOQUEADO — no es trabajo de código.** Ver §3.1 | **las dos áreas**, no Alex | 2.545 personas |
| A4 | ~~`contrato_beneficiario.beneficiario_id`~~ **HECHO**: 2.950 filas enlazadas, cero sin cruce, cero ambigüedad | — | Conecta plata con personas |
| A5 | ~~`asegurar_beneficiario_persona` desde `inscribir_persona`~~ **HECHO** (código + backfill) | — | Ver la corrección de abajo |
| A6 | ~~Poblar `estrato_ideca`~~ **HECHO**: 79 colegios y 393 escuelas. Queda 1 escuela sin resolver (la que está fuera de Kennedy) | — | Habilita "colegios por estrato" |
| A7 | **Corregir las rutas rotas del panel de área** ~~y los estilos faltantes~~ **HECHO 2026-08-05** | — | — |

#### 3.1 Por qué A3 está bloqueado (revisado el 2026-08-05)

Este documento decía que A3 era esfuerzo **XS**: "poner `actividad_plan_id` a
32 eventos". Al ir a hacerlo, no se puede — y no por esfuerzo, sino porque no
existe a qué engancharlos. Los 32 se parten en dos, y las dos mitades están
bloqueadas en el área, no en el código.

**Relacionamiento Interinstitucional — 17 eventos, 2.408 personas.**
Son las Novenas de barrio (Cumpleaños de Kennedy 833 inscritos, Vegas de Santa
Ana 338, Casablanca 139…). Tiene **exactamente una** actividad candidata, así
que técnicamente el mapeo es único. Pero mírala:

| | |
|---|---|
| Proyecto | `000007895` — **el nombre es el código**, sin dependencia ni programa |
| Actividad | id 107, descripción **"mujeres caminando ver 1"** |

Es un proyecto de relleno con una actividad de prueba. Colgar 2.408 personas de
unas Novenas de Navidad a *"mujeres caminando ver 1"* sería **peor que dejarlas
sin enganchar**: convertiría un hueco visible en una atribución falsa, y el
avance quedaría reportado contra una meta que no existe. Que haya una sola
opción no la vuelve la opción correcta.

→ **Lo que hace falta:** que Relacionamiento cargue su proyecto y su línea real
de plan para las Novenas. Ahí el enganche son minutos.

**Desarrollo Estratégico y Mejora — 15 eventos, 137 personas.**
Son los Recorridos. El área **no tiene ningún proyecto** en la base, así que no
hay ni una actividad candidata.

→ **Lo que hace falta:** que el área cargue su proyecto.

**La lección para este documento:** "XS" se estimó mirando el número de filas a
actualizar (32) sin mirar si existía el destino. El esfuerzo de escribir no es
el esfuerzo de la tarea cuando lo que falta es el dato del otro lado.

---

### Bloque B — ✅ HECHO el 2026-08-05

| # | Qué | Estado |
|---|---|---|
| B1 | ~~Abrir festivales, tramos viales y parques-obras al público~~ | ✅ los tres responden **200 a un anónimo**; el Banco sigue en 401. Al anónimo solo se le sirven los festivales **publicados** |
| B2 | ~~Redondear coordenadas a 6 decimales~~ | ✅ en contorno, UPZ, barrios, parques, tramos y parques-obras. Medido sobre parques: **278 → 86 KB gzip de geometría (−69 %)** |
| B3 | ~~Parques a lazy~~ | ✅ la carga inicial pasó de **342 KB a 39,9 KB gzip** (contorno 5,5 + escuelas 27 + catálogos 5,3 + eventos 1,5). **Y de ahí a 10,8 KB el 2026-08-06** con MAP-03 — ver bloque M |
| B4 | ~~Retirar la capa de oferta formativa~~ | ✅ fuera del mapa. El endpoint Django sigue en pie: borrarlo es decisión de Alex (bloque D) |
| B5 | ~~Exponer el filtro por estrato~~ | ✅ la leyenda **es** el filtro. Medido: 5.002 manzanas → **2.408** (estrato 2) → **565** (sin estrato) |
| B6 | ~~Ubicación obligatoria + PATCH que descarta lat/lng~~ | ✅ crear sin ubicación es 400; el PATCH aplica la coordenada nueva **moviendo el punto propio**, nunca el de la Alcaldía ni uno compartido |

#### 3.2 Lo que se aprendió haciendo B6

El bug del PATCH no era una rama olvidada: la condición decía
`if not lugar_incidencia_id and hay lat/lng`, y el comentario encima decía
"si llegan lat/lng nuevos… se reemplaza". El formulario **siempre** manda el
`lugar_incidencia_id` que ya tenía el evento, así que la condición nunca se
cumplía. Código y comentario llevaban meses diciendo cosas distintas y ganaba
el código, en silencio y con un 200 de respuesta.

Y hay una trampa que el arreglo obvio no ve: **corregir el punto en sitio está
mal cuando el punto no es tuyo**. 18 de las 54 actividades comparten el
`lugar_incidencia` de la Alcaldía; mover ese registro las habría movido a las
18 de un golpe. Por eso `_puede_mover_en_sitio` es una guarda de solo lectura
con dos preguntas —¿es el de por defecto? ¿lo comparte alguien?— y solo si las
dos dan que no se toca la fila. Medido hoy: 4 actividades tienen punto propio
y exclusivo, 18 están en la Alcaldía, 32 no tienen ninguno.

### Bloque M — el mapa, tras el plan de corrección (2026-08-06)

El reporte completo con la evidencia es
[`docs/informes/GATE1_MAPA_2026-08-06.md`](informes/GATE1_MAPA_2026-08-06.md).
Acá va solo el estado y lo que falta decidir.

| # | Qué | Estado |
|---|---|---|
| M-01 | ~~La capa de barrios pintaba tiras y features fuera de Kennedy~~ | ✅ **defensivo, en producción.** No era la malla vial (210 features: 144 Polygon + 66 MultiPolygon, cero LineString) ni parseo: 13 barrios con el polígono de otro (M22) que se servían sin filtro. Se descartan al armar; la semilla vuelve a tapar el sector. 🔴 **La raíz sigue abierta** — ver abajo |
| M-02 | ~~Parques amontonados en un punto~~ | ✅ **el síntoma no existía.** 554 coordenadas distintas de 554, 0 nulos, 0 fuera del bbox de Bogotá: las tres hipótesis (geocoding, nulos, CRS) caen con los datos. Lo real era **un** par duplicado en la capa de obras (un parque, dos contratos), ya agrupado en un marcador |
| M-03 | ~~El mapa cargaba capas al abrir~~ | ✅ **abre solo con el croquis** (decisión de Alex). De 38,9 KB gzip a **10,8 KB, −72 %**. Las escuelas eran 27 KB tirados: se descargaban para no pintarse |
| M-04 | 🟡 **Nuevo**: los nombres de la capa de obras llegan con la codificación rota | `URBANIZACIàN … AM\x90RICAS` en los bytes del endpoint. Lo lee el ciudadano en el popup. Es de datos y toca contratos, no solo el mapa. **Sin decidir si entra ahora o aparte** |

**El umbral que estaba en el filo.** El filtro de M-01 descartaba con >50 % del
área fuera de Kennedy, y dos barrios se salvaban con **48,9 %** — a 1,1 puntos
del corte. Medido el barrido: bajarlo a **0,35** lleva el derrame fuera de la
localidad de **3,38 % a 0,42 %** y cuesta 0,05 pp de cobertura, porque la semilla
tapa lo que se descarta. Aplicado. Es paliativo, no cura.

#### 🔴 La raíz de M-01 / M22 — lo único que la cierra de verdad

Repoblar esas geometrías con el `SCACODIGO` correcto. **La fuente ya está en la
BD**: `sector_catastral`, 1.230 filas, sincronizada — no hay que bajar nada de
IDECA. Lo que falta es la correspondencia `barrio.codigo` → `SCACODIGO`.
Resolviendo por nombre normalizado (medido, solo lectura):

| | Cuántos |
|---|---|
| Candidato único por nombre | **8** de 13 |
| Ambiguo (LAS ACACIAS, 3 candidatos) | 1 |
| Sin coincidencia | 4 |

**Y el match por nombre es una pista, no una prueba**: `barrio` son 325 barrios
finos y `sector_catastral` son sectores más gruesos, así que dos cosas con el
mismo nombre pueden no ser el mismo polígono. Cada una se verifica contra el
contorno antes de escribir. Es **DML sobre la BD compartida: de Alex** (§9 de
`CLAUDE.md`), con backup previo.

**De quién es qué:** M-04 y la raíz de M-01 son decisiones de Alex. La
validación visual del mapa (Gate 2 del plan) también.

### Bloque C — estructural: que agregar cosas deje de doler

> **En curso (2026-08-05).** C5 cerrado. C1–C4 y C6 en implementación; cada uno
> se tacha aquí al entrar a producción.

| # | Qué | Detalle |
|---|---|---|
| C1 | ~~**Estado del mapa en la URL**~~ **✅ HECHO 2026-08-05** | Filtros, capas, filtro de estratos, panel y centro/zoom se serializan a query params. Se leen al arrancar (la primera petición ya sale filtrada; un enlace conserva su encuadre) y se escriben con `replaceUrl` + debounce (compartir una vista, recargar y el botón atrás ya funcionan). Los QR sin query siguen abriendo con los defaults |
| C2 | **✅ HECHO 2026-08-05 (PR-0→PR-2)** · PR-3+ evaluado y descartado | **Hecho**: PR-0 registro declarativo `capas.registry.ts` (fija el contrato `publica`, el valor de B1); PR-1 el **panel** se deriva del registro (los 11 `<label>` a mano → un `@for`, verificado visualmente por Alex); PR-2 **`toggleCapa` genérico** (el switch de 13 ramas → un motor + `capaRuntime`, verificado adversarialmente carácter por carácter). Agregar una capa pasó de tocar 5 sitios a 3 declarativos. **PR-3 (loaders genéricos) NO se hace, por decisión de ingeniería**: los loaders no son repetición —cada capa arma marcadores y popups genuinamente distintos (banco circleMarker por estrato, colegios divIcon+matrícula, CAI fijo/móvil, festivales ★, avance)—; genericizarlos reubicaría ese código de presentación dentro del registro, sin borrarlo, y exigiría re-verificar cada popup/ícono a mano por una ganancia modesta. El "−330" del análisis sobrecontó: la repetición real estaba en el template y el toggle, que sí se quitaron (~130 líneas menos) |
| C3 | **Parcial ✅ 2026-08-05** · resto pendiente | **Hecho**: (a) columna `synced_at` **unificada** en las 3 tablas que usaban otro nombre (`ingerido_en`/`sincronizado_at`) — DDL de metadatos aplicado + 2 modelos y 3 comandos actualizados; (b) **licencias** declaradas como constante (`core/licencias.py`, 7 fuentes CC BY 4.0) e impresas por el orquestador. (c) **seco-por-defecto** en los 5 comandos que escribían sin flag (`--dry-run`→`--write`, invertido) + orquestador y tests al día: ahora una corrida manual NO escribe salvo `--write`. (d) **helper `SyncOficialCommand`** (`core/sync_oficial.py`) con `--write`, `hash_fila()` y `upsert()` de una sola sentencia (`INSERT … ON CONFLICT … DO UPDATE`, inyecta las columnas espejo), **probado en aislamiento** (10 tests, sin tocar la BD; uno verifica que reproduce el SQL que `sync_placas` ya usa). **Pendiente**: cablearlo a cada comando + su DDL aditivo de columnas espejo — se hace **uno por uno verificando cada sync al correrlo**, no a ciegas (pegan a servicios externos y escriben en la BD compartida). `fecha_corte` (cai, colegio) NO se renombra: la leen muchas vistas y es la convención de fecha-de-fuente de esas tablas. **Scope de estratificación**: **Bogotá** (decidido por Alex 2026-08-05 — el geocoder del borde lo necesita; el mapa ya recorta a Kennedy al servir) |
| C4 | **Código ✅ HECHO 2026-08-05** · instalar el cron → **falta Alex** | `sync_fuentes_oficiales` ahora es declarativo, **seco por defecto** (`--write` para persistir — invierte el default peligroso), cubre las 11 fuentes en 10 invocaciones, saltea las pesadas (placas, 1,77M filas) salvo `--incluir-pesadas`, y loguea a `logs/`. `cron_sync_oficial.sh` corre con `--write`. 11 tests. **Pendiente**: la línea del `crontab` del host la pones tú (§9) |
| C5 | ~~**Tests de la cadena financiera**~~ **✅ HECHO 2026-08-05** | 15 tests en `apps/presupuesto/tests/test_saldos.py` fijan las tres guardas (`_saldo_disponible_cdp`, `_validar_saldo_cdp`, `ContratoActividadPlanForm.clean()`). Prueban el **borde**: gastar todo el saldo pasa, un peso más lo bloquea — el `>` estricto queda blindado. Sin escribir en la BD ni datos reales (se aísla la decisión) |
| C6 | **Parte segura ✅ 2026-08-05** · datos → decisión de área | **Hecho**: glosario desambigua las tres "actividad" (Evento/ActividadPlan/Actividad-catálogo) y las dos puentes (`contrato_actividad_plan` ✅ llega al KPI vs `contrato_actividad` no) en `docs/GLOSARIO.md`; y `VincularContratoActividadView` → `VincularContratoActividadPlanView` (escribe al plan, el nombre engañaba). **Medido**: la puente del catálogo tiene **18 filas / 16 contratos**, **0 solapan** con la del plan → el panel ignora los 16. **No hay DML limpio**: cada contrato necesita saber a qué `ActividadPlan` mapear (dato del área, como A3). Opciones para Alex: (a) dejar como está + documentado, (b) que cada área re-enganche vía el plan, (c) retirar el catálogo si no aporta |

### Bloque D — limpieza (con evidencia, riesgo BAJO salvo aviso)

| Qué | Tamaño |
|---|---|
| Forms Django sin un solo import: `presupuesto/forms.py`, `forms_cdp.py`, 6 de `admin_org.py`, 3 de `login/forms.py` | ~700 líneas |
| `mapa_kennedy.js` + `.css` huérfanos (su template ya no existe) + las **8 URLs geo** que solo ellos consumían | 1.312 líneas + 8 rutas |
| `static/admin/` commiteado por error — **shadowea los assets reales de Django** | 125 archivos |
| Capa DRF v2 de dashboard nunca conectada (8 endpoints) + 14 de caracterización + legacy de votaciones | 22+ rutas |
| `votaciones.tar.gz`, `estructura.txt` (volcado de árbol de hace 11 meses) | — |
| `staticfiles/` huérfana, root-owned | **89 MB** |
| Frontend: `app.component.html/scss/spec` (scaffold de `ng new`, el spec está roto), `presupuesto-list.component.ts`, `eventos.types.ts` | — |
| **Archivar ~90 scripts SQL y crear un ledger** | Hay colisiones de numeración (dos `005`, tres `003`) y **77 scripts sin registro de si se aplicaron**. Sin ledger, cada auditoría repite este trabajo |

### Bloque E — seguridad, accesibilidad y documentación

**Seguridad — ✅ los cuatro cerrados el 2026-08-06.** Cada uno resultó distinto de
como estaba escrito acá, así que queda el registro de lo que era de verdad:

| # | Lo que decía este documento | Lo que era | Cómo se cerró |
|---|---|---|---|
| **S-3** | "el rate limit de v2 se saltea cambiando de path" | Peor: **la versión con límite es la que nadie usa**. El kiosko y Angular pegan a v1, que no tenía ninguno (medido: 70 POST, cero 429) | Límite real en v1 (30/min votar, 20/min validar) — pero **solo después** de arreglar la IP, ver abajo |
| **S-1** | un endpoint que devuelve nombre por cédula | **Dos**: el gemelo de votaciones no estaba listado, y encima no lo llama nadie | Respuesta en dos niveles: con el `?t=` firmado del QR o con sesión, los datos; sin eso, si existe y ni un nombre. Nunca se bloquea el acceso |
| **S-4** | "los QR se acuñan sin auth para cualquier id" | Cierto, y además `/qr/candidate/<id>.png` era un oráculo de ids | Acuñar exige `votaciones_admin`; las dos rutas PNG retiradas. El kiosko no se toca: el ciudadano escanea, no acuña |
| **S-2** | "parece omisión" | Lo era. Y sobrevivió porque **no estaba en ninguna de las dos listas** del test que vigila qué es público | Gate + entra a la lista |

#### 🔴 El hallazgo que ninguno de los cuatro anticipaba

**nginx no sabía quién era el cliente.** Medido sobre el access log real: el
100 % de las peticiones figuraba como `172.18.0.1` o `127.0.0.1`, porque la
conexión no llega del ciudadano sino de ngrok por el gateway de Docker. Las tres
zonas de `limit_req` usan `$binary_remote_addr` — o sea que **las tres eran topes
globales, no por cliente**.

Y ya estaba haciendo daño: la zona `caracterizacion_api`, creada para frenar a un
bot enumerando cédulas, le ponía **10 peticiones por minuto a todos los
ciudadanos juntos**. El sexto vecino que abría el wizard en el mismo minuto
recibía un 429 por culpa de los cinco anteriores.

Se arregló en dos mitades, porque una sin la otra no sirve: el bloque `real_ip`
en `nginx.conf` (con OK de Alex) y `RATELIMIT_IP_META_KEY` en `settings.py`
—django-ratelimit leía `REMOTE_ADDR`, donde gunicorn pone el contenedor de
nginx—. Verificado cliente por cliente: el cliente A se topa con su 429 y el
cliente B, desde otra IP, pasa.

**La lección para este documento:** los cuatro ítems describían síntomas leídos
del código. Tres de los cuatro eran peores de lo escrito, y el problema más caro
—el rate limit global— no era ninguno de ellos: era la premisa que los cuatro
daban por buena.

**Queda abierto de seguridad:** `QR_TOKEN_ENFORCE` sigue en modo suave (el `?t=`
ya viaja en los QR de votaciones, pero el lado público todavía no lo exige), y
el `UNIQUE (evento, document_number)` **ya no existe en la BD**: el anti-doble-voto
vive solo en código Python bajo `select_for_update`.

**Accesibilidad — ✅ las 5 pantallas nuevas, cerradas el 2026-08-06.**
Las 5 (`colegios-list`, `colegio-detalle`, `resumen-vigencia`, `area-panel`,
`area-cai`) no habían pasado por el plan del mapa. Lo que se hizo:

| Lo que decía este documento | Lo que se hizo |
|---|---|
| En `colegios-list` la fila con `role="button"` es la **única** vía al detalle | El nombre del colegio es un `<a routerLink>` de verdad, con `aria-label` que incluye la sede (un colegio de 4 sedes daba 4 enlaces idénticos). La fila sigue clickeable para el mouse, pero ya sin `role`/`tabindex`: se acabaron el nombre de 6 celdas pegadas y el "no responde a Espacio". Mismo tratamiento en la tabla de CAI, donde la acción (centrar el mapa) pasó a un `<button>` real dentro de la celda |
| El error del formulario de entregas no se anuncia | **La causa que decía este documento —`role="alert"` ausente— era FALSA**: está desde el 2026-06-04 (`git log --diff-filter=A`). La causa real: `validar()` llenaba `seccionesConError` pero **nunca** `erroresCampo`, del que cuelgan los `<p class="field__error">`. Al fallar la validación del navegador, el ciudadano leía "Completa todos los campos requeridos" sin que nada dijera **cuál**. Ahora `validar()` escribe error por campo (tipo de documento, número, nombre, apellido, insumos, firma). Se quitó de paso el mensaje de firma duplicado |
| 11 barras de carga/error sin live region | **13 en estas 5 pantallas**, todas con `role="status"` (carga/aviso) o `role="alert"` (fallo). El número de arriba se quedaba corto |
| `<th>` sin `scope` | Los 32 `<th>` de las 5 pantallas llevan `scope="col"`, incluida la columna de acciones, que estaba vacía y no se anunciaba (`<span class="ui-sr-only">Acciones</span>`) |
| Tablas de 8 columnas sin wrapper responsive | Las 5 tablas envueltas en `.ui-table-responsive` — que **ya existía** y lo usaban 25 de los 27 archivos con tabla: estas pantallas eran la excepción, no la regla |
| Contraste `#D97706` = 3,19:1 | → `#B45309` (5,02:1) en el badge "móvil" de CAI y en su marcador del mapa. Ojo: **el problema no era "sobre blanco"** sino texto **blanco sobre naranja**, que da el mismo 3,19:1 (el contraste es simétrico) |

**Lo que NO se tocó, y por qué.** Medido sobre todo el frontend, el problema es
mucho más grande que las 5 pantallas: **82 barras** de carga/error sin live
region en ~35 componentes, **299 `<th>` sin `scope`**, y 2 tablas sin wrapper
(`actividades-subgrupo`, `proyecto-360`). Es una barrida mecánica pero sobre
archivos que no se leyeron: poner `role="alert"` a ciegas en una barra que es un
aviso, y no un fallo, empeora las cosas. Va como frente propio.

- **Font Awesome no está instalado** — solo `lucide-angular`, y hay **615**
  `<i class="fa …">` en el proyecto que no pintan nada. En estas 5 pantallas el
  único que hacía daño de verdad era el botón de borrado de `colegio-detalle`,
  cuyo **único** contenido era el icono: quedaba un botón en blanco. Ahora dice
  "Borrar". Los otros son decorativos (van junto a un texto que sí se ve). Qué
  hacer con los 615 —instalar Font Awesome o migrar todo a lucide— es decisión
  de Alex, no de esta tanda.

**Documentación — ✅ lo que mentía, cerrado el 2026-08-06.** Lo que miente pesa
más que lo que falta, así que se atacó primero:

| Lo que decía | Qué se hizo |
|---|---|
| `FRONTEND_ANGULAR.md:253` manda compilar **sin `--base-href=/app/`** — el comando que dejó la SPA en blanco el 2026-06-18 | Arreglado en la **causa**, no en el texto: `frontend/angular.json` ahora fija `"baseHref": "/app/"` en la configuración `production`, así que `npm run build` a secas ya sale bien (verificado: el `index.html` del build sale con `<base href="/app/">`). Un documento que dice "acuérdate de la bandera" es una bandera más que olvidar. La guía además lo explica y deja el comando de comprobación |
| `CLAUDE.md` afirma que no hay DRF, que `kactivo` está activa, que existen `kordial` y `VitalK`, y describe un "plan activo" sobre una rama que ya no está. Lista 6 apps de 13 | Las apps y el DRF del §3 ya se habían corregido el 2026-08-05; faltaba el §7, que **se contradecía con el §3 dentro del mismo archivo** ("Sin DRF" en el punto 7 contra "todo lo nuevo es DRF" en el 3). Reescritos los puntos 4, 7 y 8. El punto 4 llevaba **más de un año** diciéndole a cada sesión nueva que la rama `feat/integracion-geo-eventos-dashboard` era el trabajo en curso: se conservan sus hechos de BD, que sí siguen vigentes, y se retira el "plan activo" |
| `PLAN_FRONTEND.md` describe Angular como decisión **pendiente y condicional**. **Archivar** | Archivado en `docs/_historico/2026-05_plan_frontend.md` con una nota de por qué. Una sesión anterior (2026-07-16) lo había detectado y **no lo archivó porque exigía reescribir `CLAUDE.md`** — eso es justo lo que se hizo ahora, junto con `docs/README.md` y `.claude/agents/api.md` (que además apuntaba a dos rutas que ya no existían) |
| `DEUDA_TECNICA.md` da por abiertos 8 ítems ya cerrados y tiene 3 cifras mal | Repasado ficha por ficha contra el código. **Seis** estaban cerrados (M-EDU, R1, B6, F5, F6 y dos de las tres "mentiras más caras"). Retirados, con el motivo de cada uno. Se agregaron dos fichas nuevas con la deuda de accesibilidad ya **medida** (F7) y la de Font Awesome (F8) |
| Falta manual de módulo para 8 apps en producción | **Sigue faltando** — es lo único de este bloque que no es drift sino ausencia. Entre ellas **caracterización** (8 wizards) y **presupuesto** (la cadena central) |

**La lección de método, que vale para todo este documento.** El caso más caro
ya lo corrigió `ESTADO.md` §3.1 por su cuenta, y conviene no perderlo: el hueco
de RBAC del motor de consulta de beneficiarios —que cualquiera con el módulo
`dashboard_ia` viera el universo completo de personas— se declaró "verificado
abierto" el 2026-08-03 estando **cerrado desde el 2026-07-14** (commit
`01c573c`). El error fue de método: se hizo `grep` del
símbolo `aplicar_subgrupo`, y el arreglo usa otros nombres
(`scope.personas_beneficiarias_visibles`, `scope.participaciones_visibles`, en
`apps/dashboard/services/ia_beneficiarios.py`). **Buscar un nombre no es
verificar una propiedad** — es el mismo tipo de error que los cuatro ítems de
seguridad de este bloque, que también describían síntomas leídos del código.

---

## 4. Lo que no se toca sin decisión de un área

| Qué | Quién |
|---|---|
| Los CSV con cédulas y el repositorio público | Alex |
| A qué actividad del plan aporta cada una de las 32 Novenas/Recorridos | el área dueña del evento |
| Los 20 contratos sin actividad: cuál va con cuál | cada área, desde la pantalla nueva |
| El 74 contra 75 de sedes distritales | Secretaría de Educación |
| Dónde están los CAI móviles | Secretaría de Seguridad |
| Migrar `scan.html` a Angular (desata media limpieza del backend) | Alex |
| Borrar cualquier cosa del bloque D | Alex |

---

## 5. Cómo se midió

Ocho revisiones en paralelo, todas de solo lectura: `SELECT` sobre
`poblacion_kennedy`, `GET` a los endpoints propios y a los servicios del
Distrito, `git ls-files`, `crontab -l`, análisis AST del árbol. No se ejecutó
ningún comando de sincronización, ni siquiera en seco.

Las cifras de este documento son medidas, no estimadas. Cuando algo no se pudo
verificar —los ~90 scripts SQL sin ledger— dice que no se sabe, en vez de
suponerlo.

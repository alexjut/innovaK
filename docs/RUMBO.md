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

### 0.2 Tres tokens HMAC vivos publicados

`docs/manuales_modulos/cultura.md:41-43`. Detectado el 2026-07-16, sigue igual.
Rotarlos exige rotar `SECRET_KEY`. `QR_TOKEN_ENFORCE` sigue en `False`, o sea
que los formularios públicos con QR **hoy no validan token**.

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

**🔴 Corrección a este mismo documento.** La primera versión decía que A5
"unifica los dos universos" dando a entender que valía 2.545. **Vale 136.** De
las 2.693 personas inscritas, **solo 137 tienen número de documento
registrado**: las otras 2.556 se capturaron solo con nombre. El backfill no las
puede convertir en beneficiario, y hace bien — inventarles un documento sería
peor que no tenerlas.

**Hallazgo nuevo: 2.556 personas atendidas sin forma de identificarlas.** No se
pueden deduplicar, ni verificar, ni cruzar con otro sistema. Son datos
históricos de Novenas y Recorridos; recuperar el documento no es cosa de
código. Y de las 137 que sí lo tienen, **una falló por documento duplicado**:
dos filas de `persona` comparten el documento 1030547250, o sea que hay
personas repetidas en la base.

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
| B3 | ~~Parques a lazy~~ | ✅ la carga inicial pasó de **342 KB a 39,9 KB gzip** (contorno 5,5 + escuelas 27 + catálogos 5,3 + eventos 1,5) |
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

### Bloque C — estructural: que agregar cosas deje de doler

> **En curso (2026-08-05).** C5 cerrado. C1–C4 y C6 en implementación; cada uno
> se tacha aquí al entrar a producción.

| # | Qué | Detalle |
|---|---|---|
| C1 | ~~**Estado del mapa en la URL**~~ **✅ HECHO 2026-08-05** | Filtros, capas, filtro de estratos, panel y centro/zoom se serializan a query params. Se leen al arrancar (la primera petición ya sale filtrada; un enlace conserva su encuadre) y se escriben con `replaceUrl` + debounce (compartir una vista, recargar y el botón atrás ya funcionan). Los QR sin query siguen abriendo con los defaults |
| C2 | **PR-0 ✅ HECHO 2026-08-05** · rewiring → **necesita QA visual** | Existe el registro declarativo `capas.registry.ts` (las 13 capas como datos) + su spec, que **fija el contrato de `publica`** (Banco=false, resto=true) — el valor estructural de B1. **Falta el rewiring** del componente (template → toggle → loaders, los −330 líneas), que según el propio plan se verifica **capa por capa mirando el mapa** (swatch, popup, sub-leyendas, orden de polígonos): eso no se hace a ciegas —ya se coló un bug de z-index así— y se hará con el mapa abierto en el navegador |
| C3 | **Parcial ✅ 2026-08-05** · resto pendiente | **Hecho**: (a) columna `synced_at` **unificada** en las 3 tablas que usaban otro nombre (`ingerido_en`/`sincronizado_at`) — DDL de metadatos aplicado + 2 modelos y 3 comandos actualizados; (b) **licencias** declaradas como constante (`core/licencias.py`, 7 fuentes CC BY 4.0) e impresas por el orquestador. (c) **seco-por-defecto** en los 5 comandos que escribían sin flag (`--dry-run`→`--write`, invertido) + orquestador y tests al día: ahora una corrida manual NO escribe salvo `--write`. **Pendiente**: upsert en 1 sentencia y poblar `fuente`/`hash_fila`/`fecha_fuente` donde falten (van con el helper `SyncOficialCommand` que los escriba — agregar columnas vacías antes es prematuro). `fecha_corte` (cai, colegio) NO se renombra: la leen muchas vistas y es la convención de fecha-de-fuente de esas tablas. **Scope de estratificación**: **Bogotá** (decidido por Alex 2026-08-05 — el geocoder del borde lo necesita; el mapa ya recorta a Kennedy al servir) |
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

**Seguridad:**
- **S-3**: votaciones v1 y v2 están ambas ruteadas; el rate limit de v2 **se saltea cambiando de path**. Relleno de urnas.
- **S-1**: `/caracterizacion/api/persona/?doc=` devuelve nombre completo desde una cédula, sin auth. Mitigado **solo en nginx** — quien pegue a gunicorn directo lo salta.
- **S-4**: los QR de votaciones se acuñan sin auth para cualquier id.
- **S-2**: `/geo/api/oferta-formativa/` sin gate, mientras sus vecinos del mismo archivo sí lo tienen. Parece omisión.

**Accesibilidad** (las 5 pantallas nuevas no pasaron por el plan del mapa):
- 🔴 En `colegios-list`, la fila con `role="button"` es la **única** vía al detalle: sin `<a>`, sin tecla Espacio, y el nombre accesible es la concatenación de las 6 celdas.
- 🔴 El error del formulario de entregas no se anuncia (`role="alert"` ausente): con lector de pantalla, "Registrar" no hace nada.
- 11 barras de carga/error sin live region; `<th>` sin `scope`; tablas de 8 columnas sin wrapper responsive.
- Contraste: `#D97706` sobre blanco da **3,19:1**. Debe ser `#B45309` (5,02:1).
- **Font Awesome no está instalado** — solo `lucide-angular`. Cada `<i class="fa …">` del proyecto no pinta nada, y uno de ellos es el único contenido de un botón de borrado. Es previo y general, pero hay que decidirlo.

**Documentación** — lo que miente pesa más que lo que falta:
- `docs/frontend/FRONTEND_ANGULAR.md:253` manda compilar **sin `--base-href=/app/`**: es exactamente el comando que dejó la SPA en blanco el 2026-06-18. **Seguir la guía rompe producción.**
- `CLAUDE.md` —lo primero que se lee cada sesión— afirma que no hay DRF (hay 46 archivos con APIView), que `kactivo` está activa (borrada en mayo), que existen `kordial` y `VitalK` (no existen), y describe un "plan activo" sobre una rama que ya no está. Lista 6 apps de 13.
- `docs/frontend/PLAN_FRONTEND.md` describe Angular como decisión **pendiente y condicional**. Mantenerlo vivo hace que se proponga HTMX en agosto de 2026. **Archivar.**
- `DEUDA_TECNICA.md` da por abiertos 8 ítems ya cerrados y tiene 3 cifras mal. Un documento de deuda con un tercio de fichas falsas hace que la próxima sesión desconfíe de todo.
- Falta manual de módulo para 8 apps en producción, entre ellas **caracterización** (8 wizards) y **presupuesto** (la cadena central).

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

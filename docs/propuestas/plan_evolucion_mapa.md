# Plan — Evolución del Mapa de Kennedy y la plataforma geoespacial

> **v2 — 2026-07-16.** Reescrito tras la decisión de Alex: *"la mejor opción, la más
> profesional; siempre lo más óptimo"*. La v1 proponía un camino conservador
> (posponer MapLibre, PostGIS opcional). **Era el cauteloso, no el profesional** —
> abajo está el argumento técnico del cambio, no es complacencia.
>
> Cada número está **medido contra producción**, no estimado.
> Fase 0 ✅ ejecutada · Fase 1 aprobada (Alex autorizó reconstruir la imagen).

---

## 0. Qué cambió respecto de la v1, y por qué

**(1) Fase 2 y 3 no se pueden separar.** La v1 proponía teselas primero y MapLibre
"cuando haga falta". Está mal: si Leaflet consume teselas vectoriales necesita
`leaflet.vectorgrid`, que las **re-dibuja en Canvas/SVG** — se pierde justo el
beneficio (GPU) y se hace el trabajo de capas **dos veces**: una para que Leaflet
las trague, otra para tirarlo y poner MapLibre. **MapLibre es el consumidor nativo
de vector tiles.** Van juntas.

**(2) PostGIS pasa de "opcional" a fundación — en instancia propia.** El índice
shapely + STRtree en RAM por worker, cacheado en Redis, es un **workaround**, no
arquitectura. Existe porque no hay PostGIS — pero esa restricción aplica a la **BD
compartida**, no a una nuestra. El dato geográfico de referencia (manzanas, placas,
barrios) **lo sincronizamos de Catastro; no lo produce innovaK**: no pertenece a la
BD operacional. Separarlo es la arquitectura correcta, y de paso respeta intacta la
restricción que peleamos.

**(3) Lo que NO hacemos, y también es criterio profesional.** Más tecnología no es
más profesional:

| Descartado | Por qué |
|---|---|
| Tile server (Martin / pg_tileserv) | El dato es **casi inmutable** (Decreto 394 de **2017**). Un servidor vivo para dato inmutable es sobreingeniería: agrega un contenedor, carga a la BD y un punto de falla, a cambio de nada. **PMTiles pre-construido es superior aquí**: cacheable para siempre, sin runtime, sin BD. |
| PostGIS en `poblacion_kennedy` | BD compartida con otros sistemas. Nunca. |
| 3D / terreno | Sin caso de uso. Si aparece, MapLibre ya lo trae. |

---

## 1. Arquitectura objetivo

```
  Catastro / IDECA  (ArcGIS REST · WFS)
        │  GDAL/ogr2ogr · capas como DATA · cron mensual · fecha_fuente
        ▼
  innova_gis  (PostGIS PROPIO — solo dato de referencia)          ← NO es poblacion_kennedy
        │                                    │
        │ tippecanoe                         │ ST_Contains / ST_Intersects (SQL)
        ▼                                    ▼
  capas.pmtiles  (archivo estático)     geocoder · estrato_en_punto · joins
        │  nginx + HTTP range requests
        ▼
  MapLibre GL  (Angular · style spec declarativo)
```

**Qué desaparece:** el índice shapely en RAM, su caché de Redis, la invalidación
manual, los 8,67 MB por HTTP, el raspador por capa, y `estrato_en_punto` en Python.

---

## 2. De dónde partimos (medido, 2026-07-16)

```
Frontend      Leaflet 1.9.4 · mapa.component.ts = 1.093 líneas (un archivo hace todo)
Transporte    GeoJSON crudo. cache_page 1h en Redis. gzip por nginx.
Motor         shapely + STRtree en Python, índice cacheado en Redis. SIN PostGIS.
Ingesta       1 comando a mano por capa (sync_estratificacion → ArcGIS REST)

manzana_estrato  18.929 filas · 29,10 MB   (Kennedy: 4.966 · 8,67 MB · 2,84 MB gzip)
barrio              325 filas · solo 75 con geometría          ← deuda M22
upz                  12 · escuela 241 puntos · parque 554 puntos
```

Disponible en Catastro y hoy fuera de alcance sin escribir código nuevo:
`manzana` (44.519) · `lote` (933.817) · `sectorcatastral` (1.230) ·
`placadomiciliaria` · `barrioslegalizados` (1.709) · + carpetas de ambiente,
movilidad, espaciopúblico, recreación y deporte, salud, educación…

---

## 3. Fase 0 — Geocodificador ✅ **EJECUTADA** (`feat/geo-fase0-geocoder`, `bb69bcb`)

```
dirección → placa domiciliaria oficial (Catastro) → punto → manzana → estrato
```

`services/geocoder.py` · `asignar_estrato_org --por-direccion` · 21 tests sin red.
**6/24 → 14/24** medido en dry-run contra producción. Sin DDL.

Las 3 reglas de formato de Catastro (no documentadas en ningún lado; descubiertas
probando y blindadas con tests): **BIS pegado** (`KR 72FBIS`) · **en calle el SUR va
en la vía** (`CL 42F S`) · **en carrera el SUR va en la placa** (`KR 78M` + `58J 05 S`).

**Guardia de Kennedy:** solo se acepta el punto si cae dentro del contorno. Sin él el
geocodificador da respuestas *seguras pero equivocadas* — una inscripción del piloto
resolvía a "estrato 4" con 78 % de acuerdo, apuntando fuera de la localidad. Delató 4
organizaciones que declararon barrio de Kennedy con dirección de otra localidad →
revisión manual.

**Pendiente al migrar a PostGIS:** cachear `placa → punto` en `innova_gis` (hoy cada
corrida vuelve a preguntarle a Catastro).

### 3-bis. Fase 0-bis — Las direcciones se eligen, no se escriben ✅ (2026-07-16)

Ejecutada el mismo día, en `feat/direcciones-que-existen` (`4cbf46c`).
**Ninguna dirección se captura ya como texto libre: el usuario elige una que existe.**

- `geocoder.sugerir()` + endpoints `/geo/api/direcciones/{sugerir,validar}/`
  (`apps/georeferenciacion/api/direcciones.py`, ruteados en `urls.py:55-58`).
- Componente Angular `shared/direccion/direccion-picker.component.ts`, conectado al
  form público del Banco y al de eventos.
- **Caché `geocodificacion_cache`** (DDL **011 aplicado**) — imprescindible: ver la
  medición de Catastro en `DEUDA_TECNICA.md` **G7** (1 acierto de 6, timeouts a 60 s).
  **Catastro no se consulta en vivo.**
- Capa `placa_domiciliaria` — DDL **012 APLICADO** (OK de Alex, 2026-07-16); el
  `sync_placas` de las **1,77 M de placas** de Bogotá quedó corriendo.
- **2 bugs corregidos:** el estrato `0` de Catastro ya no se devuelve (cae al voto
  del entorno); el rescate por barrio ya no aplica a direcciones que resolvieron
  fuera de Kennedy.

**Estado:** ✅ **cascadeada a producción** (`produccion=3fa59cf`, 2026-07-16), sync
completo (1.771.088 placas · 217.672 en Kennedy).

**G4 se cerró midiendo, no parcheando:** la dirección más larga de las 1.771.088
placas de Bogotá tiene **25 caracteres** (promedio 16) y **ninguna** pasa de 50.
El límite de `CharField(50)` no puede alcanzarse con una dirección elegida del
catastro, así que no hay callejón sin salida que arreglar.

---

## 3-ter. Fase 0-ter — Repintar y ordenar el mapa con lo que YA tenemos

**Decisión de Alex (2026-07-16):** *"en la evolución del mapa está repintar lo que
tenemos ya y ordenar bien el mapa con todo lo que ya tenemos"*.

Va **antes** de la Fase 1. El motivo es sencillo: hoy el mapa muestra bastante
menos de lo que la BD ya sabe, y eso no lo arregla PostGIS ni MapLibre — lo
arregla ordenar lo que hay. Traer tecnología nueva sobre un mapa desordenado
mueve el desorden de lugar.

**Lo que la BD tiene, y qué ve el mapa hoy** (medido 2026-07-16):

| Capa | Filas | ¿La muestra el mapa? |
|---|---|---|
| `placa_domiciliaria` | 1.771.088 · 217.672 en Kennedy | **no** (es de hoy) |
| `manzana_estrato` | 18.929 · 4.966 en Kennedy | **no dibuja** — ver "Bug abierto" |
| `sector_catastral` | 1.230 · **cubren 95,9 % del contorno** | **no** (es de hoy) |
| `barrio_legalizado` | 1.709 · 138 en Kennedy · cubren 21,1 % | **no** (es de hoy) |
| `parque` | 554 | sí |
| `escuela` | 241 (25 caen fuera de la localidad) | sí |
| `barrio` | 325 (75 con geometría) → **cubren 56 %** | parcial — deuda **M22** |
| `upz` | 12 | sí |
| `lugar_incidencia` | 71 | sí |
| `inscripcion_banco_iniciativa` | 24 · 14 con punto (desde hoy) | **no** (pendiente) |

### Por qué el mapa se ve mal — diagnóstico medido (2026-07-16)

Alex: *"creo que el mapa está mal dibujado"*. Lo estaba, y por una razón concreta:

- **El mapa dibuja el 56 % del territorio.** De 325 barrios solo 75 tienen
  geometría, así que el 44 % de Kennedy sale en blanco: un queso suizo. Es M22.
- **`manzana_estrato` cubre 67,9 %, y eso está bien** — el 32 % restante son las
  calles entre manzanas. Ese número no hay que "arreglarlo".
- **25 de 241 escuelas caen fuera de la localidad** (10 %). Cuatro están a menos
  de 50 m del borde (precisión, tolerable) pero **una está a 4,7 km**, en otra
  localidad. Mismo problema que las 7 organizaciones del Banco: dirección sin
  validar al capturar.
- **`parque` está sano**: 554/554 con geometría legible, ninguno a más de 423 m
  del contorno, y traen estrato propio. La diferencia con `escuela` es el origen:
  parque vino con geometría de Catastro, escuela vino de direcciones escritas.

**La salida NO es reparar el catálogo de 325 barrios cruzando nombres** — eso ya
se midió y es un callejón sin salida (`barrioslegalizados` acierta 2 de 13,
`sectorcatastral` 3 de 13). La salida es pintar la capa oficial:

| Capa oficial | Polígonos que tocan Kennedy | Cubren |
|---|---|---|
| **`sector_catastral`** | 135 | **95,9 %** ← la que arregla el mapa |
| `barrios_legalizados` | 163 | 21,1 % |

O sea: **56 % → 95,9 %**. `barrios_legalizados` NO lo arregla (son solo los barrios
que pasaron por el trámite de legalización, una quinta parte del suelo) y conviene
dejarlo escrito para que nadie lo vuelva a intentar. Entra igual por valor propio:
qué barrios están legalizados y por cuál acto administrativo.

**Ninguna de las dos resuelve M22 para el Banco.** El estrato de una organización
lo da el geocodificador contra la placa domiciliaria, no el polígono del barrio.
Son para **dibujar**.

### Hecho hoy (2026-07-16) — cascadeado a producción

- **DDL 013**: `sector_catastral` (1.230) + `barrio_legalizado` (1.709),
  sincronizadas y verificadas contra la BD local. Códigos en TEXT, no integer:
  traen ceros a la izquierda (`'004622'`, `'08'`) que son parte del código.
- **Bug de la clave de Catastro**: la config de `barrios_legalizados` apuntaba el
  upsert a `CODIGO_ID`, un campo que el servicio **publica pero nunca llena**
  (NULL en las 1.709 filas). El sync bajaba 1.709 polígonos, los descartaba todos
  y reportaba éxito. La clave real es `OBJECTID`.
  **Y ya había un test para eso** (`test_la_clave_esta_entre_las_columnas_mapeadas`)
  que pasaba: la config era coherente *de forma* (mapeaba `CODIGO_ID → codigo` y
  usaba `codigo` de clave). El bug vivía en el dato, no en la forma — ningún test
  unitario lo veía. Por eso el arreglo de fondo fue en el sync: ahora cuenta los
  descartes por motivo y **bajar features sin quedarse con ninguna fila es error,
  no éxito silencioso**.
- **Estratificación aligerada**: Catastro entrega 14-15 decimales por coordenada
  (nanómetros en un mapa de ciudad). Servida a 6 decimales (~11 cm): **2,71 MB →
  1,01 MB gzip**, con 0,05 % de diferencia de área.
- **Capas de tipo de evento retiradas del panel**: eran los MISMOS `tipos_evento`
  que los chips de "Tipo de evento" en Filtros, por otra vía (los chips filtran en
  el servidor, los checkboxes escondían en el navegador). Podías filtrar "Curso"
  arriba, destildarlo abajo y no ver nada sin explicación.
- **Coordenadas del Banco** (DDL 012): las 24 inscripciones no se veían en el mapa
  porque la tabla nunca tuvo lat/lon. El picker las resolvía y `buildFormData()`
  **las botaba al enviar**. Arreglada la captura (no solo el backfill: si no, cada
  inscripción nueva vuelve a nacer invisible). 14 de 24 quedan dibujables.

### 🔴 Bug abierto — la estratificación no dibuja

**Síntoma**: se prende el check, la petición sale, y no aparece nada.

**Descartado con evidencia** (no son la causa):

- Los datos: 4.966 manzanas, geometría impecable (0 nulos, 0 anillos rotos, 0
  ilegibles), estratos 0-4.
- El endpoint: 200 en 0,7 s, con sesión **y** con JWT. `recortado_a_kennedy=true`.
- El bundle: fresco, contiene la capa, el checkbox y la leyenda.
- La función de estilo: existe, recibe `properties.estrato` y devuelve la paleta
  correcta (`fillColor` + `fillOpacity: 0.55`).
- El renderer de canvas: **no está roto**. Va dentro de `style` y no como opción de
  `L.geoJSON` porque es parte de `PathOptions` — así lo tipa `@types/leaflet` y
  Leaflet lo aplica igual vía `setStyle`. Moverlo no compila.
- El orden de `ngModel`/`(change)`: los listeners del directivo se registran dentro
  de `ɵɵelementStart`, antes que los del template → el modelo sí está actualizado.
- El CSS: la regla `canvas {...}` del SCSS está dentro de `.chart-box` (Chart.js) y
  además la encapsulación de Angular no alcanza los elementos que Leaflet crea en
  runtime.

**Evidencia del navegador** (Alex, consola): `canvas=1 paths=569`.

- `canvas=1` → **el renderer existe y la capa se agregó al mapa**. Descarta todo el
  camino toggle → petición → `L.geoJSON` → `addTo`.
- `paths=569` **no son las manzanas** (son 4.966; `L.geoJSON` crea un elemento por
  feature). Son las otras capas: 554 parques + contorno + eventos. Los atributos
  reportados (`fill:"none"`, `stroke:"rgb(214,0,28)"`) corresponden **exactamente**
  al contorno de la localidad (`style: {color:'#D6001C', weight:3, fill:false,
  dashArray:'6 6'}`), que es así a propósito.
- Además: si las manzanas se dibujaran como SVG **no habría canvas**. El renderer de
  canvas pinta en el bitmap, no produce paths.

**Siguiente paso** — el canvas existe, así que la pregunta es si está pintado:

```js
(()=>{const c=document.querySelector('.leaflet-overlay-pane canvas');if(!c)return 'no hay canvas';
const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;
for(let i=3;i<d.length;i+=4)if(d[i])n++;
return `buffer=${c.width}x${c.height} css=${c.style.width}x${c.style.height} pintados=${n}`})()
```

- `buffer=0x0` → el canvas no tiene tamaño: bug de dimensionado.
- `pintados=0` con buffer normal → el redraw no ocurrió o dibujó en vacío.
- `pintados>0` → está pintado y no se ve: z-order u opacidad.

**Alcance:**

1. **Estratificación al mapa.** Es la capa que da contexto a todo lo demás: un
   evento en estrato 2 y otro en estrato 4 no son el mismo evento. Está en BD
   (`manzana_estrato`), el endpoint la sirve recortada a Kennedy y aligerada, y el
   frontend la pide — pero **no dibuja**: ver "Bug abierto" arriba.
1-bis. **Pintar `sector_catastral`.** Es lo que lleva el mapa del 56 % al 95,9 %
   del territorio. La capa ya está en BD desde hoy; falta el endpoint (recorte al
   contorno, mismo patrón que estratificación) y la capa en el frontend.
1-ter. **Las 24 del Banco al mapa.** Ya tienen punto (14 de 24). Falta el endpoint
   GeoJSON y el sub-filtro "Iniciativas" bajo la pestaña **Deporte** de
   `mapa-tabs`. **Tope como dato, no como código** (decisión de Alex 2026-07-16):
   `BANCO_MAPA_TOPE = 93` — hoy con 24 no hace nada; el día que entren más, pinta
   las 93 mejores por calificación cambiando ese número, sin desplegar. Las 93 son
   las que recibirán incentivo a futuro; **todas las que entren se muestran** para
   que cuando se elijan ya estén en el mapa.
2. **Un componente de mapa reutilizable.** Hoy hay **5 componentes que instancian
   `L.map()` cada uno por su cuenta** (`mapa`, `infra-detalle`, `subgrupo-detalle`,
   `festivales-list`, `evento-form`) y **cero** código compartido. Agregar una capa
   hoy es agregarla cinco veces. Extraer a `shared/` es la precondición de todo lo
   que sigue — incluida la Fase 2.
3. **Orden de capas y leyenda.** Definir el apilado (polígonos de contexto abajo →
   puntos de dato arriba), agrupar la leyenda por naturaleza (territorio /
   equipamiento / actividad) y que los controles digan qué prenden.
   *Parcial (2026-07-16):* retiradas del panel las capas de tipo de evento, que
   duplicaban los chips de Filtros por otra vía.
4. **M22 deja de bloquear.** 250 de 325 barrios no tienen geometría, y el mapa los
   pinta como si el territorio no existiera. Con `sector_catastral` (95,9 %) +
   `manzana_estrato` + el geocodificador, el barrio deja de ser la unidad
   obligatoria de agregación.
5. **Las 25 escuelas mal ubicadas.** Regeocodificar sus direcciones con el picker.
   La herramienta ya existe y es instantánea (capa local). Una está a 4,7 km, en
   otra localidad: no es ruido de borde, es dato malo.

### Lección transversal de la jornada

Tres bugs distintos, el mismo patrón: **fallan en silencio y reportan éxito**.

- El sync descartaba 1.709 polígonos y decía "ESCRITO: 0 filas" en verde.
- El endpoint del mapa devolvía `200` con `features: []` sin loggear: desde el
  navegador, "no hay data" y "se rompió" se veían idénticos.
- El frontend hacía `error: () => { /* sin capa, no rompe el mapa */ }` y se tragaba
  el error entero.
- Y el picker resolvía la coordenada de la sede y `buildFormData()` la botaba.

Ninguno lanzaba una excepción. Por eso llevaban meses ahí. **Al agregar una capa o
un campo, la pregunta no es "¿funciona?" sino "¿cómo me entero de que no?"**.

**Por qué antes de la Fase 1:** si el mapa se reordena después de migrar a PostGIS
y PMTiles, se reordena dos veces. Y el componente compartido del punto 2 es
requisito de la Fase 2 (MapLibre) igual — se hace ahora o se hace ahí, pero se hace.

---

## 4. Fase 1 — `innova_gis` (PostGIS propio) + ingesta declarativa

**Aprobada por Alex** (autorizó reconstruir la imagen).

### 1a. Contenedor `innova_gis`

`postgis/postgis:16-3.4`, volumen propio, **solo dato de referencia**. Reconstruible
desde cero corriendo el sync: **no hay dato irremplazable** — todo viene de Catastro.
Eso lo hace de bajo riesgo: si se pierde, se re-sincroniza.

`poblacion_kennedy` **no se toca**. Django usa dos conexiones (`DATABASES['gis']`) +
un router: `apps.georeferenciacion` (capas de referencia) → `gis`; todo lo demás →
`default`. Sin FKs cruzadas entre bases (se cruzan por código, como ya hace el
proyecto con los catálogos).

### 1b. GDAL — "algo mejor que ArcGIS"

El problema no es ArcGIS como fuente: es que lo **raspamos a mano, capa por capa**.
`sync_estratificacion.py` está escrito para UNA capa (detecta campos, convierte rings
de Esri, upsert). Cada capa nueva = repetir todo.

**GDAL/`ogr2ogr`** es el estándar de facto y habla **todas** las fuentes con una sola
interfaz: ArcGIS REST (`ESRIJSON`), WFS, Shapefile, GeoJSON, GeoPackage, CSV, PostGIS,
Parquet. Reproyecta, filtra, recorta y renombra campos en un paso. Entra por el
Dockerfile (`gdal-bin` + `python3-gdal`) → **reconstrucción de imagen** (autorizada).

### 1c. Capas como DATA (el patrón que el proyecto ya usa)

Igual que la rúbrica en `puntaje.py` y los formularios en `captura_schema.py`:

```python
CAPAS = {
  "estratificacion": {
     "fuente": "arcgis",
     "url": ".../ordenamientoterritorial/estratificacion/MapServer/1",
     "campos": {"CODIGO_MANZANA": "codigo_manzana", "ESTRATO": "estrato"},
     "destino": "manzana_estrato", "clave": "codigo_manzana",
     "recorte": "kennedy", "refresco": "mensual",
  },
  "placa_domiciliaria": {...},   # capa nueva = UNA entrada, sin código nuevo
  "sector_catastral":  {...},
}
```

Un comando `sync_capa <nombre>` con `--dry-run`, conteos antes/después y
`fecha_fuente`. Cron mensual.

**Fuentes complementarias en el mismo registro:** IDECA / Datos Abiertos Bogotá
(WFS + CKAN) · OpenStreetMap / Overture (cuando no exista lo oficial o para contraste).

### 1d. Lo que se cae solo al llegar PostGIS

- `estrato_en_punto()` → `ST_Contains` en SQL. Se borran el índice en RAM, la caché
  de Redis y su invalidación.
- `estrato_de_barrio()` → `ST_Intersects` (join espacial real, no voto en Python).
- Las 25 sedes fuera del contorno → una query, no un script.

**Costo:** ~1 semana. **Riesgo:** medio (imagen + contenedor nuevo; ver §7).

---

## 5. Fase 2 — PMTiles + MapLibre **(juntas)**

**PMTiles**: un archivo, servido por nginx, el navegador pide **rangos HTTP**. Cero
tile server, cero PostGIS en runtime. Generado por `tippecanoe` desde `innova_gis`,
dentro del mismo pipeline de la Fase 1 → reproducible.

**MapLibre GL**: render en GPU, *style spec* declarativo, traga 100k+ features.
Habilita servir `manzana` (44.519) y hasta `lote` (933.817), hoy impensables.

**Efecto medido esperado:** **2,84 MB → ~50–200 KB** por viewport.

Implica reescribir `mapa.component.ts` (1.093 líneas) y cambiar el modelo mental
(Leaflet dibuja capas; MapLibre aplica un estilo declarativo). Se aprovecha para
partirlo en componentes.

**Costo:** ~2 semanas. **Riesgo:** medio — la ruta vieja se conserva hasta validar.

---

## 6. Fase 3 — Consolidación

Migrar `geo_estrato` a SQL, borrar el índice shapely/Redis, cachear placas, y
sincronizar `sectorcatastral` + `barrioslegalizados` (**+27 y +46 geometrías** para el
mapa — *no* para el Banco, ver §8). Reescribir `mapa_kennedy_eventos.js` si sobrevive.

**Costo:** ~3 días.

---

## 7. Riesgo real y cómo se acota

| Riesgo | Mitigación |
|---|---|
| **Reconstruir la imagen** (hallazgo C) | Ya es reconstruible (`fix/infra-deps-rebuild` en producción) y hay rollback `innovak-innova_k:rollback-20260709`. `docker compose up -d --build` **NO reconstruye**: hay que construir a mano y recrear el contenedor. Procedimiento en `_historico/2026-07-16_estratificacion_ideca_estado.md` §4-ter. |
| Contenedor nuevo (`innova_gis`) | No guarda nada irremplazable: se re-sincroniza de Catastro. Toca `docker-compose.yml` → **doble confirmación** (regla del proyecto). |
| Router de dos BD | `poblacion_kennedy` intacta. Tests de router para que ninguna app escriba en la base equivocada. |
| Reescribir el mapa | Ruta nueva en paralelo; la vieja se borra al validar. |

---

## 8. Lo que este plan **no** arregla — y hay que decirlo

**M22 no se arregla: se reclasifica.** Medido hoy contra los 13 barrios que bloquean
al Banco:

| Capa oficial | Cubre de los 13 | Geometrías nuevas de 250 |
|---|---|---|
| `barrioslegalizados` (138 en Kennedy) | **2 / 13** | +46 |
| `sectorcatastral` (1.230 en Bogotá) | **3 / 13** | +27 |
| `data/barrios_kennedy.geojson` (del repo) | **0 / 13** | +3 |

**Cruzar nuestro catálogo de 325 barrios por nombre contra capas oficiales es un
callejón sin salida:** es un catálogo interno que no corresponde 1:1 con ningún
producto de Catastro. Vale sincronizarlas **para el mapa**, no para el Banco — eso ya
lo resolvió el geocoding (Fase 0).

Tampoco arregla: las **25 sedes con coordenadas fuera del contorno** (anotado, sin
tocar, por instrucción de Alex).

---

## 9. Orden y costo

| Fase | Qué | Costo | Riesgo |
|---|---|---|---|
| **0** ✅ | Geocodificador | — | — |
| **1** | `innova_gis` (PostGIS) + GDAL + capas como data | ~1 sem | medio |
| **2** | PMTiles + MapLibre (juntas) | ~2 sem | medio |
| **3** | Consolidación (SQL, caché, capas nuevas) | ~3 días | bajo |

**Total ~3,5 semanas.** La v1 prometía "1 semana" posponiendo MapLibre — pero esa
semana compraba un Leaflet con teselas que igual íbamos a tirar. Esto cuesta más y
**no hay que volver a hacerlo**.

---

## 10. Decisiones que necesito de Alex

1. **`docker-compose.yml`** se toca para agregar `innova_gis` → la regla del proyecto
   pide **doble confirmación**.
2. **Ventana para recrear el contenedor** `innova_k` con la imagen nueva (GDAL). No es
   un `restart`: es build a mano + recreate, con rollback listo.
3. Confirmar que **`poblacion_kennedy` sigue vetada** para PostGIS (yo asumo que sí, y
   el plan entero se apoya en eso).

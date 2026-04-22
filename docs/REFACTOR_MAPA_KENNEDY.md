# Auditoría Mapa Kennedy — Plan de Refactor

**Fecha**: 2026-04-22
**Rama**: `feat/mapa-kennedy-dashboard`
**Objetivo**: mostrar eventos creados en `/geo/mapa-kennedy/` y reparar
filtros/capas no conectados a BD.

> Este documento es **solo lectura**. No toca código productivo. Sirve
> como plan de trabajo para la próxima sesión.

---

## 1. Estado actual

### 1.1 URL y view

- **URL**: `/geo/mapa-kennedy/` en `apps/georeferenciacion/urls.py:30`.
- **View**: `mapa_kennedy` en `apps/georeferenciacion/views/mapa_kennedy_view.py:164`.
- **Template renderizado**: `geo-mapas/mapa_kennedy_standalone.html`.
- **Contexto pasado**: `upz_list`, `barrio_list`, `ultima_actualizacion`.
- La view **NO consulta eventos ni BD de presupuesto**; solo prepara
  catálogos UPZ/Barrios (con fallback a `choices.py`) para los selects
  del sidebar.

Archivo duplicado encontrado: `apps/georeferenciacion/views/mapa_kennedy.py`
(9 líneas) que NO está enganchado al URL (código muerto — deuda, no
toca hoy).

### 1.2 Templates involucrados

| Archivo | Líneas | Estado |
|---------|-------:|--------|
| `templates/geo-mapas/mapa_kennedy_standalone.html` | 470 | **ACTIVO** — el que la view renderiza |
| `templates/geo-mapas/mapa_kennedy_view.html` | 406 | OBSOLETO (view actual no lo usa) |
| `templates/geo-mapas/mapa_kennedy_standalone copy.html` | 462 | Backup obvio (deuda) |
| `templates/geo-mapas/graficos.html` | 285 | Dashboard de gráficos (ruta separada) |
| `templates/geo-mapas/mapa_embebido.html` | 14 | Stub minimalista |

Template activo carga **JS externo** en
`static/georeferenciacion/js/mapa_kennedy.js` (576 líneas) + bundle
duplicado en `apps/georeferenciacion/static/...` (577 líneas).

### 1.3 Endpoints API consumidos

Declarados en `mapa_kennedy.js:7-17` y llamados por `initKennedy()`:

| Endpoint | Función backend | Estado | Qué devuelve hoy |
|----------|-----------------|:-:|------------------|
| `/geo/api/lugares` | `api_lugares` | ✅ OK | 236 `GeoReferenciacion` como GeoJSON Points (personas caracterizadas, **NO eventos**) |
| `/geo/api/lugares/crear` | `api_crear_lugar` | ✅ OK | crea GeoReferenciacion nueva |
| `/geo/api/estadisticas` | `api_estadisticas` | ✅ OK | count total + actualizados hoy + pendientes |
| `/geo/api/choropleth` | `api_choropleth` | ⚠ parcial | depende de `_as_geojson_list` que devuelve vacío sin GeoDjango |
| `/geo/api/lugares.csv` | `api_lugares_csv` | ✅ OK | export CSV |
| `/geo/api/barrios` | `api_barrios_geojson` | ❌ **ROTO** | devuelve `FeatureCollection` vacío (requiere GeoDjango) |
| `/geo/api/upz` | `api_upz_geojson` | ❌ **ROTO** | idem |
| `/geo/api/localidad/:codigo/` | `api_localidad_geojson` | ❌ **ROTO** | idem |
| `/geo/api/localidad/kennedy` | `api_localidad_kennedy_geojson` | ❌ **ROTO** | idem |
| **`/geo/api/eventos/`** | — | **NO EXISTE** | **falta crear** |

`_as_geojson_list()` en `apis.py:338-361` falla al `import django.contrib.gis`
(GeoDjango no instalado + modelos sin `GeometryField`). Las coordenadas
de UPZ/Barrios/Localidad **viven en archivos GeoJSON**
(`apps/georeferenciacion/data/*.geojson`), no en BD — por eso los
endpoints nuevos `api_kennedy_contorno` / `api_kennedy_barrios`
(creados en feat anterior) funcionan sirviendo esos archivos directo.

### 1.4 Filtros UI

Desde sidebar del template + `buildQuery()` del JS (`mapa_kennedy.js:47-66`):

| Filtro (id HTML) | Query param | Backend lo procesa | Fuente de datos en UI | Estado |
|-------------------|-------------|:-:|-----------------------|--------|
| `f-upz` (multi select) | `?upz=` | ✅ `_base_queryset` | `upz_list` desde view | OK |
| `f-barrio` (multi select) | `?barrio=` | ✅ | `barrio_list` desde view | OK |
| `f-tipo` (multi select) | `?tipo=` | ✅ parcial (campo `tipo_punto_codigo`) | **Hardcoded: deporte/cultura/educacion** | ⚠ opciones no vienen de BD |
| `f-subgrupo` (multi select) | `?subgrupo=` | ✅ (coerce `sub1`→`1`) | **Hardcoded: sub1/sub2/sub3** | 🔴 **FAKE** — placeholders |
| `q` (input text) | `?q=` | ✅ busca en nombre/direccion/etc | libre | OK |
| `layer-*` checkboxes | (solo client-side) | N/A | toggle de capas | variable (ver 1.5) |

### 1.5 Capas Leaflet

El JS `initKennedy()` (líneas 71-525) construye estas capas:

| Capa | Fuente | Interactiva | Estado |
|------|--------|:-:|--------|
| Tiles base | `openstreetmap.bzh/br/` | N/A | ⚠ **dominio exótico** (mismo riesgo que OSM directo: 403 en producción pública) |
| `cluster` (L.markerClusterGroup) | `/geo/api/lugares` (236 puntos de personas) | sí | OK, pero confunde: esto **no son eventos** |
| `heatLayer` | mismos datos | no | OK (toggle `#heatmap-toggle`) |
| `upzLayer` (L.geoJSON) | `/geo/api/upz` | sí | ❌ vacío (endpoint roto) |
| `barriosLayer` | `/geo/api/barrios` | sí | ❌ vacío |
| `localidadLayer` | `/geo/api/localidad/kennedy` | sí | ❌ vacío |
| `drawnItems` (leaflet-draw) | input usuario | sí | OK (dibujar polígonos) |
| `tempMarker` | click sobre mapa | sí | OK (crear lugar nuevo) |

Las capas rotas se agregan con `addLayer(layerObj)` pero el GeoJSON está
vacío → no se ve nada al activar el toggle (fallo silencioso).

### 1.6 Datos actuales en BD relacionados al mapa

```
Total eventos:                35
  Con lugar_incidencia:        0   ← NINGUNO tiene ubicación registrada
  Con indicador:               0   ← NINGUNO tiene KPI asignado
  Con ambos:                   0

LugarIncidencia rows:          0   ← tabla vacía (refactor recién desplegado)
GeoReferenciacion rows:      236   ← caracterizaciones de personas (no eventos)

tipo_evento rows:              4   (ENTREGA, CAPACITACION, CURSO, INFO_TERRENO)
presu_indicador_meta_proyecto: 0   (KPIs no creados todavía)
actividad_indicador:           0
presu_avance_ind_periodo:      0

Lugar:                       224   (223 del catálogo + 1 genérico "Ubicación de eventos")
UPZ:                         ?    (catálogo, no visto en este conteo)
Barrio:                      ?
```

**Lectura clave**: los 35 eventos existentes son **pre-refactor** (tenían
`disciplina_id`/`grupo_id`/`curso_id`, hoy borrados). Los eventos
*nuevos* creados con el form refactorizado **sí traerán**
`lugar_incidencia_id`, pero **todavía nadie ha usado el form nuevo**.
Hasta que alguien cree el primer evento con ubicación, el mapa de
eventos estará vacío por diseño.

---

## 2. Hallazgos por severidad

### 🔴 BLOQUEADORES

#### B1 — No existe endpoint de eventos georreferenciados

No hay `/geo/api/eventos/` ni `/geo/api/eventos-geojson/`. El mapa no
tiene forma de pedirle al backend "dame los eventos con lat/lon".
**Requerido crear uno desde cero** antes de poder pintar nada.

#### B2 — La capa que carga hoy (`/geo/api/lugares`) devuelve caracterizaciones de PERSONAS, no eventos

El cluster actual con 236 puntos es semánticamente distinto. Si solo
agregamos eventos, debemos decidir:

- (a) Reemplazar el cluster actual por eventos (pierde visualización de
  caracterizaciones).
- (b) Capa paralela: cluster de eventos + cluster de personas, con
  toggle entre ambos.
- (c) Endpoint unificado con `?tipo=evento|persona`.

Mi recomendación: **(b) capa paralela**. Mantiene comportamiento
actual + agrega capacidad nueva sin romper lo que funciona.

#### B3 — Tiles base OSM "bzh" es frágil

`openstreetmap.bzh/br/` es un mirror no oficial. Vimos en el refactor de
`crear_evento` que `tile.openstreetmap.org` bloquea con 403 desde ngrok
público. El mirror bzh probablemente tiene el mismo riesgo (o es más
lento). En `crear_evento.html` migramos a CartoDB Voyager con éxito —
aplicar lo mismo aquí.

### 🟡 FUNCIONALIDAD FALTANTE

#### F1 — Filtros hardcoded

- `f-tipo` tiene opciones literales `deporte/cultura/educacion`. No
  vienen de `TipoEvento.objects.all()` ni de ninguna tabla real. Al
  filtrar eventos por tipo, estas opciones son irrelevantes.
- `f-subgrupo` tiene placeholders `sub1/sub2/sub3`. El backend los
  convierte a `[1, 2, 3]` y filtra — pero los subgrupos reales de BD no
  son esos ids obligatoriamente. **Es un filtro inservible**.

Ambos deberían recibir sus opciones desde el context de la view
(`tipos_evento`, `subgrupos`) como hacemos en `crear_evento.html`.

#### F2 — Sidebar con 3 stats cards hardcoded

`"Total de lugares: 236"`, `"Actualizados hoy: 12"`, `"Pendientes: 8"`
escritos literalmente en HTML. El JS (`setKPI`) los sobreescribe con
llamada a `/geo/api/estadisticas`, pero el valor inicial visible antes
de que termine el fetch es mentira. Cosmético: reemplazar por `—` o
spinner.

#### F3 — Filtros de fecha ausentes

No hay `f-desde` / `f-hasta`. Para eventos esto es crítico: queremos
ver "eventos de esta semana", "último mes", etc. Hay que agregarlos.

#### F4 — Filtro de indicador ausente

Una vez que eventos tengan `indicador_id`, debería poder filtrarse por
qué KPI aportan. No existe este selector.

### 🟢 QUICK WINS (<10 min)

- **Q1**: cambiar tiles a CartoDB Voyager (copy/paste del fix que ya
  hicimos en `crear_evento.html`).
- **Q2**: agregar `/geo/api/kennedy/contorno/` y
  `/geo/api/kennedy/barrios/` (creados en feat anterior) a la lista de
  endpoints de `mapa_kennedy.js` **como fallback** cuando los otros
  devuelvan vacío. Así se ven los polígonos de Kennedy sin arreglar
  GeoDjango. O reemplazar directamente los rotos.
- **Q3**: remover valores hardcoded en stats cards del sidebar.

---

## 3. Lo que falta para mostrar eventos

Checklist concreto:

- [ ] **Endpoint `/geo/api/eventos/`** que devuelve `FeatureCollection`
      con todos los eventos que tienen `lugar_incidencia_id NOT NULL`.
      Properties sugeridas: `id`, `nombre`, `descripcion`,
      `fecha_inicio`, `tipo_evento_codigo`, `tipo_evento_nombre`,
      `dependencia_nombre`, `subgrupo_nombre`, `indicador_nombre`,
      `magnitud_aportada`. Filtros por query string:
      `?dependencia_id=`, `?subgrupo_id=`, `?tipo_evento=`,
      `?indicador_id=`, `?desde=YYYY-MM-DD`, `?hasta=YYYY-MM-DD`.
- [ ] **URL registrada** en `apps/georeferenciacion/urls.py`.
- [ ] **En el JS `mapa_kennedy.js`**: agregar constante
      `eventos: \`${APP_PREFIX}/api/eventos\`` al objeto `API`.
- [ ] **Nueva capa** `eventosCluster` en el JS, con marcadores
      coloreados por `tipo_evento` y popup con datos del evento.
- [ ] **Toggle en sidebar** `#layer-eventos` para mostrar/ocultar.
- [ ] **Filtros UI** de la cascada (dependencia → subgrupo →
      funcionario) que ya existen para `crear_evento` — deben poblar
      selects del mapa. Subgrupos dinámicos (no `sub1/sub2/sub3`).
- [ ] **Date range**: `f-desde` / `f-hasta` con `<input type="date">`.
- [ ] **View del mapa** actualizada: pasar `dependencias_list` y
      `tipos_evento_list` al context además de UPZ/Barrios.
- [ ] **Link "Editar evento"** en el popup, llevando a
      `/evento/<id>/editar/` (ya existe esa URL).

---

## 4. Plan de implementación para mañana (fases atómicas)

### Fase A — Endpoint de eventos como GeoJSON (estimado: 45 min)

Archivos tocados:
- `apps/georeferenciacion/views/apis.py` (nueva función
  `api_eventos_geojson`).
- `apps/georeferenciacion/urls.py` (1 path nuevo).

La view recorre `Evento.objects.filter(lugar_incidencia_id__isnull=False)`,
`select_related` hacia `lugar_incidencia__geo_referenciacion`,
`tipo_evento`, `dependencia`, `subgrupo`, `indicador`. Construye
features Point con coordinates desde `geo_referenciacion.longitud/latitud`
(ya en WGS84, ok) y properties con los nombres esperados.

Filtros query-string opcionales. Retorna 200 con `FeatureCollection`.

Validar con `Client().get('/geo/api/eventos/')` y con el caso edge
"0 eventos con ubicación" → devuelve features=[] sin error.

### Fase B — Layer de eventos en el mapa (estimado: 1h)

Archivos tocados:
- `templates/geo-mapas/mapa_kennedy_standalone.html` (agregar toggle
  `#layer-eventos`, agregar entry a la legenda).
- `static/georeferenciacion/js/mapa_kennedy.js` y su duplicado en
  `apps/georeferenciacion/static/...` (sincronizar) — nueva función
  `cargarEventos()` con fetch + markerClusterGroup + popup HTML +
  toggle listener.

Colorear marcadores por `tipo_evento_codigo` (ENTREGA=verde,
CAPACITACION=azul, CURSO=amarillo, INFO_TERRENO=rojo). Popup con:
nombre, fecha, tipo, responsable, aporta a indicador "X" con magnitud
Y, link a editar.

### Fase C — Quick wins aplicados (estimado: 20 min)

- **C1**: migrar tiles a CartoDB Voyager (copy del fix ya hecho).
- **C2**: apuntar las capas de UPZ/Barrios/Localidad a los endpoints
  nuevos `/geo/api/kennedy/contorno/` y `/geo/api/kennedy/barrios/`,
  o crear además `/geo/api/kennedy/upz/` leyendo `Upz.geojson` y
  filtrando por localidad Kennedy.
- **C3**: remover valores hardcoded de `#total-lugares`,
  `#actualizados-hoy`, `#pendientes-verificacion` (poner `—` inicial).

### Fase D — Arreglar filtros hardcoded (estimado: 1h)

- **D1**: cambiar `f-tipo` para recibir opciones desde el context
  (`tipos_evento_list`).
- **D2**: cambiar `f-subgrupo` para poblarse vía cascada dependencia
  (fetch al endpoint `api/subgrupos/?area_id=X` que ya existe).
- **D3**: agregar `f-dependencia` como padre de `f-subgrupo`.
- **D4**: agregar `f-desde` / `f-hasta` (date inputs).
- **D5**: agregar `f-indicador` (opcional, si queremos cruzar con KPI).

### Fase E — Validación integral + commit + push

- `docker compose restart innova_k`.
- Probar con usuario real creando un evento nuevo en `/evento/crear/`
  y verificando que aparezca en el mapa tras recargar.
- Smoke test de endpoints.
- Commit multi-fase o commit único, según dinámica de la sesión.
- Push a `feat/mapa-kennedy-dashboard`.

**Estimación total realista**: **4-5 horas** si todo fluye. Las fases
A/B son las grandes, C es rápido, D puede expandirse si el usuario
quiere más filtros.

---

## 5. Decisiones pendientes del usuario (preguntas para mañana)

1. **¿Mostrar todos los eventos o solo últimos N meses?**
   - Sugerencia: default últimos 12 meses + filtro date range para
     ajustar.

2. **¿Click en marcador → popup de solo lectura, o con link a editar/ver?**
   - Sugerencia: popup con datos + link "✏ Editar" visible solo para
     Admin/Lider (mismo criterio que acceso a `crear_evento`).

3. **¿Heatmap además de markers?**
   - Útil si hay muchos eventos concentrados. No urgente.

4. **Capas de contexto (UPZ/Barrios/Localidad) — ¿usar los endpoints
   nuevos que arreglé ayer o reescribir los existentes (api_barrios_geojson,
   api_upz_geojson) para servir los archivos reproyectados?**
   - Opción limpia: reescribir los existentes para que lean los archivos
     que ya están en WGS84. Deprecate los endpoints nuevos (ya usados
     desde `crear_evento`). Requiere coordinar. Si no quieres
     dualidad, Fase D podría incluir este refactor.

5. **Filtros PRIORITARIOS vs nice-to-have**:
   - Date range: prioritario.
   - Tipo de evento: prioritario.
   - Dependencia + subgrupo: importante.
   - Indicador/KPI: nice-to-have (si hay pocos KPIs al inicio, no
     ayuda filtrar).

6. **¿Mantener capa de "caracterizaciones" (personas) o reemplazarla
   por eventos?** Recomendé capa paralela en B2 — confirma.

7. **Deuda técnica: ¿queremos incluir M18 nuevo en
   `DEUDA_TECNICA.md`**? Candidatos:
   - Endpoints `api_*_geojson` de UPZ/Barrios/Localidad dependen de
     GeoDjango y devuelven vacío (ya mencionado como M14 implícito en
     hallazgo de la sesión pasada, nunca formalizado).
   - JS duplicado (`static/georeferenciacion/js/mapa_kennedy.js` vs
     `apps/georeferenciacion/static/.../mapa_kennedy.js`).
   - Templates "copy.html" de backup en git.

---

## 6. Riesgos identificados

- **R1 — El JS del mapa (577 líneas) es complejo**: inyectar cambios
  en el orden equivocado (p.ej. `initKennedy` se llama antes de que el
  DOM esté listo) puede romper toda la página. Plan: solo *agregar*
  funcionalidad nueva en funciones propias, no modificar estructura
  existente.

- **R2 — Hay dos copias del JS** (`static/...` y
  `apps/georeferenciacion/static/...`). Editar solo una puede pasar
  desapercibido si el servidor sirve la otra. Solución: detectar cuál
  usa el `{% static %}` actualmente (probablemente la de `apps/`
  sobrescribe via `collectstatic`) y editar ambas o solo la fuente.

- **R3 — Tiles "bzh" podrían estar funcionando hoy**, hay que
  verificarlo antes de cambiar (aunque el plan es cambiarlo por
  seguridad).

- **R4 — El popup del evento** no debe leakar datos sensibles
  (documento de funcionario, etc). Revisar qué properties se exponen.

- **R5 — Performance**: si mañana hay 1000+ eventos, cargar todos en
  un fetch puede ser lento. Paginar si el volumen crece. Por ahora
  con 0 eventos el volumen no es problema.

- **R6 — Filtro cascada**: si acoplamos `f-dependencia` →
  `f-subgrupo` → `f-funcionario` debemos asegurar que al cambiar
  `f-dependencia` se limpie el `f-subgrupo` o hacer flow similar al
  de `crear_evento.html`.

---

## 7. Fuera de scope para este PR

- Reescritura completa de `api_lugares` (sigue sirviendo
  caracterizaciones, no es urgente separar).
- Arreglar endpoints GeoDjango (scope muy grande; instalar GeoDjango +
  añadir `GeometryField` a modelos + migración).
- Dashboard de cumplimiento de KPIs (gráficos). Ruta `/geo/graficos/`
  existe pero no es parte de este trabajo.
- Mapa público no autenticado (el actual requiere login — se queda
  así).
- Edición de eventos desde el mapa (link a `/evento/<id>/editar/` sí,
  pero refactor del editor es aparte).
- Eliminar la carpeta duplicada `apps/georeferenciacion/static/` y el
  template "copy.html" (limpieza general, aparte).

---

## 8. Referencias internas

- Refactor anterior que creó los tipos, modelos, cascada y ubicación
  híbrida: commits `728c890..e9f7eeb` en `feat/kpis-avances-indicadores`
  (ya mergeado a `desarrollo`, `Pruebas`, `produccion`).
- Helper `crear_con_fallback_id` y `get_lugar_generico` en
  `apps/georeferenciacion/utils.py` (reutilizable si se crea un lugar
  desde el mapa).
- Endpoints estáticos ya disponibles:
  - `/geo/api/kennedy/contorno/` — `localidad_kennedy.geojson` WGS84.
  - `/geo/api/kennedy/barrios/` — `barrios_kennedy.geojson` WGS84
    (111 features).
- Patrón de tiles funcional en `templates/eventos/crear_evento.html`
  (CartoDB Voyager).

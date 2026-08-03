# Plan — mapa de Kennedy: corrección, UX y accesibilidad

Fecha: 2026-08-03 · Página objetivo: `/app/mapa` (pública, sin login)
Archivos núcleo: `frontend/src/app/features/mapa/mapa.component.ts` (1691 líneas,
template inline), `.scss` (630), `core/geo/geo.service.ts`,
`apps/georeferenciacion/views/apis.py` y `api/views.py`.

---

## Contexto

El mapa acaba de salir a producción con las capas de barrios, UPZ y escuelas
(cascada 2026-08-03). Al revisarlo, Alex reporta dos cosas: que un punto de
Seguridad *"siempre aparece"* aunque no se seleccione ese subgrupo, y que
*"no tenemos UX de mapas, falta harto"*.

Este plan cubre las tres cosas: el defecto de datos que hace inútil el filtro,
la UX, y la accesibilidad — que para una página pública de una entidad de
gobierno no es cosmética.

---

## 1. Hallazgo que reordena las prioridades

**Los 13 eventos del mapa están en la MISMA coordenada.** Verificado contra
producción:

```
coordenadas distintas: 1
  (-74.1573, 4.6313) -> 13 eventos     ← Transversal 78K #41A-04 = la Alcaldía
```

Reparto: 8 de Seguridad, 4 de Cultura, 1 de Deporte.

**El filtro NO está roto.** El backend responde correcto: `?subgrupo_id=38`
devuelve exactamente los 8 de Seguridad (`api/views.py:138-141`, con
`getlist` para multiselect). Los chips y las pestañas sí recargan del servidor
(`mapa.component.ts:1541,1550,1570`).

Lo que pasa es que **hay 13 marcadores apilados en el mismo píxel**. Al filtrar
a Cultura siguen quedando 4 ahí; el punto nunca desaparece y el popup que se
abre es el del marcador que quedó encima. De ahí la lectura razonable de que
"siempre aparece" y "pertenece a Seguridad".

**Causa raíz** — está documentada en CLAUDE.md (sesión 2026-06-11):
`get_lugar_incidencia_default()` en `EventoCRUDView.post` pone **en la Alcaldía
todo evento creado sin coordenadas**. Ningún evento tiene ubicación real.

Esto conecta con una regla ya establecida del proyecto: las direcciones no se
capturan como texto libre; se autocompletan contra Catastro y se guarda lat/lon.
Los eventos actuales nacieron sin ese paso.

### Qué hacer, en orden

1. **Dejar de mentir visualmente (rápido).** Un marcador que está en la Alcaldía
   por defecto no debe pintarse como si fuera su ubicación real. Dos piezas:
   - Marcar en el backend el evento cuya ubicación es la de respaldo
     (`ubicacion_aproximada: true` en las propiedades del GeoJSON).
   - En el mapa: agrupar los apilados (spiderfy/cluster) o desplazarlos en
     abanico, y rotular el popup con *"Ubicación no registrada — se muestra en
     la sede de la Alcaldía"*.
2. **Contar lo que no se puede pintar.** Igual que ya se hace con las escuelas
   sin ubicación (`mapa.component.ts:352-369`), un bloque *"N actividades sin
   ubicación registrada"* con su lista. Un hueco visible es mejor que un dato
   falso — es el mismo criterio con el que se rechazó el emparejamiento difuso
   de barrios.
3. **Capturar la ubicación de verdad.** Reusar `app-direccion-picker`
   (`shared/direccion/direccion-picker.component.ts:54`), que ya hace
   autocompletado Catastro + pin en el mapa, en el formulario de creación de
   actividad. Es la solución de fondo; las dos anteriores son mitigación.

> Decisión pendiente de Alex: si los 13 eventos actuales se
> re-georreferencian a mano (son pocos) o se dejan marcados como aproximados.

---

## 2. Segundo defecto real: el buscador no filtra el mapa

`renderEventos()` (`mapa.component.ts:1487`) itera `this.eventos().features`,
mientras la tabla y los KPIs usan `eventosFiltrados()`
(`mapa.component.ts:500-509`). Escribir en "Buscar" cambia la tabla y el
contador, **pero no los marcadores**.

Fix: que `renderEventos()` lea `eventosFiltrados()`. Una línea, pero hoy la
página se contradice a sí misma en pantalla.

---

## 3. UX

Ordenado por daño real, no por esfuerzo.

| # | Problema | Dónde |
|---|---|---|
| U1 | **4 capas exigen sesión en una página pública.** Un visitante marca "Malla vial", "Parques (obras)", "Festivales" o "Banco" y recibe 401: el check queda encendido y no pasa nada, sin mensaje | `api/views.py:451,497`, `festivales/api/views.py:238`, `apis.py:957` |
| U2 | **7 capas se tragan el error** (`error: () => {}`) y 2 no tienen handler | `mapa.component.ts:697,752,983,1015,1053,1104,1159` · sin handler `:1329,1372` |
| U3 | **El banner de error nunca se limpia** — no hay un solo `errorMsg.set('')` en el archivo. Una vez sale, queda hasta recargar | `:428` |
| U4 | **Solo 1 de 11 capas tiene indicador de carga.** Las otras 10 se marcan y el mapa no cambia hasta que llegue la respuesta | `:177-179` |
| U5 | **Mensajes de sesión en una página sin login**: "Verifica tu sesión", "la sesión expiró, vuelve a entrar" | `:665,1455` |
| U6 | **Font Awesome no está cargado en el SPA** → todos los `<i class="fa …">` renderizan vacíos, incluidos los chevrons que son la única señal de que dos secciones se pliegan. El proyecto ya migró a `lucide-angular` | `angular.json:41-45` · iconos en `:69,231,269,357` |
| U7 | **En móvil el panel de filtros va ANTES del mapa** y ocupa casi toda la altura: se abre `/app/mapa` y no se ve el mapa | `.scss:66-77` |
| U8 | **La tabla desborda horizontal** en móvil (5 columnas, sin `overflow-x`). Ya existe `.ui-table-responsive` que lo resuelve | `.scss:392-397` · `_table.scss:6-12` |
| U9 | **Códigos crudos en pantalla**: `BANCO_INICIATIVAS`, `CULTURA_ORG`, `UPZ 48`, `Manzana <código catastral>`, `CIV`, `KPI`, "geometría"/"declarado" | `:1676-1679,854-859,1441-1443,1116,1523,898-899` |
| U10 | **Fechas en ISO crudo** (`2026-07-15`) en tabla y popups, habiendo ya un formateador con locale es-CO | `:329,1518` · `format.util.ts` |
| U11 | **Hover de barrio/UPZ sin equivalente táctil**: en móvil el nombre del barrio es inalcanzable. La barra de estado dice literalmente *"Pasa el cursor sobre el mapa"* | `:1344-1353,1385-1395,1255` |
| U12 | **Breadcrumb que se calcula y nunca se pinta** (la ruta va sin `LayoutComponent`) | `:535-540` |
| U13 | **Sin estado vacío en el mapa**: 0 features = mapa en blanco sin explicación | — |

---

## 4. Accesibilidad

La página es pública y de una alcaldía. `docs/propuestas/ux_pendiente.md:12-39`
ya la tenía en el backlog por nombre, y `.claude/agents/estilos.md:73-78` fija el
estándar del proyecto: *"A11y es no-negociable"*.

| # | Problema | Dónde |
|---|---|---|
| A1 | **`<html lang="en">`** en una app 100 % en español. Un lector de pantalla la lee con fonética inglesa. Django sí tiene `lang="es"`, pero ese template no sirve la SPA | `frontend/src/index.html:2` |
| A2 | **Sin `<main>` ni skip-link**: `/mapa` va fuera de `LayoutComponent`, que es donde viven ambos. Hay que ponerlos en el componente | `app.routes.ts:196-212` · modelo en `layout.component.ts:37,42` |
| A3 | **3 elementos interactivos solo-click, no focusables**: los dos headers colapsables y la fila de tabla que centra el mapa. Sin `role`, sin `tabindex`, sin `aria-expanded` | `:268,327,354` |
| A4 | **Cero handlers de teclado** en todo el archivo | — |
| A5 | **Los polígonos y los marcadores de evento no son focusables** (son `<path>` SVG) → sus popups, que son el contenido principal, son inalcanzables por teclado | `:966,1000,1331,1374,1433,1499` |
| A6 | **`role="tablist"` a medias**: los hijos no tienen `role="tab"` ni `aria-selected`, y no hay `tabpanel`. Declarado, no implementado | `:240-253` |
| A7 | **El mapa no tiene alternativa textual** — `<div>` pelado, sin `role` ni resumen | `:257` |
| A8 | **Los 3 `<canvas>` de Chart.js están vacíos** para lectores de pantalla | `:296,300,304` |
| A9 | **Carga y error sin live region**: `.mapa-loading` y `.mapa-error` no se anuncian | `:258-263` |
| A10 | **`<th>` sin `scope`** en las dos tablas | `:318-322,374-378` |
| A11 | **Ningún control llega a 44 px táctiles**: chips ~24, tabs ~22, checkboxes ~20. El token `$touch-target-min: 44px` existe y no se usa | `.scss:134,353,167` · `_tokens.scss:139` |
| A12 | **Codificación solo por color** en estratos, avance de obras y tipo de evento — sin forma ni patrón que los distinga | `:1435,1093,1498` |
| A13 | **`.mapa-pill` con texto blanco sobre color de BD sin validar contraste**: cualquier color claro que cargue un administrador deja el texto ilegible | `.scss:429` · `:331` |
| A14 | **Controles de Leaflet en inglés**: "Zoom in", "Zoom out", "Close popup" | `:629-633` |
| A15 | **Sin `prefers-reduced-motion` propio** en el SCSS del mapa | — |

### Qué reutilizar (no inventar)

- **Modelo de a11y del proyecto**: `features/publico/entregas-publico.component.ts`
  (48 `aria-`, landmarks, live regions, `role="alert"`, acordeón con
  `aria-expanded`). Es el patrón a copiar.
- **Tokens**: `frontend/src/styles/_tokens.scss` — incluye `$focus-ring` y
  `$touch-target-min`. La regla del proyecto es consumir tokens, nunca hex
  sueltos (`_components.scss:109-114`); hoy todo el color cartográfico del mapa
  está hardcodeado y duplicado entre TS y SCSS.
- **Componentes ya hechos**: `.ui-table-responsive`, `.ui-empty-state`,
  `.ui-info-bar`, `.ui-skip-link`, `.ui-sr-only`, `ToastService`.
- **Iconos**: `lucide-angular`, ya registrado global.

---

## 5. Fases propuestas

**Fase 0 — la mentira visual (medio día).** §1.1 + §1.2 + §2. Es lo que Alex
reportó y lo que hace que el mapa no se pueda usar para decidir nada.

**Fase 1 — que el mapa no engañe cuando falla (1 día).** U1–U5: capas que
exigen sesión avisan en vez de callar, errores que se limpian, indicador de
carga por capa, y quitar el copy de sesión de una página pública.

**Fase 2 — accesibilidad estructural (1–1½ días).** A1, A2, A3, A6, A9, A10 +
teclado para lo que hoy es solo-click. Todo con el patrón de
`entregas-publico`. Es la fase que más cambia para un usuario con lector de
pantalla y la que menos riesgo tiene de romper nada.

**Fase 3 — móvil y toque (1 día).** U7, U8, U11, A11. Hoy el mapa en móvil es
prácticamente inservible: el panel tapa el mapa y el hover no existe.

**Fase 4 — pulido (1 día).** U6, U9, U10, U13, A12–A15. Iconos que se vean,
lenguaje sin códigos internos, fechas en español, contraste validado.

**Verificación de cada fase:** `docker exec innova_k python scripts/run_smoke_tests.py`
(996 hoy) + `npx ng build --base-href=/app/` + prueba manual en
`https://intranet-public-alk.ngrok.app/app/mapa` sin sesión y desde móvil.
No hay tests de frontend que cubran el mapa (0 `.spec.ts`) ni herramienta de
a11y instalada — vale la pena evaluar `axe-core` como parte de la Fase 2.

---

## 6. Pendientes anteriores, aún abiertos

Del `ESTADO.md` de `mapa-escuelas`, cascadeado a producción con el gate
levantado a mano:

- **§2.5** Revisión de los tres CSV para el área — sin hacer.
- **§2.6** README del módulo `georeferenciacion` — es un stub con un TODO.

Y de la sesión de hoy:

- Los 2 commits de `feat/presupuesto-conciliacion-oficial` (script del evento
  de Paz + diagnóstico del censo) siguen sin cascadear. El script no es
  ejecutable en el servidor mientras no esté en la rama desplegada.
- Contenedor `innovak_home_preview` en el 8099, sin uso.

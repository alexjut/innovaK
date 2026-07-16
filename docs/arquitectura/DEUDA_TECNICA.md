# Deuda técnica activa — innovaK

**Última actualización:** 2026-07-16 (sesión de orden documental: se consolidó
aquí la deuda que estaba suelta en 6 documentos + 8 hallazgos nuevos de la
sesión de estratificación/direcciones).

**Fuente única de deuda.** Si un defecto conocido no está en este archivo, no
existe como deuda. No abrir listas de pendientes en propuestas, handoffs ni
manuales: van aquí, con `archivo:línea`.

> El histórico de ítems cerrados vive en
> [`_historico/cronograma_deuda.md`](../_historico/cronograma_deuda.md).

---

## 🔴 Crítico — exposición legal (abrir antes que nada)

| ID | Resumen |
|----|---------|
| **P1** | **Datos personales reales en repo público.** `github.com/alexjut/innovaK` es **público** y hay cédulas de ciudadanía + nombres completos + nº de contrato CPS versionados: `docs/operacion/usuarios_georef.md:16-17` (2 personas) y `docs/usuarios_solicitados.md:18,26-45` (1 persona, repetida 3×, incluida la transcripción de un oficio). Tratamiento sin autorización expresa en canal público → **Ley 1581/2012 (habeas data)**. Están **tracked** y aparecen en **5 commits**: borrarlos del HEAD **no basta**, hay que purgar el historial (`git filter-repo`) y reescribir el remoto. Nombres sin cédula también en `docs/manuales_uso/README.md:15` y `docs/manuales_uso/cultura.md:4`. **Arreglo:** borrar los 2 archivos, mover el roster a `credenciales_georef.local.txt` (ya gitignored, `.gitignore:139`), y en `manuales_uso/*` sustituir nombre por rol. **Agravante:** `docs/infra/despliegue_kubernetes.md:14` afirma que el repo es *privado* — el dossier razonó su seguridad sobre una premisa falsa. **Nota:** la regla `docs/README.md:73-74` (*"si un doc deja de ser vigente se mueve a `_historico/`. **No se borra**"*) empuja a archivar cédulas en vez de eliminarlas → necesita excepción explícita para datos personales. |
| **P2** | **3 tokens HMAC vivos publicados** en `docs/manuales_modulos/cultura.md:41-43`. Son HMAC-SHA256 derivados de `SECRET_KEY`, **estables por evento y sin expiración** (`apps/login/services/qr_token.py`). Hoy inofensivos porque el modo es suave (`QR_TOKEN_ENFORCE=False`, `core/settings.py:337`), pero **quedan quemados antes de que la fase 2 los active**, y rotarlos exige rotar `SECRET_KEY`. |

---

## 🔴 Geo / eventos — hallazgos de la sesión 2026-07-16

Todos verificados contra el código de la rama `feat/direcciones-que-existen`.

| ID | Sev | Resumen | Evidencia |
|----|-----|---------|-----------|
| **G1** | ALTA | **El `PATCH` de evento crea una cadena geo nueva en CADA edición → georreferencias huérfanas.** El backend crea `Lugar→GeoReferenciacion→LugarIncidencia` cuando llegan lat/lng y no llega `lugar_incidencia_id`; el form siempre manda lat/lng y **nunca** manda `lugar_incidencia_id`. Editar 5 veces un evento deja 4 cadenas huérfanas. Nadie las borra. | `apps/login/api/views.py:1486-1495` + `frontend/src/app/features/eventos/evento-form.component.ts:849-851` (manda lat/lng siempre) |
| **G2** | ALTA | **La ubicación del evento no es obligatoria en NINGÚN lado.** El backend no la exige y se justifica diciendo *"el form la pide"*; el form **no la pide** (`camposRequeridos()` no incluye ubicación). Resultado: los eventos sin ubicación se anclan mudos en la Alcaldía vía `get_lugar_incidencia_default()` y nadie se entera. O se exige en ambos lados, o se asume el default y se borra el comentario. | `apps/login/api/views.py:1350-1352` (comentario) + `evento-form.component.ts:811-820` (`camposRequeridos()`) |
| **G3** | MEDIA | **La bbox de Kennedy valida en la ruta muerta y falta en la viva.** El guard de bbox está en `api_crear_lugar` — que **nadie llama** — y **no está** en `_crear_lugar_incidencia`, que es la ruta que usa el form de eventos. Hoy se puede anclar un evento en cualquier coordenada del planeta. | guard en `apps/georeferenciacion/views/apis.py:488`; ausente en `apps/login/api/views.py:1313-1335` |
| **G4** | MEDIA | **Callejón sin salida al elegir dirección en el detalle por red del Banco.** `direccion-picker` **no acota el largo** (0 `maxlength` en `frontend/src/app/shared/direccion/direccion-picker.component.ts`) y escribe la dirección normalizada de Catastro en `InscripcionBancoRedDetalle.direccion` = `CharField(max_length=50)`. El backend **sí valida** y rechaza con *"El campo 'direccion' del detalle por red excede 50 caracteres"*. **No es un `DataError`** (esa lectura era errada): es peor de usar — el usuario **no puede corregirlo**, porque el picker solo acepta direcciones elegidas de la lista, no editadas. **Arreglo:** ampliar la columna a 120 (como `InscripcionBancoEscenarioDetalle`, que ya es 120) o truncar/validar en el picker. | modelo `apps/banco_iniciativas/models/inscripcion.py:356`; validación `apps/banco_iniciativas/forms/inscripcion.py:613-618`; picker en `banco-publico.component.ts:823-826` |
| **G5** | BAJA | **`api_crear_lugar` es código muerto y además incompleto.** Crea `Lugar`+`GeoReferenciacion` pero **nunca** un `LugarIncidencia`, y no lo llama nadie desde el frontend (0 hits de `lugares/crear` en `frontend/src`; solo lo tocan los tests). O se conecta, o se borra junto con su URL. Hoy su única función real es **retener la validación de bbox que le falta a la ruta viva** (ver G3). | `apps/georeferenciacion/views/apis.py:453-541`, URL en `apps/georeferenciacion/urls.py:52`, test en `apps/georeferenciacion/tests/test_smoke.py:10` |
| **G6** | BAJA | **Comentario que miente en el form de eventos.** Dice *"backend Angular CRUD aún no crea LugarIncidencia, sólo persiste lugar_incidencia_id si llega"*. Sí la crea, desde `_crear_lugar_incidencia`. El comentario es la causa probable de G1: describe un backend que no existe. | `frontend/src/app/features/eventos/evento-form.component.ts:846-848` vs `apps/login/api/views.py:1313` |
| **G7** | ALTA | **Catastro no sirve para consultas interactivas — medido 2026-07-16.** La misma consulta 6 veces → **1 acierto en 6,6 s** y **5 respuestas vacías SIN error en 1,8 s** (falla en silencio: devuelve vacío, no excepción). Un `COUNT` con bbox se cae por **timeout a los 60 s**. Cualquier feature que dependa de consultarlo **en vivo** está condenada: hay que sincronizar a tabla propia y consultar local (es exactamente lo que hacen `sync_capa` y `geocodificacion_cache`). **Escribir esto antes de que alguien proponga "consultamos Catastro al vuelo".** | medición de sesión; mitigación en `apps/georeferenciacion/services/capas.py` + tabla `geocodificacion_cache` (DDL 011 aplicado) |
| **G8** | MEDIA | **M22 sigue viva y ya no tiene salida por catálogo.** 79/111 barrios sin `geometry`. **Cruzar nuestro catálogo de 325 barrios por nombre contra las capas oficiales es un callejón sin salida** (medido: `barrios_legalizados` **2/13**, `sector_catastral` **3/13**, `data/barrios_kennedy.geojson` **0/13**): son productos distintos, no hay correspondencia 1:1. El geocodificador **esquiva** la deuda (resuelve por dirección→placa→manzana, sin barrio), pero la deuda **sigue** para el mapa. **No volver a intentar cargar el geojson del repo.** Requiere la capa oficial de Catastro que corresponda al catálogo de 325 → **insumo externo**, mismo bucket que la planilla DANE de M-EDU. | `docs/propuestas/plan_evolucion_mapa.md` §8; capas en `apps/georeferenciacion/services/capas.py` |

---

## 🟡 Banco de Iniciativas

| ID | Sev | Resumen | Evidencia |
|----|-----|---------|-----------|
| **B1** | MEDIA | **`auto_detalle` está doble-codificado**: es un `jsonb` que contiene un *string* JSON, no un array. `auto_detalle->'C2_territorialidad'` devuelve NULL **siempre** → cualquier query analítica sobre ese campo falla en silencio. | `apps/banco_iniciativas/services/puntaje.py` |
| **B2** | BAJA | `RUBRICA_AUTO["bloque_auto_max"] = 30` mientras `calcular_caracterizacion()` devuelve `"max": 65`. El snapshot de `banco_rubrica` **guarda el 30** → la rúbrica archivada para auditoría declara un techo falso. | `apps/banco_iniciativas/services/puntaje.py` |
| **B3** | BAJA | `total` se calcula en **dos** lugares (`guardar_caracterizacion()` y `_recalcular_total()`). Cualquier criterio nuevo hay que tocarlo en ambos o los totales divergen. | `apps/banco_iniciativas/services/puntaje.py` |
| **B4** | BAJA | `banco_rubrica` no tiene columna `id`. | tabla BD |
| **B5** | BAJA | `BancoEvaluacionInscripcion` no tiene `bono_estrato` → si se aprueba el bono por estrato hace falta DDL aditivo (nullable) + backup. | `apps/banco_iniciativas/models/` |
| **B6** | BAJA | **Soporte legal sigue opcional** (`required=False`) pese a la decisión de hacerlo obligatorio. Único residuo vivo de la propuesta v2. | `apps/banco_iniciativas/forms/inscripcion.py:146,208` |
| **B7** | MEDIA | **`manuales_modulos/banco.md` no documenta puntaje /105, ranking ni panel de comité.** Hacerlo **antes** de usar el módulo con Deportes. Las URLs del manual sí están al día (SPA). | `docs/manuales_modulos/banco.md` |
| **B8** | — | **C2 territorialidad reparte 0/10 a las 24 del piloto**: el form no capturó UPZ. No es bug de cálculo, es un dato que nunca se pidió. **Decisión pendiente (Alex):** capturar UPZ en el form o dejar C2 en 0. | `apps/banco_iniciativas/services/puntaje.py` |

---

## 🟡 Datos

| ID | Sev | Resumen | Evidencia |
|----|-----|---------|-----------|
| **D1** | MEDIA | **25 de 241 sedes con coordenadas fuera del contorno de Kennedy** (tabla `escuela`). Anotado sin tocar por instrucción de Alex. Se resuelve con una query cuando exista PostGIS propio (Fase 1 del plan de mapa). | tabla `escuela` |
| **D2** | BAJA | **1 sede sin resolver** (`estrato_ideca IS NULL`): sus coordenadas caen fuera de Kennedy y del bbox de descarga. Se deja NULL a propósito: **no se infiere**. | `apps/georeferenciacion/management/commands/asignar_estrato_sedes.py` |
| **D3** | — | **`estrato_ideca_org` del piloto: 13 de 24.** Las otras 11 quedan NULL **a propósito** (fuera de Kennedy / no existen / sin dirección). No es un bug: es el techo real del dato. | evento 62 |
| **D4** | MEDIA | **No usar el `estrato` autodeclarado como fallback.** Medido: de 6 casos contrastables contra IDECA **solo 2 coinciden**, y los otros 4 difieren **todos en la misma dirección** (el oficial es más alto que el declarado) — el sesgo esperable cuando declarar menos da más puntos. n=6, pero incentivo + consistencia direccional bastan para no fundar plata pública ahí. | medición 2026-07-16 |
| **M-EDU** | MEDIA | Crear tabla `sede_educativa` (colegios DANE) para que la pestaña "Educación" del mapa tenga su capa propia. **Bloqueada por insumo externo** (planilla DANE de Alex). Confirmado que en `poblacion_kennedy` no existe `sede_educativa`/`colegio`/`institucion_educativa`/`plantel`. | ~2–3 h una vez llegue la planilla |

---

## 🟡 Frontend / infra

| ID | Sev | Resumen | Evidencia |
|----|-----|---------|-----------|
| **F1** | MEDIA | **La multi-alcaldía no existe, y dos docs la venden como implementada.** `environment.prod.ts` es **código muerto**: `angular.json` no tiene `fileReplacements`, así que el build de prod compila `environment.ts`. Nadie sustituye los `__ENV_*__`. Cambiar `appName`/`alcaldiaName`/`apiBaseUrl` **no hace nada**. No es drift de doc: es una feature que se cree entregada. **Ticket de código, no de doc.** | `frontend/src/environments/environment.prod.ts:23-26`, `frontend/angular.json` |
| **F2** | BAJA | **Regresión silenciosa N18:** la persistencia de la última pestaña del mapa (`LocalStorage`) se perdió al reescribir el mapa en Angular. `MEJORAS_FUTURAS.md` la declara entregada ✅. 0 hits de `localStorage` en `frontend/src/app/features/mapa/`. | `frontend/src/app/features/mapa/` |
| **F3** | BAJA | **Residuo del diseño descartado de Kenny:** `kenny-chat.types.ts:59-62` conserva `pqrsTipo`/`citaDep`/`citaDate`/`citaTime` y `flujos.spec.ts:12` testea acciones **inalcanzables** (`pqrs:`, `cita:dep:`…). Flujos que nunca se construyeron. | `frontend/src/app/features/asistente/` |
| **F4** | BAJA | **A11y nunca se auditó de forma sistemática**: no hay `axe-core` ni `pa11y` (0 hits en `frontend/package.json`). Los skip-links sí están hechos. Único pendiente real de `ux_pendiente.md`. | `frontend/package.json` |
| **F5** | MEDIA | **`docs/infra/artefactos/` divergió de la raíz en los 5 archivos.** La copia de `requirements.txt` **no tiene** `shapely`/`drf-spectacular`/`django-cors-headers`/`django-ratelimit` → **quien despliegue con esa copia, no arranca**; y su `docker-compose.yml` congela justo el bug del `build:` faltante. Copias-snapshot de artefactos vivos. **Borrar la carpeta.** | `docs/infra/artefactos/` vs raíz |
| **F6** | BAJA | **`frontend/README.md` es el boilerplate intacto de `ng new`** y recomienda `ng build` **sin `--base-href=/app/`** — exactamente el comando que dejó la SPA en blanco el 2026-06-18. Quien entre por `frontend/` lee el comando que rompe. | `frontend/README.md:15` |

---

## 🟡 RBAC

| ID | Sev | Resumen | Evidencia |
|----|-----|---------|-----------|
| **R1** | MEDIA | **`scope.py` no cubre 4 módulos**: `banco_iniciativas`, `festivales`, `caracterizacion` y el CRUD de `presupuesto` no aparecen entre sus consumidores (solo `presupuesto/services/panel_subgrupo.py:48`). Es el único hueco real del RBAC; el resto de `control_acceso_roles.md` ya está implementado y en producción. | `apps/login/services/scope.py` |
| **R2** | — | **Decisión pendiente:** el cockpit `api_beneficiarios_perfil` (`views_presupuesto.py`, módulo `presupuesto_proyectos`) expone perfiles agregados de beneficiarios **cross-subgrupo** a roles presupuestales. Se dejó **sin scopear a propósito**. Decidir si se scopea (PR aparte). | `apps/presupuesto/views_presupuesto.py` |

---

## Deuda de documentación (meta)

Ver la auditoría completa en
[`../propuestas/orden_documentacion_2026-07-16.md`](../propuestas/orden_documentacion_2026-07-16.md).
Resumen: **~90 afirmaciones falsas** en 20 documentos. Las 3 más caras:

1. `docs/frontend/FRONTEND_ANGULAR.md:254` — manda `npm run build` sin
   `--base-href=/app/`: **seguir la guía rompe producción**.
2. `docs/frontend/FRONTEND_ANGULAR.md:50-67` — *"los formularios públicos NO se
   migran a Angular"*. Están **todos migrados** (`publico.routes.ts`, 10 rutas).
   Es la mentira que ya mordió una vez, viva en otro archivo.
3. `docs/propuestas/control_acceso_roles.md:75-77` — *"no existe ningún helper de
   scope por dependencia en todo `apps/`"*. `apps/login/services/scope.py` existe,
   está en producción y lo consumen 8 módulos. Quien lo lea reconstruye desde cero
   algo que ya está.

---

## Cómo seguir

- **Mejoras (no deuda):** lo poco vivo de `MEJORAS_FUTURAS.md` (exports CSV/Excel
  de la IA, deep-link del mapa por subgrupo) se absorbe aquí; el archivo se
  propone borrar.
- **Evolución geoespacial:** [`../propuestas/plan_evolucion_mapa.md`](../propuestas/plan_evolucion_mapa.md)
  — Fase 0 ✅ ejecutada, Fase 1 aprobada, Fases 2–3 pendientes. **No es deuda**, es plan.
- **Hardening pre-gov.net:** agregar `BEHIND_TLS=true` a `.env` y reiniciar
  `innova_k`. Requiere certificado nginx primero.

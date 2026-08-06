# Deuda técnica activa — innovaK

**Última actualización:** 2026-08-06 (repaso ficha por ficha contra el código:
**6 ítems que este archivo daba por abiertos ya estaban cerrados**, ver la
sección de abajo. La revisión anterior es del 2026-07-16, cuando se consolidó
aquí la deuda suelta en 6 documentos + 8 hallazgos de estratificación).

> ### ✅ Cerrados el 2026-08-06 al verificarlos (no eran deuda viva)
>
> Un documento de deuda con fichas falsas hace que la siguiente sesión
> desconfíe de todas. Estos seis se comprobaron contra el código y se
> retiraron de las tablas:
>
> | Era | Por qué ya no |
> |---|---|
> | **M-EDU** — "crear tabla `sede_educativa`; confirmado que en `poblacion_kennedy` no existe `colegio`" | Existe desde el **2026-08-05**: `apps/educacion/models/colegio.py` con `db_table = "colegio_sede"`, más `entrega_insumo_colegio`. El módulo de Educación está en producción con 48 colegios / 79 sedes. La ficha describía el mundo previo a ese commit |
> | **R1** — "`scope.py` no cubre `banco_iniciativas`, `festivales`, `caracterizacion` ni el CRUD de `presupuesto`" | Los cuatro lo consumen hoy: `banco_iniciativas/api/views.py`, `festivales/api/views.py` + `percepcion.py`, `caracterizacion/api/views.py` y `presupuesto/api/views.py` |
> | **B6** — "soporte legal sigue opcional (`required=False`)" | En `ANEXOS` el `soporte_legal` está declarado con obligatorio `True` y entra en `ANEXOS_OBLIGATORIOS` (`banco_iniciativas/forms/inscripcion.py`). Los números de línea de la ficha (146, 208) apuntaban a otra cosa: el archivo se reescribió con la matriz oficial |
> | **F5** — "`docs/infra/artefactos/` divergió; borrar la carpeta" | La carpeta ya no existe |
> | **F6** — "`frontend/README.md` es el boilerplate de `ng new` y manda `ng build` sin `--base-href`" | El archivo ya no existe. Y aunque volviera, el comando desnudo ya no rompe: ver abajo |
> | **Deuda de doc #1 y #2** | Las dos se arreglaron el 2026-08-06 en `docs/frontend/FRONTEND_ANGULAR.md` (ver más abajo). La #3 (`control_acceso_roles.md`) ya estaba corregida |
>
> **Y la lección de método, que ya recogió `ESTADO.md` §3.1 y conviene no
> perder:** el hueco de RBAC del motor de consulta de beneficiarios —que
> cualquiera con el módulo `dashboard_ia` viera el universo completo de
> personas— se declaró "verificado abierto" el 2026-08-03 estando **cerrado
> desde el 2026-07-14** (commit `01c573c`). El error fue del
> método: se hizo `grep` del símbolo `aplicar_subgrupo`, y el arreglo usa otros
> nombres — `scope.personas_beneficiarias_visibles(user)` y
> `scope.participaciones_visibles(user)`, ambos en
> `apps/dashboard/services/ia_beneficiarios.py`. Buscar **un nombre** no es
> verificar **una propiedad**.

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
| **P2** | **3 tokens HMAC publicados — código resuelto el 2026-08-06, falta el `.env` y el purge.** Estaban en `docs/manuales_modulos/cultura.md`, retirados del working tree (barrido de todo el repo: no aparecían en ningún otro archivo, rastreado o no). Lo que los hacía difíciles de quemar era que se derivaban de `SECRET_KEY`, y rotarla tumba las sesiones de Redis y los enlaces de restablecimiento; `SECRET_KEY_FALLBACKS` no servía porque habría dejado válidos justo los tokens filtrados. Ahora la firma usa **`QR_TOKEN_SECRET`**, una clave propia, con `QR_TOKEN_SECRETS_LEGACY` para rotar sin matar el material impreso. **Sigue abierto:** (a) poner `QR_TOKEN_SECRET` en el `.env` del servidor y reiniciar — mientras no esté, el fallback a `SECRET_KEY` mantiene los tres tokens filtrados vivos; (b) los valores siguen alcanzables en el historial de git hasta que corra el purge. |

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

---

## 🟡 Frontend / infra

| ID | Sev | Resumen | Evidencia |
|----|-----|---------|-----------|
| **F1** | MEDIA | **La multi-alcaldía no existe, y dos docs la venden como implementada.** `environment.prod.ts` es **código muerto**: `angular.json` no tiene `fileReplacements`, así que el build de prod compila `environment.ts`. Nadie sustituye los `__ENV_*__`. Cambiar `appName`/`alcaldiaName`/`apiBaseUrl` **no hace nada**. No es drift de doc: es una feature que se cree entregada. **Ticket de código, no de doc.** | `frontend/src/environments/environment.prod.ts:23-26`, `frontend/angular.json` |
| **F2** | BAJA | **Regresión silenciosa N18:** la persistencia de la última pestaña del mapa (`LocalStorage`) se perdió al reescribir el mapa en Angular. `MEJORAS_FUTURAS.md` la declara entregada ✅. 0 hits de `localStorage` en `frontend/src/app/features/mapa/`. | `frontend/src/app/features/mapa/` |
| **F3** | BAJA | **Residuo del diseño descartado de Kenny:** `kenny-chat.types.ts:59-62` conserva `pqrsTipo`/`citaDep`/`citaDate`/`citaTime` y `flujos.spec.ts:12` testea acciones **inalcanzables** (`pqrs:`, `cita:dep:`…). Flujos que nunca se construyeron. | `frontend/src/app/features/asistente/` |
| **F4** | BAJA | **A11y nunca se auditó de forma sistemática**: no hay `axe-core` ni `pa11y` (0 hits en `frontend/package.json`). Los skip-links sí están hechos. Único pendiente real de `ux_pendiente.md`. | `frontend/package.json` |
| **F7** | BAJA | **Nadie mide la accesibilidad, y la deuda está cuantificada.** Tras cerrar las 5 pantallas nuevas (2026-08-06) quedan, medidos sobre `frontend/src`: **82 barras** de carga/error sin live region en ~35 componentes, **299 `<th>` sin `scope`** y 2 tablas sin `.ui-table-responsive`. Es barrida mecánica, pero sobre archivos no leídos: poner `role="alert"` a ciegas en una barra que es un aviso empeora las cosas. Va junto con **F4** (instalar `axe-core`, que es lo que evita que esto se vuelva a acumular). | `frontend/src/app/features/` · faltan `actividades-subgrupo.component.ts` y `proyecto-360.component.ts` |
| **F8** | ~~BAJA~~ | ~~**Font Awesome no está instalado**~~ **✅ RESUELTO 2026-08-06.** Se self-hosteó Font Awesome Free 7.3.1 (sin CDN: la red de la Alcaldía no siempre sale). Subset generado de **199 iconos** de los 2.307 del paquete → el CSS del bundle pasó de 30 KB a **14 KB gzip**; `fa-brands` (113 KB) no se despacha porque no se usa ni un icono de marca. **Los 199 verificados: 0 faltantes.** El subset trae guardián (`npm run iconos:verificar`) que falla con código 1 si alguien agrega un icono y no regenera — sin eso el subset reintroduce el mismo hueco mudo que veníamos de arreglar. Detalle y licencias en [`../propuestas/font_awesome_selfhost.md`](../propuestas/font_awesome_selfhost.md) | `frontend/scripts/generar_subset_fa.js` |
| **F9** | BAJA | **Migración de Font Awesome a lucide — medida, no hecha.** Es la otra mitad de F8, y se difiere a propósito: 199 iconos en 80 archivos no se migran a mano en medio de otra cosa. Ya está dimensionada en `docs/propuestas/fa_a_lucide.csv`: **85 son coincidencia exacta de nombre** (mecánicos), 20 sinónimo a revisar y **94 sin candidato** (decisión de diseño). El caso espinoso son los 12 iconos que el backend manda por `modulos_area.py` e interpola como `class="fa {{ m.icono }}"`: lucide se usa por componente, no por clase, así que migrarlos exige cambiar el contrato del backend. **Limpieza previa gratis:** hay el mismo icono con dos nombres por mezclar épocas de FA (`fa-exclamation-triangle`/`fa-triangle-exclamation`, `fa-info-circle`/`fa-circle-info`). | `docs/propuestas/fa_a_lucide.csv` |

---

## 🟡 RBAC

| ID | Sev | Resumen | Evidencia |
|----|-----|---------|-----------|
| **R2** | — | **Decisión pendiente:** el cockpit `api_beneficiarios_perfil` (`views_presupuesto.py`, módulo `presupuesto_proyectos`) expone perfiles agregados de beneficiarios **cross-subgrupo** a roles presupuestales. Se dejó **sin scopear a propósito**. Decidir si se scopea (PR aparte). | `apps/presupuesto/views_presupuesto.py` |

---

## Deuda de documentación (meta)

Ver la auditoría completa en
[`../propuestas/orden_documentacion_2026-07-16.md`](../propuestas/orden_documentacion_2026-07-16.md).
Resumen: **~90 afirmaciones falsas** en 20 documentos. Las 3 más caras estaban
listadas acá y **las tres están cerradas** (2026-08-06):

1. ✅ `docs/frontend/FRONTEND_ANGULAR.md` mandaba `npm run build` sin
   `--base-href=/app/` — **seguir la guía rompía producción**. Arreglado en dos
   niveles: la guía lo explica, y sobre todo `frontend/angular.json` ahora fija
   `"baseHref": "/app/"` en la configuración `production`, así que el comando
   desnudo ya sale correcto. Deja de depender de que alguien recuerde la
   bandera, que es como se rompió el 2026-06-18.
2. ✅ `FRONTEND_ANGULAR.md` §"Regla B" declaraba los formularios públicos
   **intocables por Angular**. Están todos migrados desde el 2026-06-04
   (`publico.routes.ts`, 10 rutas bajo `/app/p/*`); las vistas Django viejas
   redirigen. La sección ahora dice la verdad y marca el kiosko de votación
   como la única excepción.
3. ✅ `docs/propuestas/control_acceso_roles.md` ya no contiene la frase *"no
   existe ningún helper de scope"*. `apps/login/services/scope.py` está en
   producción y hoy lo consumen 10 archivos.

**Lo que sigue abierto de documentación** es el volumen: quedan las otras ~87
afirmaciones del inventario del 2026-07-16, y **faltan manuales de módulo para
8 apps en producción** — entre ellas `caracterizacion` (8 wizards) y
`presupuesto` (la cadena central). Eso no es drift, es ausencia.

---

## Cómo seguir

- **Mejoras (no deuda):** lo poco vivo de `MEJORAS_FUTURAS.md` (exports CSV/Excel
  de la IA, deep-link del mapa por subgrupo) se absorbe aquí; el archivo se
  propone borrar.
- **Evolución geoespacial:** [`../propuestas/plan_evolucion_mapa.md`](../propuestas/plan_evolucion_mapa.md)
  — Fase 0 ✅ ejecutada, Fase 1 aprobada, Fases 2–3 pendientes. **No es deuda**, es plan.
- **Hardening pre-gov.net:** agregar `BEHIND_TLS=true` a `.env` y reiniciar
  `innova_k`. Requiere certificado nginx primero.

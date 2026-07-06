# Deuda técnica activa — innovaK

**Última actualización:** 2026-07-06 (sesión de orden: CSS muerto borrado, limpieza residual catalogada)
**Total pendiente:** **0 deuda crítica.** 1 media (M-EDU, bloqueada por insumo) + 5 de limpieza de bajo riesgo (L1–L5).

> El histórico de 66 ítems cerrados vive en
> [`_historico/cronograma_deuda.md`](./_historico/cronograma_deuda.md).
> Las **mejoras escaladas** (N17, N18 con plan alta pendiente pero
> mínima/media ya entregada) viven en
> [`MEJORAS_FUTURAS.md`](../informes/MEJORAS_FUTURAS.md), separadas de la deuda.

---

## 🔴 Bugs latentes / Riesgos (0)

_(Categoría limpia desde 2026-05-11.)_

## 🟡 Convenciones cosméticas (0)

_(Todas resueltas en sesión 2026-05-25 — ver histórico para detalle.)_

---

## Pendientes Jóvenes a la E (0)

**J5 CERRADO 2026-06-11:** ya estaba implementado desde el 2026-06-09
(endpoint `/jovenes-a-la-e/api/insights/`, panel Angular Chart.js y
Excel de 4 hojas con Matriz 1 presupuestal + Matriz 2 ejecución
contractual) — verificado en vivo. Nota: las matrices salen vacías
hasta que exista un evento `JOVENES_BECA` real con KPIs vinculados
(el 100055 de mayo fue borrado).

**Decisión Alex 2026-05-21:** la dotación a sedes (convenio 955-2025, meta 23773) reusa el `tipo_evento='ENTREGA'` ya existente, sin tabla nueva — no requiere PR.

---

## Pendiente Mapa Kennedy (Educación)

| ID | Severidad | Resumen | Esfuerzo |
|----|-----------|---------|----------|
| M-EDU | MEDIA | Crear tabla `sede_educativa` (colegios DANE) para que la pestaña N18 "Educación" tenga su propia capa, igual que Cultura/Deporte tienen `escuela`. Hoy se reusan las capas de Cultura/Deporte+Lugares pero no hay datos específicos de colegios formales del territorio. | DDL + carga 74 sedes target convenio 955-2025 + endpoint `/geo/api/kennedy/sedes-educativas/` + capa Angular (~2–3 h una vez Alex pase la planilla DANE) |

**Hallazgo BD 2026-06-01:** búsqueda exhaustiva en `poblacion_kennedy`
confirma que las únicas tablas con coordenadas son `escuela` (241 filas
Cultura+Deporte, NO colegios) y `geo_referenciacion` (306 filas
Cultura/Deporte/NULL). El catálogo `tipo_punto` solo tiene Cultura y
Deporte. No existe `sede_educativa`, `colegio`, `institucion_educativa`
ni `plantel`. **Diferido a después de cerrar Etapa D Angular.**

---

## Limpieza pendiente post full-Angular (2026-07-06)

El corte a full-Angular retiró los templates (Lotes 1-7) pero dejó residuos
de bajo riesgo. En la sesión de orden 2026-07-06 se borró el CSS/HTML muerto
seguro (20 archivos: `static/css/*`, `static/style.css`, builds viejos en
`static/dist/css/style*`, `mapa_escuelas.html` ×4, 3 SCSS vacíos y
`_partials/paginator.html`). Queda pendiente lo que requiere decisión o PR aparte:

| ID | Severidad | Resumen | Esfuerzo |
|----|-----------|---------|----------|
| L1 | BAJA | **Trim del monolito `static/scss/base.scss`** (9.472 líneas): 12 partials (`_cultura`, `_deporte`, `_kactivo`, `_hub`, `_table`, `_filter-bar`, `_info-bar`, `_back-link`, `_empty-state`, `_badge`, `_components`, `_componentes`) solo estilaban templates ya borrados. Borrarlos exige editar los `@use` de `base.scss` y rebuild. | ~1 h + verificar que el chrome vivo (`.base-*`, sidebar, footer, `.vot-*`, `.ui-breadcrumb`) no se rompa |
| L2 | BAJA | **Retiro de ~90 vistas Django que solo `redirect('/app/...')`** en 24 archivos (organizador). Ningún template las referencia, pero pueden estar en `reverse()`/bookmarks. Los `public.py` de QR **se quedan** (puente de QR impresos). | PR de URLs+views |
| L3 | BAJA | **`staticfiles/` (207 archivos trackeados)** — output de `collectstatic` que no debería estar en git; se regenera en deploy. Borrar + gitignorar toca el mount de `docker-compose.yml` → confirmación de Alex. | 30 min + doble confirmación |
| L4 | BAJA | **`apps/kordial` y `apps/VitalK`** — scaffolds vacíos no instalados. Borrar código muerto (requiere decisión explícita de Alex, CLAUDE.md §9). | 10 min |
| L5 | DUDOSA | **`templates/votaciones/dashboard.html`** — `dashboard_page` lo renderiza pero ningún enlace apunta a `votaciones:dashboard`; superseded por `/app/votaciones`. Confirmar antes de borrar. | 15 min |

---

## Cómo seguir

**Mejoras (no deuda):** ver [`MEJORAS_FUTURAS.md`](../informes/MEJORAS_FUTURAS.md) — N17 (Consulta IA alta) y N18 (sub-mapas alta) con su alcance mínima/media ya entregado.

**Evolución del frontend:** ver [`PLAN_FRONTEND.md`](../frontend/PLAN_FRONTEND.md)
— camino híbrido con destino Angular condicional, 4 etapas
(A: UX híbrida HTMX+Alpine+Tom Select · B: backend a API REST ·
C: decisión Angular · D: migración strangler). Tablero de tareas en §4
del plan. **No es deuda**, es evolución gradual con regla de oro
*Angular-ready*.

**Hardening pre-gov.net (cuando aplique):** agregar `BEHIND_TLS=true` a `.env` y reiniciar `innova_k`. Requiere certificado nginx primero.

# Deuda técnica activa — innovaK

**Última actualización:** 2026-07-06 (sesión de orden: limpieza L1–L5 completada)
**Total pendiente:** **0 deuda crítica, 0 de limpieza.** Solo 1 media (M-EDU, bloqueada por planilla DANE).

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

## Limpieza post full-Angular (2026-07-06) — RESUELTA

El corte a full-Angular retiró los templates (Lotes 1-7). La sesión de orden
2026-07-06 cerró TODOS los residuos de bajo riesgo:

| ID | Resultado |
|----|-----------|
| — | 20 archivos CSS/HTML muerto borrados (`static/css/*`, `static/style.css`, builds viejos `static/dist/css/style*`, `mapa_escuelas.html` ×4, 3 SCSS vacíos, `_partials/paginator.html`). |
| L1 ✅ | Trim de `static/scss/base.scss`: 11 partials huérfanos fuera; `base.css` 181→121 KiB (−31%). Chrome vivo intacto. |
| L2 ✅ | 69 vistas-puente `redirect('/app/...')` + 69 URLs retiradas. Públicos QR / kiosko / exports / DRF conservados. |
| L3 ✅ | `staticfiles/` (STATIC_ROOT, 207 archivos) desversionado + gitignored. |
| L4 ✅ | `apps/kordial` y `apps/VitalK` (scaffolds muertos) borrados. |
| L5 ✅ | `templates/votaciones/dashboard.html` + `dashboard_page` + URL borrados (superseded por `/app/votaciones`). |

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

# Deuda técnica activa — innovaK

**Última actualización:** 2026-05-25 (C2, C3, C6 alineación modelos ↔ BD)
**Total pendiente:** **0 deuda activa** + 1 feature opcional de Jóvenes a la E (no es deuda, es scope diferido)

> El histórico de 66 ítems cerrados vive en
> [`_historico/cronograma_deuda.md`](./_historico/cronograma_deuda.md).
> Las **mejoras escaladas** (N17, N18 con plan alta pendiente pero
> mínima/media ya entregada) viven en
> [`MEJORAS_FUTURAS.md`](./MEJORAS_FUTURAS.md), separadas de la deuda.

---

## 🔴 Bugs latentes / Riesgos (0)

_(Categoría limpia desde 2026-05-11.)_

## 🟡 Convenciones cosméticas (0)

_(Todas resueltas en sesión 2026-05-25 — ver histórico para detalle.)_

---

## Pendientes Jóvenes a la E

| ID | Severidad | Resumen | Esfuerzo |
|----|-----------|---------|----------|
| J5 | BAJA | Insights Chart.js + descarga Excel (Matriz 1 presupuestal + Matriz 2 ejecución contractual). Patrón Banco. | 3 h |

**Decisión Alex 2026-05-21:** la dotación a sedes (convenio 955-2025, meta 23773) reusa el `tipo_evento='ENTREGA'` ya existente, sin tabla nueva — no requiere PR.

---

## Cómo seguir

**Mejoras (no deuda):** ver [`MEJORAS_FUTURAS.md`](./MEJORAS_FUTURAS.md) — N17 (Consulta IA alta) y N18 (sub-mapas alta) con su alcance mínima/media ya entregado.

**Evolución del frontend:** ver [`PLAN_FRONTEND.md`](./PLAN_FRONTEND.md)
— camino híbrido con destino Angular condicional, 4 etapas
(A: UX híbrida HTMX+Alpine+Tom Select · B: backend a API REST ·
C: decisión Angular · D: migración strangler). Tablero de tareas en §4
del plan. **No es deuda**, es evolución gradual con regla de oro
*Angular-ready*.

**Hardening pre-gov.net (cuando aplique):** agregar `BEHIND_TLS=true` a `.env` y reiniciar `innova_k`. Requiere certificado nginx primero.

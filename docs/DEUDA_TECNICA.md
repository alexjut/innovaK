# Deuda técnica activa — innovaK

**Última actualización:** 2026-05-21 (PR-1+PR-2 Jóvenes a la E aplicados)
**Total pendiente:** 3 convenciones BAJA + **5 features pendientes** de Jóvenes a la E (no son deuda, son scope diferido)

> El histórico de 63 ítems cerrados vive en
> [`_historico/cronograma_deuda.md`](./_historico/cronograma_deuda.md).
> Las **mejoras escaladas** (N17, N18 con plan alta pendiente pero
> mínima/media ya entregada) viven en
> [`MEJORAS_FUTURAS.md`](./MEJORAS_FUTURAS.md), separadas de la deuda.

Lista compacta agrupada por **categoría operativa** (no por dominio
técnico) para que la salud del sistema se lea de un vistazo: lo que
puede romper algo va primero. IDs estables — no se renumera al borrar.

---

## 🔴 Bugs latentes / Riesgos (0)

_(Categoría limpia por primera vez. N22 cerrado con UNIQUE INDEX parcial
en sesión 2026-05-11; C4 resultó falsa alarma — la BD ya tenía FK
formales en todas las columnas `upz_codigo`/`barrio_codigo`.)_

## 🟡 Convenciones cosméticas (3)

Inconsistencias **sin daño actual** pero ensucian el código. Se limpian
oportunísticamente al tocar el código adyacente; no requieren PR
dedicado.

| ID | Severidad | Resumen |
|----|-----------|---------|
| C2 | BAJA | `db_column` declarado a veces sí, a veces no. Convención CLAUDE.md §3 pide declararlo siempre en FKs. |
| C3 | BAJA | Mix de `IntegerField` y `BigAutoField` como PKs entre modelos. |
| C6 | BAJA | Sin convención uniforme de `on_delete` (mix de `DO_NOTHING`, `SET_NULL`, `CASCADE`). |

---

## Pendientes Jóvenes a la E

Captura + vista organizador + sync KPI + cripto Mongo + selects → todos
aplicados el 2026-05-21. Solo queda lo siguiente:

| ID | Severidad | Resumen | Esfuerzo |
|----|-----------|---------|----------|
| J5 | BAJA | Insights Chart.js + descarga Excel (Matriz 1 presupuestal + Matriz 2 ejecución contractual). Patrón Banco. | 3 h |

**Cerrados 2026-05-21:**
- ✅ J1 Vista organizador (list + detalle + validar/rechazar) — `apps/jovenes_a_la_e/views/organizador.py` + templates BEM.
- ✅ J2 Sync `AvanceIndicador` al validar — crea filas en `presu_avance_ind_periodo` para cada KPI vinculado a la `actividad_plan` del evento; al rechazar después de validar, revierte.
- ✅ J3 Cripto Mongo para firma — reusa `apps/documentos/services/mongo_storage.guardar` igual que Banco; `firma_mongo_id` persistido en `EntregaBeca`.
- ✅ J4 Selects UPL/Barrio — `ModelChoiceField` en el form, persistencia en `upl_codigo` / `barrio_codigo` de `entrega_beca`.

**Decisión Alex 2026-05-21:** la dotación a sedes (convenio 955-2025, meta 23773) reusa el `tipo_evento='ENTREGA'` ya existente, sin tabla nueva — no requiere PR.

## Cómo seguir

**Convenciones restantes (cosméticas, sin urgencia):** C2, C3, C6. Se limpian oportunísticamente al tocar el código adyacente — no requieren PR dedicado.

**Mejoras (no deuda):** ver [`MEJORAS_FUTURAS.md`](./MEJORAS_FUTURAS.md) — N17 (Consulta IA alta) y N18 (sub-mapas alta) con su alcance mínima/media ya entregado.

**Hardening pre-gov.net (cuando aplique):** agregar `BEHIND_TLS=true` a `.env` y reiniciar `innova_k`. Requiere certificado nginx primero.

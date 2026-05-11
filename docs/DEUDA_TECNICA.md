# Deuda técnica activa — innovaK

**Última actualización:** 2026-05-11 (N21 cerrado)
**Total pendiente:** 3 ítems · **0 bugs latentes** + **3 convenciones** (todas BAJA, cosméticas)

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

## Cómo seguir

**Convenciones restantes (cosméticas, sin urgencia):** C2, C3, C6. Se limpian oportunísticamente al tocar el código adyacente — no requieren PR dedicado.

**Mejoras (no deuda):** ver [`MEJORAS_FUTURAS.md`](./MEJORAS_FUTURAS.md) — N17 (Consulta IA alta) y N18 (sub-mapas alta) con su alcance mínima/media ya entregado.

**Hardening pre-gov.net (cuando aplique):** agregar `BEHIND_TLS=true` a `.env` y reiniciar `innova_k`. Requiere certificado nginx primero.

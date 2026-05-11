# Deuda técnica activa — innovaK

**Última actualización:** 2026-05-11 (N27 cerrado)
**Total pendiente:** 7 ítems · **2 bugs latentes** + **4 convenciones** + **1 bloqueada**

> El histórico de 63 ítems cerrados vive en
> [`_historico/cronograma_deuda.md`](./_historico/cronograma_deuda.md).
> Las **mejoras escaladas** (N17, N18 con plan alta pendiente pero
> mínima/media ya entregada) viven en
> [`MEJORAS_FUTURAS.md`](./MEJORAS_FUTURAS.md), separadas de la deuda.

Lista compacta agrupada por **categoría operativa** (no por dominio
técnico) para que la salud del sistema se lea de un vistazo: lo que
puede romper algo va primero. IDs estables — no se renumera al borrar.

---

## 🔴 Bugs latentes / Riesgos (2)

Cosas que **pueden causar fallas reales**. Prioridad de atención.

| ID | Severidad | Resumen | Acción mínima |
|----|-----------|---------|---------------|
| N22 | BAJA | **`Beneficiario` sin UNIQUE parcial.** Race condition latente: 2 requests concurrentes (`banco_iniciativas/forms/inscripcion.py:466`, `caracterizacion/views/deporte.py:29`, `caracterizacion/views/salud.py`) pueden crear 2 filas para la misma persona. No urgente con baja concurrencia, pero el Banco apunta a 280 organizaciones. | Auditar duplicados existentes + `CREATE UNIQUE INDEX idx_beneficiario_persona ON beneficiario(persona_id) WHERE tipo='PERSONA' AND persona_id IS NOT NULL`. **Requiere DDL.** |
| C4 | MEDIA | **UPZ y Barrio sin FK formal.** Los `IntegerField` `upz_codigo`/`barrio_codigo` no tienen `FOREIGN KEY` en BD. Pueden quedar valores huérfanos sin alerta. Ya hizo daño histórico (M22: 79/111 mismatches IDECA). | Auditar huérfanos + `ALTER TABLE ... ADD CONSTRAINT FOREIGN KEY`. Decisión Alex sobre huérfanos: `SET NULL` o borrar. **Requiere DDL.** |

## 🟡 Convenciones (4)

Inconsistencias **sin daño actual** pero ensucian el código. Se limpian
oportunísticamente al tocar el código adyacente; no requieren PR
dedicado.

| ID | Severidad | Resumen |
|----|-----------|---------|
| N19 | BAJA | **Form Banco no crea Persona desde `rep_nombre+rep_numero_doc`.** Si la cédula no existe en BD, NO se crea Persona automáticamente. Limpio: agregar `rep_nombre1/2/apellido1/2` separados (UX cambia). Pragmático: split heurístico (frágil). Ver `apps/banco_iniciativas/forms/inscripcion.py:417-421`. Requiere decisión UX. |
| N21 | BAJA | **Sector ↔ Subgrupo acoplados por nombre.** `SECTORES_META` en `apps/caracterizacion/sectores.py:25` asume nombres específicos (Cultura→1, Deporte→2, Mujer→40, Salud→45, Juventud→46). Si Alex renombra un subgrupo, los reportes se rompen silenciosamente. Solución: pasar a `subgrupo_id`. |
| C2 | BAJA | `db_column` declarado a veces sí, a veces no. Convención CLAUDE.md §3 pide declararlo siempre en FKs. |
| C3 | BAJA | Mix de `IntegerField` y `BigAutoField` como PKs entre modelos. |
| C6 | BAJA | Sin convención uniforme de `on_delete` (mix de `DO_NOTHING`, `SET_NULL`, `CASCADE`). |

## ⏳ Bloqueada por decisión Alex (1)

| ID | Resumen | Decisión pendiente |
|----|---------|---------------------|
| C5 | **Rename de modelos votaciones a español.** CLAUDE.md §3 declara votaciones como **excepción explícita** al "español en todo" (Event/Voter/Vote/Candidate). El ítem contradice la convención documentada. | Alex debe decidir: ¿revocar la excepción y proceder con el rename (~2h)? ¿O cerrar C5 como "no es deuda, es decisión de diseño documentada"? |

---

## Cómo seguir

**Alto impacto (DDL puntual con confirmación):**
- **N22** — UNIQUE parcial en `beneficiario(persona_id)`. Auditoría previa + DDL.
- **C4** — FK formal UPZ/Barrio. Auditoría de huérfanos + DDL.

**Decisión pendiente:**
- **C5** — confirmar si se mantiene la excepción de votaciones o se hace rename.

**Mejoras (no deuda):** ver [`MEJORAS_FUTURAS.md`](./MEJORAS_FUTURAS.md) — N17 (Consulta IA alta) y N18 (sub-mapas alta) con su alcance mínima/media ya entregado.

**Hardening pre-gov.net (cuando aplique):** agregar `BEHIND_TLS=true` a `.env` y reiniciar `innova_k`. Requiere certificado nginx primero.

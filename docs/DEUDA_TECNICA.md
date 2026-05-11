# Deuda técnica — innovaK

**Última actualización:** 2026-05-11 (M17+M22+N20+N9+N23+N17 mín+N18 mín+S9+N3 cerrados)
**Total pendiente:** 11 ítems · N17 y N18 ahora BAJA tras alcance mínimo aplicado

> El histórico de los 61 ítems ya cerrados vive en
> [`_historico/cronograma_deuda.md`](_historico/cronograma_deuda.md).

Lista compacta de deuda activa, agrupada por categoría y ordenada por
severidad. Cada ítem tiene un identificador estable (no se renumera al
borrar resueltos) para citar en commits futuros.

---

## 🔐 Seguridad (0)

_(S9 resuelto sesión 2026-05-11 — ver cronograma)_

## 🧹 Mantenibilidad (2)

| ID | Severidad | Resumen |
|----|-----------|---------|
| N19 | BAJA | **Form Banco no crea Persona desde `rep_nombre+rep_numero_doc`.** Si la cédula no existe en BD, NO se crea Persona automáticamente. Solución limpia: agregar `rep_nombre1/nombre2/apellido1/apellido2` separados al form (UX cambia). Solución pragmática: split heurístico (frágil). Ver `apps/banco_iniciativas/forms/inscripcion.py:417-421`. |
| N27 | BAJA | **Datos sucios usuarios y subgrupos.** Usuario `Coordionador` (typo) con 6 grupos asignados invalida pruebas por rol. Subgrupo `Prticipación` (typo, id=3) y `Seguridad` duplicado (id=5 e id=38) en `dep_id=3`. Requiere SQL puntual + decisión Alex. |

## 📐 Convenciones y schema (7)

| ID | Severidad | Resumen |
|----|-----------|---------|
| C4 | MEDIA | UPZ y Barrio usan `IntegerField` como FK lógica sin constraint formal en BD. |
| C2 | BAJA | `db_column` declarado a veces sí, a veces no. Convención requiere declararlo siempre en FKs (CLAUDE.md §3). |
| C3 | BAJA | Mix de `IntegerField` y `BigAutoField` como PKs entre modelos. |
| C5 | BAJA | (PARCIAL) Mezcla de idiomas en `apps/votaciones/`: nombres de modelos siguen en inglés (Event/Voter/Candidate/Vote). Login propio ya eliminado en 2026-04-27. Pendiente: rename de modelos+vistas+templates a español. |
| C6 | BAJA | Sin convención uniforme de `on_delete` (mix de `DO_NOTHING`, `SET_NULL`, `CASCADE`). |
| N21 | BAJA | **Sector ↔ Subgrupo acoplados por nombre (no FK).** Los 6 sectores en `SECTORES_META` (`apps/caracterizacion/sectores.py`) asumen que existe un Subgrupo con el mismo label (Cultura→1, Deporte→2, Mujer→40, Salud→45, Juventud→46). Si Alex renombra el subgrupo "Cultura" en `/org/subgrupos/`, los reportes que crucen sector ↔ subgrupo se rompen silenciosamente. Solución: agregar `subgrupo_id` a `SECTORES_META` o al modelo. |
| N22 | BAJA | **`Beneficiario` sin UNIQUE parcial.** La idempotencia de `asegurar_beneficiario_persona/_organizacion` depende exclusivamente de la lógica de aplicación (`filter().first()`). Race condition latente: 2 requests concurrentes para la misma persona pueden crear 2 filas. No urgente por baja concurrencia. Fix: `CREATE UNIQUE INDEX idx_beneficiario_persona ON beneficiario(persona_id) WHERE tipo='PERSONA' AND persona_id IS NOT NULL`. **Requiere DDL.** |

## ✨ UX / Producto (2)

| ID | Severidad | Resumen |
|----|-----------|---------|
| N17 | BAJA | **Consulta Inteligente sigue limitada a `login_persona`** (alcance mínimo ya aplicado 2026-05-11: UI con ejemplos clickables + FIELD_MAPPING ampliado a ~70 sinónimos). Pendiente plan **media** (5 modelos nuevos + `QueryType.AGGREGATE/JOIN` + selector gráfica, 1 sem) y **alta** (text-to-SQL real con `gpt-4o` + exports + comparaciones, 2-4 sem). |
| N18 | BAJA | **Sub-mapas por subgrupo de Inversión Local — alcance mínimo aplicado 2026-05-11.** Barra de 18 pestañas (Todos + 17 subgrupos dep_id=3) encima del mapa. Click sincroniza el select del sidebar y reaplica `cargarEventos()`. Plan **media** (KPIs por subgrupo en panel lateral + capas filtradas, 2d) y **alta** (sub-mapas independientes con color/leyenda/zoom propios + persistencia, 3-4d) quedan abiertos. |

---

## Cómo seguir

**Quick wins (< 30 min cada uno):**
- ⚡ Para activar hardening TLS cuando entre gov.net: agregar `BEHIND_TLS=true` a `.env` y reiniciar `innova_k`. Requiere certificado en nginx primero.

**Alto impacto (1-3h cada uno):**
- **N27** — limpiar datos sucios (1 script SQL puntual + decisión nombres).

**Estratégico (decisión + DDL — requiere Alex):**
- **N22** — UNIQUE parcial en `beneficiario(persona_id)`.
- **C5** — rename completo de modelos votaciones a español (Event→Evento, etc.).
- **N21** — pasar `SECTORES_META` a `subgrupo_id` (FK formal).

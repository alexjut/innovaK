# Deuda técnica — innovaK

**Última actualización:** 2026-05-11
**Total pendiente:** 18 ítems

> El histórico de los 61 ítems ya cerrados vive en
> [`_historico/cronograma_deuda.md`](_historico/cronograma_deuda.md).

Lista compacta de deuda activa, agrupada por categoría y ordenada por
severidad. Cada ítem tiene un identificador estable (no se renumera al
borrar resueltos) para citar en commits futuros.

---

## 🔐 Seguridad (2)

| ID | Severidad | Resumen |
|----|-----------|---------|
| S9 | BAJA | `DATABASE_URL` y `DB_PASSWORD` ambos en `.env` (redundancia que confunde). Acción: borrar manualmente `DATABASE_URL` de `.env`, no se usa en código. |
| N23 | BAJA | **PII expuesta en `/caracterizacion/api/persona/`.** Endpoint público (sin auth) devuelve nombre+apellido al pasar cédula válida. Diseño justificado para autollenado de wizards, pero abre enumeración (60 r/s + lista de cédulas obtiene nombres). Mitigación: rate limit nginx 5-10 r/min o exigir `?evento_id=X` válido. |

## 🧹 Mantenibilidad (5)

| ID | Severidad | Resumen |
|----|-----------|---------|
| M17 | MEDIA | Mejorar geocoding con API IDECA (hoy `LugarIncidencia` se crea con coords del usuario, sin validación contra el catálogo oficial). |
| M22 | MEDIA | Mismatch IDECA: 79/111 barrios sin `geometry` por inconsistencia en códigos. |
| N20 | MEDIA | **Wizards internos sin trazabilidad organizacional.** Cuando un Coordinador llena `/dashboard/caracterizacion/<sector>/` sin evento, la fila queda con `evento_id=NULL` pero NO se guarda quién la levantó ni desde qué subgrupo. Conviene `funcionario_id` o `usuario_creador_id` en las 6 tablas `caracterizacion_*`. **Requiere DDL — confirmación de Alex.** 3 caminos: (a) DDL `funcionario_id`, (b) evento técnico automático del día, (c) validación en wizard. |
| N19 | BAJA | **Form Banco no crea Persona desde `rep_nombre+rep_numero_doc`.** Si la cédula no existe en BD, NO se crea Persona automáticamente. Solución limpia: agregar `rep_nombre1/nombre2/apellido1/apellido2` separados al form (UX cambia). Solución pragmática: split heurístico (frágil). Ver `apps/banco_iniciativas/forms/inscripcion.py:417-421`. |
| N27 | BAJA | **Datos sucios usuarios y subgrupos.** Usuario `Coordionador` (typo) con 6 grupos asignados invalida pruebas por rol. Subgrupo `Prticipación` (typo, id=3) y `Seguridad` duplicado (id=5 e id=38) en `dep_id=3`. Requiere SQL puntual + decisión Alex. |

## 📐 Convenciones y schema (8)

| ID | Severidad | Resumen |
|----|-----------|---------|
| C4 | MEDIA | UPZ y Barrio usan `IntegerField` como FK lógica sin constraint formal en BD. |
| N3 | MEDIA | `ContratoProyecto`/`ContratoActividad` sin `id` propio (PK compuesta). Intento previo de `ALTER` falló por ese motivo. Solución: `ADD COLUMN id BIGSERIAL UNIQUE NOT NULL` (sin reemplazar PK) + ajustar modelos. Pospuesto: 1:1 efectivo en datos actuales. **Requiere DDL.** |
| C2 | BAJA | `db_column` declarado a veces sí, a veces no. Convención requiere declararlo siempre en FKs (CLAUDE.md §3). |
| C3 | BAJA | Mix de `IntegerField` y `BigAutoField` como PKs entre modelos. |
| C5 | BAJA | (PARCIAL) Mezcla de idiomas en `apps/votaciones/`: nombres de modelos siguen en inglés (Event/Voter/Candidate/Vote). Login propio ya eliminado en 2026-04-27. Pendiente: rename de modelos+vistas+templates a español. |
| C6 | BAJA | Sin convención uniforme de `on_delete` (mix de `DO_NOTHING`, `SET_NULL`, `CASCADE`). |
| N21 | BAJA | **Sector ↔ Subgrupo acoplados por nombre (no FK).** Los 6 sectores en `SECTORES_META` (`apps/caracterizacion/sectores.py`) asumen que existe un Subgrupo con el mismo label (Cultura→1, Deporte→2, Mujer→40, Salud→45, Juventud→46). Si Alex renombra el subgrupo "Cultura" en `/org/subgrupos/`, los reportes que crucen sector ↔ subgrupo se rompen silenciosamente. Solución: agregar `subgrupo_id` a `SECTORES_META` o al modelo. |
| N22 | BAJA | **`Beneficiario` sin UNIQUE parcial.** La idempotencia de `asegurar_beneficiario_persona/_organizacion` depende exclusivamente de la lógica de aplicación (`filter().first()`). Race condition latente: 2 requests concurrentes para la misma persona pueden crear 2 filas. No urgente por baja concurrencia. Fix: `CREATE UNIQUE INDEX idx_beneficiario_persona ON beneficiario(persona_id) WHERE tipo='PERSONA' AND persona_id IS NOT NULL`. **Requiere DDL.** |

## ✨ UX / Producto (3)

| ID | Severidad | Resumen |
|----|-----------|---------|
| N17 | MEDIA | **Consulta Inteligente limitada a una sola tabla.** `/dashboard/consulta-inteligente/` solo consulta `login_persona` con 40 campos hardcoded en `apps/dashboard/ai_config.py`. No cruza Evento/Asistencia/Inscripción/Caracterización/Banco/Contratos. Solo 4 `QueryType`: COUNT, FILTER, GROUP, TOP — sin JOINs ni agregados temporales. Plan progresivo: (1) mínima — UI con ejemplos visibles + expandir whitelist y sinónimos (1d); (2) media — 5 modelos nuevos accesibles + `QueryType.AGGREGATE/JOIN` + selector de gráfica (1 semana); (3) alta — text-to-SQL real con `gpt-4o` + exports + gráficas configurables + comparaciones cruzadas (2-4 sem). |
| N9 | BAJA | Hub presupuesto con 12 cards y topbar con 13 tabs (densidad UX). Considerar agrupar en sub-secciones visuales (ej. Planeación / Ejecución / Seguimiento). |
| N18 | BAJA | **Sub-mapas por subgrupo de Inversión Local.** Mapa Kennedy tiene multiselect de subgrupo en sidebar pero la UX es plana. Para los 15 subgrupos con `dep_id=3` (Cultura, Deporte, Educación, Mujer, Ambiente, Seguridad, Buen trato, Acuerdos ciudadanos, Coordinación IL, Infraestructura, Paz, Participación, Reactivación Económica, Subsidio C, Seguridad), agregar **un mapa propio por subgrupo**. Reusa infra existente (`/geo/api/eventos/?subgrupo=X` ya filtra). Plan: (1) mínima — botones tipo pestaña + reaplica filtro + zoom default (½d); (2) media — KPIs por subgrupo en panel + capas filtradas (2d); (3) alta — sub-mapas independientes con color/leyenda/zoom propios + persistencia última selección por user (3-4d). |

---

## Cómo seguir

**Quick wins (< 30 min cada uno):**
- **S9** — borrar manualmente `DATABASE_URL` de `.env` (Alex, no se usa en código).
- ⚡ Para activar hardening TLS cuando entre gov.net: agregar `BEHIND_TLS=true` a `.env` y reiniciar `innova_k`. Requiere certificado en nginx primero.

**Alto impacto (1-3h cada uno):**
- **N17 mínima** — UI con ejemplos visibles + expandir whitelist y sinónimos en `ai_config.py`.
- **N9** — reorganizar hub presupuesto en sub-secciones visuales.
- **N27** — limpiar datos sucios (1 script SQL puntual + decisión nombres).
- **N18 mínima** — botones tipo pestaña sobre el mapa Kennedy + zoom default.
- **N23** — rate limit puntual nginx para `/caracterizacion/api/persona/`.

**Estratégico (decisión + DDL — requiere Alex):**
- **N3** — `id BIGSERIAL UNIQUE` en `ContratoProyecto`/`ContratoActividad`.
- **N20** — `funcionario_id` en las 6 tablas `caracterizacion_*`.
- **N22** — UNIQUE parcial en `beneficiario(persona_id)`.
- **C5** — rename completo de modelos votaciones a español (Event→Evento, etc.).
- **N21** — pasar `SECTORES_META` a `subgrupo_id` (FK formal).

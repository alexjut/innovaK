# Informe — Deuda de datos RBAC (B-deuda-2 y B-deuda-3)

**Fecha:** 2026-06-25 · **Alcance:** solo lectura sobre `poblacion_kennedy`. No se
modificó ningún dato. Insumo para que Javier coordine quién carga lo faltante; no
propone valores concretos.

---

## B-deuda-2 · Gobierno de datos de `contrato`

**Corrección a la premisa previa:** "~100/104 contratos sin subgrupo/proyecto" es
**inexacto**. Los 104 (100%) tienen subgrupo **derivable** (por dos caminos). El
hueco real es **funcionario, actividad (KPI), valor y cdp_id**.

| Métrica | Cantidad | % |
|---|---:|---:|
| Total contratos | 104 | 100% |
| Sin fila en `contrato_proyecto` (sin puente proyecto) | 4 | 3.8% |
| Sin `contrato_actividad_plan` (sin actividad → sin KPI) | 100 | 96.2% |
| Sin NINGUNA ligadura a proyecto | 0 | 0% |
| `valor` NULL | 98 | 94.2% |
| `cdp_id` NULL | 100 | 96.2% |
| `funcionario` NULL | 104 | 100% |

> La columna es `contrato.funcionario` (INTEGER, sin FK formal), no `funcionario_id`.

### Integridad: dos caminos mutuamente excluyentes
Los 4 contratos sin `contrato_proyecto` (ids 97-100) son exactamente los 4 que SÍ
tienen `contrato_actividad_plan` (su proyecto se deriva por la cadena de actividad).
Los otros 100 tienen puente `contrato_proyecto` pero no actividad.

| Grupo | # | `contrato_proyecto` | `contrato_actividad_plan` | Subgrupo derivable |
|---|---:|:--:|:--:|---|
| A (masa) | 100 | Sí | No | Sí (vía puente) |
| B (97-100) | 4 | No | Sí | Sí (vía actividad) |

Subgrupos derivados: Cultura(1)=95 · Infraestructura(37)=4 · Deporte(2)=1 ·
Seguridad(38)=4. Solo 6 contratos (ids 99-104) tienen `valor`.

### Acción de Javier (qué falta, sin proponer valores)
1. **`funcionario` — falta en 104/104 (CRÍTICO RBAC).** Pedir responsable por
   contrato a administración de contratos.
2. **Actividad — falta en 100/104.** Pedir actividad_plan + meta + concepto a
   planeación/presupuesto (sin ella el contrato no rueda al KPI).
3. **`valor`/`cdp_id` — 98/100 NULL.** Pedir a presupuesto (saldo = ΣCDP − Σcomp.).
4. **4 puentes faltantes (grupo B):** deuda de integridad interna; decidir con
   presupuesto si se normaliza `contrato_proyecto` o se acepta derivación por
   actividad como fuente única. No requiere dato externo.

---

## B-deuda-3 · Desfase `evento.subgrupo_id` vs `proyecto.subgrupo_id`

| Métrica | Cantidad |
|---|---:|
| Eventos totales | 52 |
| Con `actividad_plan_id` (en alcance) | 19 |
| **Desfases (`evento.subgrupo_id` ≠ `proyecto.subgrupo_id`)** | **0** |

Distribución (todos coinciden): Seguridad(38)=13 · Cultura(1)=5 · Deporte(2)=1.

**Inventario limpio hoy.** Acción = **monitoreo preventivo**, no corrección. (Aparte:
33 eventos sin `actividad_plan_id` y 1 con `subgrupo_id` NULL = deuda de captura,
no desfase.)

**Impacto del modelo:** el panel-subgrupo (B3) usa `evento.subgrupo_id` (operativo);
el rollup presupuestal usa la cadena del proyecto. Pueden divergir sin romper nada,
pero un desfase silencioso haría que un evento aparezca en el panel de un subgrupo y
sume presupuesto en otro → dejar verificación recurrente.

---

## Queries de verificación (read-only)

```sql
-- B-deuda-2
SELECT COUNT(*) FROM contrato;                                                    -- 104
SELECT COUNT(*) FROM contrato co WHERE NOT EXISTS
  (SELECT 1 FROM contrato_proyecto cp WHERE cp.contrato_id=co.id);                -- 4
SELECT COUNT(*) FROM contrato co WHERE NOT EXISTS
  (SELECT 1 FROM contrato_actividad_plan ca WHERE ca.contrato_id=co.id);          -- 100
SELECT COUNT(*) FROM contrato WHERE valor IS NULL;                                -- 98
SELECT COUNT(*) FROM contrato WHERE cdp_id IS NULL;                               -- 100
SELECT COUNT(*) FROM contrato WHERE funcionario IS NULL;                          -- 104

-- B-deuda-3 (debe dar 0 filas)
SELECT e.id, e.subgrupo_id AS ev_sg, p.subgrupo_id AS pr_sg, p.codigo
FROM evento e
JOIN actividad_plan ap ON ap.id = e.actividad_plan_id
JOIN proyecto p       ON p.id  = ap.proyecto_id
WHERE e.subgrupo_id IS DISTINCT FROM p.subgrupo_id
ORDER BY e.id;
```

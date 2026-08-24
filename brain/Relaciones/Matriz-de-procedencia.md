# Matriz de procedencia

De dónde sale cada campo del expediente. Medido sobre los **25 contratos**
(2026-08-24). Evidencia completa en
`docs/operacion/descubrimiento_completitud_expediente_2026-08-24.md`.

| Campo | Fuente | Modelo.campo | Hoy | Precargable | Editable | Quién |
|---|---|---|---|---|---|---|
| Número/tipo/vigencia | [[SECOP]] | `Contrato.contrato_*` | 25/25 | ya está | no | — |
| Objeto | [[SECOP]] | `Contrato.objeto` | 24/25 | **sí** | no | — |
| Valor | [[SECOP]] | `Contrato.valor` | 22/25 | **sí** | no | — |
| Fecha inicio/fin | [[SECOP]] | `Contrato.fecha_*` | 20/25 | **sí** | no | — |
| **Contratista** | [[SECOP]] | `Contrato.proveedor_id` | **0/25** | **sí** | no | — |
| CDP | interno | `Contrato.cdp_id` | 4/25 | parcial | sí | [[Subgrupo]] |
| **Etapa** | **ninguna** | `Contrato.etapa` | **0/25** | **no** | sí | Subgrupo |
| **Forma de pago** | **ninguna** | *no existe* | — | **no** | sí | Subgrupo |
| Plan de pago | [[SECOP]] | `SecopPlanPago` | 20/25 | **ya ingerido** | no | — |
| Ejecución financiera | [[SECOP]] | `valor_pagado` | 25/25 | **sí** | no | — |
| Ejecución técnica | interno | `Contrato.ejecucion` | 4/25 | ¿derivable? | sí | Subgrupo |
| Proyecto | interno | `ContratoProyecto` | 20/25 | no | sí | Subgrupo |
| Actividad | interno | `ContratoActividadPlan` | 5/25 | no | sí | Subgrupo |
| Metas | **derivada** | ver [[Contrato-Meta]] | 5/25 | derivada | no | — |
| Área ejecutora | [[SEGPLAN]] | `Dependencia` (provisional) | — | sí | no | — |

## Lo que dice esta tabla

**El mayor golpe de completitud no necesita un formulario.** Los 25/25
contratos tienen espejo en SECOP: de ahí salen 3 valores, 5 fechas, 1 objeto y
**25 contratistas**. Ver [[Precedencia-de-fuentes]].

**Lo único que de verdad no existe en ninguna parte es la forma de pago.**

Relacionado: [[Contrato]] · [[Mi-Area]] · [[Precedencia-de-fuentes]]

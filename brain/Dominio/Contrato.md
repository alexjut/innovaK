# Contrato

Tabla `contrato`, `managed=False`. **25 filas** (2026-08-24).

> [!bug] `contrato.id` no tiene secuencia
> Insertar exige el fallback `MAX(id)+1`. Deuda S5 conocida.

## Completitud medida (25 contratos)

| Campo | Tiene | Fuente que podría llenarlo |
|---|---|---|
| número/tipo/vigencia | 25/25 | [[SECOP]] |
| objeto | 24/25 | [[SECOP]] `objeto_contrato` |
| valor | 22/25 | [[SECOP]] `valor_contrato` |
| fecha inicio / fin | 20/25 | [[SECOP]] `fecha_*` |
| **contratista** | **0/25** | [[SECOP]] `proveedor` + `documento_proveedor` |
| cdp | 4/25 | interno |
| **etapa** | **0/25** | **ninguna** — se captura |
| ejecución (%) | 4/25 | interno |
| plan de pago | 20/25 | [[SECOP]] `secop_plan_pago`, ya ingerido |
| **forma de pago** | — | **el campo no existe en ninguna tabla** |

Los **25/25** tienen espejo en `secop_contrato`. La precarga es el mayor golpe
de completitud disponible y no necesita un solo formulario.

## Etapa contractual

Catálogo `EtapaContrato` (4 filas, DDL 010 **ya aplicado** el 2026-08-23):
Formulación · Ejecución · Liquidación · Sancionatorio.

> [!note] No se deriva de SECOP
> SECOP dice «Modificado» en 20 de nuestros 25 contratos, y eso significa que
> hubo **otrosí**, no una etapa. `etapa = NULL` significa «pendiente de
> registrar», nunca «Ejecución» por defecto.

Las tres columnas van juntas: `etapa`, `etapa_fecha`, `etapa_usuario_id`. Sin
fecha ni autor no hay auditoría, y sobre información contractual el dato no vale.

No se creó catálogo nuevo: `fase_proyecto` es de **proyecto**, tiene 3 filas y
meterle «Sancionatorio» habría contaminado un catálogo de otra cosa.

Relacionado: [[Contrato-Proyecto]] · [[Contrato-Meta]] · [[SECOP]] · [[CDP-CRP]]

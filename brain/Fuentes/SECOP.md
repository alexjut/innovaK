# SECOP II

Sistema oficial de contratación pública. Fuente **autoritativa** de lo
contractual: número, objeto, valor, fechas, contratista, pagos.

## Espejos en la BD (solo lectura, `managed=False`)

| Tabla | Filas | Qué trae |
|---|---|---|
| `secop_contrato` | **3.073** | contratos adjudicados de Kennedy |
| `secop_plan_pago` | **36.210** | pagos individuales; 4.889 contratos con referencia parseada |

Cobertura de **nuestros** 25 contratos: **25/25** con espejo, **20/25** con plan
de pago. Medido 2026-08-24.

## Lo que SECOP NO trae

- **Forma de pago.** `SecopContrato.modalidad` es modalidad de *contratación*
  (licitación, contratación directa…). No es lo mismo y no debe usarse como tal.
- **Etapa contractual.** `estado_contrato` dice «Modificado» en 20 de 25, que
  significa **otrosí**, no una etapa. Ver [[Contrato]].
- **CDP.** Ver [[CDP-CRP]].

## Dos trampas de la fuente, ya resueltas

1. **La pareja (contrato, pago) NO es única.** Cuatro pagos vienen dos veces con
   distinto aprobador. Se guardan ambos con `secuencia` y **sólo el primero
   suma**: sumarlos habría duplicado plata real.
2. **Las referencias vienen en 62 formatos**, con punto y con guion. El parseo
   se persiste en columnas (`ref_tipo`, `ref_numero`, `ref_vigencia`) en vez de
   repetirse en cada consulta. Las 1.097 que no parsean **se guardan y se
   cuentan**, nunca se descartan en silencio.

Relacionado: [[Contrato]] · [[Matriz-de-procedencia]] · [[Precedencia-de-fuentes]]

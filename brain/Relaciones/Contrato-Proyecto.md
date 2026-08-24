# Contrato ↔ Proyecto

Tabla `contrato_proyecto`. Es la vía **principal** por la que un [[Contrato]]
llega a un [[Subgrupo]]: contrato → proyecto → `proyecto.subgrupo_id`.

## Medido (2026-08-24)

- **20 filas**, 20 contratos distintos.
- Cardinalidad real hoy: **todos 1:1** (cada contrato, un proyecto).
- La tabla **admite N**: PK compuesta con `id BIGSERIAL` aparte. No asumir 1.

> [!info] El «24/25» del dashboard
> `contrato_proyecto` (20) ∪ [[Contrato-Meta|contrato_actividad_plan]] (5) = **24
> de 25**, cero contradicciones. **1 contrato** no llega por ninguna vía.
>
> Usar sólo la primera vía mandaba $2.117.962.446 de Seguridad a un cajón de
> «sin subgrupo». Por eso la atribución es la **unión** de las dos.

El contrato faltante se engancha desde [[Mi-Area]], no con un mapping a mano.

Relacionado: [[Contrato]] · [[Proyecto]] · [[Contrato-Meta]] · [[Mi-Area]]

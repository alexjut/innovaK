# CDP y CRP

**CDP** — Certificado de Disponibilidad Presupuestal: hay plata reservada.
**CRP** — Certificado de Registro Presupuestal: la plata quedó comprometida.

## Estado medido (2026-08-24)

- `Contrato.cdp_id`: **4 de 25**.
- SECOP **no** publica el CDP: se captura o se trae de otra fuente.

La cadena financiera con validación de saldo ya existe:

```
Proyecto → CDP → Contrato (valor ≤ saldo del CDP)
                    └→ ContratoActividadPlan (Σ ≤ valor del contrato)
```

> [!important] `$0` no es «sin dato»
> `$0` = sabemos que es cero. `Sin dato` = no hay información suficiente.
> **Nunca** convertir ausencia en cero. Medido en el dashboard: 21 celdas con
> cero real y 30 con null, cada una con su motivo.

Relacionado: [[Contrato]] · [[SECOP]]

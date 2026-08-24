# Contrato ↔ Meta

> [!danger] NO existe, y NO debe crearse
> La relación es **derivada** y su cardinalidad real es **N, no 1**.

## La cadena

```
Contrato → contrato_actividad_plan → ActividadPlan
         → actividad_indicador → Indicador → MetaProyecto → Meta
```

## La evidencia que cierra la discusión

Medido el 2026-08-24 sobre los 5 contratos que hoy llegan al plan:

| Contrato | Actividades | KPIs | **Metas distintas** | ¿Determinable? |
|---|---|---|---|---|
| 97 | 3 | 3 | **3** | ✗ |
| 98 | 7 | 7 | **7** | ✗ |
| 99 | 2 | 2 | **2** | ✗ |
| 100 | 2 | 2 | **2** | ✗ |
| 105 | 1 | 2 | **1** | ✓ |

Cuatro de cinco tocan varias metas. **Sólo uno** resuelve a una — y es el más
pequeño del sistema (Educación).

## Qué se hace con eso

- **No** crear tabla `contrato_meta`: un campo escalar sería una mentira
  estructural. Un contrato financia varias actividades que aportan a varios
  indicadores; eso es correcto, no un defecto del dato.
- **No** pedirle al usuario que elija «la» meta: obligaría a inventar una
  respuesta que no existe.
- **Sí** mostrar el **conjunto** de metas que ya se deriva. Cuando es una, se
  dice «✓ determinada automáticamente». Cuando son varias, se listan.

Relacionado: [[Contrato]] · [[Meta]] · [[Indicador]] · [[Actividad]]

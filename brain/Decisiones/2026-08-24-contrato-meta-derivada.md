# 2026-08-24 · La relación Contrato ↔ Meta se deriva, no se persiste

**Estado:** cerrada · **Evidencia:** medida sobre la BD

## Decisión

**No** se crea tabla `contrato_meta`. **No** se le pide al usuario que elija
«la» meta de un contrato.

## Por qué

La cardinalidad real es **N**. De los 5 contratos que llegan al plan, cuatro
tocan 3, 7, 2 y 2 metas distintas; **sólo uno** resuelve a una.

Un campo escalar sería una **mentira estructural**: un contrato financia varias
actividades que aportan a varios indicadores, y eso es correcto. Pedirle al
funcionario que elija una lo obligaría a inventar una respuesta que no existe.

## Qué se hace en su lugar

Mostrar el **conjunto** derivado. Cuando es una: «✓ determinada
automáticamente». Cuando son varias: se listan.

Detalle en [[Contrato-Meta]].

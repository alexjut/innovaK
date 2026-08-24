# Indicador (KPI)

`presu_indicador_meta_proyecto`. Cuelga de un `MetaProyecto`; una [[Meta]] puede
tener varios.

Se conecta a la ejecución por `ActividadIndicador` (`actividad_indicador`), que
enlaza [[Actividad]] ↔ Indicador. Ahí es donde un [[Contrato]] alcanza una
[[Meta]] — y por eso la alcanza en plural.

`tipo_agregacion`: SUMA / ULTIMO / PROMEDIO / MAX.

> [!note] Regla general vs. aporte de vigencia
> La meta del cuatrienio y lo que aporta **esta** vigencia son cifras distintas
> y se guardan aparte. No confundirlas al calcular avance.

Relacionado: [[Meta]] · [[Actividad]] · [[Contrato-Meta]]

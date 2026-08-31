# 2026-08-27 · La formulación no es una etapa del contrato

**Estado:** tomada · **Reemplaza a:** CLARIFY-2 de `specs/003`

## Decisión

**«En elaboración» y «Formulación» salen del ciclo de vida del contrato** y
pasan a un dominio propio, **FORMULACIÓN**, que vive entre [[Meta]] y la
contratación.

Una Meta tiene varias formulaciones. Cada una lleva su propio workflow, su
checklist configurable, su completitud y sus documentos, y termina —o no— en un
contrato.

## Por qué

Porque las dos ocurren **antes de que el contrato exista**. Un catálogo de
etapas del contrato que empieza por «el contrato todavía no existe» describe
otra cosa.

Y porque el modelo anterior obligaba a que el contrato naciera **sin número**:
una fila de `contrato` con `contrato_numero` NULL. Eso arrastraba un filtro
`contrato_numero IS NOT NULL` en los 17 sitios que suman dinero, dos CHECK de
equivalencia, y un DDL más. Con la formulación en su propia tabla, **un
contrato vuelve a ser siempre un contrato** y ese filtro deja de existir.

## Lo que costó comprobar

- **Ningún contrato usó nunca esas etapas**: `etapa_codigo` está NULL en los 25.
  Retirarlas no migra un solo dato.
- **No hay un literal 5 ni 1 cableado** como código de etapa en el backend: los
  dos endpoints validan contra el catálogo y el stepper compara `orden` de
  forma relativa. Salvo un `<select>` del frontend, que sí los congela.
- **La cardinalidad «una formulación → varios contratos» está probada con
  nuestros datos**: los 24 contratos conciliados salen de sólo 17
  `proceso_de_compra` distintos en [[SECOP]].
- **El área ya está formulando**: 13 de las 54 filas de `actividad_plan` no son
  actividades, son enunciados de formulación escritos en el único campo de
  texto que había a mano.

## Lo que NO se decidió acá

- Si la formulación cuelga de la Meta o de la actividad del plan.
- Si la completitud lleva peso por requisito — contradice
  [[2026-08-24-auditoria-antes-que-captura]] y la decisión de completitud plana
  del mismo día, y hay que reabrirla en vez de escribirla de lado.
- El catálogo definitivo de estados del contrato, que exige mirar el proceso
  institucional y no inventarlo.

El detalle, con la evidencia, en `specs/004-formulacion/plan.md`.

Relacionado: [[Contrato]] · [[Meta]] · [[SECOP]] · [[Precedencia-de-fuentes]]

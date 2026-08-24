# 2026-08-24 · La auditoría se diseña antes que los formularios

**Estado:** cerrada

## Decisión

La tabla de auditoría se diseña e implementa **antes** de abrir cualquier campo
de captura manual nuevo.

## Por qué

Hoy **no existe** auditoría genérica. Si los campos manuales nacen primero,
nacen sin rastro — y sobre información contractual un dato sin autor ni fecha no
se puede defender ante un ente de control.

Hay precedente de hacerlo bien: las tres columnas de etapa (`etapa`,
`etapa_fecha`, `etapa_usuario_id`) se crearon **juntas**, por este motivo.

Relacionado: [[Auditoria]]

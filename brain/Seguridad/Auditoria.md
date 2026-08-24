# Auditoría

## Qué hay hoy — poco

**No existe tabla de auditoría genérica.** Medido 2026-08-24. Lo que hay:

- **Columnas de rastro por campo**: `Contrato.etapa_fecha`,
  `Contrato.etapa_usuario_id`. Van junto al dato, y por eso el dato vale.
- `created_at` / `updated_at` sueltos en algunos modelos.
- `AuditoriaPertenencia` — es de **permisos**, no sirve para esto.

## Por qué se diseña ANTES que los formularios

Si nacen primero los campos manuales, nacen **sin rastro**. Y sobre información
contractual un dato sin autor ni fecha no vale: no se puede defender ante un
ente de control.

Ya hay un precedente que lo hizo bien: las tres columnas de etapa se crearon
**juntas** —valor, fecha, usuario— precisamente por eso.

## Qué debe registrar

```
quién · cuándo · valor anterior · valor nuevo · proyecto · contrato · fuente
```

`fuente` importa por [[Precedencia-de-fuentes]]: hay que poder distinguir «lo
escribió una persona» de «llegó de SECOP».

Relacionado: [[Scope-por-subgrupo]] · [[Precedencia-de-fuentes]] · [[Contrato]]

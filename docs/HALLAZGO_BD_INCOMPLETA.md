# Hallazgo crítico: BD incompleta para modelo SIPSE

## Fecha: 2026-04-20 (noche)

## Severidad: CRÍTICA (bloquea dashboard y reportes SIPSE)

## Descubrimiento

Al verificar el esquema real de BD para diseñar el refactor de
`crear_evento` con alimentación de avance de KPIs, se descubrió que la
estructura actual no soporta el modelo de negocio completo.

## Diagnóstico exhaustivo (verificado 2026-04-20 noche)

### Tabla `actividad_plan` — EXISTE

Columnas:

- `id` (bigint PK, `nextval('actividad_plan_id_seq')`).
- `proyecto_id` (bigint, NOT NULL, FK → `proyecto(id)` ON DELETE CASCADE).
- `actividad_id` (integer, nullable, FK → `actividad(id)`).
- `descripcion` (text, NOT NULL).
- `descripcion_ci` (text, nullable).

Índices:

- `actividad_plan_pkey (id)`.
- `idx_actividad_plan_proyecto (proyecto_id)`.
- `uq_actividad_plan (proyecto_id, descripcion_ci)`.
- `uq_actividad_plan_proy_act (proyecto_id, actividad_id)`.

FKs:

- `actividad_id` → `actividad(id)`.
- `proyecto_id` → `proyecto(id)` ON DELETE CASCADE.

**NO hay** columna `meta_id` ni `meta_proyecto_id`.

### Tabla `meta_proyecto` — EXISTE

Columnas: `id`, `meta_id`, `proyecto_id`.

FKs:

- `meta_id` → `metas(codigo)`.
- `proyecto_id` → `proyecto(id)`.

Sin relación con `actividad_plan`.

### Tabla `presu_indicador_meta_proyecto` — NO EXISTE

### Tabla `presu_avance_ind_periodo` — NO EXISTE

### No hay ninguna tabla que conecte actividad con meta

Búsqueda en `information_schema.tables` por patrones
`%actividad%meta%` y `%meta%actividad%`: cero resultados.

## Observación importante

Esta mañana (2026-04-20) el script 006 DDL creó índices sobre las
tablas `presu_indicador_meta_proyecto` y `presu_avance_ind_periodo`,
pero estas tablas NO existen en BD. Hay dos hipótesis:

- (a) Los comandos `CREATE INDEX` fallaron silenciosamente sin alertar.
- (b) El script 006 fue escrito especulativamente asumiendo tablas
  futuras.

**Pendiente de verificar con Alex** qué ocurrió.

## Impacto en el proyecto

1. El refactor de `crear_evento` puede avanzar para limpiar código y
   agregar `actividad_plan_id`, pero NO puede alimentar avance de
   KPIs.
2. El dashboard público no podrá mostrar cumplimiento de metas.
3. Los reportes a SIPSE tendrán datos incompletos.
4. La cadena operativa Proyecto→Meta→KPI→Actividad→Evento está
   truncada.

## Trabajo pendiente para resolver

### DDL de BD (coordinar con Alex)

- [ ] Crear tabla `presu_indicador_meta_proyecto` con columnas
      apropiadas.
- [ ] Crear tabla `presu_avance_ind_periodo` con columnas apropiadas.
- [ ] Decidir relación actividad-meta:
  - opción A: agregar FK `meta_proyecto_id` a `actividad_plan`.
  - opción B: crear tabla puente `actividad_meta`.
- [ ] Si aplica, agregar triggers o lógica de app para alimentar
      avance.

### Código (después de BD)

- [ ] Modelos Django nuevos (`Indicador`, `AvanceIndicador`).
- [ ] View `crear_evento` actualizado para alimentar avance.
- [ ] Endpoints API para el dashboard.
- [ ] Vistas de reporte.

### Estimación: 1 semana + coordinación con Alex

## Prioridad

ALTA — debe resolverse antes de completar el dashboard público o
cualquier reporte hacia la alcaldía / SIPSE. El refactor de
`crear_evento` puede avanzar parcialmente sin esto.

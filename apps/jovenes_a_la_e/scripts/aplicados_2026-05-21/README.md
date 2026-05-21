# DDL aplicado — 2026-05-21

## Script: `001_jovenes_setup.sql`

Crea el schema del módulo Jóvenes a la E (scope sólo BECAS).

**Backup pre-DDL:** `~/Proyectos/postgres/backups/poblacion_kennedy_pre_jovenes_20260521_093929.dump`.

### Cambios aplicados a `poblacion_kennedy`

- Tabla nueva `elemento_dotacion` (5 filas seed: kit académico, sostenimiento, matrícula, transporte, alimentación).
- Tabla nueva `entrega_beca` (BIGSERIAL, 30 columnas + UNIQUE(evento_id, numero_documento) + 5 índices + 2 FKs a `evento` y `persona`).
- Tabla nueva `entrega_beca_elemento` (puente M2M, PK compuesta).
- INSERT en `tipo_evento`: `JOVENES_BECA` con flags `permite_inscripcion=TRUE`, `permite_qr=TRUE`, `requiere_actividad_plan=TRUE`.

### Cambios NO aplicados (scope reducido vía decisión Alex 2026-05-21)

- ❌ NO se creó `sede_educativa`, `entrega_dotacion_sede`, `entrega_dotacion_elemento`.
- ❌ NO se creó `tipo_evento='JOVENES_DOTACION_SEDE'`.
- ✅ La dotación a sedes (convenio 955-2025, meta 23773) reusa el tipo `ENTREGA` ya existente en BD.

### Seeds ejecutados

```bash
docker exec innova_k python manage.py seed_jovenes_a_la_e
# Tipos de evento: 0 nuevos (de 1). Elementos: 0 nuevos (de 5).
# (todo ya estaba sembrado por el DDL — comando idempotente)

docker exec innova_k python manage.py seed_modulos
# Catálogo: 20 módulos sincronizados (1 nuevos).
# Asignación: 2 nuevas + 60 preexistentes.
# Caché de permisos invalidada (nueva versión: 225).
```

### Reversa

Ver bloque comentado al final de `001_jovenes_setup.sql`. Restaurar
backup `pre_jovenes_20260521_093929.dump` también funciona.

### Pendiente post-DDL (vía UI de presupuesto, no scripts)

1. Crear metas 23771 y 23772 + `meta_proyecto` ligado al proyecto Educación.
2. Crear los KPIs en `presu_indicador_meta_proyecto` (Acceso=700, Permanencia=700).
3. Crear `actividad_plan` para convenio 773-2025 + vincular a KPIs.
4. Crear evento de captura tipo `JOVENES_BECA` ligado a esa actividad_plan — el QR se genera al guardar.

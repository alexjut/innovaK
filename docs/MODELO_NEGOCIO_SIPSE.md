# Modelo de negocio: cadena Proyecto → Meta → KPI → Actividad → Evento

## Fecha: 2026-04-20 (noche)

## Descripción aportada por el usuario

```
Proyecto
  │
  │ tiene N
  ▼
Meta (con fecha_inicio, fecha_fin)
  │
  │ se mide por
  ▼
KPI / Indicador
  │
  │ se alimenta desde
  ▼
Actividad (necesaria para cumplir la meta)
  │
  │ tiene N
  ▼
Evento
  │
  │ suma avance directo al
  ▼
KPI de la meta correspondiente
```

## Puntos clave

1. Las metas tienen fechas (inicio y fin) que delimitan su vigencia.
2. Las metas se miden por sus KPIs (indicadores).
3. Las actividades existen para cumplir una meta específica.
4. Cada evento creado en innovaK debe sumar avance al KPI
   correspondiente.
5. El cálculo de cumplimiento de meta se hace sobre los avances de sus
   KPIs.

## Estado en la BD actual

Ver [`HALLAZGO_BD_INCOMPLETA.md`](./HALLAZGO_BD_INCOMPLETA.md) para
detalle de qué falta.

Esta cadena NO está completa en la BD hoy. Falta:

- Tabla de KPIs (`presu_indicador_meta_proyecto` no existe).
- Tabla de avances (`presu_avance_ind_periodo` no existe).
- Relación actividad ↔ meta.
- Mecánica de alimentar avance desde evento.

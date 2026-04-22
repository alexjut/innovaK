# Contexto SIPSE y su relación con innovaK

## Fecha: 2026-04-20

## ¿Qué es SIPSE LOCAL?

Sistema oficial de la Secretaría Distrital de Gobierno (Circular 14 del 1
de noviembre de 2018). Lo usan las 20 alcaldías locales de Bogotá para
gestionar los Fondos de Desarrollo Local (FDL).

## Estructura jerárquica oficial

```
Plan de Desarrollo Distrital (PDD) — "Bogotá Camina Segura 2024-2027"
└── Metas de Resultado del PDD
    └── Metas de Producto (MP) del PDD
        └── Plan de Desarrollo Local (PDL) — uno por alcaldía
            └── Proyectos de Inversión Local
                └── Metas del Proyecto de Inversión (MPI)
                    └── Indicadores/KPIs de la meta (mide cumplimiento)
                        └── Actividades (contribuyen al KPI)
                            └── Eventos/Instancias operativas (suman avance)
```

## Decisiones de negocio confirmadas 2026-04-20

1. "Proyecto interno" = Proyecto SIPSE (terminología coloquial).
2. Metas siempre son metas SIPSE (MPI).
3. innovaK es UNIDIRECCIONAL: consume IDs de SIPSE, NO reporta hacia atrás.
4. Los eventos operativos de innovaK deben alimentar directamente el
   avance del KPI de la meta correspondiente.

## Cadena operativa del negocio (según usuario 2026-04-20)

```
Proyecto
  │
  ├── Metas
  │     ├── fecha_inicio / fecha_fin (rango de vigencia)
  │     ├── KPIs/indicadores (cómo se mide cumplimiento)
  │     │     └── avances por período
  │     └── Actividades (necesarias para cumplir la meta)
  │           └── Eventos (cada evento suma avance al KPI)
```

## Valor operativo que innovaK agrega sobre SIPSE

- Georeferenciación de eventos.
- Colores por dependencia (UX).
- QR de inscripción.
- Registro de participantes.
- Dashboard público.
- Instancias como grupos de participantes (nuevo requisito).

## Fuentes consultadas

- https://www.ambientebogota.gov.co/web/intranet/sipse
- Manual SIPSE 2025 (Secretaría Distrital de Ambiente).
- Presentación SIPSE Local — Veeduría Distrital 2019.
- SDP — Programación y Seguimiento a la Inversión.

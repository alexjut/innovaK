# SIPSE — marco oficial y cadena de negocio en innovaK

> Documento de referencia conceptual. No cambia con el código —
> describe el marco institucional sobre el cual opera innovaK.
> **Última revisión:** 2026-04-29 (consolidado de CONTEXTO_SIPSE +
> MODELO_NEGOCIO_SIPSE).

---

## ¿Qué es SIPSE LOCAL?

Sistema oficial de la Secretaría Distrital de Gobierno
(Circular 14 del 1 de noviembre de 2018). Lo usan las 20 alcaldías
locales de Bogotá para gestionar los Fondos de Desarrollo Local (FDL).

innovaK **consume** IDs de SIPSE (proyectos, metas) pero **no reporta
hacia atrás**: el flujo es unidireccional. Lo que innovaK aporta sobre
SIPSE es el operativo del territorio: georreferenciación, QRs,
inscripciones, participantes, avances en tiempo real al KPI.

---

## Estructura jerárquica oficial

```
Plan de Desarrollo Distrital (PDD) — "Bogotá Camina Segura 2024-2027"
└── Metas de Resultado del PDD
    └── Metas de Producto (MP) del PDD
        └── Plan de Desarrollo Local (PDL) — uno por alcaldía
            └── Proyectos de Inversión Local
                └── Metas del Proyecto de Inversión (MPI)
                    └── Indicadores / KPIs de la meta
                        └── Actividades (contribuyen al KPI)
                            └── Eventos / Instancias operativas
                                  (suman avance al KPI)
```

---

## Cadena operativa del negocio en innovaK

```
Proyecto
  │
  │ tiene N
  ▼
Meta  (con fecha_inicio, fecha_fin)
  │
  │ se mide por
  ▼
KPI / Indicador
  │
  │ se alimenta desde
  ▼
Actividad  (necesaria para cumplir la meta)
  │
  │ tiene N
  ▼
Evento
  │
  │ suma avance directo al
  ▼
KPI de la meta correspondiente
```

### Reglas operativas

1. Las metas tienen fechas (inicio y fin) que delimitan su vigencia.
2. Las metas se miden por sus KPIs (indicadores).
3. Las actividades existen para cumplir una meta específica.
4. Cada evento creado en innovaK debe sumar avance al KPI
   correspondiente (vía `actividad_indicador` y
   `presu_avance_ind_periodo`).
5. El cálculo de cumplimiento de meta se hace sobre los avances
   acumulados de sus KPIs.

---

## Estado actual en la BD

La cadena está **completa e implementada** desde la sesión 2026-04-25/26:

- `meta_proyecto` — asocia proyecto a meta del catálogo `metas`.
- `presu_indicador_meta_proyecto` — KPIs de la meta (con
  `meta_magnitud` y `tipo_agregacion`).
- `actividad_indicador` — vínculo M:N entre `actividad_plan` y
  KPI (qué actividad aporta a qué indicador).
- `presu_avance_ind_periodo` — avances por período (`origen` =
  EVENTO / MANUAL / AJUSTE).
- `evento` — con campo `indicador` y `magnitud_aportada` para que cada
  evento alimente directo al KPI.

Vista 360° del proyecto:
`/presupuesto/proyectos/<id>/` muestra la cadena completa con barras
de avance por meta y KPI.

---

## Glosario rápido

| Sigla | Significado |
|-------|-------------|
| **SIPSE** | Sistema de Información para la Planeación, Seguimiento y Evaluación |
| **PDD** | Plan de Desarrollo Distrital |
| **PDL** | Plan de Desarrollo Local (uno por alcaldía) |
| **MP** | Meta de Producto (PDD) |
| **MPI** | Meta del Proyecto de Inversión |
| **FDL** | Fondo de Desarrollo Local |
| **KPI** | Key Performance Indicator (en innovaK = `Indicador`) |

---

## Valor operativo que innovaK agrega sobre SIPSE

- Georreferenciación de eventos sobre el mapa de Kennedy.
- Colores por dependencia / tipo de evento (UX visual).
- Generación automática de QR para inscripciones.
- Registro masivo de participantes.
- Dashboard público con avance en vivo de KPIs.
- Banco de Iniciativas Recreodeportivas (formularios públicos
  por convocatoria).
- Trazabilidad financiera: CDP → Contrato → Vinculación →
  ActividadPlan → Evento.

---

## Fuentes oficiales consultadas

- <https://www.ambientebogota.gov.co/web/intranet/sipse>
- Manual SIPSE 2025 (Secretaría Distrital de Ambiente).
- Presentación SIPSE Local — Veeduría Distrital 2019.
- SDP — Programación y Seguimiento a la Inversión.

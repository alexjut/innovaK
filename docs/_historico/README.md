# Histórico de docs

Planes ya ejecutados, hallazgos resueltos y snapshots temporales del
proyecto innovaK.

**Convención:** prefijo `YYYY-MM-DD_` con la fecha en que se generó
el doc original. Listables cronológicamente con `ls _historico/`.

Para recuperar contexto de cómo se llegó al estado actual, este es el
lugar. Si necesitas restaurar un doc al estado vivo, usa `git mv` para
sacarlo de aquí (no lo edites archivado — los archivados son
inmutables, salvo correcciones de typos).

---

## Índice cronológico

| Fecha | Archivo | Por qué se archivó |
|-------|---------|--------------------|
| 2026-04-22 | [`2026-04-22_hallazgo_bd_incompleta.md`](./2026-04-22_hallazgo_bd_incompleta.md) | Gap del schema reportado y resuelto en PR-D/PR-E (sesión 2026-04-25/26). |
| 2026-04-23 | [`2026-04-23_plan_demo_siembra.md`](./2026-04-23_plan_demo_siembra.md) | Plan de seed `DEMO_*` ejecutado: 10 proy + 20 metas + 34 KPIs + 55 eventos. |
| 2026-04-23 | [`2026-04-23_plan_redisenio_dashboard.md`](./2026-04-23_plan_redisenio_dashboard.md) | Hub principal y sub-hubs entregados en PR-C. Propuestas Power BI movidas a `propuestas/ux_pendiente.md`. |
| 2026-04-23 | [`2026-04-23_refactor_mapa_kennedy.md`](./2026-04-23_refactor_mapa_kennedy.md) | 12 fases del refactor del mapa ejecutadas en sesión 2026-04-23. |
| 2026-04-23 | [`2026-04-23_ux_inventario.md`](./2026-04-23_ux_inventario.md) | Snapshot temporal de URLs/templates/modelos. Reemplazado por `MAPA_APLICACION.md` con datos al 2026-04-29. |
| 2026-04-24 | [`2026-04-24_plan_integral_innovak.md`](./2026-04-24_plan_integral_innovak.md) | UX/hub/breadcrumb entregados en PR-A→PR-H4. Propuestas pendientes (a11y) movidas a `propuestas/ux_pendiente.md`. |
| 2026-04-24 | [`2026-04-24_refactor_crear_evento_analisis.md`](./2026-04-24_refactor_crear_evento_analisis.md) | Análisis ejecutado en PR-F (sesión 2026-04-25/26). |
| 2026-04-20 | [`2026-04-20_instancias_eventos.md`](./2026-04-20_instancias_eventos.md) | Idea inicial nunca implementada; el caso se cubrió con Beneficiarios/captura genérica. Sin modelo `Instancia` en el código. |
| 2026-04-23 | [`2026-04-23_formularios_por_tipo_evento.md`](./2026-04-23_formularios_por_tipo_evento.md) | Superada por el motor `captura_generica` (2026-06-09). |
| 2026-04-27 | [`2026-04-27_cronograma_semana.md`](./2026-04-27_cronograma_semana.md) | Cronograma de una semana ya transcurrida (snapshot). |
| 2026-05-27 | [`2026-05-27_fusion_kactivo_evento.md`](./2026-05-27_fusion_kactivo_evento.md) | Ejecutada: `apps/kactivo` fusionada en `login.Evento` y borrada (2026-05-27). |
| 2026-06-18 | [`2026-06-18_festivales_propuesta.md`](./2026-06-18_festivales_propuesta.md) | Ejecutada: `apps/festivales/` existe. El manual vivo está en `manuales_modulos/festivales.md`. |
| 2026-06-11 | [`2026-06-11_retiro_templates_django.md`](./2026-06-11_retiro_templates_django.md) | Plan de retiro de templates ya ejecutado (Lotes 1-7, full-Angular en producción). La limpieza residual (CSS/views) vive en `arquitectura/DEUDA_TECNICA.md` §Limpieza post full-Angular. |
| 2026-05-08 | [`2026-05-08_banco_iniciativas_v2.md`](./2026-05-08_banco_iniciativas_v2.md) | Propuesta v2 del Banco: DDL aplicado (`scripts/aplicados_2026-05-08/`) y superada por los Lotes 2/3/4 y la rúbrica v4. El único residuo vivo (soporte legal opcional) quedó en `DEUDA_TECNICA.md` **B6**. |
| 2026-06-11 | [`2026-06-11_migracion_html_angular.md`](./2026-06-11_migracion_html_angular.md) | Inventario de la migración HTML→Angular. Cerrada: quedan 3 templates y 1 vista que renderiza (el kiosko de votación). El doc mapeaba 171 URLs que ya no existen. |
| 2026-07-06 | [`2026-07-06_onboarding_kenny.md`](./2026-07-06_onboarding_kenny.md) | Propuesta del onboarding: ejecutada. `apps/onboarding/` en producción desde `1741dd8`. El doc seguía diciendo "sin implementar". |
| 2026-07-08 | [`2026-07-08_estratificacion_ideca_plan.md`](./2026-07-08_estratificacion_ideca_plan.md) | Plan por PRs de la estratificación IDECA. PR-0..PR-6 en producción. Se archiva por el **porqué**: R1 (PostGIS vetado sobre la BD compartida) y el fallback shapely, que siguen rigiendo el diseño geo. |
| 2026-07-09 | [`2026-07-09_estratificacion_runbook_ddl.md`](./2026-07-09_estratificacion_runbook_ddl.md) | Runbook del DDL de estratificación: ejecutado el 2026-07-09 (18.929 manzanas, 241 sedes). Valor histórico: registra sus propias correcciones (`pg_dump` por TCP no pasa `pg_hba`; `compose up --build` era un no-op). |
| 2026-07-16 | [`2026-07-16_estratificacion_ideca_estado.md`](./2026-07-16_estratificacion_ideca_estado.md) | Registro de estado de la estratificación (diario). Todo lo técnico quedó en producción. Lo vivo se extrajo a `DEUDA_TECNICA.md` **D1-D4** y **G8**. Contiene el procedimiento de rebuild de la imagen (§4-ter). |
| 2026-07-16 | [`2026-07-16_handoff_banco_estratificacion.md`](./2026-07-16_handoff_banco_estratificacion.md) | Handoff de sesión, ejecutado el mismo día (PR-A rúbrica v4 en producción, 24/24 recalculadas). Lo vivo se extrajo a `DEUDA_TECNICA.md` **B7/B8/R2**. |
| 2026-07-16 | [`2026-07-16_rbac_dashboard_ia_scope_fix.md`](./2026-07-16_rbac_dashboard_ia_scope_fix.md) | Reporte del fix de RBAC en el motor de consulta de beneficiarios (`01c573c`, en producción). El único doc de la auditoría 2026-07-16 sin una sola afirmación falsa. |

> **Auditoría 2026-07-16.** La revisión completa de la documentación
> (58 docs verificados contra el código, ~90 afirmaciones falsas) está en
> [`../propuestas/orden_documentacion_2026-07-16.md`](../propuestas/orden_documentacion_2026-07-16.md).

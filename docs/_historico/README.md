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

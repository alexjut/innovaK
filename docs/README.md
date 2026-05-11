# Documentación — innovaK

Sistema de información interno de la **Alcaldía Local de Kennedy**
(Bogotá). Django 4.2 + PostgreSQL externa + Docker.
Owner: Alex (`alexjut`).

Esta carpeta contiene la documentación curada del proyecto. Los detalles
operativos (convenciones, comandos, flujo git, decisiones tomadas,
bitácora de sesiones) viven en [`/CLAUDE.md`](../CLAUDE.md) en la raíz
del repo.

---

## 📌 Operativos (consulta diaria)

| Doc | Para qué sirve |
|-----|----------------|
| [`../CLAUDE.md`](../CLAUDE.md) | Convenciones, flujo git, decisiones, bitácora de sesiones. Lo que toda sesión nueva lee primero. |
| [`ARQUITECTURA.md`](./ARQUITECTURA.md) | Visión de alto nivel: stack, apps, modelos, despliegue. |
| [`MAPA_APLICACION.md`](./MAPA_APLICACION.md) | Mapa exhaustivo de URLs, vistas, modelos, flujos críticos y cobertura de tests. Snapshot vigente. |
| [`DEUDA_TECNICA.md`](./DEUDA_TECNICA.md) | Lista de deuda **activa** organizada por categoría operativa (🔴 bugs / 🟡 convenciones / ⏳ bloqueadas). |
| [`MEJORAS_FUTURAS.md`](./MEJORAS_FUTURAS.md) | Mejoras escaladas (alcance mínimo/medio ya entregado, plan alta opcional). No son deuda — son roadmap. |
| [`_historico/cronograma_deuda.md`](./_historico/cronograma_deuda.md) | Histórico cronológico de los ítems de deuda cerrados. |
| [`ANALISIS_VALOR.md`](./ANALISIS_VALOR.md) | Análisis crítico del valor del software, riesgos y foco recomendado. Para mostrar a stakeholders. |

## 📚 Referencia (información estable)

| Doc | Para qué sirve |
|-----|----------------|
| [`referencia/SIPSE.md`](./referencia/SIPSE.md) | Marco oficial SIPSE de la Secretaría Distrital de Gobierno + cadena de negocio Proyecto→Meta→KPI→Actividad→Evento. |
| [`referencias-institucionales/`](./referencias-institucionales/) | PDFs oficiales de la Alcaldía (cuestionarios, manuales). |

## 🚧 Propuestas (vivas, sin ejecutar)

| Doc | Estado |
|-----|--------|
| [`propuestas/instancias_eventos.md`](./propuestas/instancias_eventos.md) | Modelo de "instancias" (grupos de participantes). 7 decisiones técnicas pendientes con Alex. |
| [`propuestas/formularios_por_tipo_evento.md`](./propuestas/formularios_por_tipo_evento.md) | Patrón de formularios dinámicos por `tipo_evento` (ENTREGA, CURSO, CAPACITACION pendientes). |
| [`propuestas/ux_pendiente.md`](./propuestas/ux_pendiente.md) | 3 propuestas UX consolidadas: WCAG 2.2 AA, árbol presupuestal D3.js, "Tableros de Control". |

## 🗄 Histórico

[`_historico/`](./_historico/) — planes ejecutados, hallazgos resueltos
y snapshots temporales. Conservados para entender cómo se llegó al
estado actual. Ver [`_historico/README.md`](./_historico/README.md)
para índice cronológico.

---

## Convenciones de documentación

- **Markdown puro**, sin extensiones de wiki ni Mermaid pesado.
- **Español en todo** (excepción: nombres técnicos y citas de código).
- Cada doc operativo lleva **fecha de última revisión** en el encabezado.
- Si un doc deja de ser vigente, se mueve a `_historico/` con prefijo
  `YYYY-MM-DD_`. **No se borra** (preserva contexto histórico).
- **Nuevos docs** entran a la carpeta que corresponda según la regla:
  - Raíz = vivo + consultado a diario.
  - `referencia/` = estable, no cambia con el código.
  - `propuestas/` = aún no construido.
  - `_historico/` = hecho o descartado.

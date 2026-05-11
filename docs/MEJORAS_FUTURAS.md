# Mejoras escaladas pendientes — innovaK

Ítems con alcance **mínimo / medio** ya entregado en producción. Las
versiones "alta" quedan como roadmap opcional, sin compromiso de fecha.

> No son deuda técnica activa: son iteraciones de producto. La deuda
> real vive en [`DEUDA_TECNICA.md`](./DEUDA_TECNICA.md). El histórico
> cerrado en [`_historico/cronograma_deuda.md`](./_historico/cronograma_deuda.md).

---

## N17 — Consulta Inteligente avanzada

`/dashboard/consulta-inteligente/` solo consulta `login_persona`. La meta
es que cruce Evento, Asistencia, Inscripción, Caracterización, Banco y
Contratos.

| Alcance | Estado | Esfuerzo | Detalle |
|---------|--------|----------|---------|
| Mínimo | ✅ aplicado 2026-05-11 (`d81c98e`) | — | UI con 8 ejemplos clickables + `FIELD_MAPPING` expandido a ~70 sinónimos coloquiales (edad, víctimas, migrantes, lgbt, oficio, salario, vivienda). |
| Media | ⏳ abierto | ~1 semana | Habilitar 5 modelos nuevos (Evento, Asistencia, Inscripción, Caracterización, Banco) + `QueryType.AGGREGATE` y `QueryType.JOIN` + selector de tipo de gráfica en UI. |
| Alta | ⏳ abierto | 2-4 semanas | Text-to-SQL real con `gpt-4o`, exports CSV/Excel, gráficas configurables, comparaciones cruzadas y serie temporal. |

**Cuándo se debería abordar:** cuando un usuario pida una pregunta concreta
que NO se pueda responder con el alcance actual y el costo de
implementación se justifique frente a una consulta SQL puntual de Alex.

---

## N18 — Sub-mapas por subgrupo de Inversión Local

Mapa Kennedy con 17 subgrupos (`dep_id=3`). El sidebar tenía solo un
multiselect plano; la idea es que cada subgrupo tenga UX dedicada.

| Alcance | Estado | Esfuerzo | Detalle |
|---------|--------|----------|---------|
| Mínimo | ✅ aplicado 2026-05-11 (`9da7099`) | — | Barra de 18 pestañas (Todos + 17 subgrupos) encima del mapa. Click → filtra eventos + capa Escuelas + capa Lugares según el subgrupo. |
| Media | ✅ aplicado 2026-05-11 (`e1fdee6`) | — | KPIs inline al hacer click ("X eventos · Y próximos · Z ejecutados") + persistencia `LocalStorage` (recuerda la última pestaña entre cargas). |
| Alta | ⏳ abierto | 3-4 días | URLs propias `/geo/mapa-kennedy/subgrupo/<id>/` con color/leyenda/zoom propios + back-link al mapa general + breadcrumb. |

**Cuándo se debería abordar:** cuando emerja un caso concreto (ej.
"quiero compartir el mapa de Mujer en una reunión con un link directo")
o cuando un subgrupo tenga suficientes capas específicas que justifiquen
una vista dedicada.

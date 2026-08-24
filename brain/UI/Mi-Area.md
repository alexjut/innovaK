# Mi Área

`/app/mi-area/<slug>` — el punto operativo de cada [[Subgrupo]].

```
AREA_ROUTES → AreaPanelComponent
  → GET /presupuesto/api/areas/<slug|id>/panel/  (AreaPanelView)
  → apps/presupuesto/services/panel_area.py
```

## El ancla, que ya es la correcta

`panel_area` deriva todo de **`proyecto.subgrupo_id`**, no de
`evento.subgrupo_id`.

> [!info] Por qué se cambió
> El panel anterior derivaba todo del evento. Funcionaba para las áreas que
> capturan eventos y **escondía** a las que no: Deporte tenía 24 actividades del
> plan y UN evento; Educación e Infraestructura tenían contratos y CERO eventos.
> Sus paneles salían en blanco. Un panel que dice «no hay nada» cuando hay 24
> actividades planeadas no está vacío: **está mintiendo**.

## Lo que ya existe y hay que reutilizar

| Pieza | Qué hace |
|---|---|
| `panel_area(subgrupo_id)` | Área → Proyectos → Metas/KPI → Actividades → Contratos + Eventos |
| **`sueltos`** | expone lo NO enganchado, con `n`, `de`, `que_significa` e `items` |
| `VincularContratoActividadPlanView` | engancha contrato ↔ actividad desde la propia pantalla |
| `resolver_area(slug\|id)` | 45 slugs, cero colisiones; acepta id para no romper enlaces viejos |

`sueltos` **ya es** «pendientes», pero a nivel de RELACIONES. Lo que falta es
completitud a nivel de **campo por contrato**. Ver [[Matriz-de-procedencia]].

## Qué NO debe mostrar

Es pantalla de funcionario, no de diagnóstico. Nunca «falta DDL», «la tabla
contrato tiene 18 columnas» ni «CRP tiene 0 filas». Se dice **`Sin dato`** o
**`Pendiente por diligenciar`**. Ver [[Dashboard-360]].

Relacionado: [[Subgrupo]] · [[Contrato]] · [[Scope-por-subgrupo]] · [[Dashboard-360]]

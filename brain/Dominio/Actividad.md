# Actividad

> [!danger] «Actividad» nombra DOS cosas distintas
> - **`ActividadPlan`** (`actividad_plan`) — la actividad del PLAN, la que
>   cuelga del proyecto. Es la que importa en la cadena presupuestal.
> - **`ActividadContrato`** (`contrato_actividad`) — puente al catálogo de 74
>   filas. **No** es la misma.
>
> La puente correcta hacia el plan es **`contrato_actividad_plan`**. El nombre
> viejo `VincularContratoActividadView` inducía a leer la puente equivocada.
> Ver `docs/GLOSARIO.md`.

`ActividadPlan` → `ActividadIndicador` → [[Indicador]] → [[Meta]].

También: `Evento.actividad_plan_id` — un evento ejecutado suma avance al KPI de
su actividad.

Relacionado: [[Contrato-Meta]] · [[Indicador]] · [[Mi-Area]]

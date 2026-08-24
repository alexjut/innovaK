# Subgrupo

La unidad operativa. En la interfaz se llama **Área** («Mi Área»).

> [!warning] «Área» nombra dos cosas
> - **Dependencia / Subgrupo** — lo vivo, lo que usa el sistema.
> - Catálogo `Area` de PLANIG — 10 filas, muerto.
>
> Agrupar «por área» significa agrupar por **subgrupo**.

## Medido (2026-08-24)

- **45 subgrupos** en total.
- **8 tienen proyectos**, y por tanto plan:

| id | Subgrupo | Proyectos |
|---|---|---|
| 38 | Seguridad | 3 |
| 37 | Infraestructura | 2 |
| 1 | Cultura | 2 |
| 9 | CPS y Planta | 1 |
| 6 | Subsidio tipo C | 1 |
| 8 | **Educación** | 1 |
| 2 | Deporte | 1 |
| 7 | Relacionamiento Interinstitucional | 1 |

Los otros 37 no tienen plan: no es que su panel esté roto.

## Cómo se ancla

El área de cualquier cosa se sabe por `proyecto.subgrupo_id`, **no** por
`evento.subgrupo_id`. Ver [[Mi-Area]] — ese cambio de ancla fue lo que sacó a
Educación e Infraestructura de un panel en blanco.

El slug de la URL (`educacion`) lo resuelve `resolver_area()`; acepta slug o id.
45 slugs distintos, cero colisiones.

Relacionado: [[Proyecto]] · [[Scope-por-subgrupo]] · [[Mi-Area]]

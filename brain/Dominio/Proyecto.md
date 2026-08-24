# Proyecto

Raíz de la cadena presupuestal. Cuelga de un [[Subgrupo]] por `proyecto.subgrupo_id`.

> [!danger] El identificador canónico es `id`, no `codigo`
> `2784` es el **código** del proyecto con `id=2802`. En `2788` los dos
> coinciden, así que el error se ve intermitente y por eso sobrevivió. Hay test
> que lo fija.

## Cadena

```
Subgrupo → Proyecto → Meta → Indicador (KPI)
              └────→ Contrato
```

`Proyecto → ActividadPlan → ActividadIndicador → Indicador → MetaProyecto → Meta`

> [!warning] `metas.proyecto_id` está NULL en las 24 filas
> Columna de enganche muerta. El vínculo real va por `meta_proyecto`.

## Ejemplo vivo

Educación tiene **un** proyecto: `id=2805`, `codigo=0002377`,
«Kennedy Germinando Futuros», con **1 actividad del plan** y **1 contrato**.

Relacionado: [[Contrato]] · [[Meta]] · [[Contrato-Proyecto]]

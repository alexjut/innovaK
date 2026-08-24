# Permisos y roles

Sistema **dinámico**, no cableado: `modulo` + `rol_modulo` + `rol_meta`, con
caché en Redis versionada (un `INCR` invalida todo — O(1)).

```python
@modulo_required("presupuesto_proyectos")   # ✅ el vigente
@group_required("Admin")                    # ❌ retirado 2026-05-04
```

- **19 módulos** en el catálogo (`seed_modulos`).
- Bypass: `is_superuser` siempre pasa.
- Sólo el rol **Admin** está protegido (no se puede desactivar ni quedarse sin
  usuarios).

## Dos capas distintas, no confundirlas

| | Qué controla | Dónde |
|---|---|---|
| **Módulo** | *qué pantalla* puede abrir | `@modulo_required` |
| **Scope** | *sobre qué datos* puede actuar | `subgrupos_visibles()` |

Tener el módulo `presupuesto_proyectos` **no** da derecho a tocar los contratos
de otra área. Ver [[Scope-por-subgrupo]].

> [!warning] El prefijo `Coordinador` da poder de creación
> Cualquier grupo cuyo nombre **empiece** por `Coordinador` obtiene poder de
> creación en su área (`es_coordinador` / `puede_crear_en_area`). **Nunca**
> nombrar así a un rol de solo lectura: entraría a los flujos de creación sin
> querer.

Relacionado: [[Scope-por-subgrupo]] · [[Mapa-del-sistema]]

# Scope por subgrupo

Educación sólo modifica Educación. Cultura sólo Cultura.

```python
subgrupos_visibles(user) -> set[int] | None
#  None      = ve todo (superuser)
#  set()     = no ve nada → deny
#  {8, 37}   = esos subgrupos
```
`apps/login/services/scope.py`

## La regla

> **La autorización se valida en el backend, siempre.** Ocultar un botón no es
> autorizar: el usuario manda la petición que quiera.

## Hueco abierto (2026-08-24)

`VincularContratoActividadPlanView` (`api/views.py`) valida que la **actividad**
sea del área:

```python
proyecto_ids = set(Proyecto.objects.filter(subgrupo_id=subgrupo_id)...)
if act is None or act.proyecto_id not in proyecto_ids: → 400
```

…pero **`contrato_id` entra crudo al `get_or_create`**, sin comprobar que el
contrato pertenezca al área. Un usuario de Educación puede enganchar un
[[Contrato]] de Seguridad a su plan cambiando un id en la petición.

**Hay que cerrarlo antes de abrir más escritura desde [[Mi-Area]].** Es
exactamente el caso «no confiar en ocultar botones por frontend».

Relacionado: [[Mi-Area]] · [[Contrato]] · [[Auditoria]]

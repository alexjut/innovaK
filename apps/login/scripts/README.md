# Scripts SQL del módulo `login` / sistema de roles

| Script | Aplicado | Descripción |
|---|---|---|
| `001_n15_setup.sql` | 2026-04-30 | N15 PR-1: 3 tablas nuevas (`modulo`, `rol_modulo`, `rol_meta`) + rename grupo `lider participacion` → `LiderParticipacion` + seed `rol_meta` para 7 grupos (Admin protegido). |
| `001_n15_setup_rollback.sql` | — | Rollback del 001 (no usado). |
| `002_n15_fix_usuario_grupos_unique.sql` | 2026-04-30 | Hotfix: borra duplicados en `usuario_grupos` y agrega `UNIQUE(usuario_id, group_id)`. Detectado al ver "alexjut" 3 veces en el rol Admin. |

**Backup pre-N15**: `~/Proyectos/postgres/backups/poblacion_kennedy_pre_n15_20260430_171530.dump`

**Catálogo `modulo` y asignación `rol_modulo`** se siembran con management command idempotente:

```bash
docker exec innova_k python manage.py seed_modulos
```

Re-ejecutarlo es seguro (usa `update_or_create` para módulos y
`get_or_create` para asignaciones).

**Escotillas de emergencia**:

- Superuser bypassea todo (`is_superuser=True` siempre pasa `@modulo_required`).
- Reset programático si Admin queda sin acceso:
  ```python
  from apps.login.services.permisos import reset_modulos_admin
  reset_modulos_admin()
  ```

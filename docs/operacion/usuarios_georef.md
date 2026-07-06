# Usuarios de Deportes / georeferenciación

> Acceso al aplicativo (incluye el mapa de georeferenciación, módulo
> `mapa_kennedy`). Login en `/app/auth/login`.
>
> ⚠️ **Las contraseñas NO van en este archivo** (es versionado en git). Las
> temporales se generan al crear las cuentas y quedan en el archivo
> **gitignored** `credenciales_georef.local.txt` (raíz del proyecto): ábrelo,
> entrégalas **por canal seguro**, y **bórralo**. Cada usuario debe cambiar su
> clave en `/perfil/cambiar-password/` al ingresar.

## Cuentas

| Nombre | Cédula | CPS | Usuario | Rol | Scope | Acceso georef |
|--------|--------|-----|---------|-----|-------|---------------|
| Daniel Hernando Lugo Jaramillo | 1018474432 | CPS-085-2026 | `daniel.lugo` | CoordinadorDeportes | subgrupo Deporte | ✅ (ya existía) |
| Miguel Ángel Arias Moreno | 1030553666 | CPS-353-2026 | `miguel.arias` | Lider_contrato | subgrupo Deporte | ✅ |

- **Daniel**: ya tenía cuenta (`daniel.lugo`) con acceso a georef vía
  CoordinadorDeportes → no se modifica. Si olvidó su clave, un admin la resetea
  (`crear_usuarios_georef --reset-daniel --apply` o por Django admin).
- **Miguel**: líder de un segundo proyecto de Deportes. Rol `Lider_contrato`
  (incluye `mapa_kennedy`, eventos, banco, presupuesto_proyectos, etc.), con
  scope de subgrupo **Deporte** (ve todo lo de Deporte, no solo su proyecto —
  el aislamiento por proyecto no existe hoy en el RBAC).

## Cómo se crean / re-ejecutan

Idempotente (match por cédula, no duplica):

```bash
# Vista previa sin escribir nada:
docker exec innova_k python manage.py crear_usuarios_georef

# Crear/asignar de verdad (genera la temporal de Miguel):
docker exec innova_k python manage.py crear_usuarios_georef --apply

# Opcional: resetear también la clave de daniel.lugo:
docker exec innova_k python manage.py crear_usuarios_georef --apply --reset-daniel
```

## Gestión de contraseñas (admins)

- **Reset si la olvidan**: Django admin (`/admin/`, usuario → cambiar
  contraseña) o re-correr el command con `--reset-daniel` (o extenderlo para
  Miguel). El admin nunca ve la clave que el usuario fija después.
- **"Forzar cambio al primer ingreso"** NO está implementado de forma nativa
  en la plataforma; hoy la temporal funciona hasta que el usuario la cambia
  voluntariamente. Convertirlo en obligatorio sería una mini-feature aparte
  (flag `must_change_password` + check en el login/SPA).

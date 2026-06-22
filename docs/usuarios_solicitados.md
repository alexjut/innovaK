# Usuarios solicitados — innovaK / KennedyConecta

> Registro de las personas que cada área ha **solicitado** dar de alta en la
> plataforma, con sus datos oficiales, el **rol** que se les asignará y el
> **estado**. Sirve de trazabilidad antes de crear los usuarios.
>
> Roles acotados: cada usuario ve **solo su área** + el mapa + lo público.
> (Catálogo de roles: ver `seed_modulos.ASIGNACION_INICIAL`.)

Última actualización: 2026-06-22.

---

## Estado de creación

| # | Nombre | Cédula | Contrato | Área | Rol a asignar | Estado |
|---|--------|--------|----------|------|---------------|--------|
| 1 | Angélica del Pilar Fernández Acero | 35.533.059 | CPS-140-2026 | **Cultura** | `Coordinador` (solo Cultura) | ✅ Creado — usuario `angelica.fernandez` |

> Leyenda estado: ⏳ Por crear · ✅ Creado · 🔑 Creado + clave entregada.

---

## 1 · CULTURA

### 1.1 Angélica del Pilar Fernández Acero
- **Cédula:** 35.533.059
- **Contrato:** CPS-140-2026
- **Usuario creado:** `angelica.fernandez` · **Rol:** `Coordinador` (rol de
  Cultura). Clave temporal entregada por canal seguro (NO se guarda en el
  repo); la cambia en **Mi Perfil → Cambiar contraseña**.
- **Alcance (solo Cultura):** Mapa, Festivales (proyecto 2780), Cursos,
  Asistencia, Caracterización, Consulta IA, Registro de personas. **No** ve
  Presupuesto, Banco, Infraestructura ni Votaciones.
- **Capacitación:** solicitó espacio de capacitación sobre el manejo de la
  plataforma (agendar).
- **Solicitud original (oficio):**

  > De manera respetuosa, solicito su valioso apoyo para la creación de mi
  > usuario de acceso a la plataforma de Georreferenciación, con el fin de
  > desarrollar las actividades propias de mi contrato en el área de Cultura.
  > Nombre: Angélica del Pilar Fernández Acero · Cédula: 35.533.059 ·
  > Contrato: CPS-140-2026. De igual manera, agradezco si es posible programar
  > un espacio de capacitación sobre el manejo y funcionamiento de la
  > plataforma.

---

## 2 · INFRAESTRUCTURA

> Pendiente: el área debe enviar sus responsables (ver el correo de solicitud
> en `docs/MANUAL_INFRAESTRUCTURA.md`). Roles previstos:
> - **`LiderInfraestructura`** — administra contratos de obra, insights, reportes.
> - **`SeguimientoInfraestructura`** — registra el avance (cortes con evidencia);
>   no crea ni borra estructura.

| Nombre | Cédula | Contrato | Rol a asignar | Estado |
|--------|--------|----------|---------------|--------|
| _(pendiente de envío del área)_ | | | `LiderInfraestructura` | — |
| _(pendiente de envío del área)_ | | | `SeguimientoInfraestructura` | — |

---

## Procedimiento de creación (referencia interna)

1. Verificar si la **persona ya existe** (por documento) — si existe, se reusa.
2. Crear **Usuario** vinculado a la Persona (username sugerido:
   `nombre.apellido`), con clave temporal.
3. Asignar el **rol** de la tabla (grupo + módulos via roles admin).
4. Entregar usuario + clave temporal; la persona la cambia en **Mi Perfil →
   Cambiar contraseña**.
5. Marcar el estado en este documento.

# Documentación — innovaK / KennedyConecta

Sistema de información interno de la **Alcaldía Local de Kennedy** (Bogotá).
Django 4.2 + PostgreSQL externa + Angular + Docker. Owner: Alex (`alexjut`).

Los detalles operativos (convenciones, comandos, flujo git, decisiones,
bitácora) viven en [`/CLAUDE.md`](../CLAUDE.md). Esta carpeta está organizada
por temas; abajo el índice maestro.

> **¿Recién llegas?** → [`GETTING_STARTED.md`](GETTING_STARTED.md) (arranque
> local) y [`GLOSARIO.md`](GLOSARIO.md) (vocabulario de dominio). La puerta de
> entrada general es el [`/README.md`](../README.md) del repo.

---

## 📁 Estructura

| Carpeta / archivo | Qué contiene |
|---------|--------------|
| [`GETTING_STARTED.md`](GETTING_STARTED.md) | Arranque local paso a paso (Docker, `.env`, build Angular). |
| [`GLOSARIO.md`](GLOSARIO.md) | Vocabulario de dominio (SIPSE, Meta/KPI, CDP, subgrupo, roles…). |
| [`arquitectura/`](arquitectura/) | Arquitectura del sistema, deuda técnica, mapa de la aplicación. |
| [`infra/`](infra/) | Despliegue (dossier Kubernetes) y artefactos de referencia. |
| [`frontend/`](frontend/) | Plan de frontend, Angular, despliegue, migración HTML→Angular, retiro de templates. |
| [`manuales_modulos/`](manuales_modulos/README.md) | Manual por **módulo** (cómo funciona cada flujo). |
| [`manuales_uso/`](manuales_uso/README.md) | Manual por **área/rol**, entregado a cada usuario. |
| [`propuestas/`](propuestas/) | Propuestas y diseños (algunas pendientes de decisión). |
| [`informes/`](informes/) | Informes, análisis de valor, cronogramas, mejoras futuras. |
| [`referencia/`](referencia/) | Marcos de referencia (SIPSE, etc.). |
| [`referencias-institucionales/`](referencias-institucionales/) | Documentos institucionales originales (PDFs). |
| [`_historico/`](_historico/README.md) | Planes y diagnósticos ya ejecutados (archivo). |

Archivos en la raíz:
- `usuarios_solicitados.local.md` — registro de usuarios. **No versionado** (no se versiona: tiene cédulas y contratos de personas reales, y el repo es público (Ley 1581). Vive en la máquina del admin, gitignored por `*.local.md`).
  solicitados/creados por área (datos, rol, estado).

---

## 🗂️ Atajos por tema

**Arquitectura y estado técnico**
- [arquitectura/ARQUITECTURA.md](arquitectura/ARQUITECTURA.md) — fuente de verdad del sistema.
- [arquitectura/MAPA_APLICACION.md](arquitectura/MAPA_APLICACION.md) — mapa de URLs, vistas, modelos, tests.
- [arquitectura/DEUDA_TECNICA.md](arquitectura/DEUDA_TECNICA.md) — deuda activa priorizada.
- [arquitectura/diagnostico_ciclo_planeacion.md](arquitectura/diagnostico_ciclo_planeacion.md) — qué del ciclo Plan→Proyecto→Vigencia→Meta→CDP→CRP→Contrato→Ejecución existe hoy, medido (2026-08-26).

**Frontend**
- [frontend/FRONTEND_ANGULAR.md](frontend/FRONTEND_ANGULAR.md) — cómo se trabaja
  el frontend hoy. El plan por etapas de mayo de 2026 (camino híbrido con
  Angular "condicional") **se archivó el 2026-08-06** en
  [`_historico/2026-05_plan_frontend.md`](_historico/2026-05_plan_frontend.md):
  ya se ejecutó, y mantenerlo vivo hacía que se propusiera HTMX en agosto.
- La migración HTML→Angular **cerró el 2026-06-11**; su inventario se archivó en
  [`_historico/2026-06-11_migracion_html_angular.md`](_historico/2026-06-11_migracion_html_angular.md).
- [frontend/DESPLIEGUE_FRONTEND.md](frontend/DESPLIEGUE_FRONTEND.md) — despliegue del SPA.
- [frontend/FRONTEND_ANGULAR.md](frontend/FRONTEND_ANGULAR.md) — guía Angular.

**Operación / usuarios**
- `usuarios_solicitados.local.md` — quién recibió acceso. **No versionado** (no se versiona: tiene cédulas y contratos de personas reales, y el repo es público (Ley 1581). Vive en la máquina del admin, gitignored por `*.local.md`).
- [manuales_uso/](manuales_uso/README.md) — manuales por rol entregado (ej. Cultura).
- [manuales_modulos/](manuales_modulos/README.md) — manuales por módulo (Infraestructura, Cultura, Banco).

**Informes y roadmap**
- [informes/INFORME_MAYO_2026.md](informes/INFORME_MAYO_2026.md) · [informes/ANALISIS_VALOR.md](informes/ANALISIS_VALOR.md) · [informes/MEJORAS_FUTURAS.md](informes/MEJORAS_FUTURAS.md)

**Referencia y decisiones**
- [referencia/SIPSE.md](referencia/SIPSE.md) — marco oficial + cadena Proyecto→Meta→KPI→Actividad→Evento.
- [propuestas/control_acceso_roles.md](propuestas/control_acceso_roles.md) — modelo de roles/acceso (borrador).

---

## Convenciones

- **`manuales_modulos/`** = un manual por módulo (cómo funciona el flujo).
- **`manuales_uso/`** = un manual por área/rol que se entrega a un usuario.
- Al crear un usuario nuevo: registrar en `usuarios_solicitados.local.md` (local, no versionado) y, si es un
  área nueva, agregar su manual en `manuales_uso/`.
- **Markdown puro**, español en todo (excepción: nombres técnicos/código).
- Si un doc deja de ser vigente, se mueve a `_historico/` con prefijo
  `YYYY-MM-DD_`. **No se borra.**
- Si un doc diverge del código, **manda el código** y se actualiza el doc.

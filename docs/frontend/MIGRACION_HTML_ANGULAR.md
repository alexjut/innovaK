# Inventario de migración HTML → Angular (2026-06-04)

Mapa COMPLETO de las 171 URLs no-API de Django y su estado en Angular.

> **Decisión Alex 2026-06-04 ("B — todo va para Angular"):** los formularios
> públicos de QR (Banco, Jóvenes, los 6 wizards de caracterización, entrega de
> insumos, QR del evento) **SÍ se migran a Angular** bajo `/app/p/*`, siguen
> siendo **públicos** (endpoints DRF `AllowAny` + rutas fuera del authGuard). La
> vista Django vieja redirige a la Angular. Constraint permanente: **lo público
> sigue público** (el mapa y los forms los usa el ciudadano sin login).

**Leyenda:**
- ✅ **EN ANGULAR** — ya migrado, el organizador lo usa desde el SPA.
- 🌐✅ **PÚBLICO EN ANGULAR** — form público de QR migrado a `/app/p/*` (AllowAny, sin guard).
- ❌ **FALTA** — funcionalidad de organizador aún sólo en HTML.
- 🌐 **PÚBLICO PENDIENTE** — form público de QR aún en HTML, por migrar a `/app/p/*`.
- 💀 **ZOMBI** — sin uso real; candidato a borrar.

---

## LOGIN / PERFIL / REGISTRO

| URL Django | Estado | Ruta Angular |
|---|---|---|
| `login/` | ✅ | `/auth/login` |
| `logout/` | ✅ | (auth) |
| `perfil/` | ✅ | `/perfil` |
| `perfil/cambiar-password/` | ✅ | `/perfil` |
| `crear-persona/` | ✅ | `/admin` (Personas → Crear) |
| `crear-participante/<id>/` | 🌐 | inscripción participante |
| `index/`, `formulario/`, `evento/`, `listado/` (módulo *formulario*) | 💀 | zombi kactivo legacy |

## DASHBOARD / IA

| URL | Estado | Angular |
|---|---|---|
| `dashboard/` | ✅ | `/` (hub) |
| `dashboard/consulta-inteligente/` | ✅ | `/ia` |
| `dashboard/personas/` | ✅ | `/analitica` |
| `dashboard/hub/{presupuesto,actividades,admin,votaciones}/` | ✅ | hubs Angular |
| `dashboard/hub/actividades/tipo/...` | ✅ | `/actividades/tipo/...` |
| `dashboard/presupuesto/` | ✅ | `/presupuesto/dashboard` |
| `dashboard/caracterizacion/<sector>/` | ✅ | hub caracterización |
| `dashboard/...caracterizaciones/` | ✅ | `/caracterizacion/evento` |
| `dashboard/placeholder/*` | 💀 | zombi |

## EVENTOS / ACTIVIDADES

| URL | Estado | Angular |
|---|---|---|
| `eventos/` | ✅ | `/eventos` |
| `evento/crear/` | ✅ | `/eventos/nueva` |
| `evento/<id>/editar/` | ✅ | `/eventos/:id/editar` |
| `eventos/insights/` | ✅ | `/eventos/insights` |
| `evento/tipos_evento/` (listar/crear) | ✅ | `/eventos/tipos` |
| `evento/tipos_evento/<c>/editar/` | ✅ | edición inline en `/eventos/tipos` |
| `evento/tipos_evento/<c>/{desactivar,reactivar}/` | ✅ | toggle en `/eventos/tipos` |
| `evento/<id>/qr/` | 🌐✅ | `/app/eventos/:id/qr` (Django redirige) |
| `evento/inscripcion/<id>/` + `registro-exitoso/` | 🌐✅ | `/app/p/inscripcion/:id` (Django redirige) |
| `evento/asistencia/<id>/` | 🟡 | en `/cursos` (asistencia) |
| `evento/asistencia-pdf/<id>/` | ❌ | export PDF falta |
| `evento/info-terreno/{confirmar,exitoso}/` | 🌐✅ | `/app/p/info-terreno/:id` (GPS+fotos; Django redirige) |

## ENTREGA DE INSUMOS (tipo ENTREGA — nuevo 2026-06-04)

| URL | Estado | Angular |
|---|---|---|
| `entregas/api/publico/<id>/{catalogos,inscribir}/` | 🌐✅ | `/app/p/entrega/:id` (form público QR, insumo+cantidad) |
| `entregas/api/entregas/` (organizador list) | ✅ | `/app/entregas` (Beneficiarios) |
| `entregas/api/entregas/<id>/` (detalle) | ✅ | `/app/entregas/:id` |
| `entregas/api/entregas/<id>/estado/` (validar/rechazar) | ✅ | (detalle) — sync KPI al validar |

## CURSOS

| URL | Estado | Angular |
|---|---|---|
| `cursos/` + `<id>/` (detalle, sesiones, lista, notas, reporte) | ✅ | `/cursos` |
| `cursos/<id>/reporte/{excel,pdf}/` | ❌ | export falta |

## BANCO DE INICIATIVAS

| URL | Estado | Angular |
|---|---|---|
| `banco-iniciativas/inscripciones/` | ✅ | `/banco` |
| `.../<pk>/` (detalle) | ✅ | `/banco/:id` |
| `.../<pk>/validar/` | ✅ | (detalle) |
| `.../<pk>/firma/` | ✅ | (detalle) |
| `.../insights/` | ✅ | `/banco/insights` |
| `.../exportar/` (CSV) | ❌ | export falta |
| `banco-iniciativas/<id>/inscribir/` + `exitoso/` | 🌐✅ | `/app/p/banco/:id` (Django redirige) |

## JÓVENES A LA E

| URL | Estado | Angular |
|---|---|---|
| `jovenes-a-la-e/entregas/` | ✅ | `/jovenes` |
| `.../<pk>/` + validar/rechazar | ✅ | `/jovenes/:id` |
| `.../insights/` | ✅ | `/jovenes/insights` |
| `.../exportar/` (Excel) | ❌ | export falta |
| `jovenes-a-la-e/<id>/beca/` + `exitoso/` | 🌐✅ | `/app/p/jovenes/:id` (Django redirige) |

## CARACTERIZACIÓN

| URL | Estado | Angular |
|---|---|---|
| organizador (hub/list/detalle) | ✅ | `/caracterizacion` |
| `caracterizacion/<id>/` (6 wizards) | 🌐✅ | `/app/p/caracterizacion/:id` (wizard dinámico schema-driven; Django redirige) |

## ADMINISTRACIÓN — ORG

| URL | Estado | Angular |
|---|---|---|
| `org/{dependencias,subgrupos,funcionarios,organizaciones,proveedores,beneficiarios}/` lista | ✅ | `/admin` (Org, tabs) |
| `.../nuevo/` (crear) | ✅ | (form crear) |
| `.../<pk>/editar/` (las 6) | ✅ | (botón Editar) |
| `org/beneficiarios/exportar/{,excel}/` | ❌ | export falta |

## ADMINISTRACIÓN — ROLES

| URL | Estado | Angular |
|---|---|---|
| `org/roles/` + nuevo/detalle/editar/toggle/modulos | ✅ | `/admin` (Roles) |
| `org/roles/<id>/usuarios/{agregar,quitar}/` | ✅ | gestión usuarios en `/admin/roles/:id` (buscar+agregar / quitar) |

## PRESUPUESTO

| URL | Estado | Angular |
|---|---|---|
| `presupuesto/home/` | ✅ | `/presupuesto` |
| `proyectos/` lista/nuevo/editar | ✅ | `/presupuesto/proyectos` |
| `proyectos/<id>/` (360°) | ✅ | `/presupuesto/proyectos/:id` |
| `proyectos/<id>/cdp/{asignar,quitar}/` | ✅ | proyecto-360: "Asignar CDP existente" + "Quitar" (PATCH proyecto_id) |
| `programas/` list/nuevo/editar/detalle | ✅ | `/presupuesto/programas` + detalle `/programas/:id` (resumen + proyectos) |
| `objetivos/` list/nuevo | ✅ | `/presupuesto/objetivos` |
| `metas/` + `meta-proyecto/` list/nuevo/editar | ✅ | `/presupuesto/metas`, `/meta-proyecto` |
| `conceptos/` list/nuevo/editar/eliminar | ✅ | `/presupuesto/conceptos` (eliminar con botón 🗑) |
| `cdp/` list/nuevo/editar/detalle | ✅ | `/presupuesto/cdps` + `/cdps/:id` |
| `contratos/` list/nuevo/editar/detalle | ✅ | `/presupuesto/contratos` + `/contratos/:id` |
| `contratos/<id>/vinculaciones/nueva/` | ✅ | (detalle contrato → Vincular) |
| `contratos/vinculaciones/<pk>/{editar,desactivar}/` | ✅ | detalle contrato: editar monto / desactivar (✏/🚫) |
| `indicadores/` list/nuevo/editar/detalle | ✅ | `/presupuesto/indicadores` + `/indicadores/:id` |
| `avances/` list/nuevo/editar | ✅ | `/presupuesto/avances` |
| `actividad-indicador/` list/nueva | ✅ | `/presupuesto/actividad-indicador` |
| `actividades/nueva,renombrar,eliminar,migrar` | ✅ | proyecto-360: crear + renombrar + eliminar · migrar bulk en `/presupuesto/actividades` (2026-06-11) |
| `actividades-plan/<pk>/` (detalle) | ✅ | proyecto-360: expand "Ver detalle" (KPIs + eventos + contratos) |
| `actividades/por-subgrupo/` | ✅ | `/presupuesto/actividades` — agregada por subgrupo + filtros + migrar a catálogo (2026-06-11; la vista Django redirige) |
| `ajax/*`, `presupuesto/ping/` | 💀 | helpers / zombi |

## VOTACIONES

| URL | Estado | Angular |
|---|---|---|
| `votaciones/dashboard/` + organizer events/artists (CRUD) | ✅ | `/votaciones` |
| `votaciones/{listado,registro}/` (votantes) | ✅ | `/votaciones/votantes` |
| `votaciones/scan/` | 🌐 | voto público |
| `votaciones/qr/{event,candidate}/<id>.png` | 🌐 | QR (se ve en detalle Angular) |

## GEO

| URL | Estado | Angular |
|---|---|---|
| `geo/mapa-kennedy/` | ✅ | `/mapa` (Leaflet nativo) |

---

# RESUMEN — LO QUE FALTA (organizador, ❌)

**Todo el organizador migrado al 2026-06-09.** Cerrados en esta jornada:

~~1. Presupuesto: asignar/quitar CDP↔proyecto · gestión de actividad-plan · editar/desactivar vinculación · detalle de programa · eliminar concepto.~~ ✅ HECHO 2026-06-09.
~~2. Exports: Banco CSV · Jóvenes Excel · Beneficiarios CSV/Excel · Curso Excel/PDF · Asistencia PDF.~~ ✅ HECHO 2026-06-09 (botones Angular que abren los endpoints Django con la sesión de `MeView`).
~~3. Eventos: form de editar tipo de evento.~~ ✅ HECHO 2026-06-09 (edición inline).
~~4. Roles: gestión de usuarios del rol.~~ ✅ HECHO 2026-06-09 (buscar+agregar / quitar, con protección rol Admin).

~~**Único pendiente (no bloqueante, baja prioridad):**~~ ✅ CERRADO 2026-06-11:
- `actividades/por-subgrupo/` → `/app/presupuesto/actividades` (GET `/presupuesto/api/actividades/por-subgrupo/` con catálogos y filtros en cascada; vista Django redirige a la SPA).
- `actividades/migrar/` → botón "Migrar a catálogo" en la misma pantalla (POST `/presupuesto/api/actividades/migrar/`).

**La migración HTML→Angular del organizador está 100% completa.**

# FORMS PÚBLICOS — MIGRACIÓN A ANGULAR (decisión B 2026-06-04)

**Ya en Angular (`/app/p/*`, públicos):**
- ✅ Banco → `/app/p/banco/:id`
- ✅ Jóvenes beca → `/app/p/jovenes/:id`
- ✅ Caracterización (6 sectores, wizard dinámico) → `/app/p/caracterizacion/:id`
- ✅ Entrega de insumos (con cantidad) → `/app/p/entrega/:id`
- ✅ QR del evento → `/app/eventos/:id/qr`
- ✅ Inscripción genérica de participante → `/app/p/inscripcion/:id` (2026-06-09)
- ✅ Info-terreno (GPS + fotos) → `/app/p/info-terreno/:id` (2026-06-09)

**Decisión 2026-06-09 — `votaciones/scan/` SE QUEDA en Django:**
El scan de voto es una página pública autocontenida (kiosko de votación con
su propio JS) que emite el voto vía `fetch` a `api_vote` y valida identidad.
Es un flujo sensible distinto, ya funcional y fuera del SPA organizador.
Migrarlo añade riesgo a la integridad del voto por beneficio mínimo → se deja
en HTML. El QR PNG (`votaciones/qr/*.png`) se sirve como imagen embebida en
el detalle Angular (no es página, no requiere migración).

**No quedan formularios públicos pendientes de migrar.**

> El QR PNG (`votaciones/qr/*.png`) se sigue sirviendo desde Django como imagen
> embebida en el detalle Angular — no es una página, no requiere migración.

# ZOMBI BORRADO (💀) — 2026-06-09
Eliminados (cadena completa: template + vista + URL + enlaces muertos), tras
verificar que ninguno era feature real ni tenía enlace vivo desde la SPA:
- `templates/login/formulario/*` (scaffold demo con datos hardcodeados) + 4 URLs
  + item de sidebar en `base.html` + breadcrumb `login:index`.
- `dashboard/placeholder.html` (placeholders reemplazados por listas reales en
  PR-D/E) + 3 URLs + 3 breadcrumbs + vista `placeholder_proximamente`.
- `presupuesto/ping/` (healthcheck) + URL + vista `ping`.
- `mapa_kennedy_standalone copy.html` (duplicado accidental, 0 referencias).

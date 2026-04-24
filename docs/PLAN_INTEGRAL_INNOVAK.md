# Plan Integral innovaK — rediseño, UX, accesibilidad y flujos

> **Fecha**: 2026-04-23 (cierre del día).
> **Rama**: `feat/mapa-kennedy-dashboard`.
> **Alcance**: documento maestro que consolida **todo lo que falta** al
> proyecto para pasar de "funcional con demo" a "robusto, accesible y
> mantenible". Base única para priorizar las próximas sesiones.
>
> Este documento **no ejecuta nada**. Es plan de trabajo.

---

## 0. Ubicación de este plan en la timeline del proyecto

Sesiones previas (de la bitácora CLAUDE.md §11):
- **2026-04-20**: auditoría, consolidación Git, hotfix S1–S4 propagado a producción.
- **2026-04-22**: reproyección GeoJSON Kennedy, fix autocomplete Nominatim, merge KPIs avances.
- **2026-04-23**: esta sesión larga — refactor mapa-kennedy (C1–C4), PR1 INFO_TERRENO con GPS/fotos, dashboard ejecutivo (KPIs + metas + cards + gráficos), siembra demo (10 proy / 20 metas / 34 KPIs / 55 eventos / 62 avances).

Commits de hoy (12 en esta rama):

```
622c254  docs: plan de rediseño dashboard — próxima sesión
7801cd9  feat(dashboard): sección de Metas del Plan con progreso agregado
505bdc1  feat(dashboard): cards y gráficos superiores con data operativa
e6f5cb5  feat(demo): siembra data robusta para dashboard ejecutivo
f0e48be  docs: plan detallado de siembra demo + roadmap PRs dashboard
a9d296b  feat(dashboard): sección de KPIs del Plan con avance físico
d4f3918  docs: inventario completo del proyecto para UX (Fase 1)
4c58d2f  fix(eventos): 2 bugs que bloqueaban el flujo end-to-end de PR1
038b543  fix(kactivo): alinea modelo Evento y admin con schema BD actual
dd026f3  feat(eventos): PR1 INFO_TERRENO con confirmación GPS + fotos
32b8aac  docs: plan de formularios dinámicos por tipo de evento
b837631  chore(mapa-kennedy): archivar scripts aplicados + bitácora
```

Docs generados hoy (8 archivos):
- `UX_INVENTARIO_2026-04-23.md`
- `PLAN_FORMULARIOS_POR_TIPO_EVENTO.md`
- `PLAN_DEMO_SIEMBRA.md`
- `PLAN_REDISENO_DASHBOARD.md`
- (+ actualizaciones a `DEUDA_TECNICA.md` §M22, `CLAUDE.md` §11)

---

## 1. Visión macro — 4 ejes de trabajo

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│   EJE A: Rediseño UX          EJE B: Accesibilidad          │
│   (navegación, pantallas,       (WCAG AA, teclado,          │
│    hub de botones, árbol)       contraste, lectores)        │
│                                                              │
│   EJE C: Flujos de usuario    EJE D: Robustez técnica       │
│   (roles, CRUD completos,       (tests, deuda crítica,      │
│    onboarding, permisos)        monitoring, backups)        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

Cada eje tiene secciones propias (§2–§5). Al final, priorización
consolidada (§6) y preguntas abiertas para Alex (§7).

---

## 2. EJE A — Rediseño UX

### 2.1 Problema actual

- **Menú principal tiene solo 7 enlaces** (sidebar `base.html`) para una app con **130+ URLs**. 90% de la funcionalidad no es descubrible.
- **Dashboard lineal**: toda la información en una sola página scrolleable. 6 secciones apiladas.
- **Sin pantallas dedicadas** por concepto: Metas, KPIs, Eventos, Proyectos comparten un único `/dashboard/presupuesto/`.
- **Home (`/`)** con 7 cards, pero 3 duplican lo del sidebar, otras 4 son rutas que también están en el menú.
- **`/index/`** existe en el menú sin nombre claro — nadie sabe qué es.

### 2.2 Arquitectura propuesta (detallada en `PLAN_REDISENO_DASHBOARD.md`)

```
/ (home)                         → Landing sin cambios (login/selección rol)
/dashboard/                      → Hub de tableros (NUEVO — grilla de botones)
/dashboard/presupuesto/          → Dashboard ejecutivo actual (se mantiene)
/dashboard/metas/                → Pantalla dedicada Metas PDD
/dashboard/indicadores/          → Pantalla dedicada KPIs detallados
/dashboard/eventos/              → Pantalla dedicada Eventos (listado + mini-mapa)
/dashboard/arbol-presupuesto/    → Gráfico árbol tipo Power BI (plan → años → monto)
/dashboard/consulta-inteligente/ → Ya existe, incluir en el hub
/geo/mapa-kennedy/               → Mapa geo (sin cambios)
/evento/crear/                   → Formulario crear evento (sin cambios grandes)
```

### 2.3 Componentes UI nuevos

1. **Hub de botones** (`templates/dashboard/hub.html`):
   - 8–12 botones, grid 4 cols desktop / 2 tablet / 1 móvil.
   - Color temático, icono FA, título + subtítulo.
   - Hover: elevación + sombra; foco accesible (EJE B).

2. **Breadcrumb persistente**:
   - En cada pantalla dedicada, "⟵ Hub" + migas.
   - Visible en sidebar: sección actual resaltada.

3. **Filtros universales** (reutilizable):
   - Componente JS con selects: vigencia, sector, dependencia, rango fecha.
   - Sincroniza con querystring (`?vigencia=2026&sector=Cultura`).
   - Todos los endpoints API lo respetan.

4. **Árbol presupuestal** (nuevo, pendiente decisión técnica):
   - D3.js `tree layout` (flexible, custom tooltips) o Mermaid (rápido, limitado).
   - Responsive (scroll horizontal en móvil).

### 2.4 Revisión del sidebar (`base.html`)

**Menú actual**:
```
1. Dashboard        (/)
2. Mapa Kennedy     (/geo/mapa-kennedy/)
3. ?                (/index/)              ← sin nombre claro
4. Crear Evento     (/evento/crear/)
5. Votaciones       (/votaciones/)
6. Crear Persona    (/crear-persona/)
7. Tipos de evento  (/evento/tipos_evento/)
```

**Menú propuesto** (estructurado por áreas, colapsables):

```
▼ Tableros
   ├─ Dashboard Ejecutivo     /dashboard/
   ├─ Mapa Kennedy            /geo/mapa-kennedy/
   └─ Consulta Inteligente    /dashboard/consulta-inteligente/

▼ Eventos
   ├─ Ver eventos             /eventos/              (YA EXISTE, sin link)
   ├─ Crear evento            /evento/crear/
   └─ Tipos de evento         /evento/tipos_evento/

▼ Plan Presupuestal
   ├─ Proyectos               /presupuesto/proyectos/
   ├─ Programas               /presupuesto/programas/
   ├─ Metas PDD               /dashboard/metas/      (NUEVO)
   ├─ Indicadores             /dashboard/indicadores/(NUEVO)
   └─ CDP                     /presupuesto/cdp/

▼ Personas
   ├─ Crear Persona           /crear-persona/
   ├─ Participantes           /kactivo/cultura/participantes/
   └─ Funcionarios            (NUEVO, pendiente)

▼ Votaciones
   └─ Gestión votaciones      /votaciones/

▼ Admin (solo grupo Admin)
   ├─ Admin Django            /admin/
   └─ Validaciones            /kactivo/validaciones/
```

---

## 3. EJE B — Accesibilidad (WCAG 2.1 AA)

### 3.1 Estado actual

- **Lang**: `<html lang="es">` en `base.html` ✓
- **`aria-label`**: solo 5 archivos lo usan parcialmente (base, index_kactivo, lista_eventos, login/formulario, cursos/cargue). El resto (93 templates) sin etiquetas.
- **`alt=`**: cobertura dispersa.
- **Contraste**: sin auditar. Bootstrap 5 base tiene contraste decente pero los custom (`.presdash-*`, badges de colores) no verificados.
- **Foco visible**: los `.nav-link` heredan `:focus` de Bootstrap. Algunos `<a>` custom no.
- **Navegación por teclado**: no probada.
- **Lectores de pantalla**: sin tests.

### 3.2 Checklist mínimo para llegar a AA

| # | Criterio | Estado actual | Acción |
|---|---|---|---|
| 1.1.1 | Texto alternativo (`alt=`) en `<img>` | Parcial | Auditar todos los `<img>`, agregar `alt=""` descriptivo o `""` decorativo |
| 1.3.1 | Encabezados jerárquicos (`<h1>`→`<h6>`) | Parcial | Una `<h1>` por pantalla, no saltar niveles |
| 1.3.5 | `autocomplete="..."` en inputs relevantes | NO | Agregar a formularios de persona/evento |
| 1.4.3 | Contraste 4.5:1 texto normal | NO auditado | Usar WebAIM contrast checker sobre `.presdash-*` |
| 1.4.11 | Contraste 3:1 componentes UI | NO auditado | Idem |
| 2.1.1 | Todo accesible por teclado | NO probado | Testing manual con Tab/Shift+Tab |
| 2.4.3 | Orden de foco lógico | Parcial | Revisar tabindex en formularios multi-paso |
| 2.4.4 | Propósito del enlace claro del texto | Parcial | Evitar "click aquí", "ver más" genéricos |
| 2.4.7 | Foco visible | Parcial | Estilo `:focus-visible` global |
| 3.1.1 | `lang` declarado | ✓ | — |
| 3.3.1 | Errores identificados | Parcial | Los Django `form.errors` aparecen; custom messages no siempre |
| 3.3.2 | Etiquetas o instrucciones en inputs | Parcial | `<label for="...">` en todos los form-controls |
| 4.1.2 | Roles ARIA correctos en widgets | NO | Modals, dropdowns custom necesitan `role`, `aria-expanded`, `aria-controls` |
| 4.1.3 | Status messages | NO | Django `messages` framework → agregar `role="status"` o `role="alert"` |

### 3.3 Plan de accesibilidad por fases

**Fase B1 — Quick wins (2–3 h)**:
- Revisar `base.html`: skip-link "Saltar al contenido", `role="main"`, `role="navigation"` en sidebar, `aria-current="page"` en link activo.
- CSS global `:focus-visible` con outline visible (p.ej. `outline: 2px solid #3b82f6; outline-offset: 2px;`).
- Auditar con axe DevTools (extensión Chrome) sobre las 5 pantallas más usadas: home, dashboard, mapa, crear_evento, login.
- Lista de hallazgos priorizada → PR chicos.

**Fase B2 — Formularios accesibles (3–4 h)**:
- Todos los `<input>` con `<label for="id">` explícito.
- `autocomplete="email|name|tel|postal-code|bday"` donde aplique.
- `aria-describedby` para hints y errores.
- Validación HTML5 + mensajes claros.
- Foco auto al primer error tras submit.

**Fase B3 — Componentes complejos (4–6 h)**:
- Modales (crear_lugar, nuevo lugar en mapa): `role="dialog"`, `aria-labelledby`, trap focus, ESC cierra.
- Dropdowns custom: `aria-expanded`, `aria-controls`, keyboard nav.
- Cascada dependencia→subgrupo→funcionario: anunciar cambios con `aria-live="polite"`.
- Leaflet map: alternativa textual (tabla) para usuarios sin mouse — decisión si vale la pena.

**Fase B4 — Contraste y visual (1–2 h)**:
- Correr WebAIM contrast checker sobre paleta custom.
- Ajustar badges (colores claros sobre fondo blanco pueden fallar 3:1).
- Modo alto contraste opcional (CSS custom property toggleable).

### 3.4 Herramientas

- **axe DevTools** (Chrome extension) — auditoría automática.
- **Wave** (webaim.org/extension) — complementario.
- **Lighthouse** sección Accessibility — score CI/CD futuro.
- **NVDA** (Windows) o **VoiceOver** (Mac) — test manual con lector.

---

## 4. EJE C — Flujos de usuario

### 4.1 Roles actuales en Django

```
Admin                  8 usuarios
UsuarioGeneral         2 usuarios
Docente                2 usuarios
Coordinador            1 usuario
Lider                  1 usuario
lider participacion    2 usuarios
─────────────────────────────────
Total: 7 usuarios únicos (+ superusers: 3, staff: 3)
```

### 4.2 Gaps por rol

**Admin** (8 usuarios):
- Acceso al admin de Django: ✓
- Crea/edita todo: parcial (faltan CRUDs, ver §4.3)
- Ver estadísticas de uso: ✗

**Coordinador / Lider / lider participacion**:
- No está claro qué pueden hacer vs Admin.
- Los `@group_required` están en algunas views, pero no hay matriz documentada.

**UsuarioGeneral / Docente**:
- Rol vivo en kactivo pero kactivo está casi sin uso (0 cursos, 0 clases).

**Funcionario** (rol aplicativo, no Django):
- 18 en BD, reciben QR al crear eventos, escanean para confirmar.
- NO tienen login propio. La aplicación asume que el login es de quien crea el evento.

### 4.3 CRUD existentes vs faltantes

**Entidades con CRUD completo** (crear + listar + editar + desactivar/eliminar):

| Entidad | Crear | Listar | Editar | Eliminar |
|---|---|---|---|---|
| Persona | ✓ | — | — | — |
| Participante | ✓ (vía persona) | ✓ | — | — |
| Evento | ✓ | ✓ | ✓ | ✗ (solo `activo=False`) |
| TipoEvento | ✓ | ✓ | ✓ | ✓ (desactivar/reactivar) |
| Proyecto | ✓ | ✓ | ✓ | ✗ |
| Programa | ✓ | ✓ | ✓ | ✗ |
| Objetivo | ✓ | ✓ | — | — |
| ConceptoGasto | ✓ | ✓ | ✓ | ✓ |
| CDP | ✓ | ✓ | ✓ | — |
| ActividadPlan | ✓ | — (solo API) | — | ✓ |
| Contrato | ✓ | — | — | — |
| Curso (kactivo) | ✓ | ✓ | — | — |
| Lugar (kactivo) | ✓ | ✓ | — | — |

**Entidades SIN UI de creación** (solo admin Django o BD directa):

- **Dependencia** (catálogo)
- **Subgrupo** (catálogo)
- **Funcionario** (solo existe por INSERT manual — crítico)
- **Meta PDD** (`metas` tabla)
- **MetaProyecto**
- **Indicador / KPI** (`presu_indicador_meta_proyecto`)
- **ActividadIndicador** (asociación N:N)
- **Avance** (`presu_avance_ind_periodo`) — se crea automáticamente desde eventos, pero sin UI para avances manuales.
- **Docente, Clase, Grupo, Disciplina** (kactivo, todos vacíos).
- **Parque, Escuela** (nuevas de C4.3).
- **Barrio, UPZ, Localidad** (catálogos territoriales — admin Django sí).

### 4.4 Flujo de onboarding (nuevo usuario)

**Hoy**: nada. Un usuario nuevo recibe credenciales por fuera del sistema y entra a un dashboard sin contexto.

**Propuesto**:
1. Welcome page post-login (primera vez): "Hola, <nombre>. Tu rol es <grupo>. Puedes hacer <acciones_por_rol>."
2. Tour guiado (opcional): librería `intro.js` o similar, 5–6 pasos destacando el sidebar, dashboard, mapa.
3. Link "Tutorial" en el footer del sidebar, siempre accesible.
4. Mini-"inbox" con tareas pendientes del usuario (ej: "Tienes 3 eventos sin confirmar en terreno").

### 4.5 Matriz de permisos que falta documentar

Para cada URL sensible, declarar qué grupo puede acceder. Crear `docs/MATRIZ_PERMISOS.md`. Plantilla:

```
URL                                     Admin  Coord  Lider  Funcionario  Público
/admin/                                   ✓     ✗      ✗        ✗           ✗
/dashboard/                               ✓     ✓      ✓        ✓           ✗
/evento/crear/                            ✓     ✓      ✓        ✗           ✗
/evento/info-terreno/confirmar/<id>/      ✓     ✓      ✓        ✓          ✓(QR)
/evento/tipos_evento/                     ✓     ✗      ✗        ✗           ✗
/presupuesto/proyectos/nuevo/             ✓     ✗      ✗        ✗           ✗
...
```

Luego cruzar con `@group_required` del código → encontrar inconsistencias.

---

## 5. EJE D — Robustez técnica

### 5.1 Deuda conocida pendiente (de `DEUDA_TECNICA.md`)

| Código | Título | Severidad | Estado |
|---|---|---|---|
| M1 | Modelos duplicados en login+kactivo (Evento, Programa, Lugar) | ALTA | Parche hoy `038b543`; falta unificar definitivamente |
| M2 | App `apps/documento/` abandonada | ALTA | Eliminada el 2026-04-20 ✓ |
| M5 | `apps/votaciones/` sin `apps.py` | BAJA | — |
| M6 | Archivos de views > 500 líneas | MEDIA | `login/views/eventos.py` sigue en 887 |
| M7 | `LANGUAGE_CODE`/`TIME_ZONE` duplicados en settings | BAJA | — |
| M10 | **Ausencia completa de tests** | ALTA | Crítico. 0 tests en el proyecto. |
| M11 | Sin logger estructurado | BAJA | — |
| M17 | Geocoding con IDECA en lugar de Nominatim | MEDIA | UX transparente mitigada hoy |
| M22 | Barrios con geometry incompleta (32/111) | MEDIA | Creada hoy en C4.3 |
| S5 | `MAX(id)+1` manual en 5 sitios | ALTA | Helper arreglado hoy (`4c58d2f`); deuda de schema persiste |
| S6 | SQL con f-string en insert dinámico | MEDIA | — |
| S7 | Views sin `@login_required` potencialmente sensibles | MEDIA | — |

**Tablas con modelo Django pero sin tabla en BD (crítico — bomba de tiempo)**:

```
presupuesto.Contrato              → public.contrato
presupuesto.ContratoProyecto      → public.contrato_proyecto
presupuesto.ContratoActividad     → public.contrato_actividad
login.TipoRedSocial               → tipo_red_social
login.NivelSocioeconomico         → nivel_socioeconomico
login.TenenciaVivienda            → tenencia_vivienda
login.TipoSalud                   → tipo_salud
login.TipoSangre                  → tipo_sangre
```

Cualquier view que importe/toque uno de estos **explota con `ProgrammingError`**. Eliminar los modelos o crear las tablas.

**Tablas BD sin modelo Django (50 huérfanas)** — destacada: `stg_beneficiarios` con **5,985 rows invisibles para el sistema**. Decisión pendiente: importar datos a Persona, eliminar, o ignorar.

### 5.2 Tests — el gran vacío (M10)

**Estado**: 0 tests. `tests.py` en cada app vacío.

**Plan mínimo de tests para llegar a nivel "rescate"**:

| Tipo | Objetivo | Qué cubre | Esfuerzo |
|---|---|---|---|
| Smoke | Nada explota al arrancar | `manage.py check`, `manage.py test` vacío, templates renderean | 1 h |
| Vistas críticas | `/dashboard/`, `/evento/crear/`, `/geo/mapa-kennedy/` devuelven 200 autenticado | 3 tests de integración | 2 h |
| Endpoints API | 12 endpoints JSON principales devuelven 200 con JSON válido | 12 tests paramétricos | 3 h |
| Flujos | Crear evento INFO_TERRENO end-to-end (setUp + POST + verificar registro) | 1–2 tests e2e | 2–3 h |
| Total fase 1 | | | **~8 h** |

Agregar CI mínima (GitHub Actions): `pytest` en cada push a `feat/*`, bloqueo de merge si falla.

### 5.3 Observabilidad

Hoy: `logger.exception` en algunos except, sin agregación.

Faltante:
- **Logging estructurado** (JSON) — existe el módulo `logging`, solo falta config.
- **Sentry** o similar — capturar errores 500 en producción.
- **Métricas de app** (Prometheus o sencillo: request duration, error rate) — opcional, bueno a futuro.
- **Monitoring de endpoints críticos** — uptime de `/dashboard/`, `/geo/mapa-kennedy/`.

### 5.4 Backups y recuperación

**Hoy**: cron del host a las 02:00 → `poblacion_kennedy_diario.dump` (se sobrescribe).

**Gaps**:
- Sin rotación (solo 1 archivo, se pisa cada día).
- Sin backup off-site (todo en el mismo servidor).
- Sin test de restauración periódico.

**Propuesto**:
- Rotación: mantener últimos 7 días + últimos 4 domingos + últimos 6 meses.
- Copia semanal a S3 o almacenamiento externo.
- Script `test_restore.sh` que cada mes restaura el dump en BD temporal y verifica counts.

### 5.5 Configuración patológica descubierta esta sesión

- `STATICFILES_DIRS` incluye `static/`, pero `static/` también es el mount de `STATIC_ROOT` via `docker-compose.yml` → `collectstatic` copia a sí mismo y provoca que fuentes en `apps/*/static/` pierdan prioridad.
- Arreglado parcialmente con `.gitignore` en `d814f48`. **Raíz**: requiere separar volumes en docker-compose (doble confirmación Alex).

### 5.6 Documentación de dev

Faltante:
- **README.md** en raíz con: prerequisitos, arranque local, variables de entorno, tests.
- **ARCHITECTURE.md** con diagrama de bloques (apps + BD externa + redis + nginx).
- **CONTRIBUTING.md** con flujo git (ya está en CLAUDE.md pero falta versión externa).
- **docstrings** en funciones de services y modelos — parcial.

---

## 6. Priorización consolidada

Con el criterio **impacto × urgencia × esfuerzo**:

### 🔥 Urgente (bloquea valor o es riesgo activo)

1. **Arreglar 8 modelos con tabla inexistente** (§5.1) — cualquier admin o query los activa. Decisión: crear tablas o eliminar modelos.
2. **PR A (Hub de botones)** del rediseño dashboard — destraba PRs B, C, D.
3. **Tests smoke mínimos** (§5.2) — sin eso, cada deploy es fe ciega.
4. **Matriz de permisos documentada** (§4.5) — evitar que un usuario vea lo que no debe.

### 🟡 Importante (alto valor, no bloquea)

5. **Accesibilidad fase B1 quick wins** (§3.3) — 2–3 h, cumple WCAG básico.
6. **PRs B/C/D del dashboard** (pantallas dedicadas Metas/KPIs/Eventos).
7. **CRUD UI para Funcionario** (§4.3) — hoy solo hay INSERT manual.
8. **CRUD UI para Metas/Indicadores** — sembrar data desde UI, no scripts.
9. **Menú del sidebar reorganizado** (§2.4) — descubrir el 90% invisible.
10. **Deuda M1 (modelos duplicados)** — unificar `kactivo.Evento` / `login.Evento`.
11. **Deuda S5 (MAX+1)** — agregar secuencias a `lugar_incidencia`, `evento`, etc.

### 🔵 Deseable (mejoras claras pero diferibles)

12. **Onboarding** (§4.4) — tour guiado, welcome page.
13. **PR E del dashboard** (árbol presupuestal) — depende de data real.
14. **Integración con IDECA** (deuda M17).
15. **Tests de integración extensivos** (§5.2 fases posteriores).
16. **Sentry + logging estructurado** (§5.3).

### ⚪ Out of scope por ahora

- Rediseño visual completo (nuevo branding).
- Mobile app nativa.
- Integración con Power BI externo.
- Sistema de notificaciones push.

---

## 7. Preguntas abiertas para la próxima sesión

1. **De los 4 ejes (§2–§5)**, ¿cuál pesa más para ti hoy? Rediseño (EJE A) se siente lo más cercano visualmente, pero los 8 modelos rotos (EJE D §5.1) son bomba de tiempo.
2. **Roles**: ¿los 6 grupos Django (Admin, UsuarioGeneral, Docente, Coordinador, Lider, lider participacion) son los que quedarán, o hay que reestructurar? Algunos (Docente, UsuarioGeneral) parecen de versiones pasadas de kactivo.
3. **Tests**: ¿entramos a escribir tests (M10) o quedas con el "rescate" aceptando el riesgo?
4. **Funcionario sin UI**: ¿aceptable que solo Admin lo cree vía Django admin, o construimos pantalla pública en `/funcionarios/crear/`?
5. **Kactivo vivo o dormido**: los 0 cursos / 0 clases / 0 docentes… ¿se van a usar alguna vez? Si no, considerar eliminar la app (deuda técnica limpia).
6. **Permisos del mapa Kennedy**: el mapa hoy requiere login. ¿Debería ser público (al menos en modo lectura) para comunicación externa?
7. **`stg_beneficiarios` (5,985 rows)**: ¿importar a Persona, crear UI de consulta, o borrar?
8. **Contratos**: la tabla `public.contrato*` no existe pero el modelo sí. ¿Crear BD schema, o eliminar los modelos porque no se usará?

---

## 8. Cómo usar este documento

1. **Hoy (cierre)**: commit y push del doc. Dashboard queda listo para demo.
2. **Próxima sesión**:
   a. Alex responde preguntas de §7.
   b. Se elige 1 ítem de la categoría 🔥 (§6) y se arranca.
   c. Cada item se desglosa en PR chicos. No bundles grandes.
3. **Cada 1–2 semanas**: revisitar este doc, marcar ítems completados, ajustar prioridades.

Este plan es **vivo**. Si la realidad contradice algo aquí, gana la realidad y se actualiza.

---

## 9. Métricas para medir progreso

En cada sesión futura, reportar:
- **Cobertura de tests** (`pytest --cov` %).
- **Issues de axe DevTools** en pantallas principales (count).
- **Modelos con tabla BD** vs total (hoy 82 / 90 ≈ 91%).
- **URLs en menú** vs URLs totales (hoy 7 / 130 ≈ 5%).
- **Pantallas con `aria-label` suficiente** (hoy 5 / 98 ≈ 5%).
- **Commits por semana en `desarrollo`** (velocidad de feature vs bugfix).

---

## Anexo A — URLs de creación existentes (snapshot hoy)

Rutas con `crear`/`nuevo` documentadas:

```
kactivo:
  POST /kactivo/cultura/crear-lugar/       crear_lugar_cultura
  POST /kactivo/cultura/crear-curso/       crear_curso_cultura
  POST /kactivo/registro/                  formulario_participante
  POST /kactivo/acudiente/<int>/           registrar_acudiente
  POST /kactivo/documentos/<int>/          cargue_documento

login:
  POST /crear-persona/                     crear_persona
  POST /crear-participante/<int>/          crear_participante
  POST /evento/crear/                      crear_evento
  POST /evento/tipos_evento/crear/         crear_tipo_evento
  POST /evento/<int>/editar/               editar_evento
  POST /evento/info-terreno/confirmar/<int>/  confirmar_llegada_info_terreno

presupuesto:
  POST /presupuesto/proyectos/nuevo/       proyecto_nuevo
  POST /presupuesto/proyectos/<int>/editar/ proyecto_edit
  POST /presupuesto/programas/nuevo/       programa_nuevo
  POST /presupuesto/programas/<int>/editar/ programa_editar
  POST /presupuesto/objetivos/nuevo/       objetivo_nuevo
  POST /presupuesto/actividades/nueva/     actividad_nueva
  POST /presupuesto/actividades/migrar/    actividad_migrar_desde_texto
  POST /presupuesto/actividades/renombrar/<int>/ actividad_renombrar
  POST /presupuesto/conceptos/nuevo/       concepto_gasto_crear
  POST /presupuesto/conceptos/<int>/editar/ concepto_gasto_editar
  POST /presupuesto/contratos/nuevo/       contrato_nuevo
  POST /presupuesto/cdp/nuevo/             cdp_new
  POST /presupuesto/cdp/<int>/editar/      cdp_edit
  POST /presupuesto/tematicas/crear-rapida/ tematica_crear_rapida

votaciones:
  POST /votaciones/organizador/eventos/nuevo/                 event_new
  POST /votaciones/organizador/eventos/<int>/editar/          event_edit
  POST /votaciones/organizador/artistas/<int>/editar/         candidate_edit

georeferenciacion:
  POST /geo/api/lugares/crear               api_crear_lugar (JSON)
```

**Faltan UI de creación para** (listado §4.3): Funcionario, Dependencia, Subgrupo, Meta, MetaProyecto, Indicador, Avance manual, Docente, Disciplina, Grupo, Clase, Parque, Escuela, Barrio, UPZ, Localidad.

---

## Anexo B — Roles Django hoy

```
Admin                  8 usuarios
UsuarioGeneral         2
Docente                2
Coordinador            1  (único — usuario "Coordionador" = Javier Aguilar)
Lider                  1
lider participacion    2
Total usuarios únicos: 7
Superusers: 3 (pertenecen a Admin)
Staff: 3
```

Decisión para próxima sesión: consolidar vs mantener esta lista.

---

**Fin del documento.**

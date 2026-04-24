# Inventario del proyecto innovaK — 2026-04-23

> Base para la sesión de UX integral del 2026-04-24. Documenta todo lo
> que existe hoy en el sistema para poder identificar **gaps** contra
> la referencia de Power BI que el usuario tiene como objetivo.
>
> **Nada fue modificado en la generación de este documento — solo lectura.**

---

## 1. Estado del repo

- **Rama actual**: `feat/mapa-kennedy-dashboard`
- **Working tree**: limpio
- **Últimos 15 commits** (esta sesión arriba, hotfix del 2026-04-20 abajo):

```
4c58d2f fix(eventos): 2 bugs que bloqueaban el flujo end-to-end de PR1
038b543 fix(kactivo): alinea modelo Evento y admin con schema BD actual
dd026f3 feat(eventos): PR1 INFO_TERRENO con confirmación GPS + fotos
32b8aac docs: plan de formularios dinámicos por tipo de evento
b837631 chore(mapa-kennedy): archivar scripts aplicados + bitácora sesión
7f11bed feat(mapa-kennedy): leyenda explica formas + cascada UPZ→Barrio
323ddb2 feat(mapa-kennedy): capas Parques y Escuelas conectadas a BD
32c71ef feat(bd): carga C4.3c/d/e — geometrías, 554 parques, 241 escuelas
447b098 chore(scripts): DDL + importers C4.3c/d/e con verificaciones
c7d06f0 feat(mapa-kennedy): capas UPZ/Barrios/Localidad datos reales
d814f48 chore(mapa-kennedy): elimina duplicados static/ y código muerto
3f98771 feat(mapa-kennedy): filtros conectados a BD real con cascada
3940118 refactor(mapa-kennedy): extrae CSS y JS inline a archivos
9d32071 refactor(mapa-kennedy): limpieza de controles muertos + IDs
52af0fa feat(mapa-kennedy): renderiza eventos con markers y popups
```

---

## 2. Modelos Django por app (con rows reales en BD)

### 2.1 `apps.login` — personas, funcionarios, eventos, catálogos

| Modelo | Tabla | Rows | Estado |
|---|---|---|---|
| **Persona** | `persona` | **6,938** | ✓ base del sistema |
| **Participante** | `participante` | **2,693** | ✓ |
| PersonaDocumento | `persona_documento` | 3,932 | ✓ |
| ContactoPersona | `contacto_persona` | 1 | placeholder |
| TipoDocumento | `tipo_documento` | 6 | catálogo |
| EstadoCivil | `estado_civil` | 7 | catálogo |
| EPS | `eps` | 10 | catálogo |
| ARL | `arl` | 7 | catálogo |
| Dependencia | `dependencia` | 5 | ✓ |
| Subgrupo | `subgrupo` | 44 | ✓ |
| Cargo | `cargo` | 4 | catálogo |
| TipoFuncionario | `tipo_funcionario` | 2 | catálogo |
| **Funcionario** | `funcionario` | **18** | ✓ (3 originales + 15 Javier) |
| TipoEvento | `tipo_evento` | 4 | ✓ |
| **Evento** | `evento` | **46** | ✓ core del sistema |
| **EventoInfoTerreno** | `evento_info_terreno` | **1** | ✓ nuevo (PR1) |
| AccesoSalud / ServicioBasico / TipoVivienda / TipoDispositivo / Sisben | varios | 0-8 | catálogos, varios con tabla inexistente |

**Alerta:** 5 modelos de login con tabla inexistente (ver §6).

### 2.2 `apps.georeferenciacion` — mapa, polígonos, catálogo territorial

| Modelo | Tabla | Rows |
|---|---|---|
| Pais | `pais` | 93 |
| Departamento | `departamento` | 33 |
| Municipio | `municipio` | 1,094 |
| Localidad | `localidad` | 20 |
| UPZ | `upz` | 12 |
| Barrio | `barrio` | 325 |
| Zona | `zona` | 4 |
| Lugar | `lugar` | 224 |
| GeoReferenciacion | `geo_referenciacion` | 248 |
| LugarIncidencia | `lugar_incidencia` | 12 |
| **Parque** | `parque` | **554** | ✓ nuevo C4.3 |
| **Escuela** | `escuela` | **241** | ✓ nuevo C4.3 |

### 2.3 `apps.kactivo` — cultura + deporte, casi todo dormido

| Modelo | Tabla | Rows | Nota |
|---|---|---|---|
| Acudiente | `acudiente` | 0 | schema sin uso |
| Docente | `docente` | 0 | schema sin uso |
| Actividad | `actividad` | **73** | ✓ tiene datos |
| Curso | `curso` | 0 | schema sin uso |
| Programa | `programas` | 3 | |
| Disciplina | `disciplina` | 0 | schema sin uso |
| Grupo | `grupo` | 0 | schema sin uso |
| Clase | `clase` | 0 | tiene FK `evento_id` pero vacía |
| HorarioClase | `horario_clase` | 0 | |
| Asistencia | `asistencia_clase` | 0 | |
| Evento (duplicado) | `evento` | 46 | **deuda M1** mismo db_table que login.Evento |
| **ParticipanteEvento** | `participante_evento` | **2,545** | ✓ dato vivo |
| CaracterizacionCultura | `caracterizacion_cultura` | 0 | |
| CaracterizacionDeporte | `caracterizacion_deporte` | 0 | |
| TipoArchivo | `tipo_archivo` | 1 | (creada hoy por PR1) |
| DocumentoEvento | `documento_evento` | 2 | (fotos test PR1) |
| DocumentoParticipante | `documento_participante` | 0 | |
| DocumentoRequisito | `documento_requisito` | 3 | |
| EvaluacionParticipante / NotaMedica / ValidacionDocumental / Convocatoria / TipoAsistencia / ClaseParticipante | varios | 0 | dormidos |

### 2.4 `apps.presupuesto` — proyectos, actividades, indicadores

| Modelo | Tabla | Rows |
|---|---|---|
| Vigencia | `vigencia` | 8 |
| Objetivo | `objetivo` | 3 |
| Programa | `programas` | 3 |
| ConceptoGasto | `concepto_gasto` | 1 |
| CategoriaTematica | `categoria_tematica` | 1 |
| Tematica | `tematica` | 2 |
| Area | `area` | 10 |
| **Proyecto** | `proyecto` | **8** |
| **Actividad** | `actividad` | 73 |
| **ActividadPlan** | `actividad_plan` | 42 |
| MetaBD | `metas` | 10 |
| MetaProyectoBD | `meta_proyecto` | 9 |
| **Indicador** | `presu_indicador_meta_proyecto` | **6** (2 seed + 4 creados hoy) |
| ActividadIndicador | `actividad_indicador` | 20 |
| AvanceIndicador | `presu_avance_ind_periodo` | 7 |
| Contrato / ContratoProyecto / ContratoActividad | `public.contrato*` | **TABLA NO EXISTE** (§6) |

### 2.5 `apps.votaciones` — flujo independiente con QR

| Modelo | Tabla | Rows |
|---|---|---|
| Event | `votaciones_event` | 1 |
| Candidate | `votaciones_candidate` | 11 |
| Voter | `votaciones_voter` | 2 |
| Vote | `votaciones_vote` | 109 |

### 2.6 Resumen cuantitativo

- **~90 modelos Django** totales entre las 5 apps activas.
- **~40 modelos con datos reales** (no vacíos).
- **~50 modelos dormidos** (rows=0), mayoría en kactivo.
- **8 modelos apuntan a tablas inexistentes** — ver §6.

---

## 3. URLs principales (sin admin, sin static)

Total: **~130 rutas** distintas (excluyendo admin de Django). Agrupadas:

### 3.1 Core público / login (`/`)
```
/                                       dashboard
/login/  /logout/                       auth
/index/  /formulario/  /evento/  /listado/   pantallas legacy
```

### 3.2 Eventos (`/evento/`, `/eventos/`)
```
/evento/crear/                          crear_evento (form único actual)
/evento/<id>/editar/                    editar_evento
/evento/inscripcion/<id>/               inscribir_participante (QR estándar)
/evento/registro-exitoso/<id>/          registro_exitoso (muestra QR)
/evento/asistencia/<id>/                lista_asistencia (HTML)
/evento/asistencia-pdf/<id>/            lista_asistencia_pdf
/evento/info-terreno/confirmar/<id>/    PR1 — QR GPS + fotos
/evento/info-terreno/exitoso/<id>/      PR1 — preview post-confirmación
/eventos/                               listar_eventos
/evento/tipos_evento/…                  CRUD catálogo
```

### 3.3 Dashboard + Consulta Inteligente (`/dashboard/`)
```
/dashboard/                             home
/dashboard/personas/                    vista_personas
/dashboard/presupuesto/                 home presupuesto
/dashboard/consulta-inteligente/        consulta_ai (OpenAI)
/dashboard/api/personas/query           API JSON
/dashboard/api/presupuesto/*            3 endpoints JSON
```

### 3.4 Mapa y Geo (`/geo/`)
```
/geo/mapa-kennedy/                      mapa principal
/geo/graficos/                          dashboard gráficos
/geo/api/eventos/                       GeoJSON eventos
/geo/api/kennedy/contorno|barrios|upz|parques|escuelas   5 endpoints
/geo/api/lugares | estadisticas | conteos | choropleth   4 endpoints agregados
/geo/api/lugares.csv | lugares/crear                     export + alta
```

### 3.5 Kactivo — Cultura y Deporte (`/kactivo/`)
```
/kactivo/cultura/                       shell (8 pantallas: inicio, participante,
                                        docente, cursos, cargue-documental,
                                        consultas, asistencia, caracterizaciones)
/kactivo/cultura/crear-curso/           crear_curso_cultura
/kactivo/cultura/crear-lugar/           crear_lugar_cultura
/kactivo/registro/                      formulario_participante (multi-step)
/kactivo/datos-complementarios/<id>/
/kactivo/acudiente/<id>/
/kactivo/documentos/<id>/
/kactivo/resumen/<id>/
/kactivo/validacion/<id>/
/kactivo/validaciones/
/kactivo/cultura/participantes/exportar-excel/   único export Excel
```

### 3.6 Presupuesto (`/presupuesto/`)
```
/presupuesto/home/
/presupuesto/proyectos/ | /nuevo/ | /<pk>/editar/
/presupuesto/programas/ | /nuevo/ | /<pk>/editar/ | /<id>/        CRUD
/presupuesto/objetivos/ | /nuevo/
/presupuesto/actividades/nueva/ | /eliminar/ | /renombrar/ | /migrar/
/presupuesto/conceptos/ | CRUD
/presupuesto/contratos/nuevo/
/presupuesto/cdp/ | /nuevo/ | /<pk>/editar/
/presupuesto/tematicas/crear-rapida/
/presupuesto/api/proyectos | actividades-por-proyecto | plan-actividades | indicadores-por-actividad | subgrupos
```

### 3.7 Votaciones (`/votaciones/`)
```
/votaciones/                            root organizer
/votaciones/api/events/ | /<id>/candidates/   API
/votaciones/api/buscar-persona/         búsqueda
/votaciones/qr/event/<id>.png | /qr/candidate/<id>.png   QR PNG
```

---

## 4. Templates (98 archivos totales)

| Carpeta | #html | Observaciones |
|---|---|---|
| `presupuesto/` | 18 | CRUD completo de proyecto, programa, objetivo, concepto, CDP, contratos |
| `kactivo/` | 15 | Shell cultura + listados + asistencia |
| `votaciones/` | 10 | organizer + público + QR |
| `eventos/` | 8 | crear, editar, listar, asistencia, inscripción, tipos evento |
| `kactivo/deporte/` | 7 | (deporte replica cultura) |
| `kactivo/cultura/` | 7 | detalle listados |
| `cursos/` | 7 | shell alternativo (inicio, participante, docente, cursos, cargue, consultas, asistencia) |
| `login/` | 6 | auth + formularios |
| `geo-mapas/` | 5 | mapa_kennedy_standalone + graficos_dashboard + otros |
| `login/formulario/` | 4 | |
| `dashboard/` | 4 | home + consulta-ai + presupuesto |
| `eventos/info_terreno/` | **2 (nuevo PR1)** | confirmar_llegada + exitoso |
| `presupuesto/concepto_gasto/` | 2 | |
| raíz | 2 | base.html + home.html |
| `partials/` | 1 | |

---

## 5. Views por app (archivos + funciones + líneas)

### apps/login (7 archivos, 34 views, 1229 lines)
```
  eventos.py                            15 views    887 lines  ← core
  tipos_evento.py                        5 views    123 lines
  api.py                                 4 views     58 lines
  formulario.py                          4 views     32 lines
  registro.py                            3 views     97 lines
  login.py                               2 views     29 lines
  home.py                                1 views      3 lines
```

### apps/georeferenciacion (5 archivos, 38 views, 1238 lines)
```
  apis.py                               28 views    879 lines  ← APIs geo
  mapa_kennedy_view.py                   4 views    194 lines
  mapas.py                               4 views    149 lines
  mapa_kennedy.py                        1 views     10 lines
  graficos_view.py                       1 views      6 lines
```

### apps/kactivo (9 archivos, 36 views, 1083 lines)
```
  formulario_participante.py             7 views    286 lines
  deporte.py                             7 views    243 lines  ← replica cultura
  cultura.py                             7 views    238 lines
  asistencia.py                          3 views    110 lines
  consulta_participantes.py              2 views     67 lines
  cultura_shell.py                       7 views     80 lines  ← navegación
  index.py                               1 views     15 lines
  consulta_cursos.py                     1 views     18 lines
  ping_db.py                             1 views     26 lines
```

### apps/presupuesto (4 archivos, 36 views, 934 lines)
```
  catalogo.py                           19 views    540 lines  ← CRUD principal
  api.py                                 7 views    108 lines
  cdp.py                                 5 views    179 lines
  concepto_gasto.py                      5 views    107 lines
```

### apps/dashboard (1 archivo, 4 views, 163 lines)
```
  views.py                               4 views    163 lines
  views_presupuesto.py                   (+sin conteo, adicional)
```

### apps/votaciones (6 archivos, 40 views, 1223 lines)
```
  api.py                                16 views    647 lines
  organizer.py                           9 views    228 lines
  registro.py                            6 views    219 lines
  auth.py                                3 views     53 lines
  qr.py                                  3 views     39 lines
  public.py                              3 views     37 lines
```

**Total: ~188 views entre 32 archivos, ~5870 líneas.**

---

## 6. Tablas BD sin modelo Django (huérfanas)

**50 tablas** en BD sin modelo. Destacadas por cantidad de rows o relevancia:

| Tabla | Rows | Posible uso |
|---|---|---|
| **`stg_beneficiarios`** | **5,985** | Staging histórico masivo, sin UI |
| `organizacion` | 59 | Catálogo de organizaciones externas |
| **`presu_indicador`** | **6** | Indicadores "viejos" (el modelo Indicador apunta a `presu_indicador_meta_proyecto`) — confusión M1 |
| `presu_impacto_actividad_indicador` | 5 | Impactos por actividad — sin UI |
| `tipo_contrato` | 5 | Catálogo |
| `fase_proyecto` | 3 | Fases — sin UI |
| `proyecto_inversion` | 3 | Proyectos de inversión distinto a `proyecto` |
| `proyecto_inversion_item` | 9 | Items — sin UI |
| `tipo_punto` | 2 | Catálogo Cultura/Deporte ya usado |
| `grupo_sanguineo` | 8 | Catálogo salud |
| **40 tablas vacías más** | 0 | Schema preparado sin datos (cuenta_contable, elemento_pep, emprendimiento, enfermedad_cronica, fondo, forma_pago, formacion, fuente_financiacion, informacion_hogar, instancia_participacion, integrantes, modalidad_seleccion, parentesco, participante_actividad, participante_curso, periodo_fiscal, persona_conviviente, persona_enfermedad_cronica, persona_historial, persona_red_social, persona_servicio_basico, persona_tipo_dispositivo, propiedad_horizontal, proveedor, recursos, representante_legal, representante_organizacion, reservas, rubro, sala_recurso, salas, tipo_cdp, tipo_compromiso, tipo_crp, tipo_proceso, presupuesto_proyecto, presupuesto_tiempo, proyectos, presu_avance_indicador) |

### Modelos Django con tabla inexistente (WARNING)

Estos 8 modelos apuntan a tablas que no existen en BD. Al usarlos explotan:

```
presupuesto.Contrato              → public.contrato             (NO EXISTE)
presupuesto.ContratoProyecto      → public.contrato_proyecto    (NO EXISTE)
presupuesto.ContratoActividad     → public.contrato_actividad   (NO EXISTE)
login.TipoRedSocial               → tipo_red_social             (NO EXISTE)
login.NivelSocioeconomico         → nivel_socioeconomico        (NO EXISTE)
login.TenenciaVivienda            → tenencia_vivienda           (NO EXISTE)
login.TipoSalud                   → tipo_salud                  (NO EXISTE)
login.TipoSangre                  → tipo_sangre                 (NO EXISTE)
```

**Implicación**: cualquier view/admin que toque estos modelos tira `ProgrammingError`. Deuda crítica.

---

## 7. Funcionalidades detectadas

### 7.1 Dashboard / KPIs / Consulta
- **`apps/dashboard/views.py`** (4 views, 163 líneas): home, vista personas, consulta AI (OpenAI), URL redirect.
- **`apps/dashboard/views_presupuesto.py`**: home presupuesto + 3 APIs (cascada-resumen, objetivos-por-proyecto, objetivos-y-programas).
- **`apps/georeferenciacion/views/graficos_view.py`**: 1 view (6 líneas) — renderiza `geo-mapas/graficos.html`.
- **`apps/presupuesto/views/api.py`**: 7 views con endpoints AJAX para cascadas.
- Hay templates `dashboard/*.html` (4) con estructura de tarjetas.

Conclusión: dashboard existe pero **muy básico**. No hay visualización tipo Power BI con gráficos interactivos — solo tarjetas y consulta AI.

### 7.2 Reportes / Export
Solo 3 archivos tocan export:
- `login/views/eventos.py`: `lista_asistencia_pdf` (ReportLab). Genera PDF por evento.
- `kactivo/views/consulta_participantes.py`: `exportar_participantes_excel` (openpyxl).
- `georeferenciacion/views/apis.py`: `api_lugares_csv` (CSV desde filtros del mapa).

Conclusión: **no hay sistema de reportes**. Solo 3 exports ad-hoc. Falta:
- Export de eventos agregados (por mes, tipo, dependencia).
- Export de avances de KPI.
- Reportes gerenciales con tablas dinámicas.

### 7.3 Calendario
**No existe**. Grep por `calendar`/`fullcalendar` solo encuentra referencias en CSS (`btn-calendar` clase suelta en base.html) y un icon en home.html. Cero integración de librería de calendario ni modelo.

Conclusión: **gap crítico** si Power BI muestra eventos en calendario.

### 7.4 Listados con filtros
- `login.listar_eventos` (con filtros q/desde/hasta/dep/sub/page).
- `login.listar_tipos_evento`.
- `kactivo.consulta_participantes`.
- `kactivo.consulta_asistencia_{cultura,deporte}`.
- `kactivo.consulta_lugares_cultura`.
- `kactivo.consulta_docentes_cultura`.
- `presupuesto` — todos los CRUD (proyectos, programas, objetivos, actividades, conceptos, cdp).
- `votaciones.organizer` — listado de events y candidates.

Existen ~12 listados con filtro. Todos Bootstrap table plano, sin DataTables ni paginación infinita.

### 7.5 Otras capacidades visibles
- **QR**: implementado en 2 flujos (votaciones + eventos). Biblioteca `qrcode` nativa.
- **Multi-step forms**: kactivo.formulario_participante (5 pasos: registro → datos → acudiente → documentos → resumen → validación).
- **Admin Django**: completo, pero el `kactivo.EventoAdmin` rompía hasta el hotfix de hoy.
- **Geo dashboard**: mapa + gráficos agregados (UPZ, barrios, mensual, choropleth).

---

## 8. Menú principal actual

El sidebar en `templates/base.html` tiene **7 enlaces** (todos con icon):

| # | Label | URL | Ruta name |
|---|---|---|---|
| 1 | Dashboard | `/` | `login:dashboard` |
| 2 | Mapa Kennedy | `/geo/mapa-kennedy/` | `georeferenciacion:mapa_kennedy` |
| 3 | ? | `/index/` | `login:index` |
| 4 | Crear Evento | `/evento/crear/` | `login:crear_evento` |
| 5 | Votaciones | `/votaciones/` | `votaciones:organizer_events` |
| 6 | Crear Persona | `/crear-persona/` | `login:crear_persona` |
| 7 | Tipos de evento | `/evento/tipos_evento/` | `login:listar_tipos_evento` |

El `home.html` (cards de la landing) tiene **6 cards**: Dashboard, Mapa Kennedy, Index, Crear Evento, Votaciones, Presupuesto, Crear Persona (7).

**Hallazgos del menú:**
- **No hay enlace** a `/eventos/` (listado de eventos existe pero no está en el menú).
- **No hay enlace** a `/kactivo/` (toda la app cultura/deporte está invisible).
- **No hay enlace** a `/dashboard/consulta-inteligente/` (la consulta AI).
- **No hay enlace** a `/presupuesto/proyectos/` ni demás CRUDs de presupuesto.

---

## 9. Hallazgos para UX (lo que llama la atención)

### 9.1 Qué está en PRODUCCIÓN estable
- `/evento/crear/` + `/evento/inscripcion/<id>/` (QR). Flujo estándar.
- `/geo/mapa-kennedy/` con 6 capas funcionales (Escuelas, Parques, Barrios, UPZ, Localidad, Heatmap).
- `/dashboard/consulta-inteligente/` (OpenAI).
- Admin Django.
- Kactivo registro participantes (5 pasos).

### 9.2 Qué está A MEDIO HACER
- **Kactivo cultura/deporte**: schema completo, UI completa, **BD vacía** (0 cursos, 0 clases, 0 docentes). Solo 73 actividades de presupuesto y 2,545 participantes en eventos. La app cultura/deporte nunca se usó en producción.
- **Dashboard**: estructura básica (home + 3 APIs de presupuesto + consulta AI). Falta la visualización tipo Power BI.
- **Caracterización** (cultura/deporte): 2 tablas creadas pero vacías. Hay templates de listado pero no de creación.
- **Contratos**: modelo Django referencia `public.contrato*` que NO existe en BD → bomba de tiempo.
- **Presupuesto**: CRUD completo implementado pero poblado mínimamente (8 proyectos, 42 actividades_plan, 6 KPIs). Probablemente el stakeholder llena esto gradualmente.

### 9.3 Qué hay en BD SIN UI
- **`stg_beneficiarios` con 5,985 rows** — dato masivo invisible. Probablemente staging histórico.
- **`organizacion` con 59 rows** — sin módulo propio.
- **`proyecto_inversion` con 3 rows** (distinto a `proyecto`) — confusión de entidades.
- **`presu_indicador` con 6 rows** (distinto a `presu_indicador_meta_proyecto`) — deuda M1 interna de indicadores.
- **40+ tablas vacías** con schema preparado (salud, vivienda, servicios, conceptos fiscales). Alguien diseñó estructura para un sistema mucho más grande del que se usa.

### 9.4 Qué FALTA claramente (vs. dashboard Power BI de referencia)
Sin haber visto el Power BI pero por patrones típicos:
- **Visualizaciones agregadas** de KPIs (gráficos barras/línea/pie por dependencia, tipo, mes).
- **Calendario** de eventos (nada).
- **Mapa de calor** de eventos por UPZ/barrio (hay heatmap sobre lugares, no sobre eventos).
- **Tabla dinámica** con filtros combinados (dep × tipo × fecha).
- **Indicadores de cumplimiento** visibles (ej: "35% del KPI Personas Capacitadas en Emprendimiento").
- **Reportes exportables** (PDF de asistencia es lo único; faltan informes ejecutivos).
- **Drill-down** desde KPI hacia eventos que lo alimentan.
- **Panel de avances por proyecto** — apps/dashboard/views_presupuesto existe, pero el template puede estar vacío.

### 9.5 Deudas críticas que bloquearían UX nueva
- **M1** (modelos duplicados): `Evento` existe en login y kactivo. `Programa` existe en kactivo (tabla `programas`) y presupuesto (también `programas`). Pueden causar admin 500 al tocar.
- **S5** (MAX+1 manual): `lugar_incidencia` sin secuencia, el helper ya se arregló pero hay otras tablas con el mismo patrón.
- **Tablas inexistentes** para 8 modelos (contrato*, tipo_salud, etc.) — cualquier endpoint nuevo que las use explota.
- **Menú mutilado**: solo 7 enlaces para 130+ rutas. Mucha funcionalidad no descubrible.

---

## 10. Próximos pasos sugeridos (para sesión UX 2026-04-24)

1. **Alex presenta el Power BI** — yo tomo screenshots/notas de cada vista.
2. **Mapeamos gap por gap**: cada pantalla del Power BI → qué datos necesita → si existen en BD → si hay view → si hay template → qué falta.
3. **Priorizamos top-5 pantallas nuevas** del dashboard.
4. **Decidimos**: ¿rediseño de menú? ¿nueva página `/dashboard/` con tarjetas gráficas? ¿Chart.js vs. Plotly?
5. **Arrancamos con la más valiosa** en un PR pequeño.

**Preguntas abiertas para Alex:**
- ¿El Power BI muestra KPIs agregados o lista de eventos detallados?
- ¿Hay calendario en el Power BI?
- ¿Vamos a mantener admin de Django o reemplazarlo con dashboards propios?
- ¿`stg_beneficiarios` (5985 rows) es visible en el Power BI? ¿Debería tener UI aquí?
- ¿`proyecto_inversion` vs `proyecto` — cuál es el canónico?

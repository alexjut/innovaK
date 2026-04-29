# MAPA DE LA APLICACIÓN — innovaK

> Mapa operativo del sistema. Para *cómo* está construido en detalle ver
> [`ARQUITECTURA.md`](./ARQUITECTURA.md). Para deuda técnica priorizada
> ver [`DEUDA_TECNICA.md`](./DEUDA_TECNICA.md). Para historia de cada
> módulo ver §11 de [`/CLAUDE.md`](../CLAUDE.md).
>
> **Última actualización:** 2026-04-29 · **Snapshot DB:** misma fecha.

---

## 1. Visión panorámica

**innovaK** es el sistema interno de la **Alcaldía Local de Kennedy
(Bogotá)** para gestionar población atendida, planeación y ejecución
presupuestal, eventos culturales/deportivos y georreferenciación del
territorio.

**Stack** — Django 4.2.11 + Python 3.10 + PostgreSQL externa
(`poblacion_kennedy` en `10.100.102.12:5432`, todo `managed=False`) +
Redis 7 + Nginx, en Docker. Front estático con webpack + SCSS, mapas con
Leaflet, dashboards con Dash/Plotly + OpenAI.

**Roles funcionales** (grupos en `auth_group`):

| Grupo | Acceso típico |
|-------|---------------|
| `Admin` | Todo: catálogos, contratos, KPIs, organizaciones, BD |
| `Lider` | Operación: crear evento, vincular contrato, validar inscripciones banco |
| `Coordinador` | Crear persona/participante, inscripciones |
| (sin grupo, autenticado) | Lectura de listados/dashboards generales |
| **Anónimo / público** | `/evento/inscripcion/<id>/` + `/banco-iniciativas/<id>/inscribir/` + QR de votación + `/healthz` |

### 1.1 Mapa de módulos top-level

```
                                  ┌─────────────────────┐
                                  │  apps.login (raíz)  │
                                  │  Persona, Funcio-   │
                                  │  nario, Evento,     │
                                  │  catálogos, /org/*  │
                                  └─────────┬───────────┘
                                            │ Persona, Funcionario,
                                            │ Evento, TipoEvento,
                                            │ Organizacion
            ┌───────────────────────────────┼───────────────────────────────┐
            ▼                               ▼                               ▼
  ┌──────────────────┐          ┌──────────────────────┐         ┌──────────────────┐
  │ apps.presupuesto │          │ apps.banco_inicia-   │         │ apps.kactivo     │
  │ Proyecto, CDP,   │◀────────▶│ tivas (form QR       │         │ Cultura+Deporte  │
  │ Contrato, Meta-  │  evento  │ público proyecto     │         │ cursos/asisten-  │
  │ Proyecto, KPI,   │  pivote  │ 2784)                │         │ cia (legacy)     │
  │ Avance,          │          └──────────────────────┘         └──────────────────┘
  │ ActividadPlan    │
  └─────────┬────────┘
            │
            ▼
  ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
  │ apps.georeferencia-  │    │ apps.dashboard       │    │ apps.votaciones      │
  │ cion (Lugar, Barrio, │    │ Hub + Dash/Plotly +  │    │ flujo paralelo       │
  │ UPZ, GeoReferencia-  │    │ OpenAI + breadcrumbs │    │ con QR (bilingüe en  │
  │ cion, mapa Kennedy)  │    │ + cache-buster       │    │ inglés, independiente)│
  └──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

**Cadena de negocio principal (presupuestal):**

```
Proyecto ─► CDP ─► Contrato (cdp_id) ─► ContratoActividadPlan
                                              │
                                              ▼
                                       ActividadPlan ◄── Evento ─► AvanceIndicador
                                              │                          │
                                              └──► ActividadIndicador ──► Indicador (KPI)
                                                                              ▲
                                                              MetaProyecto ───┘
                                                                   ▲
                                                                Proyecto
```

---

## 2. Módulos activos

### 2.1 `apps.login` — Autenticación, personas, eventos, organizaciones
- **Propósito:** Núcleo: usuarios, Persona+catálogos demográficos, Funcionario, Evento (modelo nuevo), TipoEvento, y el CRUD organizativo (`/org/*`: Dependencia, Subgrupo, Funcionario, Organizacion, Proveedor, Beneficiario).
- **Modelos principales** (24 modelos): `Usuario` (AbstractUser), `Persona` (`db_table=persona`, 6 938 filas), `Funcionario` (18), `Evento` (101), `TipoEvento` (5), `Inscripcion`, `ContactoPersona`, `PersonaDocumento`, `Sisben`, `EventoInfoTerreno`, `Organizacion` (59), `Proveedor` (0), `Beneficiario` (3 580) + ~26 catálogos auxiliares (`Sexo`, `GrupoEtario`, `Zona`, `NivelEducativo`, `Ocupacion`, etc.).
- **URLs:** prefijo `/` (raíz). Páginas: `/login/`, `/logout/`, `/index/`, `/eventos/`, `/evento/crear/`, `/evento/<id>/editar/`, `/evento/inscripcion/<id>/` (público), `/evento/asistencia/<id>/`, `/evento/info-terreno/...`, `/evento/tipos_evento/...`, `/org/{dependencias,subgrupos,funcionarios,organizaciones,proveedores,beneficiarios}/`. APIs: `/api/personas/search/`, `/api/subgrupos/`, `/api/funcionarios/`, `/api/cursos_por_area/`, `/ajax/barrios/`.
- **Auth:** `@login_required` + `@group_required('Admin','Lider'|'Coordinador')` mayoritario. Excepciones públicas declaradas: `inscribir_participante`, `confirmar_llegada_info_terreno`. `home_view` (`/`) redirige a `dashboard:home`.
- **Servicios:** `services/theme.py`. `decorators.py` define `group_required`.
- **Tests:** `apps/login/tests/test_smoke.py` (11 tests) — 6 listas /org/*, 2 forms (regresión perf N5), Select2 endpoint, 2 listas de actividades.
- **Estado:** Vivo, en uso continuo. `apps/login/models.py` (archivo plano) ya **borrado** (sesión 2026-04-20).

### 2.2 `apps.presupuesto` — Proyectos, CDPs, contratos, metas y KPIs
- **Propósito:** Toda la cadena financiera y planeación. Hub con 12 cards bajo `/dashboard/hub/presupuesto/`.
- **Modelos principales** (22 clases en 5 archivos: `core.py`, `core_catalogos.py`, `financiero.py`, `indicadores.py`, `sql.py`):
  - Núcleo: `Proyecto` (18), `Programa` (`programas`), `Objetivo`, `Vigencia`, `Tematica`, `CategoriaTematica`, `Area`.
  - Plan: `Actividad` (catálogo SIPSE legacy), `ActividadPlan` (42), `FaseProyecto`.
  - Financiero: `ProyectoInversion`, `ProyectoInversionItem`, `PresupuestoProyecto`, `PresupuestoTiempo`, `Cdp` (1, **NUEVO** `cdp.cdp_id` FK aplicado en sesión actual), `Crp`, `ConceptoGasto`.
  - Negocio: `MetaBD` (tabla `metas`, 20), `MetaProyectoBD` (39), `Indicador` (34), `ActividadIndicador` (20), `AvanceIndicador` (62, origen=EVENTO|MANUAL|AJUSTE).
  - Contratos: `Contrato` (96, ahora con `cdp_id`/`fecha_inicio`/`fecha_fin`/`valor`), `ContratoProyecto`, `ContratoActividad` (legacy), `ContratoActividadPlan` (0 — recién creada).
- **URLs:** prefijo `/presupuesto/` — 50+ rutas: `proyectos/`, `proyectos/<id>/` (vista 360), `programas/`, `actividades/nueva/`, `actividades-plan/<id>/`, `cdp/`, `cdp/<id>/`, `contratos/`, `contratos/<id>/vinculaciones/nueva/`, `metas/`, `meta-proyecto/`, `indicadores/`, `indicadores/<id>/`, `avances/`, `actividad-indicador/`, `conceptos/`, `objetivos/`. APIs: `api/proyectos/`, `api/actividades-por-proyecto/<id>/`, `api/plan-actividades-por-proyecto/<id>/`, `api/indicadores-por-actividad/<id>/`, `api/contratos-por-proyecto/<id>/`, `api/subgrupos/[create/]`, `ajax/conceptos/`, `ajax/proyectos/`.
- **Auth:** todas con `@login_required`. Algunas POST con `@require_POST`.
- **Servicios:** `services/metrics.py` (cálculo de saldos y avance %).
- **Tests:** `apps/presupuesto/tests/test_smoke.py` (20 tests) — 11 listas + 2 vistas 360 + 404 + 3 forms + dashboard + 2 geo.
- **Estado:** Vivo, núcleo funcional. **Cadena bloqueante** activa: `valor ≤ cdp.saldo_disponible` y `Σ ContratoActividadPlan.monto ≤ contrato.valor` ya validados en forms.

### 2.3 `apps.banco_iniciativas` — Postulación pública (proyecto 2784)
- **Propósito:** Captura específica para "Banco de Iniciativas Recreodeportivas" — 280 organizaciones objetivo. Form mobile-first sin login que llena la organización tras escanear QR del evento.
- **Modelos principales** (12 clases, todos `managed=False`):
  - Catálogos: `Upl` (9), `TipoOrganizacion` (4), `RangoExperiencia` (5), `Escenario` (13), `Implemento` (35), `RangoPoblacionAtendida` (4), `RangoEtario` (5), `CaracteristicaPoblacion` (16), `EnfoqueDiferencial` (12), `TipoBeneficioAlk` (6), `DisciplinaDeportiva` (13).
  - Cabecera: `InscripcionBancoIniciativa` (~30 columnas, FK `evento`+`organizacion` UNIQUE, 0 filas hoy).
  - 5 puentes M2M: `InscripcionBancoEscenario`, `...Implemento`, `...RangoEtario`, `...Enfoque`, `...BeneficioAlk` (todos `ON DELETE CASCADE`).
- **URLs:** prefijo `/banco-iniciativas/`:
  - Públicas: `<int:evento_id>/inscribir/`, `exitoso/<int:pk>/`.
  - Organizador: `inscripciones/`, `inscripciones/<pk>/`, `inscripciones/<pk>/validar/`.
- **Auth:** form público sin `@login_required` (con `@csrf_protect` y validación de `evento.activo` + `evento.fecha_fin >= today`, devuelve HTTP 410 si expiró). Vistas organizador: `@login_required` + `@group_required('Admin','Lider')`.
- **Servicios:** form `forms/inscripcion.py` (406 líneas) hace todo el `save()` cruzado con SQL crudo para tocar columnas no mapeadas en `organizacion` (`tipo_organizacion_codigo`, `redes_sociales` JSONB).
- **Management:** `seed_banco_iniciativas` (idempotente, registra `tipo_evento codigo='BANCO_INICIATIVAS'` y verifica catálogos).
- **Tests:** `apps/banco_iniciativas/tests/test_smoke.py` (6 tests).
- **Estado:** **Recién creado** (sesión 2026-04-28/29). Esperando primer evento `BANCO_INICIATIVAS` para proyecto 2784. La integración con `crear_evento` ya está hecha: si `tipo='BANCO_INICIATIVAS'`, el QR apunta al form público.

### 2.4 `apps.georeferenciacion` — Mapa Kennedy + cadena geográfica
- **Propósito:** Lugar, Barrio, UPZ, Localidad, GeoReferenciacion, LugarIncidencia. Mapa público `/geo/mapa-kennedy/` con eventos georreferenciados, capas (UPZ, barrios, parques, escuelas, contorno Kennedy).
- **Modelos:** `models_localizacion.py`: `Localidad` (20), `UPZ` (12), `Barrio` (325), `Lugar`, `Pais`, `Departamento`, `Municipio`, `Zona`, `GeoReferenciacion` (303 — `latitud/longitud` `Decimal(9,6)`), `LugarIncidencia` (67). `models_catalogos.py`: `Parque` (554), `Escuela` (241).
- **URLs:** prefijo `/geo/`:
  - Páginas: `mapa-kennedy/`, `graficos/`.
  - APIs lugares: `api/lugares`, `api/estadisticas`, `api/conteos`, `api/choropleth`, `api/lugares.csv`, `api/lugares/crear` (POST).
  - APIs polígonos: `api/{barrios,upz,localidad/<codigo>/,localidad/kennedy}` (todos con alias `.geojson`).
  - APIs estáticas (servidos desde disco): `api/kennedy/{contorno,barrios,upz,parques,escuelas}/`.
  - Eventos: `api/eventos/` (FeatureCollection con filtros `tipo_evento`, `desde`, `hasta`, `dependencia_id`, `subgrupo_id`).
- **Auth:** **todos los endpoints `@login_required`** (revisado `apis.py`).
- **Servicios:** `views/apis.py` (829 líneas) tiene helpers `_filters`, `_to_geojson_points`, `_resolver_upz`. `scripts/` tiene importadores GeoJSON archivados en `aplicados_2026-04-23/`.
- **Tests:** cubierto desde `apps/presupuesto/tests/test_smoke.py` (2 tests geo).
- **Estado:** Vivo. Deuda M22: 79/111 barrios sin geometry por mismatch IDECA.

### 2.5 `apps.dashboard` — Hub + IA + Dash/Plotly + breadcrumbs
- **Propósito:** Hub principal `/dashboard/`, sub-hubs por módulo (Presupuesto/Actividades/Votaciones/Admin), dashboard de presupuesto con Plotly, consulta IA con OpenAI (intent → SQL → resumen), context processors globales (breadcrumb + cache-buster mtime).
- **Modelos:** ninguno (carpeta `models/` vacía).
- **URLs:** prefijo `/dashboard/`:
  - Páginas: `/` (home), `consulta-inteligente/`, `personas/`, `presupuesto/` (Plotly), `hub/{presupuesto,actividades,votaciones,admin}/`.
  - APIs: `api/personas/query` (POST), 8 APIs presupuesto (`api/presupuesto/{objetivos-por-proyecto,objetivos-y-programas,cascada-resumen,kpis-avance,resumen-ejecutivo,eventos-mes-tipo,top-sectores,metas-progreso}/`).
  - Placeholders: `placeholder/{metas,indicadores,avances}/` (legacy, hoy todo implementado).
- **Auth:** todas con `@login_required`.
- **Servicios:** `services/breadcrumbs.py`, `services/intent_analyzer.py` (OpenAI), `services/kpis_presupuesto.py`, `services/query_builder.py`. `context_processors.py` (breadcrumbs + static_version cache-buster).
- **Tests:** `apps/dashboard/tests/test_smoke.py` (9 tests) — hub + 4 sub-hubs + breadcrumb + cache-buster + redirect login.
- **Estado:** Vivo, núcleo de UX.

### 2.6 `apps.votaciones` — Flujo de votación con QR (independiente)
- **Propósito:** Festival de votaciones. **Bilingüe (inglés/español)** — única excepción a la convención de español. No depende de la cadena presupuestal.
- **Modelos** (`models/`): `Event` (1), `Candidate` (11, dos categorías "identidades"/"derechos"), `Voter` (2, unique email), `Vote` (109).
- **URLs:** prefijo `/votaciones/`:
  - Públicas (votante): `/`, `scan/`, `api/events/`, `api/events/<id>/candidates/`, `api/results/` (admin), `api/vote/` (POST, **`csrf_exempt`**), `api/validate-voter/` (POST, **`csrf_exempt`**), `qr/event/<id>.png`, `qr/candidate/<id>.png`.
  - Funcionario: `dashboard/`, `listado/`, `registro/`, organizador `eventos/`, `artistas/` con CRUD.
- **Auth:** mixto — endpoints públicos del QR votante con `@csrf_exempt` justificado (S8). Resto con `@login_required` + `@group_required('Admin','Lider')`.
- **Servicios:** `services/vote_service.py`.
- **Tests:** ninguno propio (cubierto parcialmente por smoke tests de hub).
- **Estado:** Vivo, usado en eventos puntuales.

### 2.7 `apps.kactivo` — Cultura + Deporte (legacy parcialmente activo)
- **Propósito:** Caracterización cultura/deporte, cursos, clases, asistencia, validación documental (GridFS/MongoDB).
- **Modelos:** ~25 (`karacterizacion.py`, `kasistencia.py`, `kdocumentos.py`, `subgrupo.py`, `kregistro.py`): `CaracterizacionCultura`, `CaracterizacionDeporte`, `Acudiente`, `Docente` (0), `Actividad` (legacy SIPSE), `Curso` (0), `Programa` (`db_table=programas`, **DUPLICADO** con presupuesto, M1), `Disciplina`, `Grupo`, `Lugar` (**DUPLICADO** con geo.Lugar, M1), `Clase` (0), `HorarioClase`, `AsistenciaClase` (0), `Evento` (**DUPLICADO** con login.Evento, M1), `TipoEvento` (DUPLICADO), `Convocatoria`, `TipoAsistencia`, `ClaseParticipante`, `ParticipanteEvento`, `Dependencia` (**DUPLICADO** con login), `Subgrupo` (DUPLICADO), `TipoArchivo`, `DocumentoParticipante`, `DocumentoEvento`, `DocumentoRequisito`, `ValidacionDocumental`, `EvaluacionParticipante`, `NotaMedica`.
- **URLs:** prefijo `/kactivo/` — `cultura/`, `cultura/{participante,docente,cursos,cargue-documental,consultas,asistencia,caracterizaciones,participantes,docentes,lugares}/`, `registro/`, `documentos/<id>/`, `validacion/<id>/`, `validaciones/`. Subdirectorio `sub_grupo_cultura/` con dominio específico.
- **Auth:** todas las vistas con `@login_required`.
- **Servicios:** `services/mongo_upload.py` (GridFS activo), `services/onedrive_upload.py` (stub incompleto), `services/botones.py`.
- **Tests:** ninguno.
- **Estado:** **Parcialmente activo** — cursos/clases/asistencia con 0 filas en BD, pero validación documental sigue en uso. Convive con muchos modelos duplicados (deuda M1).

### 2.8 Apps inactivas / scaffolds
| App | INSTALLED_APPS | URLs | Estado |
|-----|----------------|------|--------|
| `apps.documento` | ❌ NO | — | Abandonada (eliminada en sesión 2026-04-20) |
| `apps.kordial` | ❌ NO (eliminada) | — | Scaffold borrado |
| `apps.VitalK` | ❌ NO (eliminada) | — | Scaffold borrado |

> Las carpetas residuales `apps/kordial/` y `apps/VitalK/` aún existen
> en disco pero **no están en `INSTALLED_APPS`** (ver settings:55-72).

---

## 3. Flujos críticos del usuario (end-to-end)

### Flujo 1 — Login + acceso al hub
- **Actor:** cualquier funcionario.
- **Pasos:**
  1. `GET /login/` → render `templates/login/login.html`.
  2. `POST /login/` → `login_view` (sin `@login_required`) autentica y redirige a `dashboard:home`.
  3. `GET /dashboard/` → `dashboard_home` (login_required) muestra 6 cards top-level por rol.
- **Modelos:** `Usuario` (AuthUser).
- **Tests:** smoke dashboard 9 (cubre redirect anónimo y hub).
- ⚠ Riesgo: `login_view` no aplica rate-limit a nivel Django; depende de nginx zona `login` 5 req/s.

### Flujo 2 — Crear actividad (evento) genérico
- **Actor:** Admin / Líder.
- **Pasos:**
  1. `GET /evento/crear/` → form con cascadas (Dependencia→Subgrupo→Funcionario, Proyecto→ActividadPlan→Indicador, TipoEvento, ubicación Leaflet).
  2. JS pobla cascadas via `/api/subgrupos/?area_id=`, `/api/funcionarios/?subgrupo_id=`, `/presupuesto/api/plan-actividades-por-proyecto/<id>/`, `/presupuesto/api/indicadores-por-actividad/<id>/`, `/presupuesto/api/contratos-por-proyecto/<id>/`.
  3. Click en mapa Leaflet captura `latitud/longitud` (validados rango Colombia).
  4. `POST /evento/crear/` → `crear_evento` valida cascadas, crea `Lugar→GeoReferenciacion→LugarIncidencia` en transacción, inserta `Evento`, crea `AvanceIndicador(origen='EVENTO')` con magnitud, opcionalmente crea `ContratoActividadPlan(monto=0)`. Genera QR con URL específica por tipo.
  5. Si `tipo='INFO_TERRENO'`, además crea `EventoInfoTerreno`.
- **URL del QR según tipo:**
  - `INFO_TERRENO` → `/evento/info-terreno/confirmar/<id>/`
  - `BANCO_INICIATIVAS` → `/banco-iniciativas/<id>/inscribir/` (form público)
  - resto → `/evento/inscripcion/<id>/` (form participantes)
- **Modelos tocados:** `Evento`, `LugarIncidencia`, `GeoReferenciacion`, `Lugar`, `AvanceIndicador`, `ContratoActividadPlan`, `EventoInfoTerreno`.
- **Tests:** smoke login 11 (forms cascadas).
- ⚠ Riesgo: SI `evento_id_seq` no existe → `IntegrityError` reportado al usuario (manejado, mensaje claro). Cascada B (actividad+indicador+magnitud) es **obligatoria**, no se pueden crear eventos "huérfanos".

### Flujo 3 — Crear actividad BANCO_INICIATIVAS + inscripción pública por QR
- **Actor:** Admin/Líder crea evento; **Organización pública** llena la inscripción.
- **Pasos (organizador):**
  1. Igual al flujo 2, pero seleccionando `tipo_evento='BANCO_INICIATIVAS'`.
  2. El QR generado apunta a `/banco-iniciativas/<evento_id>/inscribir/`.
  3. Organizador imprime/comparte el QR; lo escanea la organización postulante.
- **Pasos (postulante público, sin login):**
  4. `GET /banco-iniciativas/<id>/inscribir/` → si `evento.activo=False` o `fecha_fin < today`, devuelve HTTP 410. Si OK, render `form_publico.html` (8 secciones colapsables).
  5. `POST` mismo URL → `InscripcionBancoForm.save()` crea/actualiza `Organizacion` (vía SQL crudo para `tipo_organizacion_codigo`+`redes_sociales` JSONB), crea `InscripcionBancoIniciativa` + 5 M2M (escenarios, implementos, rangos etarios, enfoques, beneficios ALK).
  6. Redirect a `/banco-iniciativas/exitoso/<pk>/`.
- **Pasos (validación organizador):**
  7. Login → `/banco-iniciativas/inscripciones/` (paginada, filtros).
  8. `GET /banco-iniciativas/inscripciones/<pk>/` → detalle.
  9. `POST /banco-iniciativas/inscripciones/<pk>/validar/` → cambia `estado='validada'` o `'rechazada'`.
- **Modelos tocados:** `Evento`, `Organizacion`, `InscripcionBancoIniciativa` + 5 puentes.
- **Tests:** smoke banco 6.
- ⚠ Riesgos:
  - El form público es **anónimo**: depende de nginx rate-limit + `@csrf_protect` + UNIQUE `(evento_id, organizacion_id)`. No hay captcha. → Si hay spam masivo, mitigación es solo nginx.
  - `form.save()` usa SQL crudo para columnas no mapeadas; si falla mid-write puede dejar Organizacion creada sin Inscripcion (transacción no envuelve los UPDATEs crudos).

### Flujo 4 — Cadena financiera: CDP → Contrato → vincular a ActividadPlan
- **Actor:** Admin/Líder.
- **Pasos:**
  1. `GET /presupuesto/cdp/nuevo/` → form CDP. Captura proyecto, valor, fecha.
  2. `GET /presupuesto/contratos/nuevo/` → `ContratoForm` filtra CDPs del proyecto seleccionado. Validación: `valor ≤ cdp.saldo_disponible` (mensaje "Saldo insuficiente del CDP {n}: disponible $X, contrato $Y").
  3. `GET /presupuesto/contratos/<id>/vinculaciones/nueva/` → `ContratoActividadPlanForm`. Valida `Σ vinculaciones ≤ contrato.valor` (sobre-asignación bloqueada).
  4. Detalle proyecto `/presupuesto/proyectos/<id>/` muestra cards por CDP con barra color (verde/amarillo/rojo).
  5. Detalle CDP `/presupuesto/cdp/<id>/` muestra contratos hijos + saldo libre.
- **Modelos:** `Cdp`, `Contrato` (con `cdp_id` FK), `ContratoActividadPlan`, `Proyecto`, `MetaProyectoBD`, `ConceptoGasto`.
- **Tests:** smoke presupuesto 20 (cubre listas + 2 vistas 360 + forms).
- ⚠ Riesgo: 96 contratos legacy con `valor=NULL` y `cdp_id=NULL` (no migrados). El form salta validación si valor=NULL → técnicamente puede crear contratos sin cdp.

### Flujo 5 — Registrar avance de KPI (manual y automático)
- **Actor:** Admin/Líder.
- **Pasos automáticos:** ver Flujo 2 — `crear_evento` inserta `AvanceIndicador(origen='EVENTO')` con la magnitud. `editar_evento` sincroniza el avance y cambia origen a `'AJUSTE'` con observación auditable.
- **Pasos manuales:**
  1. `GET /presupuesto/avances/nuevo/` → `AvanceIndicadorForm` (force `origen='MANUAL'`).
  2. `POST` crea `AvanceIndicador(indicador_id, magnitud, fecha_aporte, periodo='YYYY-MM', origen='MANUAL')`.
  3. Indicador detalle `/presupuesto/indicadores/<id>/` muestra barra de progreso + lista avances + actividades vinculadas.
- **Modelos:** `Indicador` (KPI), `AvanceIndicador`, `ActividadIndicador`.
- **Tests:** smoke presupuesto cubre lista de avances.
- ⚠ Riesgo: edición de evento permite cambiar magnitud (auditado), pero NO cambiar `indicador_id`/`actividad_plan_id` (intencional, evita huérfanos).

### Flujo 6 — Vista 360° del Proyecto
- **Actor:** Admin/Líder/Funcionario autenticado.
- **Pasos:**
  1. `GET /presupuesto/proyectos/<id>/` → 5 tiles (CDPs, Metas, KPIs, % avance, Saldo presupuestal).
  2. Sección Dinero (CDPs con barras color) + sección Contratos (con monto comprometido) + sección Metas+KPIs (barras ≥80/≥50/<50) + sección Actividades del plan (link a vista 360 de cada una).
- **Modelos:** `Proyecto`, `Cdp`, `Contrato`, `MetaProyectoBD`, `Indicador`, `AvanceIndicador`, `ActividadPlan`.
- **Tests:** `presupuesto/test_smoke.py::test_proyecto_detalle_360`.
- ⚠ Riesgo: `prefetch_related` anidado puede ser caro si proyecto tiene muchos KPIs.

### Flujo 7 — Mapa de Kennedy con eventos georreferenciados
- **Actor:** funcionario autenticado.
- **Pasos:**
  1. `GET /geo/mapa-kennedy/` → render `geo-mapas/mapa_kennedy.html` con sidebar de filtros.
  2. JS carga: contorno (`api/kennedy/contorno/`), capas opcionales (UPZ, barrios, parques, escuelas), eventos vía `/geo/api/eventos/?tipo_evento=...&dep=...`.
  3. Filtros en cascada: Dependencia→Subgrupo, UPZ→Barrio.
- **Modelos:** `Evento` + `LugarIncidencia` + `GeoReferenciacion` (joinea coords), `Parque`, `Escuela`, `Barrio`, `UPZ`.
- **Tests:** smoke presupuesto 2 (cubre `/geo/api/eventos/` y mapa).
- ⚠ Riesgo: `/api/eventos/` solo acepta un valor por filtro (no `__in` multiselect). 79/111 barrios sin geometry (M22).

### Flujo 8 — Votaciones (módulo independiente con QR)
- **Actor:** votante anónimo escanea QR. Organizador con login.
- **Pasos votante:**
  1. Escanea QR `/votaciones/qr/event/<id>.png` → URL del evento.
  2. `GET /votaciones/api/events/` → lista activa. `GET /votaciones/api/events/<id>/candidates/` → candidatos.
  3. `POST /votaciones/api/validate-voter/` (csrf_exempt) → valida documento.
  4. `POST /votaciones/api/vote/` (csrf_exempt) → registra voto.
- **Pasos organizador:**
  5. `GET /votaciones/dashboard/` (Admin/Lider) → resultados live.
  6. CRUD eventos+artistas en `/votaciones/organizador/...`.
- **Modelos:** `Event`, `Candidate`, `Voter`, `Vote`.
- **Tests:** ninguno propio.
- ⚠ Riesgo: 2 endpoints `csrf_exempt` documentados (S8 deuda histórica resuelta) — depende de nginx rate-limit. Sin tests automatizados.

---

## 4. Endpoints HTTP por módulo (resumen)

> Cuenta total: ~150+ endpoints en 7 apps. Aquí el subset crítico. Para
> lista exhaustiva ver `urls.py` de cada app.

### `apps.login` (selección — 36 rutas)
| Método | URL | Vista | Auth | Retorno |
|--------|-----|-------|------|---------|
| GET/POST | `/login/` | `login_view` | público | HTML |
| POST | `/logout/` | `logout_view` | login | redirect |
| GET | `/` | `home_view` | público | redirect dashboard |
| GET/POST | `/crear-persona/` | `crear_persona` | login + Admin/Coord | HTML |
| GET/POST | `/evento/crear/` | `crear_evento` | login + Admin/Lider | HTML+QR |
| GET | `/eventos/` | `listar_eventos` | login | HTML |
| GET/POST | `/evento/<id>/editar/` | `editar_evento` | login + Admin/Lider | HTML |
| GET/POST | `/evento/inscripcion/<id>/` | `inscribir_participante` | login | HTML |
| GET | `/api/personas/search/?q=` | `api_personas_search` | login | JSON |
| GET | `/api/subgrupos/?area_id=N` | `subgrupos_por_area` | login | JSON |
| GET/POST | `/org/{dep,sub,func,org,prov,benef}/[nuevo|<pk>/editar]/` | `admin_org.*` | login | HTML |

### `apps.banco_iniciativas` (5 rutas)
| Método | URL | Vista | Auth | Retorno |
|--------|-----|-------|------|---------|
| GET/POST | `/banco-iniciativas/<id>/inscribir/` | `inscripcion_banco_form` | **público** + csrf_protect | HTML/HTTP 410 |
| GET | `/banco-iniciativas/exitoso/<pk>/` | `inscripcion_exitosa` | público | HTML |
| GET | `/banco-iniciativas/inscripciones/` | `inscripciones_list` | login + Admin/Lider | HTML |
| GET | `/banco-iniciativas/inscripciones/<pk>/` | `inscripcion_detalle` | login + Admin/Lider | HTML |
| POST | `/banco-iniciativas/inscripciones/<pk>/validar/` | `inscripcion_validar` | login + Admin/Lider | redirect |

### `apps.presupuesto` (50+ rutas — selección)
| Método | URL | Vista | Auth | Retorno |
|--------|-----|-------|------|---------|
| GET | `/presupuesto/proyectos/` | `proyectos_list` | login | HTML |
| GET | `/presupuesto/proyectos/<id>/` | `proyecto_detalle` (vista 360) | login | HTML |
| GET | `/presupuesto/actividades-plan/<id>/` | `actividad_plan_detalle` | login | HTML |
| GET | `/presupuesto/contratos/<id>/` | `contrato_detalle` | login | HTML |
| GET | `/presupuesto/cdp/<id>/` | `cdp_detalle` | login | HTML |
| GET | `/presupuesto/indicadores/<id>/` | `indicador_detalle` | login | HTML |
| GET | `/presupuesto/api/contratos-por-proyecto/<id>/` | `api_contratos_por_proyecto` | login | JSON |
| GET | `/presupuesto/api/indicadores-por-actividad/<id>/` | `api_indicadores_por_actividad` | login | JSON |

### `apps.georeferenciacion` (24 rutas — todas login)
| Método | URL | Auth | Retorno |
|--------|-----|------|---------|
| GET | `/geo/mapa-kennedy/` | login | HTML+Leaflet |
| GET | `/geo/api/eventos/` | login | GeoJSON |
| GET | `/geo/api/kennedy/{contorno,barrios,upz,parques,escuelas}/` | login | GeoJSON |
| POST | `/geo/api/lugares/crear` | login | JSON |

### `apps.dashboard` (16 rutas — todas login)
| Método | URL | Vista | Retorno |
|--------|-----|-------|---------|
| GET | `/dashboard/` | `dashboard_home` | HTML |
| GET | `/dashboard/hub/{presupuesto,actividades,votaciones,admin}/` | `hub_*` | HTML |
| GET | `/dashboard/consulta-inteligente/` | `dashboard_ai_view` | HTML+OpenAI |
| POST | `/dashboard/api/personas/query` | `personas_query_api` | JSON |
| GET | `/dashboard/api/presupuesto/{kpis-avance,resumen-ejecutivo,...}/` | varios | JSON |

### `apps.votaciones` (~28 rutas)
| Método | URL | Auth | Notas |
|--------|-----|------|-------|
| GET | `/votaciones/scan/` | público | escaneo QR |
| GET | `/votaciones/api/events/` | público | JSON |
| POST | `/votaciones/api/vote/` | **csrf_exempt** | JSON, votante anónimo |
| POST | `/votaciones/api/validate-voter/` | **csrf_exempt** | JSON |
| GET | `/votaciones/dashboard/` | login + Admin/Lider | HTML |
| GET | `/votaciones/api/results/` | login + Admin/Lider | JSON |

### `apps.kactivo` (~25 rutas — todas login)
Páginas shell `/kactivo/cultura/{participante,docente,cursos,...}/`,
registro `/kactivo/registro/` y subrutas, validación documental,
exportar Excel.

---

## 5. Modelos de datos (resumen)

### 5.1 Resumen cuantitativo

| App | # Modelos | # Filas (suma aproximada) | Notas |
|-----|-----------|---------------------------|-------|
| `apps.login` | ~24 | 6 938 personas + 18 funcionarios + 101 eventos + 3 580 beneficiarios | catálogos demográficos pesados |
| `apps.presupuesto` | 22 | 18 proyectos · 96 contratos · 1 CDP · 42 actividades · 34 KPIs · 62 avances | núcleo financiero |
| `apps.banco_iniciativas` | 12 | 122 (catálogos) · 0 inscripciones | recién cargado |
| `apps.georeferenciacion` | 11 | 325 barrios · 12 UPZ · 554 parques · 241 escuelas · 67 lugar_incidencia | M22 79/111 barrios sin geom |
| `apps.dashboard` | 0 | — | no tiene modelos propios |
| `apps.votaciones` | 4 | 1 evento · 11 candidatos · 109 votos | bilingüe, tablas con prefijo `votaciones_` |
| `apps.kactivo` | ~25 | varias tablas con 0 filas (cursos/clases/asistencias) | parcialmente activo, mucho M1 |

**Total Django models:** ~98 clases con `db_table`. **Todos `managed=False`.**

### 5.2 Modelos polimórficos / patrones especiales

| Modelo | Tipo de polimorfismo | Notas |
|--------|----------------------|-------|
| `Beneficiario` | persona / proveedor / organizacion | Form valida cruzado, bloquea persona si Funcionario activo |
| `Evento` | tipo_evento_codigo controla flujo (genérico / INFO_TERRENO / BANCO_INICIATIVAS) | URL del QR cambia, datos extra en tablas específicas |
| `AvanceIndicador.origen` | EVENTO / MANUAL / AJUSTE | EVENTO se autogenera; AJUSTE se crea al editar magnitud |

### 5.3 Modelos duplicados (deuda M1, ALTA)

| `db_table` | Apps que lo declaran | Cuál usar |
|------------|----------------------|-----------|
| `dependencia` | login + kactivo | **login** (canónico) |
| `subgrupo` | login + kactivo | **login** |
| `programas` | presupuesto + kactivo | **presupuesto** |
| `actividad` | presupuesto + kactivo | **presupuesto** |
| `lugar` | georeferenciacion + kactivo | **geo** |
| `zona` | login + georeferenciacion | **login** (`Zona` para Persona); geo declara también `Zona` (revisar) |
| `evento` | login + kactivo | **login** (kactivo legacy) |
| `tipo_evento` | login + kactivo | **login** |

---

## 6. Catálogos (cómo se llenan)

### 6.1 Catálogos demográficos `apps.login` (todos manuales o seed inicial)
26 catálogos: `Sexo`, `IdentidadGenero`, `OrientacionSexual`, `GrupoEtnico`, `TipoDiscapacidad`, `TipoVictima`, `Zona`, `NivelEducativo`, `Ocupacion`, `SectorEconomico`, `TipoConstruccion`, `AfiliacionSalud`, `EPS`, `ARL`, `AccesoSalud`, `CalidadAccesoSalud`, `TipoDispositivo`, `TipoVivienda`, `ServicioBasico`, `TipoRedSocial`, `NivelSocioeconomico`, `EstadoCivil`, `TenenciaVivienda`, `TipoSalud`, `TipoSangre`, `GrupoEtario`. Llenados manualmente desde Adminer/SQL al setup inicial.

### 6.2 Catálogos presupuestales (manuales con UI)
`Vigencia`, `Tematica`, `CategoriaTematica`, `Objetivo`, `Programa`, `Area`, `ConceptoGasto`, `MetaBD`, `FaseProyecto`. CRUDs en `/presupuesto/conceptos/`, `/objetivos/`, `/metas/`, `/programas/`. Algunos seeds manuales en BD.

### 6.3 Catálogos geográficos (importadores GeoJSON archivados)
`Localidad`, `UPZ`, `Barrio`, `Parque`, `Escuela`. Importadores en `apps/georeferenciacion/scripts/aplicados_2026-04-23/` (archivados, no rehacer). UPZ POT 2022 + parques de IDECA (3857→WGS84) + escuelas Cultura+Deporte.

### 6.4 Catálogos Banco de Iniciativas (DDL aplicado en sesión 2026-04-28)
| Tabla | Filas | Cómo se cargó |
|-------|-------|---------------|
| `upl` | 9 | DDL inicial (UPLs Kennedy POT 2022) |
| `tipo_organizacion` | 4 | DDL inicial |
| `rango_experiencia` | 5 | DDL inicial |
| `escenario` | 13 | DDL inicial (canchas/coliseos/parques) |
| `implemento` | 35 | DDL inicial (categoría deportivo/tecnologico/logistico) |
| `rango_poblacion_atendida` | 4 | DDL inicial |
| `rango_etario` | 5 | DDL inicial |
| `caracteristica_poblacion` | 16 | DDL inicial |
| `enfoque_diferencial` | 12 | DDL inicial |
| `tipo_beneficio_alk` | 6 | DDL inicial |
| `disciplina_deportiva` | 13 | DDL inicial |
| `nivel_educativo` (extendido) | +1 | INSERT codigo 9 'Curso o diplomado' |
| `tipo_evento` (extendido) | +1 | `BANCO_INICIATIVAS` vía management command idempotente `seed_banco_iniciativas` |

### 6.5 Catálogos votaciones
Manual desde organizador UI.

---

## 7. Estado de cobertura de tests

**Total:** 46 smoke tests pasando (verificado contra el árbol actual).
Hook pre-push corre `scripts/run_smoke_tests.py` antes de cada push.

| Módulo | Archivo | # Tests | Cubre | NO cubre |
|--------|---------|---------|-------|----------|
| `apps.dashboard` | `tests/test_smoke.py` | 9 | hub principal + 4 sub-hubs + breadcrumb + cache-buster + redirect anónimo | personas_query_api (POST), Dash apps |
| `apps.login` | `tests/test_smoke.py` | 11 | 6 listas /org/* + 2 forms (regresión perf N5) + Select2 + 2 actividades | crear_evento POST, editar_evento POST, inscribir_participante, info_terreno |
| `apps.presupuesto` | `tests/test_smoke.py` | 20 | 11 listas + 2 vistas 360 + 404 + 3 forms + dashboard + 2 geo | POST de contratos, validación de saldos, vinculaciones |
| `apps.banco_iniciativas` | `tests/test_smoke.py` | 6 | (lista + detalle + form público GET + 410 expirado + redirect organizador) | POST del form público (escritura M2M), validación de duplicados, inscripcion_validar POST |
| `apps.kactivo` | — | 0 | nada | TODO |
| `apps.votaciones` | — | 0 | nada | TODO |
| `apps.georeferenciacion` | — | 0 (usa los 2 de presupuesto) | nada propio | api_eventos filtros, api_crear_lugar POST |

**Estrategia:** `unittest.TestCase` puro (no Django TestCase), bypass del runner (BD externa managed=False). Solo GETs read-only para no contaminar la BD compartida. Sin coverage medido.

**Áreas con cobertura cero (riesgo):**
- POST de escritura en TODOS los módulos (excepto Select2 perf check).
- Flujo público de `banco_iniciativas` (lo más crítico — captura los 280 datos de organizaciones).
- Votaciones (`api_vote`, `api_validate_voter`) — endpoints `csrf_exempt`.
- kactivo (validación documental, GridFS).
- Forms de cadena financiera (validación de saldo CDP, sobre-asignación contrato).

---

## 8. Hallazgos durante el mapeo

### Crítico
- **[H-1] CRÍTICO** — Form público `banco_iniciativas` sin captcha ni rate-limit a nivel Django. Solo nginx (`general` 60 r/s burst 120). Si un atacante distribuye, puede crear muchas `Organizacion` antes de que se note. Constraint UNIQUE evita inscripción duplicada pero NO crear organizaciones basura. **Recomendación:** considerar honeypot + delay mínimo antes de aceptar POST.

### Alto
- **[H-2] ALTO** — `crear_evento` y form público `banco_iniciativas` cuando la creación falla en mid-write: el form de Banco usa SQL crudo para `tipo_organizacion_codigo`/`redes_sociales` JSONB **fuera** del `transaction.atomic()` implícito de Django ORM. Si SQL crudo falla, queda Organizacion creada sin Inscripcion.
- **[H-3] ALTO** — 96 contratos legacy con `valor=NULL` y `cdp_id=NULL` (no migrados). El form Edita salta validación de saldo si `valor=NULL`. Permite bypass involuntario de la cadena bloqueante.
- **[H-4] ALTO** — `apps.votaciones.api_vote` y `api_validate_voter` con `@csrf_exempt` y sin tests automatizados. Son endpoints que escriben (Vote 109 filas hoy). Cobertura pre-push CERO.

### Medio
- **[H-5] MEDIO** — 8 modelos duplicados `db_table` entre login/kactivo/presupuesto/geo (deuda M1 ALTA conocida). `kactivo.Programa` ↔ `presupuesto.Programa` puede generar queries silenciosamente diferentes.
- **[H-6] MEDIO** — `apps/login/views/eventos.py` 993 líneas (deuda M6). `crear_evento` 280 líneas con 8 retornos por error duplicando el render. Riesgo de regresión.
- **[H-7] MEDIO** — `apps.kactivo` con muchas tablas a 0 filas (`curso`, `clase`, `asistencia_clase`, `docente`) pero código vivo y vistas con `@login_required`. Confunde al desarrollador nuevo si toca.
- **[H-8] MEDIO** — `crear_evento` recibe `hora_inicio` del form pero no la persiste (modelo Evento no tiene columna). Documentado en código pero el form sigue mostrando el campo.
- **[H-9] MEDIO** — `apps.dashboard` no tiene `models/` (carpeta `__pycache__` solo). Confuso para grep estructural — `apps.dashboard.models` no existe en sentido estricto.

### Bajo / nice-to-have
- **[H-10] BAJO** — `home_view` está en `apps/login/views/home.py` y solo redirige; queda como ruta `/` sin `@login_required` (intencional — redirige a login si anónimo).
- **[H-11] BAJO** — `apps.kordial` y `apps.VitalK` ya **no están** en INSTALLED_APPS pero las carpetas viven en disco con `apps.py` y `__init__.py`. Borrarlas físicamente.
- **[H-12] BAJO** — `apps.documento` también ausente de INSTALLED_APPS pero código vivo en disco. Confunde grep.
- **[H-13] BAJO** — `LANGUAGE_CODE` y `TIME_ZONE` declarados una vez (settings.py:139-140) — **deuda M7 documentada como duplicada está RESUELTA**, settings actual no tiene duplicación. Actualizar `DEUDA_TECNICA.md` si aplica.

---

## 9. Glosario rápido

| Término | Definición |
|---------|-----------|
| **SIPSE** | Sistema oficial de la Alcaldía de Bogotá donde se reportan proyectos. Modelo de negocio canónico. Ver `docs/referencia/SIPSE.md`. |
| **CDP** | Certificado de Disponibilidad Presupuestal. Dinero asignado al proyecto. Tabla `cdp`. |
| **CRP** | Certificado de Registro Presupuestal. Compromiso del CDP a un contrato. Tabla `crp`. |
| **KPI** | Indicador de meta (`presu_indicador_meta_proyecto`). Cada KPI cuelga de una `MetaProyecto`. |
| **Avance** | Aporte concreto a un KPI (`presu_avance_ind_periodo`). origen=EVENTO/MANUAL/AJUSTE. |
| **ActividadPlan** | Actividad operativa del plan de proyecto (tabla `actividad_plan`). NO confundir con `actividad` (catálogo SIPSE legacy). Los eventos cuelgan de aquí. |
| **MetaProyecto** | Meta cuantitativa de un proyecto (`meta_proyecto`). Vincula `Proyecto` ← `MetaBD`. |
| **UPL** | Unidad de Planeación Local (POT 2022). 9 UPLs en Kennedy. Tabla `upl`. |
| **UPZ** | Unidad de Planeamiento Zonal. 12 UPZ en Kennedy. Tabla `upz`. |
| **IDECA** | Infraestructura de Datos Espaciales del Distrito Capital. Fuente de barrios/UPZ/parques. |
| **ALK** | Alcaldía Local de Kennedy. |
| **Banco de Iniciativas** | Proyecto 2784 — convocatoria a 280 organizaciones para postular iniciativas recreodeportivas. App `banco_iniciativas`. |
| **INFO_TERRENO** | Tipo de evento donde un funcionario va a campo a confirmar llegada con GPS+fotos. |
| **Cadena bloqueante financiera** | Validaciones forzadas: `Σ contratos.valor ≤ CDP.saldo` y `Σ vinculaciones ≤ contrato.valor`. |
| **Vista 360°** | Pantallas que agregan toda la info de un Proyecto/ActividadPlan/CDP/Contrato en una sola vista. |
| **Hub / Sub-hub** | Pantalla principal `/dashboard/` con cards por módulo + sub-hubs especializados. |

---

## 10. Documentos relacionados (canónicos vivos)

- [`/CLAUDE.md`](../CLAUDE.md) — Memoria operativa para Claude Code (incluye §11 bitácora histórica).
- [`docs/README.md`](./README.md) — Índice navegable de toda la documentación.
- [`docs/ARQUITECTURA.md`](./ARQUITECTURA.md) — Stack, infra, IPs, APIs externas.
- [`docs/DEUDA_TECNICA.md`](./DEUDA_TECNICA.md) — Deuda viva + resueltos.
- [`docs/referencia/SIPSE.md`](./referencia/SIPSE.md) — Marco oficial SIPSE + cadena Proyecto→Meta→KPI.
- [`docs/propuestas/`](./propuestas/) — Propuestas vivas (instancias, formularios por tipo, ux pendiente).
- [`docs/_historico/`](./_historico/) — Planes ejecutados y hallazgos resueltos (referencia histórica).
- [`scripts/run_smoke_tests.py`](../scripts/run_smoke_tests.py) — Runner de los 46 smoke tests.

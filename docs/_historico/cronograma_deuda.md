# Cronograma de deuda técnica resuelta — innovaK

Histórico de los 61 ítems de deuda cerrados, agrupados por sesión. Cada
entrada lista el ID, el commit (si está disponible) y un resumen denso.
La deuda **pendiente** vive en [`DEUDA_TECNICA.md`](../DEUDA_TECNICA.md).

---

## 2026-04-20 — Auditoría inicial + hotfix S1-S4

Cuatro hallazgos críticos de configuración resueltos en cascada
`feat → desarrollo → Pruebas → produccion` el mismo día.

| ID | Resumen |
|----|---------|
| S1 | `SECRET_KEY` movido a `.env` (antes hardcoded en `settings.py`) |
| S2 | `DEBUG` leído de `.env` (antes `True` fijo) |
| S3 | `ALLOWED_HOSTS` desde `.env` (antes `['*']`) |
| S4 | `ONEDRIVE_TOKEN` desde `.env` (antes en repo) |
| M2 | App `apps/documento/` eliminada (abandonada, sin uso) |
| M3 | Apps `kordial` y `VitalK` eliminadas (scaffolds vacíos) |
| M4 | `apps/login/models.py` eliminado (archivo muerto que coexistía con `models/`) |

---

## 2026-04-23 — Refactor mapa Kennedy

| ID | Resumen |
|----|---------|
| M12 | Template `mapa_kennedy_standalone.html` creado |

---

## 2026-04-25/27 — Cierre módulo Actividades (9 PRs cascadeados)

Jornada maratón con cadena financiera + cierre presupuestal completo.

| ID | Resumen |
|----|---------|
| C1 | PR-H3 (`868e758`): quitado prefijo `public.` en 3 modelos de Contrato |
| N1 | Fix `b48a0dd`: fallback MAX+1 en `contrato_nuevo` |
| N2 | DDL 2026-04-27: `CREATE SEQUENCE proveedor_id_seq` |
| N4 | Fix `427ec36`: `IntegerField` sueltos → `ForeignKey` formal |
| N5 | Fix `70a67c5`: Select2 + endpoint AJAX para selectores de Persona |
| N6 | Fix `427ec36`: `verbose_name_plural` copy-paste corregido |
| N7 | Fix `427ec36`: `__str__` agregado a Proyecto/Actividad/ActividadPlan |
| N8 | Falsa alarma: `metas.codigo` es `IDENTITY ALWAYS` (PG10+) |
| P3 | Cubierto por N5 (Persona con Select2 AJAX, sin `.all()`) |
| Bug | PR-G (`a91c22c`): `Lower()` sin importar en `actividad_nueva` |
| Cache | PR-H1 (`a8a3557`): cache-buster con mtime de `base.css` |

---

## 2026-04-27 — Quick wins + hardening pre-gov.net

Tarde dedicada a deuda técnica y endurecimiento.

| ID | Resumen |
|----|---------|
| M5 | `apps/votaciones/apps.py` creado |
| M7 | Duplicados `LANGUAGE_CODE`/`TIME_ZONE` consolidados en settings |
| M8 | Dockerfile alineado con docker-compose (EXPOSE 8032 + CMD gunicorn) |
| M9 | Comentarios doc Django 4.2 |
| M13 | Lectura única de `DEBUG` en settings |
| M10 | 40 smoke tests en `apps/*/tests/test_smoke.py` ejecutables con `scripts/run_smoke_tests.py` |
| P1 | Paginación (page_size=25) en 6 listas grandes (beneficiarios 3580→144 págs, contratos, avances, organizaciones, meta_proyecto, indicadores). Partial reutilizable `templates/_partials/paginator.html` |
| S5 | Eliminado patrón `MAX(id)+1` en 4 sitios (persona, persona+participante en inscripción, cdp). Las tablas ya tenían secuencia; refactor con `INSERT...RETURNING id` y `obj.save()` directo |
| S6 | INSERT con f-string en `eventos.py:743` reforzado con whitelist `_ALLOWED_PERSONA_COLS` + `raise ValueError` si llega columna no permitida |
| S7 | 53 vistas nuevas con `@login_required` en 13 archivos. Smoke 20 URLs sin login → 20 redirigen a `/login/` |
| S8 | `api_crear_lugar` ya NO es `csrf_exempt` — valida CSRF + `@login_required`. Frontend envía `X-CSRFToken` desde cookie. `api_validate_voter`/`api_vote` mantienen `csrf_exempt` (votante público con QR, protegido por rate limit nginx 60r/s) |
| C5 (parcial) | Votaciones ya no tiene login propio. `staff_login`/`staff_logout` eliminados; usa `@login_required` + `@group_required` consistente con el resto. Pendiente: rename de modelos a español |
| Infra (nginx) | Reescrito con gzip + 5 security headers + rate limiting (general 60r/s, login 5r/s) + keepalive upstream + endpoint `/healthz` + página 503 amigable |
| Infra (Redis) | Django CACHES configurado contra Redis (db /1) + sesiones movidas a `cached_db`. Resuelve "se cayó otra app porque solo usaba la web y no nginx ni redis" |
| Feature (votaciones) | Voto múltiple administrable: campo `votos_permitidos` (default=1) en Event. Constraint UNIQUE eliminado, validación pasada al servicio `register_vote`. DDL: 2 ALTER |
| PR-J1 | 4 fixes detectados por agentes (django-security + a11y + wcag): trazas Exception en `dashboard_ai_view` → mensaje genérico; hint color en `_empty-state.scss` 2.8:1 → 4.6:1; 50 `<th scope="col">` en 8 listas; 118 emojis envueltos en `<span aria-hidden="true">` en 54 templates |
| PR-J2 / P2 | DDL CONCURRENTLY: `idx_barrio_upz`, `idx_pev_evento`, `idx_pev_part`, `idx_municipio_dpto`. Cache server-side `@cache_page` en 5 endpoints geo (api_eventos 5min, parques/escuelas 5min, barrios/upz 1h). Catálogos del mapa cacheados 1h. `SESSION_ENGINE: cached_db → cache` (Redis con TTL). `/geo/api/eventos/` cold 378ms → cached 1ms (378× speedup) |
| PR-J3 / M11 | Hardening: (1) logger estructurado key=value (`ts=... level=INFO logger=apps.X pid=N msg=...`) parseable por Loki; (2) hook git pre-push corre smoke tests, aborta si fallan; (3) settings TLS-ready condicionales detrás de `BEHIND_TLS=true` en `.env` |

---

## 2026-04-29 — Banco de Iniciativas + mapa data-driven

| ID | Resumen |
|----|---------|
| N11 | `TipoEvento.color_hex` + `css_slug` (property determinística); template con `{% for %}` sobre `tipos_evento_list`; JS lee colores desde `window.__COLORES_TIPO_EVENTO`. Cada `TipoEvento` nuevo aparece sin tocar template/JS/CSS |
| N13 | `ALTER TABLE ... ADD COLUMN id BIGSERIAL UNIQUE NOT NULL` en 5 tablas puente M2M del Banco (`inscripcion_banco_escenario`, `_implemento`, `_rango_etario`, `_enfoque`, `_beneficio_alk`). PK compuesta original preservada |

---

## 2026-04-30 — Daniel Lugo + N12 wizards + N15 PR-1/PR-2

| ID | Resumen |
|----|---------|
| Hub-card-presupuesto | Card "Presupuesto" en `/dashboard/` ahora aplica `is_admin_o_lider` consistente con "Administración". CoordinadorDeportes ya no la ve (`ff8691e`) |
| Perfil + cambio password | Vistas `/perfil/` y `/perfil/cambiar-password/` con `PasswordChangeForm` + `update_session_auth_hash`. Topbar "Mi Perfil" antes era `href="#"` (`5f0692e`) |
| N14 | Firma del Banco obligatoria (foto cámara o URL) + UX cámara con botón grande, preview, validación <2MB JS (`6d820cf`) |
| usuario_grupos UNIQUE | Tabla M2M `usuario_grupos` no tenía `UNIQUE(usuario_id, group_id)`; `alexjut` aparecía 3 veces en Admin. Borrados duplicados (17→15 filas) + ADD CONSTRAINT + `.distinct()` defensivo (`3d6639d`) |

---

## 2026-05-04 — Cierre N15 + N12 + M1 parcial

8 cascadas a producción en una jornada.

| ID | Resumen |
|----|---------|
| N15 | Cierre del sistema de roles dinámico. Migrados 145 endpoints a `@modulo_required` (43 simples + 76 presupuesto/dashboard + 26 kactivo). Sidebar dinámico vía context processor `modulos_usuario`. Cards de hubs filtradas individualmente por módulo. Bugs resueltos: substring match `'Admin,Lider'`, solo primer grupo, lógica duplicada en 4 hubs. Módulos nuevos: `personas_registro`, `votaciones_admin/_votantes`, `kactivo_participantes`. Matriz por rol consolidada en `seed_modulos.ASIGNACION_INICIAL` |
| N16 | Documento Mongo huérfano `_id=69f26eb...e424` borrado con `delete_one` defensivo (filtro por `owner.tipo` + `inscripcion_id`). Pre-borrado verificado que la fila SQL ya no existe |
| N10 | `requirements.txt` pinea `redis==5.3.1` (antes `>=5.0,<6`). Build determinístico pre-gov.net |
| P4 | 15 índices ya creados en BD declarados en `Meta.indexes` de Evento×7, ActividadPlan, MetaProyecto, Indicador×2, AvanceIndicador×4. Solo declaración Django (managed=False), no DDL |
| M6 | `apps/login/views/eventos.py` (1077 líneas) convertido en paquete `eventos/` con 5 sub-archivos por dominio: `_helpers.py` (64), `crud.py` (542), `inscripcion.py` (217), `asistencia.py` (196), `info_terreno.py` (102) |
| M1 (parcial) | 9 de 11 modelos duplicados eliminados (queda solo `zona`). Borrados de `apps/kactivo/models/`: Actividad, Programa, TipoEvento, Evento, Lugar, Dependencia, Subgrupo, CaracterizacionCultura, CaracterizacionDeporte. Resuelve bugs latentes (FK rotas, schema atrasado). 5 FK string refs migradas cross-app |
| N12 (PR-3 + PR-4) | Cierre N12: los 6 wizards de caracterización en producción. PR-3 Mujer es atómico SQL (transaction.atomic escribe `informacion_hogar` + `caracterizacion_mujer`). PR-4 Salud reusa pipeline cifrado Mongo del Banco (`mongo_storage.guardar`). Firma OBLIGATORIA en Salud (consentimiento informado) |

---

## 2026-05-11 — Limpieza M1 + WCAG + tests gating + M17/M22/N20

Sesión actual.

| ID | Resumen |
|----|---------|
| M1.6 | Elimina `georeferenciacion.Zona` duplicado. BD confirma `(codigo int PK, nombre text, descripcion text)` calza con `login.Zona`. `Persona.zona` ya apuntaba a la versión correcta. **M1 cerrado al 100%** (`a54b7f1`) |
| N24 | 5 clases SCSS `.ui-*` definidas con WCAG AA verificado. Crea `_badge.scss` (+ --muted/--info/--success), `_table.scss` (+ -responsive), `_filter-bar.scss`, `_info-bar.scss`; extiende `.ui-btn` con `&--accent` (teal-700 #0F766E → blanco 5.47:1). +35 selectores en `dist/css/base.css` (`8a77a3a`) |
| N5 (regresión) | Smoke `test_beneficiario_form_carga_rapido` falló al crecer Organizacion a 92 filas. Fix análogo a Persona: endpoint `/api/organizaciones/search/`, `BeneficiarioForm.__init__` vacía queryset al crear, JS Select2 en template. Smoke vuelve a 116/116 (`d5cc61f`) |
| N25 | `templates/caracterizacion/base_publica.html` ahora usa `<main id="main-content">` + skip-link "Saltar al contenido" oculto-pero-accesible-por-teclado. WCAG 2.4.1 Bypass Blocks (`b1b28ee`) |
| N26 | Clase `GatingRolNoSuperTests` con 6 tests que se loguean como `daniel.lugo` (CoordinadorDeportes, no superuser) y validan gating real: permitido (eventos, banco) + denegado (presupuesto, org, roles → 302) + filtrado del hub (`b1b28ee`) |
| M17 | `api_crear_lugar` (apps/georeferenciacion/views/apis.py) valida bounding box Kennedy (lat 4.59-4.68, lon -74.20 a -74.11, margen ~1km del bbox oficial). Rechaza puntos en otras localidades o ciudades con 400. Nuevo `apps/georeferenciacion/tests/test_smoke.py` con 3 casos. Mejora pragmática sin dependencia externa IDECA (`dc4c029`) |
| M22 | Management command `poblar_barrios_geometry` con dry-run/--apply. Matching por NOMBRE normalizado entre geojson IDECA (111 features) y BD (325 barrios Kennedy). Aplicado: 43 barrios pasaron de NULL a tener geometry. Cobertura 32 → 75 / 325. Los 250 restantes quedan sin geo: granularidad fina BD que IDECA no cubre a nivel catastral (decisión arquitectónica documentada) (`df234c2`) |
| N20 | DDL aplicado: `ALTER TABLE caracterizacion_{cultura,deporte,mujer,salud,poblacional,participacion_ciudadana} ADD COLUMN funcionario_id INTEGER REFERENCES funcionario(id) ON DELETE SET NULL` + 6 índices. Nuevo helper `funcionario_actual_o_none(request)` que resuelve `request.user → Persona (vía persona_set) → Funcionario activo`. Las 6 vistas de wizards pasan `funcionario_id` al `.objects.create()`. Backup pre-cambio: `poblacion_kennedy_pre_n20_20260511_091413.dump`. Rollback disponible (`9914adf`) |
| N9 | Sub-hub Presupuesto agrupado en 3 secciones por flujo de negocio: Planeación (Proyectos, Programas, Objetivos, Metas, Meta-Proyecto), Ejecución (CDPs, Contratos, Conceptos), Seguimiento (Dashboard, KPIs, Avances, Vinculación). Nuevo template `templates/dashboard/hub_presupuesto.html`. Estilos `.hub-section / __title / __subtitle` agregados a `_hub.scss` (antes faltaban aunque hub_actividades ya los usaba). Recompila base.css (`5a9e769`) |
| N23 | Rate limit estricto en nginx para `/caracterizacion/api/persona/`: zona `caracterizacion_api` con `rate=10r/m burst=5 nodelay`. El uso normal (1 lookup por persona) no se ve afectado; un bot enumerando recibe 429 al 6° hit. Verificado E2E con curl (`4df2561`) |
| N17 (mínima) | Alcance "mínimo" del plan N17 aplicado: UI con 8 ejemplos clickables (cubren los 4 QueryType: COUNT, FILTER, GROUP, TOP) + `FIELD_MAPPING` ampliado de ~25 a ~70 sinónimos coloquiales (edad, víctimas, migrantes, lgbt, oficio, salario, vivienda, etc.). Texto introductorio que explica las 4 capacidades. Planes media (5 modelos nuevos + JOINs) y alta (text-to-SQL) quedan abiertos como deuda futura (`d81c98e`) |
| N18 (mínima) | Alcance "mínimo" del plan N18 aplicado: barra de 18 pestañas (Todos + 17 subgrupos `dep_id=3`) encima del mapa Kennedy. Click sincroniza `f-subgrupo` y reaplica `cargarEventos()` manteniendo el filtro `tipo_evento` activo. Pestaña activa marcada con `btn-primary`. Sin DDL ni endpoints nuevos. Planes media (KPIs por subgrupo en panel) y alta (sub-mapas independientes + persistencia) quedan abiertos (`9da7099`) |
| S9 | Línea `DATABASE_URL=...` eliminada manualmente de `.env`. La variable nunca se leía en código (`core/settings.py` usa `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST` separados). Cero impacto en runtime. Última deuda de Seguridad cerrada → Seguridad pendiente: 0 ítems. |
| N3 | DDL aplicado: `ALTER TABLE contrato_proyecto/contrato_actividad ADD COLUMN id BIGSERIAL + ADD CONSTRAINT ... UNIQUE(id)`. PK compuesta preservada. Modelos Django actualizados con `id = BigAutoField(primary_key=True)` (antes usaban `contrato=FK(primary_key=True)` como workaround). **Bug latente resuelto**: `contrato_actividad` con contrato_id 1 y 16 tenían 2 filas cada uno pero el ORM solo veía la primera; ahora `.filter(contrato_id=X)` devuelve todas. 96 + 98 filas con id 1-N únicos. Backup: `poblacion_kennedy_pre_n3_20260511_103929.dump` (`3474a93`) |

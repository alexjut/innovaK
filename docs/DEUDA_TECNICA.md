# Deuda técnica — innovaK

**Última actualización:** 2026-04-27 (post PR-J3: hardening pre-gov.net)
**Total pendiente:** 11 ítems · **Resueltos:** 33 (ver §"Resueltos" al final)

Lista compacta de deuda activa, agrupada por categoría y ordenada por
severidad. Cada ítem tiene un identificador estable (no se renumera al
borrar resueltos) para citar en commits futuros.

---

## 🔐 Seguridad (1 pendiente)

| ID | Severidad | Resumen | Ubicación |
|----|-----------|---------|-----------|
| S9 | BAJA | `DATABASE_URL` y `DB_PASSWORD` ambos en `.env` (redundancia que confunde) | `.env` (manual) |

## 🚀 Performance (1 pendiente)

| ID | Severidad | Resumen |
|----|-----------|---------|
| P4 | BAJA | 6 índices del dashboard creados en BD pero no declarados en `Meta.indexes` |

## 🧹 Mantenibilidad (3 pendientes)

| ID | Severidad | Resumen |
|----|-----------|---------|
| M1 | ALTA | Modelos duplicados apuntando a la misma `db_table` (`Actividad`, `Programa`, `Zona`) en apps distintas |
| M6 | MEDIA | Archivos de views con >500 líneas (`apps/login/views/eventos.py` ~900) |
| M17 | MEDIA | Mejorar geocoding con API IDECA (hoy LugarIncidencia se crea con coords del usuario) |
| M22 | MEDIA | Mismatch IDECA: 79/111 barrios sin geometry |

## 📐 Convenciones (5 pendientes)

| ID | Severidad | Resumen |
|----|-----------|---------|
| C2 | BAJA | `db_column` declarado a veces sí, a veces no |
| C3 | BAJA | Mix de `IntegerField` y `BigAutoField` como PKs |
| C4 | MEDIA | UPZ y Barrio usan `IntegerField` como FK lógica sin constraint formal |
| C5 | BAJA | (PARCIAL) Mezcla de idiomas en `apps/votaciones/`: nombres de modelos siguen en inglés (Event/Voter/Candidate). Login propio ya eliminado. Pendiente: rename de modelos+vistas+templates a español. |
| C6 | BAJA | Sin convención uniforme de `on_delete` (mix de `DO_NOTHING`, `SET_NULL`, `CASCADE`) |

## 🆕 Detectado en sesión 2026-04-25/27 (3 pendientes)

| ID | Severidad | Resumen |
|----|-----------|---------|
| N3 | MEDIA | `ContratoProyecto`/`ContratoActividad` sin `id` propio. Intento de ALTER falló porque tienen PK compuesta. Solución: `ADD COLUMN id BIGSERIAL UNIQUE NOT NULL` (sin reemplazar PK) y ajustar modelos. Pospuesto: 1:1 efectivo en datos actuales. |
| N9 | BAJA | Hub presupuesto con 12 cards y topbar con 13 tabs (densidad UX). Considerar agrupar en sub-secciones. |
| N10 | BAJA | `redis-cli INFO server` muestra Redis 7.4.7 pero `requirements.txt` no fija versión cliente — sin impacto hoy, pero auditar para gov.net |
| N12 | MEDIA | Tipo de evento `CARACTERIZACION` creado con vista placeholder. Formularios específicos por sector (deporte, cultura, mujer, salud, participación ciudadana, poblacional) pendientes — las 7 tablas `caracterizacion_*` ya existen en BD. Ver `apps/kactivo/views/caracterizacion_publica.py` y `docs/propuestas/formularios_por_tipo_evento.md`. |
| ~~N13~~ | ~~ALTA~~ | ~~Tablas puente M2M de Banco de Iniciativas con PK compuesta~~ **RESUELTO** sesión 2026-04-29: aplicado `ALTER TABLE ... ADD COLUMN id BIGSERIAL UNIQUE NOT NULL` en las 5 tablas (`inscripcion_banco_escenario`, `_implemento`, `_rango_etario`, `_enfoque`, `_beneficio_alk`). PK compuesta original preservada. Validado E2E: form Banco completo con 4 multiselects M2M + firma Mongo cifrada persiste correctamente. |
| ~~N11~~ | ~~MEDIA~~ | ~~Capas y leyenda del mapa Kennedy hardcoded por tipo de evento.~~ **RESUELTO** sesión 2026-04-29: `TipoEvento.color_hex` + `css_slug` (property determinística), template con `{% for %}` sobre `tipos_evento_list`, JS lee colores desde `window.__COLORES_TIPO_EVENTO` inyectado por la vista. Cada `TipoEvento` nuevo aparece automáticamente sin tocar template/JS/CSS. |

---

## ✅ Resueltos (histórico, sin detalle)

| ID | Cómo se resolvió |
|----|------------------|
| S1 | Hotfix sesión 2026-04-20 (`SECRET_KEY` desde `.env`) |
| S2 | Hotfix sesión 2026-04-20 (`DEBUG` desde `.env`) |
| S3 | Hotfix sesión 2026-04-20 (`ALLOWED_HOSTS` desde `.env`) |
| S4 | Hotfix sesión 2026-04-20 (`ONEDRIVE_TOKEN` desde `.env`) |
| P3 | Fix N5 (Persona ahora con Select2 AJAX, sin `.all()`) |
| M2 | App `apps/documento/` eliminada (sesión 2026-04-20) |
| M3 | Apps `kordial` y `VitalK` eliminadas (sesión 2026-04-20) |
| M4 | `apps/login/models.py` eliminado (sesión 2026-04-20) |
| M12 | Template `mapa_kennedy_standalone.html` creado |
| C1 | PR-H3 (`868e758`): quitado prefijo `public.` en 3 modelos de Contrato |
| N1 | Fix `b48a0dd`: fallback MAX+1 en `contrato_nuevo` |
| N2 | DDL 2026-04-27: `CREATE SEQUENCE proveedor_id_seq` |
| N4 | Fix `427ec36`: IntegerField sueltos → ForeignKey formal |
| N5 | Fix `70a67c5`: Select2 + endpoint AJAX para selectores de Persona |
| N6 | Fix `427ec36`: `verbose_name_plural` copy-paste corregido |
| N7 | Fix `427ec36`: `__str__` agregado a Proyecto/Actividad/ActividadPlan |
| N8 | Falsa alarma: `metas.codigo` es `IDENTITY ALWAYS` (PG10+) |
| Bug | PR-G (`a91c22c`): `Lower()` sin importar en `actividad_nueva` |
| Cache | PR-H1 (`a8a3557`): cache-buster con mtime de `base.css` |
| M5 | Quick win 2026-04-27: `apps/votaciones/apps.py` creado |
| M7 | Quick win 2026-04-27: duplicados LANGUAGE_CODE/TIME_ZONE consolidados |
| M9 | Quick win 2026-04-27: comentarios doc Django 4.2 |
| M13 | Quick win 2026-04-27: lectura única de DEBUG en settings |
| M10 | Sesión 2026-04-27: 40 smoke tests en `apps/*/tests/test_smoke.py` ejecutables con `scripts/run_smoke_tests.py` |
| P1 | Sesión 2026-04-27: paginación (page_size=25) en 6 listas grandes (beneficiarios 3580→144 págs, contratos, avances, organizaciones, meta_proyecto, indicadores). Partial reutilizable `templates/_partials/paginator.html`. |
| S5 | Sesión 2026-04-27: eliminado patrón `MAX(id)+1` en 4 sitios (persona, persona+participante en inscripción, cdp). Auditoría reveló que las tablas YA tenían secuencia (`nextval`); el fallback era innecesario. Refactor con `INSERT...RETURNING id` y `obj.save()` directo. |
| M8 | Sesión 2026-04-27: Dockerfile alineado con docker-compose. EXPOSE 8032 + CMD gunicorn (antes runserver/8000). |
| Infra | Sesión 2026-04-27: nginx.conf reescrito con gzip + 5 security headers + rate limiting (general 60r/s, login 5r/s) + keepalive upstream + endpoint /healthz + página 503 amigable cuando innova_k cae. |
| Infra | Sesión 2026-04-27: Django CACHES configurado contra Redis (db /1) + sesiones movidas a `cached_db`. Antes Redis estaba corriendo pero Django no lo usaba. Resuelve el problema reportado por usuario: 'se cayó otra app porque solo usaba la web y no nginx ni redis'. |
| C5 (parcial) | Sesión 2026-04-27: módulo `votaciones` ya no tiene login propio. `staff_login`/`staff_logout` eliminados; vistas del organizador ahora usan `@login_required` + `@group_required("Admin","Lider")` (consistente con el resto del sistema). Modelos siguen en inglés (Event/Voter/Vote/Candidate) — rename completo queda para PR aparte. |
| Feature | Sesión 2026-04-27: voto múltiple administrable en módulo votaciones. Campo `votos_permitidos` (default=1) en Event, configurable al crear/editar. Constraint UNIQUE eliminado, validación pasada al servicio `register_vote` que cuenta votos previos vs permitidos. DDL aplicado: 2 ALTER (ADD COLUMN + 2 DROP CONSTRAINT). |
| S6 | Sesión 2026-04-27: INSERT con f-string en `eventos.py:743` reforzado con whitelist explícita `_ALLOWED_PERSONA_COLS` + `raise ValueError` si llega columna no permitida. Antes: cols viene de literales hardcoded (seguro pero opaco al auditor). Ahora: explícito y fail-fast. |
| S8 | Sesión 2026-04-27: `api_crear_lugar` (geo) ya NO es `csrf_exempt` — invocado por funcionario logueado, ahora valida CSRF + `@login_required`. Frontend (modal Leaflet) actualizado para enviar `X-CSRFToken` desde cookie. POST sin token responde 403. `api_validate_voter` y `api_vote` (votaciones) mantienen `csrf_exempt` con comentario explicativo: son públicos sin sesión (votante con QR), protegidos por rate limit nginx (60r/s). |
| S7 | Sesión 2026-04-27: 53 vistas nuevas con `@login_required` en 13 archivos (eventos, formulario, api login, presupuesto catalogo+api, geo apis+mapas, kactivo cultura_shell+ping_db). Smoke 20 URLs sin login → 20 redirigen a /login/. ⚠️ NOTA: `confirmar_llegada_info_terreno` y `info_terreno_exitoso` (login/views/eventos.py) están protegidas — el funcionario debe estar logueado en su celular para escanear QR de info terreno. Si rompe el flujo operativo, revertir esos 2 decoradores. |
| PR-J1 | Sesión 2026-04-27: 4 fixes detectados por agentes con skills nuevas (django-security + accessibility + wcag). (1) `dashboard_ai_view:282` ya NO expone trazas Exception al usuario — usa `logger.exception` + mensaje genérico. (2) `_empty-state.scss` hint color de `$color-neutral-400` (2.8:1) a `$color-text-muted` (4.6:1) — WCAG AA. (3) 50 `<th scope="col">` agregados en 8 listas. (4) 118 emojis envueltos en `<span aria-hidden="true">` en 54 templates — lectores de pantalla ya no los verbalizan. |
| PR-J2 / P2 | Sesión 2026-04-27: índices BD + Redis cache. DDL CONCURRENTLY (no bloqueante): idx_barrio_upz, idx_pev_evento, idx_pev_part, idx_municipio_dpto. Cache server-side con `@cache_page` en 5 endpoints geo (api_eventos_geojson 5min, kennedy_parques/escuelas 5min, kennedy_barrios/upz 1h). Catálogos del mapa (TipoEvento+Dependencia+Subgrupo) cacheados 1h con key `geo:mapa_kennedy:catalogos:v1`. SESSION_ENGINE: `cached_db` → `cache` puro (Redis con TTL automático, ya no escribe a BD). Verificado: `/geo/api/eventos/` cold 378ms → cached 1ms (378× speedup). 51 keys en Redis. |
| PR-J3 / M11 | Sesión 2026-04-27: hardening pre-gov.net. (1) Logger estructurado con formato key=value (`ts="..." level=INFO logger=apps.X pid=N msg=...`) parseable por Loki/journald. Configuración LOGGING en core/settings.py con loggers separados django/django.db/django.security/apps/core. Nivel via env var `DJANGO_LOG_LEVEL`. (2) Hook git pre-push (`scripts/git-hooks/pre-push` + instalador `scripts/install-git-hooks.sh`) corre smoke tests antes de cada push, aborta si fallan. (3) Settings TLS-ready condicionales: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=1y`, `SECURE_PROXY_SSL_HEADER` — todos detrás de flag `BEHIND_TLS=true` en .env. Hoy inactivos (HTTP plano), se activan cuando nginx tenga certificado para gov.net. |
---

## Cómo seguir

**Quick wins (< 30 min cada uno):**
- S9 — borrar manualmente `DATABASE_URL` de `.env` (Alex, no se usa en código)
- ⚡ Para activar hardening TLS cuando entre gov.net: agregar `BEHIND_TLS=true` a `.env` y reiniciar `innova_k`. Requiere certificado en nginx (TLS) primero.

**Alto impacto (1-3h cada uno):**
- Tests: ampliar smoke tests con POST/rollback (Django TestCase con --keepdb)
- P2 — completar `select_related`/`prefetch_related` en listas restantes
- S6 — refactor del INSERT dinámico con f-string (riesgo SQL injection)

**Estratégico (decisión + DDL):**
- M1 — consolidar modelos duplicados (requiere análisis previo)
- N3 — agregar `id BIGSERIAL UNIQUE` a tablas con PK compuesta
- M11 — introducir logging estructurado (impacta troubleshooting prod)
- M8 — alinear `Dockerfile` con `docker-compose.yml` (gunicorn + 8032)

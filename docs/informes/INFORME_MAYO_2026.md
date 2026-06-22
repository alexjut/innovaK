# Informe mensual — mayo 2026

> **Proyecto:** innovaK / KennedyConecta — Alcaldía Local de Kennedy
> **Período:** 2026-05-01 a 2026-05-26
> **Autor:** Alex (ingaguilarsistemas@gmail.com) + agentes Claude Code

---

## 1. Resumen ejecutivo

Mayo fue un mes de **consolidación operativa y arranque del camino
Angular-ready**. Cerró un sistema de roles dinámico, terminó los 6
wizards de caracterización ciudadana, levantó la versión 2 del Banco de
Iniciativas, dejó el mapa Kennedy con UX nivel Power BI, sacó el
módulo nuevo Jóvenes a la E (becas educativas) a producción, y arrancó
oficialmente el **Plan de Evolución del Frontend** (camino híbrido con
destino Angular condicional), instalando Tom Select, HTMX y Django REST
Framework como piloto.

Al cierre del mes el sistema queda con **0 deuda técnica activa** por
primera vez en su historia, **134 smoke tests** corriendo en cada push,
y **cero bugs latentes** en categoría crítica.

---

## 2. Métricas del mes

| Métrica | Valor |
|---------|-------|
| Días con commits a producción | 8 |
| Commits a `produccion` | 188 |
| Total commits (todas las ramas) | 191 |
| Líneas netas agregadas | +20.673 (24.669 añadidas / 3.996 eliminadas) |
| Archivos únicos modificados | 209 |
| Suite de tests al inicio del mes | 87 |
| Suite de tests al cierre del mes | **134** (+47) |
| Backups DDL pre-aplicación | 5 (`pre_n12`, `pre_n15`, `pre_n3`, `pre_n20`, `pre_n22`, `pre_n27`, `pre_jovenes`) |
| Módulos nuevos en producción | 1 (`apps.jovenes_a_la_e`) |
| Bugs latentes al cierre | **0** |
| Deuda técnica activa al cierre | **0** (3 cosméticas cerradas el 25) |

---

## 3. Cronograma por sesión

### 📅 04 de mayo — Cierre N15 + N12 + M1 parcial (54 commits)

**Sesión maratón con 8 cascadas a producción.**

**N15 — Sistema de roles dinámico (cierra al 100%):**
- PR-3: 119 endpoints migrados de `@group_required` a `@modulo_required` en 19 archivos.
- PR-3.1: separa módulo `votaciones` en `votaciones_admin` + `votaciones_votantes`.
- PR-3.2: afina matriz minuciosa de roles (Coordinador kactivo +caracterización, Docente +consultas, CoordinadorDeportes ajustes).
- PR-4: sidebar y hubs dinámicos por módulo (context processor `modulos_usuario`, frozenset cacheado). Resuelve 3 bugs latentes (substring match, solo primer grupo, lógica duplicada).
- PR-5: kactivo a `@modulo_required` (26 endpoints). Cierra N15 — decorador legacy retirado del repo.

**N12 — Wizards de caracterización (cierra 6/6):**
- PR-3: wizard Mujer atómico (escribe a 2 tablas en `transaction.atomic()`).
- PR-4: wizard Salud con firma cifrada Mongo. Cierra N12 100%.

**Deuda colateral:**
- M1: elimina 9 de 11 modelos duplicados en kactivo.
- N16: borra documento Mongo huérfano.
- N10: pin `redis==5.3.1`.
- P4: 15 índices BD declarados en `Meta.indexes`.
- M6: split `eventos.py` (1077 líneas) en paquete de 5 sub-archivos.

**Hotfixes:**
- Dashboard presupuesto vacío (helpers no importados, regresión M6).
- JS SyntaxError que dejaba presupuesto sin cargar.

**Estado de tests al cierre:** 87/87 OK.

---

### 📅 06 de mayo — Reorganización Actividades (40 commits, 7 PRs)

**Refactor completo del módulo Actividades en 3 niveles.**

- **PR-1:** hub reorganizado en 3 niveles (Tipo → Área → Lista). Antes era plano.
- **PR-2:** `TipoEvento` data-driven con flags (permite_inscripcion, requiere_actividad_plan, permite_caracterizacion). Crea tipo GENERICO. Endurece flujo Banco.
- **PR-3:** granularidad fina por `subgrupo_linea` (líneas internas en cada subgrupo de Inversión Local). Agrega Salud y Juventud como sectores.
- **PR-4:** acciones por evento (beneficiarios + caracterizaciones).
- **PR-5:** 6 wizards internos de caracterización sin requerir evento padre (cuando hace sentido).
- **PR-6:** autollenado por cédula en wizards (`/caracterizacion/api/persona/?doc=`).
- **PR-7:** Beneficiario unificado en todos los flujos de captura.

**Hotfixes:**
- Pantalla 2 de CARACTERIZACION muestra los 6 sectores directos.
- Caracterizaciones data-driven desde catálogo central.
- Auditoría 2026-05-06: consolidación de hallazgos.

---

### 📅 08 de mayo — Banco de Iniciativas v2 (11 commits)

**3 PRs sobre el módulo Banco con DDL aplicado.**

- **PR-1:** cambios triviales en 4 secciones del form (sin DDL).
- **PR-2:** refinar `tipo_organizacion` + soporte legal (DDL aplicado).
- **PR-3:** sede admin migrada a S1 + escenarios de uso actual (DDL aplicado).

**UX iteraciones:**
- Soporte legal solo por URL (sin upload de archivos al servidor).
- Popover dinámico de ayuda en campos clave.
- Validación: bloquea avance de pasos con checkboxes obligatorios vacíos.

**Adicional:** ordenamiento de eventos por reciente + botón data-driven según `tipo_evento`. Limpieza de comentarios verbosos en templates.

---

### 📅 11 de mayo — Sesión limpieza profunda + WCAG + mapa Kennedy (44 commits)

**El día con más cierres de deuda técnica del mes.**

**Limpieza de modelos:**
- M1.6: elimina `georeferenciacion.Zona` duplicado (cierra M1 al 100%).
- N3: `id BIGSERIAL UNIQUE` en `contrato_proyecto` y `contrato_actividad` (DDL aplicado).
- N5 (regresión): `BeneficiarioForm` con Select2 AJAX para Organización (crecía a 92 filas).
- N9: hub Presupuesto agrupado en 3 secciones (Planeación / Ejecución / Seguimiento).
- N17 mínima: UI con ejemplos clickables + whitelist expandida en Consulta IA.
- N18 mínima + media: pestañas por subgrupo de Inversión Local en mapa Kennedy + KPIs inline + persistencia LocalStorage.
- N19: form Banco con 4 campos rep_* + autollenado por cédula.
- N20: trazabilidad organizacional en wizards (DDL `funcionario_id` en 6 tablas caracterizacion_*).
- N21: desacopla Sector ↔ Subgrupo (mapeo explícito por id, no por nombre).
- N22: UNIQUE INDEX parcial en `beneficiario(persona_id) WHERE tipo='PERSONA'`.
- N23: rate limit nginx para `/caracterizacion/api/persona/` (`10r/m burst=5`).
- N27: limpia datos sucios (typos en subgrupos, usuario duplicado).
- S9: elimina `DATABASE_URL` muerta de `.env`.
- M17: valida bbox Kennedy en `api_crear_lugar`.
- M22: pobla `barrio.geometry` por matching de nombre con IDECA (32 → 75 barrios con geo de 325).
- C4: cierre documental (falsa alarma — FK ya existían).
- C5: rename votaciones a español (4 clases + service + 20 archivos).

**Accesibilidad WCAG:**
- N24: 5 clases SCSS `.ui-*` faltantes definidas con contraste WCAG AA verificado.
- N25: landmark `<main>` + skip-link en templates de caracterización.
- N26: 6 tests de gating con `daniel.lugo` (CoordinadorDeportes, no superuser).

**Mapa Kennedy:**
- Buscador de eventos visibles reemplaza tabla "Datos de Lugares".
- Filtros Cultura/Deporte trasladados a las pestañas N18.
- Elimina dashboard de Gráficos vestigial.
- Default sin escuelas ni lugares; pestañas activan cada capa.

**Admin:**
- Jazzmin activado para Django admin (branding institucional rojo + íconos FA por app).

**Estado al cierre:** 116/116 tests OK.

---

### 📅 14 de mayo — Insights nivel Power BI del Banco (9 commits)

**Dashboard analítico replicable.**

- Vista Insights del Banco con métricas trascendentales.
- Rediseño completo nivel Power BI con Chart.js (8 KPIs + 6 gráficos).
- Descarga CSV analítica del Banco + botón en dashboard.
- Botón descarga CSV en `/org/beneficiarios/` + fix smoke.
- **Replica:** dashboard Insights para módulo eventos (mismo patrón).
- Descarga Excel beneficiarios + manual de uso del Banco.

**Roles:**
- CoordinadorDeportes (Daniel) gana módulo `org_admin`.

**Fix de catálogo:**
- Separa Futsala de Fútbol en `DisciplinaDeportiva`.

**Estado al cierre:** 122/122 tests OK.

---

### 📅 21 de mayo — Módulo Jóvenes a la E (2 commits cascadeados con muchos cambios)

**Módulo nuevo end-to-end en una sesión.**

Contexto: convenios 773-2025 (becas) y 955-2025 (dotación), 3 metas
del proyecto 2805 "Kennedy Germinando Futuros", subgrupo Educación.

**PR-1 + PR-2 (commit `f9f3b96`):**
- DDL aplicado: 6 tablas (`sede_educativa`, `elemento_dotacion`, `entrega_beca`, `entrega_beca_elemento`, `entrega_dotacion_sede`, `entrega_dotacion_elemento`) + 2 `tipo_evento` (`JOVENES_BECA`, `JOVENES_DOTACION_SEDE`).
- App nueva `apps.jovenes_a_la_e/` con 6 modelos managed=False, form público mobile-first con cámara para firma, autollenado por cédula.
- Backup pre-DDL: `pre_jovenes_20260521_093929.dump`.
- Hotfix `002_fix_puente_id.sql`: agrega `id BIGSERIAL UNIQUE` a tabla puente.
- Decisión Alex: dotación a sedes reusa `tipo_evento='ENTREGA'` existente, sin tabla nueva.

**PR-3 J1-J4 (commit `e530721`):**
- **J1** Vista organizador: list paginada con chips de estado, detalle con 5 cards, validar/rechazar con observación.
- **J2** Sync con `AvanceIndicador` al validar: crea una fila por cada KPI vinculado a la `actividad_plan` del evento.
- **J3** Cripto Mongo: pipeline cifrado reusado del Banco con `owner={"tipo":"jovenes_beca", ...}`.
- **J4** Selects UPL/Barrio: `ModelChoiceField` en form público.

**Resultado:** flujo end-to-end probado, 128 tests OK al cierre, módulo `jovenes_a_la_e` asignado a Admin y Líder, evento real `id=100055 "Jóvenes a la E"` creado.

---

### 📅 25 de mayo — Limpieza modelos + Plan Frontend + Etapa A + B (28 commits)

**Sesión más larga del mes: 6 cascadas a producción.**

**Limpieza modelos vs BD (cierra C2/C3/C6):**
- Análisis quirúrgico con agente BD: mapeo de mismatches reales modelo Django ↔ BD `poblacion_kennedy`.
- C2 (`db_column`): 0 mismatches reales (la convención ya se respeta).
- C3 (PK types): ~25 PKs alineados al tipo real de BD (`BigAutoField` → `AutoField` donde BD es integer; agregado `id` explícito en 4 modelos de votaciones donde BD es bigint).
- C6 (`on_delete`): ~45 FKs a `DO_NOTHING` para reflejar política real de BD (managed=False). `PROTECT` conservado por mejor UX.
- **Bonus:** borrados 5 modelos muertos en `models_auxiliares.py` que apuntaban a tablas inexistentes en BD (TipoRedSocial, NivelSocioeconomico, TenenciaVivienda, TipoSalud, TipoSangre).

**Plan de Evolución del Frontend (documento operativo):**
- `docs/PLAN_FRONTEND.md` v1.0: camino híbrido con destino Angular condicional, 4 etapas (A: UX híbrida · B: backend a API REST · C: decisión · D: migración strangler).
- **Regla de oro:** todo lo nuevo nace Angular-ready (lógica separada de presentación, datos JSON-exponibles, fragmentos no páginas).
- Memorias persistentes: `feedback_angular_ready`, `reference_plan_frontend`.

**Etapa A — UX híbrida (Tom Select + HTMX):**
- #1 Tom Select en BeneficiarioForm (reemplaza Select2+jQuery, ahorro ~140kb por carga).
- #2 Tom Select en FuncionarioForm.
- #3 Tom Select en form público Banco (solo select de Barrio — 325 opciones; los catálogos chicos quedan con select HTML nativo).
- #4 HTMX en Banco validar/rechazar inscripción (response 657 bytes vs ~50kb).
- #5 HTMX en Jóvenes a la E validar entrega.
- #6 HTMX en Jóvenes a la E rechazar entrega.
- Setup HTMX 2.0.3 en `base.html` con CSRF auto-injection desde cookie.

**Etapa B — Backend a API REST (piloto):**
- DRF 3.15.2 instalado con SessionAuth + IsAuthenticated + paginación 50.
- #9 Endpoint piloto `/geo/api/eventos/` migrado a `APIView` + `EventoGeoFeatureSerializer`.
- Multiselect en `tipo_evento` y `subgrupo_id` (mejora UX del mapa).
- Browsable API en `/geo/api/eventos/` para inspección manual.

---

### 📅 26 de mayo — Caracterizaciones en mapa + ubicación editable (hoy)

**Cierra los reportes de Alex sobre el mapa.**

**Diagnóstico inicial:**
- "Proyectos no aparecen en el mapa" → por diseño (van como Eventos asociados).
- "Caracterizaciones no aparecen" → gap real: las caracterizaciones se georreferencian vía evento padre, pero el popup no mostraba el conteo.
- Evento `JOVENES_BECA #100055` sin `lugar_incidencia` (creado por SQL).
- Reporte Jorge: confirmado que era otro ambiente (KennedyConecta), sin acción en innovaK.

**Cambios:**
- `EventoGeoFeatureSerializer` ahora incluye `caracterizaciones={total, sector}` para eventos tipo CARACTERIZACION. Conteo precomputado en la view (1 query por sector, no N+1).
- `mapa_kennedy_eventos.js`: popup muestra "Caracterizaciones registradas aquí: N personas — Sector: X".
- **Editar evento ahora permite cambiar ubicación:**
  - Sección "📍 Ubicación de la actividad" con dirección + mini-mapa Leaflet inline.
  - Click en el mapa mueve el marcador y actualiza lat/lon.
  - Si el evento ya tiene `lugar_incidencia` → actualiza `GeoReferenciacion`.
  - Si no tiene → crea cadena Lugar→Geo→LugarIncidencia desde cero.
- Fix locale `|unlocalize`: `LANGUAGE_CODE='es'` renderizaba decimales con coma rota `parseFloat()` JS.
- Evento JOVENES_BECA #100055 ahora apunta a Alcaldía Local de Kennedy (4.6286, -74.1466).

**Estado final mes:** 134/134 tests OK.

---

## 4. Estado al cierre del mes (2026-05-26)

### Salud del sistema

| Indicador | Estado |
|-----------|--------|
| Bugs latentes / Riesgos | **0** |
| Deuda técnica activa | **0** |
| Convenciones cosméticas pendientes | 0 (cerradas 25-may) |
| Tests pasando | 134/134 (3 skipped por falta de datos) |
| Hook pre-push | activo (corre tests en cada push) |
| Cascada git | sincronizada en `produccion`, `Pruebas`, `desarrollo` |
| Container productivo | `innova_k` reiniciado al final de cada cascada |

### Módulos activos en producción

- `apps.login` — Persona, Usuario, Funcionario, Evento, catálogos, roles dinámicos
- `apps.kactivo` — Cultura + Deporte
- `apps.georeferenciacion` — mapa Kennedy + endpoint DRF piloto
- `apps.presupuesto` — Proyectos, programas, CDPs, contratos, KPIs, avances
- `apps.dashboard` — hub principal + sub-hubs + Insights del Banco/Eventos + Consulta IA
- `apps.votaciones` — flujo de votación con QR
- `apps.banco_iniciativas` — captura de organizaciones recreodeportivas
- `apps.caracterizacion` — 6 wizards (Cultura, Deporte, Mujer, Salud, Poblacional, Participación Ciudadana)
- `apps.jovenes_a_la_e` — **nuevo este mes:** captura de becas educativas
- `apps.documentos` — pipeline AES-256-GCM para Mongo

### Plan de Evolución del Frontend — avance

- **Etapa A (UX híbrida):** 6/8 tareas hechas (Tom Select 3/3, HTMX 3/3). Quedan #7-#8 Alpine.js (no urgente).
- **Etapa B (backend a API REST):** 1/4 tareas — piloto DRF en `/geo/api/eventos/`.
- **Etapa C (decisión Angular):** pendiente — depende de avance de B y disparadores.
- **Etapa D (migración):** condicional — solo si C aprueba.

### Pendiente reconocido (no urgente)

- **J5** Insights Chart.js + descarga Excel para Jóvenes a la E (3 h).
- **N17 alcance media** Consulta IA cruzando 5 modelos (~1 semana).
- **N18 alcance alta** URLs propias por subgrupo (3-4 días).
- **Etapa A #7-#8** Alpine.js (no urgente, sidebar/modales Bootstrap ya funcionan).
- **Hardening pre-gov.net:** activar `BEHIND_TLS=true` cuando llegue el certificado nginx.

---

## 5. Decisiones clave del mes

| Fecha | Decisión |
|-------|----------|
| 04-may | N15 PR-3.2: matriz de roles refinada (Coordinador kactivo +caracterización; Docente +consultas) |
| 06-may | `TipoEvento` data-driven con flags — comportamiento por configuración, no por código |
| 11-may | C5: rename votaciones a español (Alex revocó la excepción de CLAUDE.md §3) |
| 21-may | Antes de proponer schema nuevo, verificar que conecta con la cadena estándar Proyecto→Meta→KPI←Actividad←Evento |
| 25-may | Plan Frontend v1.0 con regla "Angular-ready" + Vite/Tailwind masivo EN PAUSA |
| 25-may | Alineación modelos↔BD: prefiero reflejar realidad (`DO_NOTHING`) que mantener lies de Django (`CASCADE` que la BD no aplica) |

---

## 6. Backups DDL aplicados en mayo

| Fecha | Backup | Cambio |
|-------|--------|--------|
| 30-abr (preserva) | `pre_n12_20260430_115315.dump` | DDL N12 wizards (caracterización) |
| 30-abr (preserva) | `pre_n15_20260430_171530.dump` | DDL N15 roles dinámicos |
| 11-may | `pre_n3_20260511_103929.dump` | BIGSERIAL UNIQUE contratos |
| 11-may | `pre_n20_20260511_091413.dump` | funcionario_id en wizards |
| 11-may | `pre_n22_20260511_161018.dump` | UNIQUE beneficiario(persona_id) |
| 11-may | `pre_n27_20260511_105806.dump` | Limpieza datos sucios |
| 21-may | `pre_jovenes_20260521_093929.dump` | DDL módulo Jóvenes a la E |

---

## 7. Próximos pasos sugeridos

1. **Etapa B continúa:** migrar 2-3 endpoints más de `georeferenciacion` a DRF (api_lugares, api_conteos) o pasar a otro módulo pequeño.
2. **Etapa A #7-#8** Alpine.js cuando aparezca un caso concreto donde duela el JS imperativo actual.
3. **J5:** Insights Chart.js + Excel para Jóvenes a la E (3 h, sin urgencia).
4. **N17 media** si emerge una pregunta a Consulta IA que la versión mínima no resuelva.

---

**Cierre:** mayo termina con un sistema más limpio, más navegable, con
un módulo nuevo en producción, dos arranques nuevos (Plan Frontend +
API REST), y cero deuda técnica activa por primera vez. La cascada git
de 4 ramas funcionó en las 8 sesiones sin un solo rollback.

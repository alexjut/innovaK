# Orden de la documentación — auditoría 2026-07-16

> **Qué es esto.** Alex pidió: *"eliminar lo que no va, lo que está pendiente, lo
> que ya se hizo… ordenemos todos los documentos"* y *"si son un solo proyecto,
> unificar"*. Esto es la auditoría completa de los **58 documentos** del repo,
> cada uno **verificado contra el código**, no contra lo que el doc dice de sí mismo.
>
> **Estado: PROPUESTA.** Los borrados **no se ejecutaron** — son irreversibles y
> los decide Alex. Lo único ya ejecutado está en §6.

---

## 0. Resumen en una pantalla

| | |
|---|---|
| Documentos auditados | **58** (`docs/` 55 + `README.md` + `CLAUDE.md` + `frontend/README.md`) |
| Líneas totales | ~15.600 |
| **HECHO** (ya ejecutado, el doc no guía nada) | **17** |
| **PENDIENTE** (trabajo vivo) | **6** |
| **DEUDA** (defecto conocido → consolidar) | **11** |
| **NO VA** (descartado, obsoleto o superado) | **9** |
| SE QUEDA (vigente y verdadero) | **15** |
| **Afirmaciones falsas encontradas** | **~90 en 20 documentos** |
| Propuesto **BORRAR** | **8 archivos · ~1.900 líneas** |
| Propuesto **ARCHIVAR** | **10 archivos · ~2.800 líneas** |

**El patrón que lo explica casi todo:** el corte a **full-Angular del 2026-06-11**
borró 69 vistas-puente, 69 URLs y ~129 templates. Invalidó de golpe la capa
"URL → vista HTML" sobre la que estaban construidos media docena de documentos.
Ninguno se actualizó. **Los docs no envejecieron: se quedaron describiendo un
sistema que dejó de existir en un solo día.**

---

## 1. 🔴 Lo que hay que atender antes que el orden documental

Apareció auditando, no se buscaba. Está en `DEUDA_TECNICA.md` como **P1/P2**.

**P1 — Cédulas reales en un repo público.** `github.com/alexjut/innovaK` es
**público**. `docs/operacion/usuarios_georef.md:16-17` y
`docs/usuarios_solicitados.md:18,26-45` publican **nombre completo + cédula +
número de contrato CPS** de 3 personas. Están *tracked* y aparecen en **5
commits** → borrarlos del HEAD **no basta**: hay que purgar el historial
(`git filter-repo`) y reescribir el remoto. Ley 1581/2012.

Tres agravantes:
- `docs/infra/despliegue_kubernetes.md:14` afirma que el repo es **privado**. No lo es.
- La cabecera de `usuarios_georef.md:6-10` presume higiene ("las contraseñas NO van
  en este archivo… es versionado en git"): protegió la contraseña y **dejó la cédula**.
- `docs/README.md` **no indexa `docs/operacion/`** → el archivo con 2 cédulas nunca
  estuvo en el radar del índice.

**Y una regla del proyecto que empuja en la dirección equivocada:**
`docs/README.md:73-74` dice *"si un doc deja de ser vigente se mueve a `_historico/`.
**No se borra**"*. Para datos personales esa regla es exactamente lo contrario de lo
que exige la ley. **Necesita una excepción explícita.**

**P2 — 3 tokens HMAC vivos** publicados en `docs/manuales_modulos/cultura.md:41-43`,
estables y sin expiración. Hoy inertes (modo suave), quemados antes de que la fase 2
los active. Rotarlos exige rotar `SECRET_KEY`.

> **Decisión previa que conviene tomar:** si el repo **debe** ser público. Si no,
> hacerlo privado ya reduce el daño mientras se purga el historial.

---

## 2. Inventario completo

Leyenda de acción: **BORRAR** · **ARCHIVAR** (`_historico/`) · **ACTUALIZAR** · **SE QUEDA**

### 2.1 Raíz y arquitectura

| Doc | Cat. | Acción | Se unifica en → | Por qué (evidencia) |
|---|---|---|---|---|
| `README.md` | HECHO | ACTUALIZAR | — | Describe bien el proyecto real; 2 datos falsos: dice **11 apps** (son **12**, falta `apps.onboarding` en `core/settings.py:63-74`) y que `apps/kordial`+`apps/VitalK` están "pendientes de borrar" — **ya no existen** (`ls apps/`). |
| `CLAUDE.md` | Mixto | **Ver §5** | — | 2.096 líneas, de las cuales **1.783 (85%) son bitácora de sesiones** (§11, líneas 313-2096). Memoria operativa y diario mezclados. **Decide Alex.** |
| `arquitectura/ARQUITECTURA.md` | DEUDA | ACTUALIZAR | **destino** (absorbe `MAPA_APLICACION.md`) | Único doc de arquitectura y lo apuntan `CLAUDE.md:2` + 2 agentes. Recuperable: su §1/§4 (dominio) sobrevivió al corte. Pero dice "11 apps" (12), "~360+ tests" (~556), y menciona 3× a `kordial`/`VitalK` como "pendientes de borrar" (borradas). **No conoce la plataforma geo nueva.** |
| `arquitectura/DEUDA_TECNICA.md` | — | ✅ **ACTUALIZADO** | **destino** de toda la deuda | Ver §6. |
| `arquitectura/MAPA_APLICACION.md` | **NO VA** | **BORRAR** | `ARQUITECTURA.md` §4/§5 · `/api/schema/` · `GLOSARIO.md` | **≈70% apunta a cosas que no existen.** Mapa de un sistema de 7 apps HTML; hoy son 12 apps y 3 templates. Una sección entera describe `apps.kactivo`, **borrada el 2026-05-27**. El propio `ARQUITECTURA.md:748-749` dice que *"la lista canónica de endpoints es el schema OpenAPI, no esta sección"*. |

### 2.2 Frontend

| Doc | Cat. | Acción | Se unifica en → | Por qué (evidencia) |
|---|---|---|---|---|
| `frontend/MIGRACION_HTML_ANGULAR.md` | HECHO | ✅ **ARCHIVADO** | — | La migración cerró. Quedan 3 templates y 1 vista que renderiza (`apps/votaciones/views/public.py:32`) — exactamente el residuo que el propio doc declaró final. **Se contradice a sí mismo en 8 de 11 tablas.** |
| `frontend/PLAN_FRONTEND.md` | **NO VA** | **ARCHIVAR** ⚠️ | — | Plan de un "destino Angular **condicional**" cuya decisión ya se tomó y ejecutó. Etapa A está muerta: **Tom Select = 0 ocurrencias en el repo**; HTMX/Alpine solo en `templates/base.html:22,28` para **una** página (el kiosko). ⚠️ **`CLAUDE.md:29-36` lo cita como regla viva** → archivarlo exige reescribir ese párrafo. **Por eso no lo archivé: toca `CLAUDE.md`.** |
| `frontend/FRONTEND_ANGULAR.md` | HECHO/DEUDA | **ACTUALIZAR** (reescritura) | — | **El doc más peligroso del repo — 16 afirmaciones falsas.** Es la única guía Angular (`docs/README.md:50`), borrarla deja un hueco. Ver §3. |
| `frontend/DESPLIEGUE_FRONTEND.md` | PENDIENTE | ACTUALIZAR | — | **El mecanismo central es correcto** (Django sirve `/app/*`, `core/urls.py:59-60`; build con `--base-href=/app/`). Único procedimiento de deploy documentado. Su contexto ("coexistencia con Django HTML") describe el mundo pre-corte. |
| `frontend/README.md` *(raíz de `frontend/`)* | **NO VA** | **BORRAR** | `GETTING_STARTED.md` §4 | **Boilerplate intacto de `ng new`.** Cero contenido de innovaK, y **activamente dañino**: `:15` manda `ng build` sin `--base-href=/app/` → el bug exacto que dejó la SPA en blanco el 2026-06-18. |

### 2.3 Propuestas

| Doc | Cat. | Acción | Se unifica en → | Por qué (evidencia) |
|---|---|---|---|---|
| `HANDOFF_banco_estratificacion.md` | HECHO | ✅ **ARCHIVADO** | vivo → `DEUDA_TECNICA.md` | Handoff **ejecutado hoy**: PR-A en producción, 24/24 en v4. Es diario, no documentación. Lo vivo (C2/UPZ, banco.md, cockpit sin scopear) se extrajo a `DEUDA_TECNICA.md` **B7/B8/R2**. |
| `rbac_dashboard_ia_scope_fix.md` | HECHO | ✅ **ARCHIVADO** | — | Reporte de `01c573c`, **ancestro de HEAD**. Las 3 rutas verificadas una por una. **Es el único doc del repo sin una sola afirmación falsa.** |
| `onboarding_kenny.md` | HECHO | ✅ **ARCHIVADO** | — | Se declara *"PROPUESTA — sin implementar"*: `apps/onboarding/` existe entera, DDL aplicado, 7 tests, `frontend/src/app/features/onboarding/`. **En producción desde `1741dd8`.** |
| `banco_iniciativas_v2.md` | HECHO | ✅ **ARCHIVADO** | vivo → `DEUDA_TECNICA.md` **B6** | DDL aplicado (`scripts/aplicados_2026-05-08/`), y los Lotes 2/3/4 ya reescribieron encima. La rúbrica v4 es de otra generación. Único residuo (soporte legal opcional) extraído a **B6**. |
| `estratificacion_ideca.md` | HECHO | ✅ **ARCHIVADO** | PR-7 → `DEUDA_TECNICA.md` | **Se declara "PROPUESTA (sin ejecutar). No se ha tocado código ni BD"** — y PR-0..PR-6 están **todos en producción**. La afirmación más grande del repo. Valor histórico real: registra el **por qué** (R1 PostGIS sobre BD compartida, fallback shapely). |
| `estratificacion_ideca_estado.md` | HECHO | ✅ **ARCHIVADO** | vivo → `DEUDA_TECNICA.md` **D1-D4** | Registro de estado = diario. Todo lo técnico en producción. Lo vivo (25 sedes fuera, estrato autodeclarado, M22) extraído a **D1-D4/G8**. Su §4-ter (procedimiento de rebuild) es la única referencia cruzada — se repuntó desde `plan_evolucion_mapa.md`. |
| `estratificacion_ideca_runbook_ddl.md` | HECHO | ✅ **ARCHIVADO** | — | Runbook **ya ejecutado el 2026-07-09** (DDL aplicado, 18.929 manzanas, 241 sedes). Valor histórico: documenta sus propias correcciones (`pg_dump` por TCP no funciona; `up -d --build` era un no-op). |
| `estratificacion_ideca_memo_comite.md` | **NO VA** | **BORRAR** | — | **Alex decidió explícitamente que estas decisiones NO van al Comité** (*"no, estas decisiones las tomamos nosotros"*). El memo entero existe para pedirle al Comité 3 decisiones que ya no se le van a pedir. **Nunca se envió a nadie.** Su contenido técnico útil (tabla de manzanas por estrato, efecto de "sin estrato oficial") ya vive en `estratificacion_ideca_estado.md` §3, archivado. |
| `plan_evolucion_mapa.md` | **PENDIENTE** | **SE QUEDA** + ACTUALIZAR | — | **El plan vivo del proyecto.** Fase 0 ✅ ejecutada hoy; Fase 1 aprobada; Fases 2–3 pendientes. **Actualizar:** DDL 012 ya aplicado y el sync de placas corriendo. |
| `control_acceso_roles.md` | DEUDA | ACTUALIZAR | huecos → `DEUDA_TECNICA.md` **R1** | **Su §1 entero es falso** (ver §3). Solo sobreviven 4 filas: `banco`, `festivales`, `caracterizacion` y CRUD de `presupuesto` sin scope → extraído a **R1**. Una vez extraído, **el doc puede borrarse**. |
| `cursos_kdapp_brecha.md` | PENDIENTE | ACTUALIZAR | — | **3 de 7 PRs ya hechos** y marcados "❌ NO EXISTE" (cupos y lista de espera están en producción). PR-3/4/5/7 siguen abiertos y son reales. |
| `ux_pendiente.md` | Mixto | **BORRAR** | a11y → `DEUDA_TECNICA.md` **F4** | Escrito contra la era Django-templates (`base.html`, FontAwesome, `apps/dashboard/static/`), retirada el 2026-06-11. §2 y §3 son NO VA. **Único pendiente real de todo el doc:** no hay `axe-core`/`pa11y` → extraído a **F4**. |
| `diseno/kenny_asistente/README.md` | **NO VA** | **ARCHIVAR** | residuo → **F3** | KENNY existe, pero **ninguno de los 5 flujos que este diseño especifica se implementó**. El menú real (`flujos.data.ts:15-17`) no tiene PQRS, citas, trámites ni noticias. Se construyó otra cosa. |
| `diseno/kenny_asistente/PROMPT.md` | **NO VA** | **ARCHIVAR** | — | Ídem. Dice *"decisiones que debes tomar con Alex ANTES de codear"* — tomadas y ejecutadas hace 10 días. Y ambos dicen **OpenAI**; el LLM real es **Mistral** (`apps/dashboard/services/kenny_llm.py:83-88`). |

### 2.4 Informes

| Doc | Cat. | Acción | Se unifica en → | Por qué (evidencia) |
|---|---|---|---|---|
| `informes/INFORME_MAYO_2026.md` | HECHO | ✅ **ARCHIVADO** | `CLAUDE.md` §11 | Informe de un mes cerrado, correcto **como registro**. Lista `apps.kactivo` como activa — borrada **1 día después** de cerrar el informe. Envejeció en 24 h. |
| `informes/ANALISIS_VALOR.md` | **NO VA** | **ARCHIVAR** | — | Snapshot de opinión del 2026-04-29. Su §7 *"foco recomendado próximos 3 meses"* **venció el 2026-07-29** y se cumplió por otra ruta. Recomendaba *"medir uso del Dashboard IA 30 días; si <2 usuarios/semana, removerlo"* — se hizo lo contrario. |
| `informes/ETAPA_B_CONTRATOS.md` | DEUDA | **BORRAR** | `/api/schema/` (Swagger `/api/docs/`) | **Se autodeclara cerrado** (`:3` "Cerrada el 2026-05-28") y sigue vendiéndose como contrato vivo "al equipo Angular" — cuyo trabajo terminó hace un mes. **Es un doc a mano que se autodescribe como espejo de un artefacto generado** (`:482-483`): duplicación por definición. Le faltan ~8 módulos. |
| `informes/MEJORAS_FUTURAS.md` | DEUDA | **BORRAR** | `DEUDA_TECNICA.md` **F2** + vivo | 44 líneas, y el que más engaña por línea. 2 ítems no justifican archivo propio; **el propio doc admite** (`:7`) que la deuda real vive en `DEUDA_TECNICA.md`. Declara ✅ entregada una feature **que se perdió en una regresión** → **F2**. |

### 2.5 Manuales

| Doc | Cat. | Acción | Se unifica en → | Por qué (evidencia) |
|---|---|---|---|---|
| `manuales_modulos/README.md` | HECHO | SE QUEDA | — | Índice exacto; convención clara. Ajuste: `:23` apunta a `usuarios_solicitados.md`, que desaparece por **P1**. |
| `manuales_modulos/festivales.md` | HECHO | **SE QUEDA** | — | **El mejor manual del set.** Verificado contra código: máx. 15 festivales, encuesta gateada, cierre a 1 día (`DIAS_GRACIA_CIERRE = 1`). **Cero afirmaciones falsas, sin tokens ni dominios hardcodeados.** |
| `manuales_modulos/infraestructura.md` | HECHO | SE QUEDA | — | Módulo real y verificado (30 tramos / 13 parques coinciden con §9). Typo menor: `:63` "CON-791-**2015**" vs 2025. |
| `manuales_modulos/banco.md` | DEUDA | ACTUALIZAR | → `DEUDA_TECNICA.md` **B7** | URLs **sí** al día (SPA). Falta puntaje/105, ranking y panel de comité (`ComiteEvaluarView`, `RecalcularLoteView`). **Antes de usarlo con Deportes.** |
| `manuales_modulos/mapa.md` | DEUDA | ACTUALIZAR | — | Quedó en el mapa **pre-estratificación**: falta la capa IDECA (que existe, `mapa.component.ts:148-158`), `/geo/api/kennedy/estratificacion/`, y los 2 endpoints de direcciones. |
| `manuales_modulos/cultura.md` | DEUDA 🔴 | **ARCHIVAR** | — | Se declara **"Manual de prueba"** para una ronda de QA ya pasada. **Publica 3 tokens HMAC vivos** (**P2**) + dominio ngrok temporal + IDs de evento hardcodeados. |
| `manuales_uso/README.md` | 🔴 PII | ACTUALIZAR | — | `:15` nombre completo + username → reemplazar por rol. |
| `manuales_uso/cultura.md` | 🔴 PII | ACTUALIZAR | — | `:4`/`:17` nominaliza el manual a una persona. **Un manual por rol no debe llevar nombre propio**: `"Manual del rol Coordinador — Cultura"` sirve para la siguiente contratista sin reeditar. Contenido verificado ✅. |

### 2.6 Referencia, infra, operación

| Doc | Cat. | Acción | Se unifica en → | Por qué (evidencia) |
|---|---|---|---|---|
| `GETTING_STARTED.md` | HECHO | ACTUALIZAR | **destino** de arranque | **Los pasos funcionan hoy** (verificado uno a uno: 4 contenedores, puertos, `--base-href=/app/` correcto). Faltan `MISTRAL_*` y `MONGO_*`; `:44` apunta a k8s como "despliegue en producción" (no lo es); `:18` dice Node 20+ y el `Dockerfile:18` instala Node 18. |
| `GLOSARIO.md` | HECHO | **SE QUEDA** | **destino** del vocabulario | **El mejor doc del repo.** Vocabulario verificado contra código. Falta: Kenny ya **no** es propuesta (está en producción) y no menciona estrato/geocodificador. |
| `referencia/SIPSE.md` | DEUDA | ACTUALIZAR + adelgazar | cadena → `GLOSARIO.md` | El marco institucional (Circular 14/2018) es su único valor propio y no envejece. El resto duplica. **Ojo:** el acrónimo SIPSE tiene **3 definiciones distintas** entre este doc y `GLOSARIO.md:14`. Hay que fijar una. |
| `infra/despliegue_kubernetes.md` | **NO VA** | **ARCHIVAR** | — | **innovaK NO se despliega en Kubernetes**: 0 manifiestos, 0 Helm; el único YAML es `docker-compose.yml`. **El doc es honesto consigo mismo** (§8.4: *"¿Manifiestos/Helm? → No"*): es un **cuestionario de intake** para el equipo Oracle, fechado 2026-06-24. El problema es el nombre y la ubicación: parece el despliegue real y `GETTING_STARTED.md:44` lo enlaza como tal. |
| `infra/artefactos/README.md` + 5 artefactos | DEUDA | **BORRAR** (carpeta) | raíz | **Los 5 divergieron.** La copia de `requirements.txt` no tiene `shapely`/`drf-spectacular`/… → **quien despliegue con ella, no arranca**. Caso de libro de por qué no se duplican artefactos vivos → **F5**. |
| `operacion/usuarios_georef.md` | 🔴 **PII** | **BORRAR + purgar historial** | `credenciales_georef.local.txt` | **P1.** |
| `usuarios_solicitados.md` | 🔴 **PII** | **BORRAR + purgar historial** | `credenciales_georef.local.txt` | **P1.** |
| `docs/README.md` | DEUDA | ACTUALIZAR | — | Es la raíz de la duplicación. No indexa `docs/operacion/` (por eso las cédulas quedaron fuera de radar); vende `infra/` como "dossier Kubernetes"; y su regla `:73-74` *"no se borra"* choca con la Ley 1581. |
| `_historico/*` (17 docs) | — | SE QUEDA | — | Correctamente archivados. `_historico/README.md` mantiene el índice cronológico. |

---

## 3. Afirmaciones falsas — lo más valioso del ejercicio

**~90 en 20 documentos.** Las que cuestan dinero o tiempo real:

### 🥇 Las que rompen producción si alguien las obedece

| Doc dice | Código dice |
|---|---|
| `FRONTEND_ANGULAR.md:254` — build de prod: **`npm run build`** (sin `--base-href`) | Es **el bug exacto** del 2026-06-18: `index.html` pide `/main.js` en la raíz → 404 → *"la SPA en blanco, parecía caída aunque el contenedor estaba Up healthy"* (CLAUDE.md). El correcto es `npm run build -- --base-href=/app/`. |
| `frontend/README.md:15` — *"Run `ng build` to build the project"* | Ídem. Y es lo primero que lee quien entra por `frontend/`. |
| `docs/infra/artefactos/requirements.txt` | Sin `shapely`/`drf-spectacular`/`django-cors-headers`/`django-ratelimit` → **Django no arranca**. |

### 🥈 Las que hacen reconstruir algo que ya existe

| Doc dice | Código dice |
|---|---|
| `control_acceso_roles.md:75-77` — *"**No existe ningún helper de scope por dependencia** en todo `apps/`… cero resultados en código de producción"* | `apps/login/services/scope.py` (237 líneas), **en producción**, consumido por **8 módulos**: `:130` `aplicar_subgrupo`, `:163` `aplicar_evento_scope`, `:221` `evento_visible`. |
| `FRONTEND_ANGULAR.md:50-67` — *"**Regla B: los formularios públicos NO se migran a Angular**"* + "lista canónica de intocables" | **Todos migrados**: `frontend/src/app/features/publico/publico.routes.ts`, 10 rutas. 4 de las 5 filas "intocables" son falsas. **Es la mentira que ya mordió una vez** — se corrigió en `MIGRACION_HTML_ANGULAR.md` y sobrevivió intacta aquí. |
| `cursos_kdapp_brecha.md:16-17` — cupos y lista de espera *"❌ NO EXISTE"* | Ambos **en producción**: `apps/login/models/evento.py:164` `cupo_maximo`; `models/inscripcion_evento.py:23` `estado` (inscrito/espera/rechazado). |
| `onboarding_kenny.md:3-5` — *"PROPUESTA — sin implementar"* | `apps/onboarding/` completa + DDL aplicado + 7 tests + frontend. En producción. |
| `estratificacion_ideca.md` (cabecera) — *"PROPUESTA (sin ejecutar). **No se ha tocado código ni BD**"* | PR-0..PR-6 **todos en producción**: `manzana_estrato` (18.929 filas), `escuela.estrato_ideca` (241 sedes), endpoint y capa del mapa. |

### 🥉 Las que describen un sistema que ya no existe

| Doc dice | Código dice |
|---|---|
| `MAPA_APLICACION.md:160-177` — `apps.kactivo` *"parcialmente activo"* (18 menciones) + *"`kordial`/`VitalK` **aún existen en disco**"* | Las 3 **borradas** (kactivo 2026-05-27; kordial/VitalK 2026-07-06). |
| `PLAN_FRONTEND.md:69` — Etapa A (HTMX+Alpine+**Tom Select**) *"**Activa**"* | **Tom Select: 0 ocurrencias en el repo.** |
| `PLAN_FRONTEND.md:46` / `ANALISIS_VALOR.md:33` — *"≈160 templates"* / *"132 templates"* | **3.** |
| `INFORME_MAYO_2026.md:23` — *"**0 deuda técnica activa** por primera vez en su historia"* | Cierto el 26-may. Hoy `DEUDA_TECNICA.md` cataloga ~25 ítems. |
| `ETAPA_B_CONTRATOS.md:100,108` — forms públicos del Banco y Jóvenes *"HTML form legacy"* | Redirects a Angular desde 2026-06-04 (`views/public.py:19-20`). |
| `FRONTEND_ANGULAR.md:31-45` — *"**Nginx hace routing transparente**"* + rollback *"en segundos al HTML legacy"* | `nginx.conf` **no tiene `location /app/`**. Django sirve `/app/*` (`core/urls.py:59-60`). El switch **nunca existió**, y el legacy está borrado: no hay rollback. |
| Tests: *"46"* (`MAPA_APLICACION`), *"105"* (`banco_v2`), *"128"* (`PLAN_FRONTEND` ×3), *"134"* (`INFORME_MAYO`), *"318"* (`ETAPA_B`), *"~360+"* (`ARQUITECTURA`), *"415"* (`k8s`) | **~556.** Siete cifras distintas en siete documentos. |

### Mención especial — el doc que dice la verdad

`propuestas/rbac_dashboard_ia_scope_fix.md`: **cero afirmaciones falsas**, las 3
rutas verificables una por una. Único desfase: *"cascada pendiente de tu OK"* → ya
cascadeado. **Es el modelo de cómo debería escribirse un reporte de cierre.**

### Dos que no son drift de doc, son bugs

- **F1 — la multi-alcaldía no existe.** `DESPLIEGUE_FRONTEND.md:115` y
  `FRONTEND_ANGULAR.md:219` venden *"cambiar 3 variables y cero código tocado"*.
  `environment.prod.ts` **nunca se usa**: sin `fileReplacements` en `angular.json`,
  el build compila `environment.ts`. **Una feature que se cree entregada.**
- **F2 — regresión silenciosa.** `MEJORAS_FUTURAS.md:38` declara ✅ entregada la
  persistencia de pestaña del mapa. **0 hits de `localStorage`** en `features/mapa/`:
  se perdió al reescribir en Angular y el doc sigue diciendo que está.

---

## 4. Qué borrar (decide Alex)

### 4.1 Borrado obligatorio — legal (**P1**)

| Archivo | Líneas | Por qué |
|---|---:|---|
| `docs/operacion/usuarios_georef.md` | 50 | Cédulas + nombres + CPS. **+ purgar historial.** |
| `docs/usuarios_solicitados.md` | 72 | Ídem. **+ purgar historial.** |

**No basta `git rm`:** están en 5 commits del remoto público.

### 4.2 Borrado propuesto — no aportan y confunden

| Archivo | Líneas | Por qué |
|---|---:|---|
| `docs/arquitectura/MAPA_APLICACION.md` | 517 | ≈70% describe cosas borradas. Lo canónico es `/api/schema/`. |
| `docs/informes/ETAPA_B_CONTRATOS.md` | 483 | Espejo a mano de un artefacto generado, cerrado hace 2 meses. |
| `docs/propuestas/estratificacion_ideca_memo_comite.md` | 187 | **Alex: las decisiones no van al Comité.** Nunca se envió. |
| `docs/propuestas/ux_pendiente.md` | 109 | Era Django-templates. Lo vivo → **F4**. |
| `docs/informes/MEJORAS_FUTURAS.md` | 44 | 2 ítems; el propio doc dice que la deuda vive en `DEUDA_TECNICA.md`. |
| `frontend/README.md` | 27 | Boilerplate de `ng new` con el comando que rompe prod. |
| `docs/infra/artefactos/` (README + 5) | ~21 + artefactos | Copias divergidas de artefactos vivos → **F5**. |

**Total propuesto a borrar: 8 archivos + 1 carpeta · ~1.900 líneas.**

Condicionados a extraer antes lo vivo (ya hecho en `DEUDA_TECNICA.md`):
`control_acceso_roles.md` (238 líneas) → borrable una vez **R1** está registrado.

### 4.3 Archivar (reversible, `git mv`)

Ya ejecutado en §6: 8 archivos. Pendientes de decisión: `PLAN_FRONTEND.md`
(toca `CLAUDE.md`), `ANALISIS_VALOR.md`, `diseno/kenny_asistente/*` (2),
`infra/despliegue_kubernetes.md`, `manuales_modulos/cultura.md`.

---

## 5. `CLAUDE.md` — propuesta, no ejecutada

**El dato:** 2.096 líneas. **§11 "Bitácora de sesiones" = líneas 313-2096 = 1.783
líneas (85% del archivo), 21 entradas** desde 2026-04-20.

Las secciones §1-§10 (312 líneas) son **memoria operativa**: qué respetar, qué no
tocar, quién aprueba qué, flujo git, heurísticas. Eso es lo que un agente necesita
cargado en cada sesión. La bitácora es **diario**: valiosa, pero es historia.

**Propuesta:**
- `CLAUDE.md` se queda en ~312 líneas: §1-§10 + un puntero a la bitácora.
- §11 → `docs/_historico/bitacora_sesiones.md` (1.783 líneas), índice cronológico
  igual que el resto de `_historico/`.
- Al hacerlo, arreglar `CLAUDE.md:29-36`, que cita `PLAN_FRONTEND.md` como regla
  viva (*"camino híbrido con destino Angular condicional — léelo antes de proponer
  cualquier reescritura UI"*). **Ese plan ya se ejecutó**: la regla que cita es de
  un mundo que no existe, y es lo primero que lee un agente antes de tocar UI.
  También `.claude/agents/api.md:13,222` apunta a `docs/PLAN_FRONTEND.md` — **ruta
  que ya no existe**.

**No lo ejecuté:** es el archivo que se carga en cada sesión y lo decide Alex.

---

## 6. Lo ya ejecutado (working tree, sin commit)

### 6.1 `DEUDA_TECNICA.md` — reescrito como fuente única

Antes declaraba *"0 deuda crítica, 0 de limpieza"*. Ahora consolida **~25 ítems**
con `archivo:línea`, recogidos de 6 documentos donde estaban sueltos:

- **P1-P2** — exposición legal (PII + tokens HMAC). **Nuevo, grave.**
- **G1-G8** — los 8 hallazgos geo/eventos de hoy.
- **B1-B8** — Banco (de `estratificacion_ideca_estado.md` §9 y `banco_iniciativas_v2.md`).
- **D1-D4 + M-EDU** — datos.
- **F1-F6** — frontend/infra.
- **R1-R2** — RBAC (de `control_acceso_roles.md` y el handoff).

> **Corrección de una deuda mal formulada.** Se me pasó como *"`maxlength="120"`
> del form contra `CharField(max_length=50)` → **DataError** potencial"*. El código
> dice otra cosa: los campos de `red_detalle` **sí** usan `maxlength="50"`
> (`banco-publico.component.ts:817,830`), y el `120` de `:940,958` corresponde a
> `InscripcionBancoEscenarioDetalle`, que **es** `max_length=120` — ahí no hay
> desalineación. **El defecto real es otro y está en G4:** el `direccion-picker`
> no acota el largo (0 `maxlength`) y el backend **sí valida** y rechaza
> (`forms/inscripcion.py:613-618`) → **no hay `DataError`**, hay un **callejón sin
> salida**: el usuario no puede acortar una dirección que eligió de una lista.
> *El código manda sobre el doc — y también sobre el encargo.*

### 6.2 Archivados con `git mv` (8 archivos, ~2.100 líneas)

Solo lo **claramente HECHO** y con valor histórico de *por qué*:

| Origen | Destino |
|---|---|
| `propuestas/HANDOFF_banco_estratificacion.md` | `_historico/2026-07-16_handoff_banco_estratificacion.md` |
| `propuestas/estratificacion_ideca.md` | `_historico/2026-07-08_estratificacion_ideca_plan.md` |
| `propuestas/estratificacion_ideca_estado.md` | `_historico/2026-07-16_estratificacion_ideca_estado.md` |
| `propuestas/estratificacion_ideca_runbook_ddl.md` | `_historico/2026-07-09_estratificacion_runbook_ddl.md` |
| `propuestas/rbac_dashboard_ia_scope_fix.md` | `_historico/2026-07-16_rbac_dashboard_ia_scope_fix.md` |
| `propuestas/onboarding_kenny.md` | `_historico/2026-07-06_onboarding_kenny.md` |
| `propuestas/banco_iniciativas_v2.md` | `_historico/2026-05-08_banco_iniciativas_v2.md` |
| `frontend/MIGRACION_HTML_ANGULAR.md` | `_historico/2026-06-11_migracion_html_angular.md` |

Índice de `_historico/README.md` actualizado. Referencia cruzada de
`plan_evolucion_mapa.md` §7 repuntada a la nueva ruta.

**No se borró nada.** No se hizo commit ni push.

---

## 7. Estructura final propuesta

**Criterio (Alex): esto es UN proyecto, no una colección de módulos.** Alguien que
llega debe poder responder sin cazar por carpetas: **qué es · cómo se corre · cómo
está armado · qué falta · qué está roto.**

```
README.md                    ← qué es innovaK (puerta de entrada)
CLAUDE.md                    ← memoria operativa del agente (~312 líneas, sin bitácora)

docs/
  README.md                  ← índice
  GETTING_STARTED.md         ← CÓMO SE CORRE      (fuente única: arranque, .env, comandos)
  GLOSARIO.md                ← QUÉ SIGNIFICA      (fuente única: vocabulario + cadena SIPSE)

  arquitectura/
    ARQUITECTURA.md          ← CÓMO ESTÁ ARMADO   (fuente única; absorbe MAPA_APLICACION)
    DEUDA_TECNICA.md         ← QUÉ ESTÁ ROTO      (fuente única de deuda)

  operacion/
    despliegue.md            ← CÓMO SE DESPLIEGA  (docker-compose real; de DESPLIEGUE_FRONTEND)

  manuales_modulos/          ← cómo funciona cada flujo (banco · festivales · infraestructura · mapa)
  manuales_uso/              ← manual por ROL, sin nombres propios

  propuestas/                ← SOLO lo vivo
    plan_evolucion_mapa.md   ← Fases 1-3 (geo)
    cursos_kdapp_brecha.md   ← PR-3/4/5/7
    estrato_criterio.md      ← (nuevo) la decisión de estrato→puntos, que la toma Alex

  referencia/SIPSE.md        ← marco institucional (adelgazado; la cadena vive en GLOSARIO)

  _historico/                ← diario y planes ejecutados
    bitacora_sesiones.md     ← (de CLAUDE.md §11)   [decide Alex]
    YYYY-MM-DD_*.md
```

**Desaparecen como carpeta:** `docs/frontend/` (lo vivo → `operacion/despliegue.md`
y `ARQUITECTURA.md`), `docs/informes/` (snapshots → `_historico/`), `docs/diseno/`
(→ `_historico/`), `docs/infra/artefactos/` (→ la raíz manda).

### Unificación — una sola fuente de verdad por tema

| Tema | Hoy vive en | Debe vivir en |
|---|---|---|
| **Cadena Proyecto→Meta→KPI→Actividad→Evento** | `GLOSARIO.md` · `README.md` · `SIPSE.md` · `ARQUITECTURA.md` · `MAPA_APLICACION.md` · `CLAUDE.md` — **6** | **`GLOSARIO.md`**; el resto enlaza |
| **Stack + "BD externa `managed=False`"** | `ARQUITECTURA.md` §2/§9 · `MAPA_APLICACION.md` · `ANALISIS_VALOR.md` · `INFORME_MAYO_2026.md` · `CLAUDE.md` — **5** | **`ARQUITECTURA.md` §2** |
| **Flujo git `feat→desarrollo→Pruebas→produccion`** | `CLAUDE.md` §5 · `README.md` · `MAPA_APLICACION.md` · `INFORME_MAYO_2026.md` · `ANALISIS_VALOR.md` + 9 propuestas — **14** | **`CLAUDE.md` §5** (ya es la tabla canónica) |
| **Inventario de endpoints** | `MAPA_APLICACION.md` §4 · `ETAPA_B_CONTRATOS.md` (entero) | **`/api/schema/`** (generado; nunca a mano) |
| **Glosarios locales** | `banco.md` §0 · `mapa.md` §0 · `SIPSE.md` · `MAPA_APLICACION.md:485-505` — **4** | **`GLOSARIO.md`** |
| **Variables de entorno** | `GETTING_STARTED.md` · `despliegue_kubernetes.md` · `infra/artefactos/README.md` — **3, las 3 sin `MISTRAL_*`** | **`GETTING_STARTED.md` §2** (+ `.env.example` versionado, solo nombres) |
| **Artefactos infra** | raíz · `docs/infra/artefactos/` — **2, ya divergidos** | **la raíz** |
| **Reglas de aprobación** | `GETTING_STARTED.md` §7 · `CLAUDE.md` §9 | **`CLAUDE.md` §9** |
| **Deuda** | 6 documentos | **`DEUDA_TECNICA.md`** ✅ ya hecho |

### Reglas propuestas para que esto no se repita

1. **Un doc que se autodescribe como espejo de un artefacto generado, se borra.**
   El OpenAPI y los artefactos de la raíz mandan. (Mató a `ETAPA_B_CONTRATOS.md` y a `artefactos/`.)
2. **Los handoffs y bitácoras no son documentación**: nacen en `_historico/` o no
   nacen. Lo vivo se extrae al doc que corresponde el mismo día.
3. **Ningún conteo en prosa** (tests, apps, templates, líneas). Envejece en días:
   7 documentos declaran 7 cifras distintas de tests. Si hace falta, que sea un comando.
4. **Excepción a "no se borra"** (`docs/README.md:73-74`): **los datos personales se
   borran y se purga el historial.** Archivar una cédula no la protege.
5. **Un doc que dice "PROPUESTA — sin ejecutar" y está ejecutado es peor que no
   tener doc.** Al cerrar un PR, el doc que lo propuso se archiva en el mismo commit.

---

## 8. Qué necesito de Alex

1. **¿El repo debe seguir siendo público?** Condiciona la urgencia de **P1**.
2. **OK para borrar** los 2 archivos con cédulas **y purgar el historial** (reescribe
   el remoto: hay que avisar a quien tenga clones).
3. **OK para los 8 borrados de §4.2** (~1.900 líneas).
4. **Confirmar que el memo al Comité es NO VA** (entendí *"estas decisiones las
   tomamos nosotros"* → el memo entero deja de tener destinatario).
5. **`CLAUDE.md`:** ¿saco la bitácora (85% del archivo) a `_historico/`? (§5)
6. **Rotación de los 3 tokens HMAC** (**P2**) — exige rotar `SECRET_KEY`.

# Fix RBAC — el motor de consulta `dashboard_ia` respeta el subgrupo

**Rama:** `fix/rbac-dashboard-ia-scope` (worktree, desde `desarrollo`)
**Fecha:** 2026-07-14
**Antecedente:** `docs/propuestas/ia_nl2sql_diagnostico.md` (rama `explore/ia-nl2sql`),
§0.4 y §Fase 1 — "cerrar el hueco RBAC". Este PR **ejecuta** esa Fase 1.

---

## 1. Hallazgo (confirmado contra el código)

El módulo `dashboard_ia` exponía **tres** rutas de datos de beneficiarios, y
**ninguna** aplicaba el alcance por subgrupo. El gate `ModuloRequiredPermission`
controla **si** un rol entra a la IA, pero no **qué** datos ve. Resultado: cualquier
rol con el módulo (`Docente`, `CoordinadorDeportes`, `UsuarioGeneral`,
`LiderParticipacion`, `Visor`, `Gestor`…) veía el **universo completo** de personas.

| Ruta | Servicio | Fuga previa |
|---|---|---|
| `POST /dashboard/api/ia/beneficiarios` (`IABeneficiariosView`) | `ia_beneficiarios.analizar` | Conteos/agrupaciones sobre TODO el universo |
| `GET /dashboard/api/ia/analitica` (`AnaliticaBeneficiariosView`) | `ia_beneficiarios.analitica` | Tablero completo de TODOS los beneficiarios |
| `POST /dashboard/api/personas/query` (`personas_query_api`) | `IntentAnalyzer` + `SafeQueryBuilder` | **Peor**: FILAS individuales de `Persona` (nombres, fecha de nacimiento) de TODA la población |

**Precisión técnica:** no era un `aplicar_subgrupo` "mal colocado" (antes de un
JOIN o sobreescrito) — es que **nunca se llamaba**; las funciones ni recibían
`user`. Además `Persona` **no tiene** `subgrupo_id`: el alcance viaja por el
**evento** (`Evento.subgrupo_id`). El primitivo correcto ya existía en
`apps/login/services/scope.py` (`eventos_visibles_ids` / `aplicar_evento_scope`),
respetando el modelo **aditivo** subgrupo ∪ contrato ∪ curso.

---

## 2. Corrección

### 2.1 Un único punto de scope (`apps/login/services/scope.py`)

Dos helpers nuevos (aditivos, no tocan lo existente):

- `participaciones_visibles(user)` → QS de `ParticipanteEvento` acotado a los
  eventos visibles del usuario.
- `personas_beneficiarias_visibles(user)` → QS de `Persona` que participaron en
  al menos un evento visible.

Ambos **fail-closed**: superuser → todo; sin alcance / `user=None` / anónimo →
`.none()` (nunca el universo completo).

### 2.2 El motor pasa a ser consciente del usuario

- `ia_beneficiarios.analizar(pregunta, user)` y `analitica(user)`: el universo,
  las participaciones por área/escenario y el bloque geo se scopean con los
  helpers de arriba.
- `query_builder.SafeQueryBuilder.build(intent, user)`: el queryset base pasa de
  `Persona.objects.all()` a `personas_beneficiarias_visibles(user)` (superuser
  conserva el universo completo). COUNT/FILTER/GROUP/TOP heredan el filtro.
- `apps/dashboard/views.py`: las 3 vistas pasan `request.user` al motor.

### 2.3 Rutas cubiertas — ninguna se salta el scope

```
                                   ┌───────────────────────────────┐
KENNY "Consultar datos" ─────────► │ POST /dashboard/api/ia/        │
Angular /app/ia          ─────────►│      beneficiarios  (analizar) │──┐
                                   └───────────────────────────────┘  │
                                   ┌───────────────────────────────┐  │  scope.
Angular /app/analitica  ─────────► │ GET  .../ia/analitica          │──┼─►personas_
                                   └───────────────────────────────┘  │  beneficiarias_
                                   ┌───────────────────────────────┐  │  visibles(user)
(consulta de personas)  ─────────► │ POST .../personas/query        │──┘  + participaciones_
                                   │  reglas → IntentAnalyzer        │     visibles(user)
                                   │  (o LLM opcional) → SafeQuery…   │
                                   └───────────────────────────────┘
```

- **KENNY es la puerta única.** Su botón "Consultar datos" pega a
  `/dashboard/api/ia/beneficiarios`; su chat LLM (`kenny_llm.responder`) **no
  devuelve filas** y delega toda cifra a ese endpoint estructurado. Por tanto la
  ruta de Kenny queda cubierta por el mismo scope.
- **Motor de reglas y LLM comparten salida.** El LLM (si hubiera `OPENAI_API_KEY`)
  solo produce el JSON de intención; el reglas-fallback produce el mismo JSON.
  Ambos convergen en `SafeQueryBuilder.build(intent, user)` / `analizar(…, user)`,
  **después** del cual se aplica el scope. No hay bifurcación que lo evite.
- **`dash_apps.py` (Dash/Plotly legacy)** llama `build(intent)` sin `user`:
  `django_plotly_dash` **no está en `INSTALLED_APPS` ni enrutado** → es código
  muerto. Con el cambio queda **fail-closed** (devuelve vacío), nunca fuga.

---

## 3. Diccionario de sinónimos ampliado (Parte 2.1)

Sin LLM externo (decisión: reglas + diccionario, sin Ollama por ahora).

- **Motor determinístico** (`ia_beneficiarios.DIMENSIONES`): `estrato` +=
  `nivel socioeconómico`; `zona` += `UPZ`, `sector`, `UPL`. Rama de
  escenarios/actividades += `festival`, `convocatoria`, `iniciativa`, `actividad`.
- **Ruta `SafeQueryBuilder`** (`ai_config.FIELD_MAPPING` + `intent_analyzer`):
  `nivel socioeconómico`→`estrato_social`; `UPZ`/`UPL`/`sector`/`barrio`→`zona_codigo`.

(`festival`/`convocatoria`/`iniciativa` no mapean a un campo de `Persona`; son
conceptos de evento y se resuelven en la rama de actividades del motor.)

---

## 4. Tests y resultados contra volumen real

Nuevo: `apps/login/tests/test_rbac_dashboard_ia_scope.py` (11 tests), registrado
en `scripts/run_smoke_tests.py`. Corre contra la BD externa **`poblacion_kennedy`
(volumen de producción)** — el runner del proyecto usa `unittest` + Test Client
sobre la BD real (no crea BD test). Usuarios/pertenencias/grupo IA **efímeros**,
limpiados por SQL crudo.

Cubre los **5 roles** del encargo por su arquetipo de alcance:

| Rol | Arquetipo de scope | Verificación |
|---|---|---|
| Coordinador | subgrupo | Universo == exactamente el del subgrupo; 0 participaciones ajenas |
| Gestor | subgrupo | Igual que Coordinador con el mismo subgrupo (el rol no amplía datos) |
| Visor | otro subgrupo | Aislado: no ve personas exclusivas del subgrupo ajeno |
| Lider_contrato | contrato | Solo eventos alcanzados por su contrato (skip si datos reales no lo permiten) |
| Profesor (`Docente`) | curso | Solo participaciones de su curso |

Más: **default-deny** (rol sin pertenencia → 0), **superuser ve todo el
universo**, y a nivel **endpoint** (la ruta de Kenny) que el `universo`/`count`
devuelto == el scopeado y **< global**, incluida la ruta de filas individuales
(`/personas/query`).

**Resultado (contra `poblacion_kennedy`):**

```
apps.login.tests.test_rbac_dashboard_ia_scope → 11 tests: 10 OK, 1 skip
  (skip = ningún contrato activo alcanza eventos con participantes en datos reales)
Suite completa run_smoke_tests.py → 555 tests OK (9 skipped)   [antes: 544]
```

Cero regresiones. Performance sin degradación: el volumen es de miles de filas
(persona 6.945, participante_evento ~2.545) y el scope agrega un `IN (ids)` sobre
`evento`/`participante_evento` — la suite completa corre en ~4,4 s.

---

## 5. Confirmación de seguridad (deliverable #3)

> **Ninguna ruta del módulo `dashboard_ia` — reglas, LLM opcional, tablero,
> filas individuales o la Dash legacy — devuelve beneficiarios fuera del alcance
> (subgrupo ∪ contrato ∪ curso) del usuario.** Todo acceso converge en
> `scope.personas_beneficiarias_visibles(user)` / `participaciones_visibles(user)`,
> que son fail-closed. La puerta de KENNY ("Consultar datos") usa exactamente esa
> ruta scopeada; su LLM conversacional no emite cifras. Verificado por 11 tests
> contra el volumen real de producción.

---

## 6. Fuera de alcance (para decisión de Alex)

- **Ollama / Qwen2.5:3b** como parser de intención: NO incluido (el reglas +
  diccionario cubre las preguntas del equipo; añadir Ollama es infra nueva). El
  diseño ya garantiza que, si algún día se cablea, su salida pasa por el mismo
  scope (§2.3).
- **Cockpit presupuestal** (`api_beneficiarios_perfil`, módulo
  `presupuesto_proyectos`/`_metas`): expone perfiles agregados de beneficiarios a
  roles presupuestales (Lider/Admin) que legítimamente ven cross-subgrupo. **No**
  se tocó — es otro módulo con otra intención. Si se quiere scopear también, es un
  PR aparte.
- **Cascada** feat→desarrollo→**Pruebas**→produccion: pendiente de tu OK. Este
  worktree se detiene con todo verde.

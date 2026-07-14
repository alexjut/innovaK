# Diagnóstico — Consulta en lenguaje natural de beneficiarios (festivales / Banco) sin API de pago

**Autor:** Sistemas / Líder Técnico de Innovación · **Fecha:** 2026-07-14
**Rama de exploración:** `explore/ia-nl2sql` (worktree, sin tocar producción)
**Estado:** SOLO DIAGNÓSTICO — no se implementó nada.

> Encargo de Alex: *"quiero quitar ese pago que hacemos a ChatGPT… proponme la
> mejor solución gratuita/open-source para consultar en lenguaje natural la BD
> de beneficiarios de festivales y proyectos, respetando el RBAC, preferible un
> endpoint DRF reutilizable."*

---

## 0. Resumen ejecutivo (TL;DR)

1. **El "pago a ChatGPT" hoy ya está prácticamente apagado.** El contenedor
   `innova_k` en ejecución **no tiene `OPENAI_API_KEY` ni `MISTRAL_API_KEY`**
   cargadas. El código está escrito para que, sin clave, caiga solo a un motor
   **determinístico por reglas** (`_fallback_rules`). Es decir: la consulta de
   beneficiarios **ya funciona 100 % gratis**; OpenAI era solo un "mejor parser"
   opcional de la redacción de la pregunta.

2. **El sistema NUNCA genera SQL crudo.** Traduce la pregunta a un JSON
   restringido (`{type, campos de una whitelist, valores}`) y lo ejecuta con el
   **ORM de Django** (`Persona.objects.filter(...).count()`). Esta es una
   arquitectura *más segura* que cualquiera de las 3 opciones que se pidió
   comparar. **No debemos retroceder a generar SQL** sobre datos de víctimas.

3. **Recomendación:** **NO adoptar PandasAI ni LangChain SQL Agent.** Ambas
   generan/ejecutan código (SQL o Python) sobre los datos y rompen el modelo de
   seguridad actual. En su lugar: **mantener el endpoint Django propio que ya
   existe** (opción 3) y, si se quiere más tolerancia a la redacción, **sustituir
   la llamada a OpenAI por un modelo local en Ollama** — que es un cambio de
   *configuración*, no de arquitectura, porque el código ya usa el cliente
   `openai` con `base_url` configurable y Ollama expone una API OpenAI-compatible.

4. **Hueco real a cerrar (más importante que la IA):** el motor de consulta
   **no aplica scope por subgrupo** (`aplicar_subgrupo`) sobre las filas. Hoy la
   única barrera es el permiso de módulo `dashboard_ia`. Un usuario con ese
   módulo ve **todo el universo** de personas, sin importar su subgrupo. Ese es
   el riesgo RBAC concreto ("un Visor no debe consultar lo que un Coordinador
   sí"), y no lo resuelve ningún LLM — se resuelve en el endpoint.

---

## 1. Contexto revisado

### 1.1 Stack existente

| Componente | Detalle |
|---|---|
| Backend | Django 4.2.11 / Python 3.10, DRF |
| BD | PostgreSQL externa compartida (`poblacion_kennedy`, 10.100.102.12:5432), **todos los modelos `managed=False`** (sin migraciones) |
| Infra | Docker Compose: `innova_k` (gunicorn 8032), `nginx` (8034), `redis`, `innova_mongo` |
| IA de pago actual | `openai==1.10.0` en `apps/dashboard/services/{intent_analyzer,kenny_llm}.py` |

### 1.2 Cómo funciona HOY la "IA de beneficiarios" (lo que se quiere migrar)

Hay **dos** caminos de IA, y conviene no confundirlos:

**A) Consulta de beneficiarios** (`IABeneficiariosView` / `AnaliticaBeneficiariosView`, gate `dashboard_ia`):

```
pregunta → IntentAnalyzer.analyze()
              ├─ (si hay OPENAI_API_KEY)  OpenAI parsea → JSON
              └─ (si no)                  _fallback_rules() por regex/keywords
           → _coerce_and_whitelist()   ← BARRERA: fuerza target=login_persona,
                                          solo campos de AIConfig.ALLOWED_FIELDS,
                                          traduce sinónimos
           → SafeQueryBuilder.build()  → ORM: Persona.objects.filter(Q(...)).count()/.values()
```

- OpenAI **solo** convierte texto libre → JSON con tipo (`count/filter/group/top`)
  y campos. **Nunca ve ni escribe SQL.** El `_coerce_and_whitelist` descarta
  cualquier campo fuera de la whitelist.
- Existe además `ia_beneficiarios.py`, que es **totalmente determinístico** (mapea
  keywords a dimensiones ORM); no usa OpenAI en absoluto.

**B) Chatbot "Kenny"** (`KennyAsistenteView`, `kenny_llm.py`): responde texto
libre contra una base de conocimiento. Usa un endpoint **OpenAI-compatible**
(`base_url` = API de Mistral por defecto) — este sí es un LLM conversacional y
es el candidato natural para apuntar a Ollama.

### 1.3 Volúmenes reales de datos (son pequeños)

| Tabla | Filas |
|---|---:|
| persona | 6.945 |
| beneficiario | 3.605 |
| organizacion | 92 |
| evento | 52 |
| inscripcion_banco_iniciativa / banco_evaluacion | 24 / 24 |
| proyecto | 14 |
| festival | 8 |
| festival_percepcion | 7 |

**Implicación:** el volumen no es el problema (miles de filas, no millones). El
reto es **generar la consulta correcta y segura**, no el rendimiento. Cualquier
enfoque cabe en memoria; lo que discrimina es la **seguridad y el RBAC**.

### 1.4 Servidor disponible

- **24 núcleos CPU**, **15 GiB RAM (~12 GiB disponibles)**, **SIN GPU**, 58 GiB
  de disco libre.
- Ya corren gunicorn + mongo + redis + nginx: hay que **compartir** esos 12 GiB.

---

## 2. Evaluación comparada de las 3 opciones

### Opción 1 — PandasAI conectado a PostgreSQL

| | |
|---|---|
| **Cómo funciona** | Un LLM genera **código Python/pandas** que se ejecuta sobre DataFrames cargados desde la BD. |
| **Pros** | Muy expresivo para análisis ad-hoc; buenos gráficos. |
| **Contras** | **(1) Ejecuta código generado por el LLM** → riesgo de ejecución arbitraria; hay que sandboxear. **(2) Carga tablas enteras a memoria** (persona 6.945 filas con datos de víctimas → pandas en RAM del proceso web). **(3) No entiende de RBAC**: filtra en pandas, no respeta subgrupo salvo que se pre-filtre el DataFrame a mano. **(4)** Duplica la lógica de negocio que ya vive en el ORM. |
| **Veredicto** | **Descartada.** Peor postura de seguridad sobre datos sensibles; no aporta nada que el ORM no dé ya. |

### Opción 2 — LangChain SQL Agent + modelo local (Ollama, Llama 3.1 8B / Mistral 7B)

| | |
|---|---|
| **Cómo funciona** | El agente inspecciona el esquema y **genera + ejecuta SQL crudo** contra Postgres en un bucle. |
| **Pros** | Cubre preguntas arbitrarias sin whitelist; el modelo local es gratis. |
| **Contras** | **(1) Genera SQL crudo sobre datos de víctimas** — exactamente el riesgo que Alex teme. Un JOIN o `WHERE` mal generado devuelve datos incorrectos con apariencia de verdad. **(2) RBAC casi imposible de garantizar**: el LLM decide las tablas; para contenerlo hay que crear un **rol de BD de solo-lectura sobre vistas restringidas** y aun así el modelo puede pedir columnas sensibles. **(3)** Dependencia pesada (LangChain) y modelo de 7-8B en **CPU sin GPU** → 5-15 tok/s, respuestas de varios segundos. **(4)** No reutiliza la lógica ORM/scope existente. |
| **Veredicto** | **Descartada** como camino principal. Máxima flexibilidad, **mínima seguridad**. El costo (rehacer el modelo de seguridad para poder confiar en SQL generado) no compensa cuando las preguntas reales son agregaciones sobre `persona`. |

### Opción 3 — Endpoint propio en Django (traduce pregunta → consulta) — **YA EXISTE**

| | |
|---|---|
| **Cómo funciona** | Justo lo que ya hay: pregunta → intención estructurada (whitelist) → **ORM**. El LLM (si se usa) solo hace el *parsing* NL→JSON, nunca toca la BD. |
| **Pros** | **(1)** El LLM no genera SQL: imposible fuga de tablas no permitidas. **(2)** Reutiliza ORM, scope y permisos de módulo. **(3)** Es un **endpoint DRF reutilizable** (lo que Alex prefiere). **(4)** Degrada con gracia: sin LLM, funciona por reglas. **(5)** El "cerebro" LLM es opcional y sustituible por Ollama con un cambio de `base_url`. |
| **Contras** | Cobertura de preguntas acotada a la whitelist (hay que ampliar campos/sinónimos a mano). No responde "cualquier cosa", pero sí lo que el negocio necesita. |
| **Veredicto** | **RECOMENDADA.** Es la base correcta; solo hay que (a) quitar la dependencia de pago apuntando a Ollama y (b) **cerrar el hueco de scope RBAC**. |

---

## 3. Recomendación justificada

**Mantener y endurecer la Opción 3 (endpoint Django con whitelist → ORM), y
sustituir el proveedor de pago por Ollama local como parser opcional.**

Por qué, en una frase: *el sistema ya resuelve el problema de forma más segura
que las alternativas; el "pago" es un extra opcional que se reemplaza con
configuración, no con una reescritura.*

Tres movimientos concretos:

1. **Quitar el pago (inmediato, riesgo cero):** confirmar que en producción no
   hay `OPENAI_API_KEY`/`MISTRAL_API_KEY` activas. Si las hay, retirarlas. El
   sistema queda en modo determinístico, gratis, hoy mismo.

2. **(Opcional) Recuperar la tolerancia a redacción con Ollama:** instalar Ollama
   en el servidor, descargar un modelo pequeño-mediano, y apuntar los clientes
   `openai` existentes (`intent_analyzer`, `kenny_llm`) a
   `http://localhost:11434/v1`. **La whitelist `_coerce_and_whitelist` sigue
   siendo la barrera** — el modelo local es solo un traductor cuya salida se
   valida igual que antes.

3. **Cerrar el hueco RBAC (lo más importante):** aplicar `aplicar_subgrupo(...)`
   sobre el queryset del `SafeQueryBuilder` antes de `.count()/.values()`, para
   que un Visor solo cuente su universo y no el de un Coordinador.

### Modelo local sugerido (CPU, sin GPU)

Para la tarea A (parsear NL→JSON) basta un modelo **pequeño**, porque la salida
es un JSON corto y guiado por ejemplos:

| Modelo | RAM aprox (Q4) | Uso |
|---|---:|---|
| `qwen2.5:3b-instruct` o `phi3.5:3.8b` | ~3-4 GiB | **Parser NL→JSON** (rápido en CPU) |
| `llama3.1:8b-instruct-q4` / `mistral:7b` | ~5-6 GiB | Chatbot Kenny (respuestas conversacionales) |

Recomendación: **empezar con un 3-4B para el parser** (latencia baja en CPU) y,
si se activa Kenny, un 7-8B para conversación. Ambos caben en los 12 GiB
disponibles, pero **no simultáneamente con holgura** junto a gunicorn/mongo —
ver riesgos.

---

## 4. Requisitos de infraestructura

- **Ollama** como servicio (contenedor `ollama` en el mismo compose, o binario en
  host). Expone `:11434` con API OpenAI-compatible (`/v1/chat/completions`).
- **RAM:** reservar ~4 GiB para un modelo 3-4B (parser) o ~6 GiB para un 7-8B.
  Con 12 GiB disponibles y gunicorn+mongo+redis ya corriendo, **un solo modelo
  cargado a la vez** es lo prudente. Configurar `OLLAMA_MAX_LOADED_MODELS=1` y
  `OLLAMA_KEEP_ALIVE` corto para liberar RAM entre consultas.
- **CPU:** sin GPU, la inferencia usa los 24 núcleos. Latencia esperada: parser
  3-4B ≈ 1-3 s; chatbot 7-8B ≈ 3-10 s por respuesta. Aceptable para uso interno
  y esporádico, **no** para alto volumen concurrente.
- **Disco:** ~3-6 GiB por modelo (hay 58 GiB, sobra).
- **Config nueva (env):** `LLM_BASE_URL=http://ollama:11434/v1`,
  `LLM_MODEL=qwen2.5:3b-instruct`, y hacer que `intent_analyzer`/`kenny_llm` lean
  `base_url` desde ahí (hoy `intent_analyzer` no pasa `base_url`; es 1 línea).
- **Red:** Ollama **solo en red interna de Docker**, nunca expuesto por nginx.

---

## 5. Riesgos y mitigaciones

| Riesgo | Severidad | Mitigación |
|---|---|---|
| **SQL/consulta incorrecta sobre datos de víctimas/beneficiarios** | Alta | Se **evita de raíz**: no generamos SQL. El LLM solo produce JSON validado por whitelist; el ORM arma la consulta. Ningún campo fuera de `ALLOWED_FIELDS` llega a la BD. |
| **Fuga RBAC: un Visor consulta el universo de un Coordinador** | **Alta (hueco actual real)** | Aplicar `aplicar_subgrupo` al queryset del `SafeQueryBuilder`. Añadir test que verifique que dos roles obtienen conteos distintos sobre los mismos datos. |
| **Modelo local inventa campos/valores** | Media | La whitelist descarta campos inexistentes; valores fuera de dominio → 0 resultados, no error. Añadir `LIMIT` en las listas (`filter`) y validación de tipos. |
| **Presión de memoria (OOM) junto a gunicorn/mongo** | Media | 1 modelo cargado a la vez, `KEEP_ALIVE` corto, modelo 3-4B para el parser. Monitorear RSS; alertar si RAM libre < 1.5 GiB. |
| **Latencia en CPU degrada UX** | Baja-Media | Parser pequeño; timeout con caída al motor determinístico (ya existe el `try/except`). Nunca bloquear la respuesta esperando al LLM > N s. |
| **Respuestas conversacionales de Kenny (alucinación)** | Media | Kenny responde sobre KB acotada; marcarlo como "orientativo". No usar Kenny para cifras oficiales — esas salen del endpoint estructurado. |
| **Datos sensibles en logs/prompts del LLM** | Media | El prompt solo lleva la **pregunta** y nombres de campos, no filas de personas. Verificar que no se logueen cédulas/nombres en el prompt. Al ser local, no sale del servidor (ventaja vs. API de pago). |

---

## 6. Plan de implementación por fases (con gate de Pruebas)

> Regla de oro: **nada llega a `produccion` sin pasar por la rama `Pruebas`** y
> el smoke suite completo (pre-push hook). Cada fase es un PR pequeño y
> reversible.

**Fase 0 — Quitar el pago (hoy, sin IA nueva).** Rama `fix/ia-sin-openai`.
- Confirmar/retirar claves de pago en prod. Documentar que el sistema queda en
  modo determinístico. Sin cambios de comportamiento para el usuario salvo menor
  tolerancia a redacciones raras. → **Pruebas** → produccion.

**Fase 1 — Cerrar el hueco RBAC (independiente de la IA).** Rama
`fix/ia-scope-rbac`.
- Aplicar `aplicar_subgrupo` en el `SafeQueryBuilder`/vistas `dashboard_ia`.
- Tests: Visor vs Coordinador obtienen conteos coherentes con su alcance.
- → **Pruebas** → produccion. *(Esta fase es la de mayor valor de seguridad.)*

**Fase 2 — Ollama en infraestructura (sin cablearlo aún).** Rama
`chore/ollama-infra`.
- Añadir servicio `ollama` al compose (red interna), descargar `qwen2.5:3b`.
- Verificar RAM/latencia bajo carga real. Feature flag apagado.
- → **Pruebas** (validar que no rompe nada) → produccion.

**Fase 3 — Cablear el parser local (detrás de flag).** Rama `feat/ia-parser-local`.
- `intent_analyzer` lee `LLM_BASE_URL`/`LLM_MODEL`; con flag on usa Ollama, con
  flag off usa reglas. La whitelist sigue validando la salida.
- Batería de preguntas de prueba (incluye la de Alex: *"¿cuántos beneficiarios
  del festival X son de estrato 1 en la UPZ Y?"*) comparando LLM vs reglas.
- Gate de **Pruebas**: revisar manualmente que las consultas generadas son
  correctas y respetan scope, **antes** de cascada.

**Fase 4 — (Opcional) Kenny conversacional local.** Rama `feat/kenny-ollama`.
- Apuntar `kenny_llm` a Ollama (7-8B). Etiquetar respuestas como orientativas.
- → **Pruebas** → produccion.

**Fase 5 — Beneficiarios de festivales en el universo IA.**
- Conectar las 7 respuestas de `festival_percepcion` y participantes de festival
  al universo consultable ("todo esto debe quedar en beneficiarios y la IA").
  Requiere decidir el mapeo percepción→persona/beneficiario (tarea aparte).

---

## 7. Qué NO hacer

- ❌ No adoptar PandasAI (ejecuta código sobre datos de víctimas).
- ❌ No adoptar LangChain SQL Agent (genera SQL crudo; RBAC no garantizable).
- ❌ No exponer Ollama por nginx ni a internet.
- ❌ No usar Kenny (LLM libre) como fuente de cifras oficiales.
- ❌ No cascadear ninguna fase a producción sin pasar por `Pruebas`.

---

## 8. Preguntas abiertas para Alex (antes de implementar)

1. ¿Confirmamos que en el servidor de producción **no** hay una `OPENAI_API_KEY`
   inyectada por otra vía (systemd, otro `.env`)? Si la hay, ¿la retiramos ya?
2. ¿La tolerancia a redacción (LLM local) es realmente necesaria, o el motor por
   reglas + ampliar sinónimos cubre las preguntas reales del equipo? *(Si basta
   con reglas, nos ahorramos toda la infra de Ollama.)*
3. Para la Fase 5: ¿cómo debe entrar un asistente de festival al universo de
   "beneficiarios" — como `persona` con `beneficiario`, o solo como registro de
   percepción con métricas agregadas?

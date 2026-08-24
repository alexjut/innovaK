# Plan · Spec 001

Cómo se construye. Cada etapa dice **qué toca**, **cómo se prueba** y **qué
riesgo cubre**.

> **La conclusión del CLARIFY cambia el tamaño de esta fase: NO hace falta DDL.**
> Etapa contractual, plan de pago y forma de pago ya tienen dónde vivir. Lo que
> falta es mapear columnas, ingerir y capturar.

---

## Etapa 0 · Cerrar el hueco de scope *(bloqueante)*

`VincularContratoActividadPlanView` valida la actividad pero **no el contrato**.
Un usuario de Educación puede enganchar un contrato de Seguridad cambiando un id
en la petición.

- **Toca:** `apps/presupuesto/api/views.py`
- **Cómo:** el `contrato_id` se valida contra los contratos del área — unión de
  `ContratoProyecto` y `ContratoActividadPlan`, la misma regla del panel.
- **Prueba:** un test que intente el acceso cruzado y espere **403**.
- **Cubre:** RF-7 · *Constitución V*

Va primero porque **toda** la escritura nueva pasa por aquí.

---

## Etapa 1 · Auditoría *(antes que cualquier formulario)*

Hoy no existe tabla de auditoría. Si los campos manuales nacen antes, nacen sin
rastro.

- **Toca:** modelo nuevo + servicio `registrar_cambio()`
- **Registra:** quién · cuándo · antes · después · proyecto · contrato · fuente
- **Requiere DDL:** sí — **una tabla nueva, aditiva**. Único DDL de la fase.
  Con backup <24 h, script de rollback y OK de Alex. *Constitución VII.*
- **Prueba:** capturar un dato deja exactamente una fila legible.
- **Cubre:** RF-8 · *Constitución IV*

---

## Etapa 2 · Ampliar el modelo `Crp` *(aditivo, sin DDL)*

`Crp` mapea 4 de ~42 columnas. Faltan `contrato_id`, `forma_pago_codigo`,
`plazo_dias`, `periodo_codigo`, `valor_neto`, `autorizacion_giro`.

- **Toca:** `apps/presupuesto/models/sql.py`
- **Riesgo real:** `metrics.py` ya usa `Crp` para «comprometido» sobre **0
  filas**. Ampliar el modelo no cambia ese cálculo, pero hay que verificar que
  no rompa nada.
- **Prueba:** los tests actuales de métricas siguen pasando.
- **Cubre:** §5.4

---

## Etapa 3 · Precarga desde SECOP *(el mayor golpe, sin un solo formulario)*

- **Toca:** comando `precargar_desde_secop`, en la línea de
  `ingest_secop_contratos`
- **Llena:** objeto, valor, fechas, **contratista** — los 25/25 tienen espejo
- **Regla:** no pisa un dato existente sin registrar el cambio en auditoría.
  *Constitución II.*
- **Prueba:** contratista pasa de **0/25**; correrlo dos veces no cambia nada
  (idempotente); un dato ya presente y distinto queda auditado, no pisado.
- **Cubre:** RF-1, RF-2

Esta etapa sola arregla más completitud que todas las demás juntas.

---

## Etapa 4 · Servicio de completitud

- **Toca:** `services/completitud_expediente.py`
- **Calcula al vuelo**, sin persistir ni cachear. *RF-3.*
- **Devuelve por contrato:** campo · valor · estado (`ok`/`pendiente`/`sin dato`)
  · fuente · si es editable
- **Distingue `$0` de `Sin dato`.** *RF-6.*
- **Metas en plural**, derivadas — nunca se piden. *RF-5.*
- **Prueba:** el contrato 105 (Educación) da la meta determinada; el 98 da sus
  siete; el 104 muestra `0 %` como cero real.
- **Cubre:** RF-3, RF-5, RF-6

---

## Etapa 5 · API de Mi Área

- **Toca:** `AreaPanelView` (se extiende, no se duplica) + endpoint de escritura
- **Escritura:** valida contrato **y** destino contra el área. *RF-7.*
- **Prueba:** acceso cruzado → 403, incluso manipulando ids.
- **Cubre:** RF-7, RF-9

---

## Etapa 6 · Mi Área — la pantalla

> ⚠️ **Frontend: coordinar con Anderson.** Trabaja en
> `feat/panel-subgrupo-ux` sobre el mismo árbol. Ver
> `docs/operacion/TRABAJO_EN_PARALELO.md`.

- Resumen del área: proyectos · contratos · **datos pendientes** · `Todos` /
  `Solo pendientes`
- Proyecto → sus contratos, cada uno con su completitud calculada
- Ficha **contrato por contrato** (nunca un formulario del subgrupo entero)
- Precargados **no editables**, con su origen visible (`SECOP ✓`)
- **Cubre:** plan §6-§10

Reutiliza tokens y patrones ya consolidados. *Constitución VIII.*

---

## Etapa 7 · Dashboard 360° consume

- El stepper **ya** lee `Contrato.etapa`: no hay copia del dato que sincronizar.
- Verificar que lo capturado aparece sin caché intermedia.
- **Cubre:** RF-9 · plan §15

---

## Etapa 8 · Segundo subgrupo

**Seguridad** (3 proyectos), no Educación.

Educación tiene 1 proyecto y 1 contrato: sirve para la mecánica, **no ejercita
la cardinalidad N** — y cuatro de los cinco contratos con actividad tocan varias
metas. Si sólo se prueba con Educación, ese caso no se ve.

- **Prueba:** funciona sin tocar una línea. Cero `if subgrupo == …`. *RF-10.*

---

## Etapa 9 · Calidad

Contraste en CI con **baseline + no-regresión** (plan §41), `ENTIDADES` borrado
con evidencia (plan §40), los 5 gráficos del expediente resueltos según el
criterio del plan §39, y la auditoría del expediente retomada **en lotes** — no
25 agentes de una (plan §43).

---

## Orden y dependencias

```
0 scope ─┬─► 1 auditoría ─► 3 precarga ─► 4 completitud ─► 5 API ─► 6 pantalla ─► 7 360°
         └─► 2 modelo Crp ──────────────────┘                                      │
                                                                    8 segundo subgrupo
                                                                              9 calidad
```

**0 y 1 son bloqueantes.** 2 y 3 pueden ir en paralelo con 1.

## Lo que este plan NO hace

- No rehace el Dashboard 360°.
- No crea `contrato_meta`.
- No toca la cadena Proyecto → Meta → KPI.
- No resuelve los ambientes — eso es la spec 002.
- **No hace DDL**, salvo la tabla de auditoría de la etapa 1.

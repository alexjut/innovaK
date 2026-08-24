# Clarify · Spec 001

Cinco preguntas quedaron abiertas en la spec. **Tres se resolvieron mirando la
base de datos** — no había que preguntarlas. Dos siguen abiertas porque son
decisión de negocio, no de código.

---

## ✅ C-2 · Forma de pago — RESUELTA, y al revés de lo que decía la spec

**La spec decía:** «no existe en ninguna tabla ni en SECOP; es lo único que
falta persistir».

**Es falso.** Barrido de las 268 tablas por nombre de columna:

| Tabla.columna | |
|---|---|
| **`crp.forma_pago_codigo`** | ← **es exactamente esto** |
| `crp.modalidad_seleccion_codigo` | modalidad de contratación |
| `secop_contrato.modalidad` | modalidad de contratación |
| `inscripcion_banco_iniciativa.modalidad_*` | otro dominio |
| `horario_clase.frecuencia` | otro dominio |

Y `crp` trae **todo el resto de la ficha financiera** que se iba a inventar:

```
contrato_id · forma_pago_codigo · plazo_dias · periodo_codigo
fecha_inicial · fecha_final · valor_crp · valor_neto · autorizacion_giro
numero_de_cdp · numero_de_crp · rubro_codigo · concepto_gasto_codigo
```

**Pero hay tres problemas, y ninguno es «falta el campo»:**

1. **La tabla tiene 0 filas.** No hay ingesta: `management/commands/` tiene
   `ingest_secop_contratos`, `ingest_secop_plan_pagos` e
   `ingest_sdp_datos_abiertos` — **ninguna de CRP**.
2. **El modelo Django mapea 4 de ~42 columnas.** `Crp` en
   `apps/presupuesto/models/sql.py` sólo declara `proyecto`, `valor_crp`,
   `fecha_inicial`, `fecha_final`. **No mapea `contrato_id` ni
   `forma_pago_codigo`** — por eso «no aparecían».
3. **`metrics.py` ya lee esa tabla vacía** para calcular «comprometido». O sea
   que hoy ese indicador se computa sobre cero filas.

**Qué cambia en la spec:** §5.4 estaba mal. No se crea un campo nuevo —
`crp.forma_pago_codigo` es el sitio correcto y ya existe. Lo que falta es
**ampliar el modelo** (aditivo, sin DDL) y **conseguir la fuente** que llena CRP.

> **Pregunta para Alex, distinta a la original:** ¿de dónde salen los CRP?
> ¿BOGDATA / PREDIS, un archivo que entrega Hacienda, u otra vía? Sin eso, la
> forma de pago sigue siendo captura manual — pero en `crp`, no en un campo nuevo.

---

## ✅ C-1 · Ejecución técnica — RESUELTA: hoy NO se puede derivar

`Contrato.ejecucion` tiene 4 de 25, y los cuatro son **de infraestructura**:

| Contrato | Ejecución | Categoría |
|---|---|---|
| 101 | 75 % | INTERVENTORIA |
| 102 | 80 % | VIAS |
| 103 | 75 % | PARQUES |
| 104 | 0 % | PARQUES |

**El 0 % del contrato 104 es un `$0` real, no un «sin dato».** *Constitución I.*

¿Se puede derivar de los KPIs? **No, porque no hay de qué derivarlo:**

| Contrato | KPIs | Avances registrados |
|---|---|---|
| 97 | 3 | **0** |
| 98 | 7 | **0** |
| 99 | 2 | **0** |
| 100 | 2 | **0** |
| 105 | 2 | 2 |

`AvanceIndicador` tiene **9 filas en todo el sistema**. Derivar un porcentaje de
ahí produciría **0 %** para casi todos — y eso sería *inventar un dato*, porque
0 % significa «no ha avanzado», no «no sabemos». *Constitución I.*

**Decisión propuesta:** se mantiene como captura del subgrupo, con
`avance_% · fecha_de_corte · observación` y auditoría, como pide el plan §20.
Se revisa cuando `AvanceIndicador` tenga masa crítica.

---

## ✅ C-5 · El contrato sin proyecto — RESUELTA: no es dato malo

Es **`id=1, CPS 1113/2024`**. Localmente está vacío: sin objeto, sin valor, sin
fechas, sin CDP.

Pero **sí tiene espejo en SECOP**: *«PRESTACIÓN DE SERVICIOS ADMINISTRATIVOS Y
LOGÍSTICOS PARA LA…»*.

O sea: **es un registro sin enriquecer, no un registro malo.** La precarga (RF-1)
le llena objeto, valor y fechas. Lo único que un humano tiene que decidir es a
qué proyecto pertenece — y eso es exactamente lo que hace el enganche desde Mi
Área que ya existe.

**No hay que borrarlo ni tratarlo aparte.**

---

## ⏳ C-3 · ¿Quién captura dentro del subgrupo? — ABIERTA

Hoy el gate de escritura es `subgrupos_visibles(user)`: **cualquiera con acceso
al área** puede escribir.

Sobre información contractual eso puede ser demasiado amplio. Las opciones:

| | Quién | Implicación |
|---|---|---|
| **A** | cualquiera del subgrupo | lo que ya hay; cero trabajo |
| **B** | sólo roles `Coordinador*` | el prefijo **ya** da poder de creación (`es_coordinador`), así que es coherente con lo existente |
| **C** | módulo nuevo `expediente_completar` | granularidad fina; hay que asignarlo a los 8 subgrupos con plan |

**Recomendación: B.** Reutiliza el mecanismo que ya existe y no inventa un
catálogo. *Constitución VIII.*

**Decide Alex.**

---

## ⏳ C-4 · ¿La completitud pondera igual? — ABIERTA

Si los 9 campos pesan lo mismo, un contrato sin etapa y sin forma de pago marca
78 % y **parece casi listo**.

| | Criterio | Ejemplo |
|---|---|---|
| **A** | todos igual | simple, honesto, no jerarquiza |
| **B** | por bloques (identidad / dinero / seguimiento) | refleja que falta el bloque completo |
| **C** | los que bloquean el 360° pesan más | dirige el esfuerzo a lo que se ve |

**Recomendación: A para la cifra, B para la presentación.** El porcentaje se
calcula plano —cualquier ponderación es una opinión disfrazada de número— y la
pantalla agrupa por bloques para que se vea *qué* falta, no sólo *cuánto*.

**Decide Alex.**

---

## Resumen

| # | Estado | Efecto |
|---|---|---|
| C-1 ejecución técnica | ✅ resuelta | captura manual; no hay de qué derivar (9 avances en todo el sistema) |
| C-2 forma de pago | ✅ resuelta | **existe en `crp.forma_pago_codigo`**; no se crea campo. Pregunta nueva: fuente de los CRP |
| C-5 contrato huérfano | ✅ resuelta | registro sin enriquecer; lo arregla la precarga + enganche |
| C-3 quién captura | ⏳ Alex | recomendación: roles `Coordinador*` |
| C-4 ponderación | ⏳ Alex | recomendación: cifra plana, presentación por bloques |

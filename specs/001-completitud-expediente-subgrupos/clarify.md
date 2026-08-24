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

> ### Respondida (Alex, 2026-08-24)
>
> **Fuente de verdad: BogData / Secretaría Distrital de Hacienda.**
> PREDIS **no** es fuente primaria nueva; sólo se conserva como histórica si
> aparecen datos cuya procedencia haya que preservar.
>
> Y una distinción que hay que mantener separada:
>
> | | |
> |---|---|
> | **Fuente de verdad** | BogData |
> | **Mecanismo de ingesta** | API / extractor / archivo controlado — *por determinar* |
>
> Prioridad del mecanismo: integración existente → extractor oficial →
> exportación oficial → carga controlada a staging.
> **Sin scraping. Sin inventar CRP. Sin pedirle a un Coordinador que escriba a
> mano un dato que existe oficialmente en BogData.**

### Qué se encontró sobre el acceso (2026-08-24)

**No hay integración con BogData en el repositorio.** Cero referencias en
código. Y hay investigación previa del 2026-07-29 que apunta en la misma
dirección:

> *«Bogotá usa PREDIS/BogData, no SIIF»* — el dataset **SECOP II Rubros
> Presupuestales** (`cwhv-7fnp`) tiene 5.891.594 filas y **cero** para los
> contratos de Kennedy (probados 5 `id_contrato` distintos).

Las 11 fuentes que hoy ingiere `sync_fuentes_oficiales` son **todas** de datos
abiertos (`datos.gov.co`, IDECA, SED, SCJ). Ninguna es de Hacienda.

**Conclusión:** hoy **no tenemos acceso técnico a BogData**. Aplica entonces la
instrucción de Alex: **ingesta desacoplada por adapter**, para que el día que
haya API, extractor o archivo oficial se cambie el adapter sin tocar el dominio.

**Lo que hay que averiguar (no es trabajo de código):** si la Alcaldía tiene
convenio de interoperabilidad con Hacienda, o si el área de presupuesto recibe
periódicamente un archivo de CRP. Es la misma vía por la que hay que conseguir
el anexo del Decreto Local para los rubros.

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

## ✅ C-3 · ¿Quién captura dentro del subgrupo? — DECIDIDA (Alex, 2026-08-24)

> **Roles `Coordinador*`.** El Coordinador del subgrupo completa lo que falta de
> **sus** proyectos y contratos. No puede tocar otro subgrupo salvo que un
> permiso explícito se lo permita. Admin y supervisión conservan lo que ya
> tienen. **La autorización se valida en backend** — ocultar el botón no basta.

El razonamiento que llevó ahí:

Hoy el gate de escritura es `subgrupos_visibles(user)`: **cualquiera con acceso
al área** puede escribir.

Sobre información contractual eso puede ser demasiado amplio. Las opciones:

| | Quién | Implicación |
|---|---|---|
| **A** | cualquiera del subgrupo | lo que ya hay; cero trabajo |
| **B** | sólo roles `Coordinador*` | el prefijo **ya** da poder de creación (`es_coordinador`), así que es coherente con lo existente |
| **C** | módulo nuevo `expediente_completar` | granularidad fina; hay que asignarlo a los 8 subgrupos con plan |

**Elegida: B.** Reutiliza el mecanismo que ya existe y no inventa un catálogo.
*Constitución VIII.*

---

## ✅ C-4 · ¿La completitud pondera igual? — DECIDIDA (Alex, 2026-08-24)

> **Cifra plana, sin ponderaciones arbitrarias:**
> `completitud = campos aplicables completos / campos aplicables totales`
>
> - Un campo marcado **`No aplica`** queda **fuera del denominador**.
> - Precargado oficial válido → completo. Manual validado → completo.
> - `Sin dato` / `Pendiente` → incompleto. **`$0` no es `Sin dato`.**
> - **Presentación por bloques**: RELACIONES · CONTRATACIÓN · FINANCIERO ·
>   SEGUIMIENTO, más la lista de faltantes con nombre.

El razonamiento:

Si los 9 campos pesan lo mismo, un contrato sin etapa y sin forma de pago marca
78 % y **parece casi listo**.

| | Criterio | Ejemplo |
|---|---|---|
| **A** | todos igual | simple, honesto, no jerarquiza |
| **B** | por bloques (identidad / dinero / seguimiento) | refleja que falta el bloque completo |
| **C** | los que bloquean el 360° pesan más | dirige el esfuerzo a lo que se ve |

**Elegida: A para la cifra, B para la presentación.** El porcentaje se calcula
plano —cualquier ponderación es una opinión disfrazada de número— y la pantalla
agrupa por bloques para que se vea *qué* falta, no sólo *cuánto*.

> **Consecuencia nueva:** aparece el estado **`No aplica`**, que la spec no
> tenía. No es lo mismo que `Sin dato`: un contrato de prestación de servicios
> sin obra no tiene «ejecución técnica de obra», y contarlo como faltante
> castigaría al área por algo que no le corresponde. Hay que definir por campo
> **cuándo** aplica — y eso es regla de negocio, no de código.

---

## Resumen

| # | Estado | Efecto |
|---|---|---|
| C-1 ejecución técnica | ✅ evidencia | captura manual; no hay de qué derivar (9 avances en todo el sistema) |
| C-2 forma de pago | ✅ evidencia + decisión | existe en `crp.forma_pago_codigo`. **Fuente: BogData**, vía adapter porque hoy no hay acceso |
| C-5 contrato huérfano | ✅ evidencia | registro sin enriquecer; lo arregla la precarga + enganche |
| C-3 quién captura | ✅ **Alex** | roles `Coordinador*`, validado en backend |
| C-4 ponderación | ✅ **Alex** | cifra plana + `No aplica` fuera del denominador; presentación por bloques |

**Las cinco cerradas.** No se reabren salvo evidencia nueva de la BD o una
contradicción institucional real.

---

## ⚠️ Conflicto detectado al ir a ejecutar T1.1

La aprobación del DDL de auditoría trae una condición que **la infraestructura
actual no permite cumplir**:

> *«pruebas primero en Desarrollo; después Pruebas; Producción únicamente
> mediante el flujo de promoción»*

**No hay una base de datos por ambiente.** Verificado hoy: un solo
`core/settings.py`, un solo host (`10.100.102.12`), cero referencias a ambiente
en el código. Las tres ramas comparten el mismo árbol y hay un solo contenedor.

**Un DDL toca los tres ambientes en el mismo instante.** No existe un
«Desarrollo» donde probarlo antes.

### Lo que sí se puede hacer, y honra la condición

Levantar un **PostgreSQL desechable** (la imagen `postgres:16-alpine` ya está en
la máquina), aplicar ahí el DDL contra un esquema equivalente, **probar el
rollback**, y sólo entonces aplicarlo a la base real con backup <24 h.

No es «Desarrollo → Pruebas → Producción», pero es lo único que separa de verdad
el ensayo del acto — y prueba lo que la condición quiere proteger: que el script
corre, que es aditivo y que el rollback funciona.

**Esto no reabre la decisión**, que sigue aprobada. Documenta que la condición
se cumple de la única forma que la infraestructura permite hoy, y que cerrarla
de verdad depende de la spec 002.

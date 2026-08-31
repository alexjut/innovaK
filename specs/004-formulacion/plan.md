# Spec 004 · Formulación como dominio propio — análisis y plan

**Creada:** 2026-08-26 · **Estado:** plan, no implementación
**Constitución:** `.specify/memory/constitution.md`
**Diagnóstico base:** [`docs/arquitectura/diagnostico_ciclo_planeacion.md`](../../docs/arquitectura/diagnostico_ciclo_planeacion.md)

> **Nada de esto está implementado.** Este documento responde la inspección A–G
> que pidió Alex antes de tocar código, y propone el plan por fases y por PR.
> Todo lo que afirma está medido contra la base real el 2026-08-26.

---

## 0 · La decisión, y lo que arrastra

**«En elaboración» y «Formulación» dejan de ser etapas del contrato.** Pasan a
un dominio propio —**FORMULACIÓN**— que vive entre META y CONTRATACIÓN.

Esto revierte una decisión de hace dos días y conviene decirlo de frente:
`specs/003-contratos-en-elaboracion/spec.md` §4.2 evaluó tres caminos y
**descartó explícitamente la opción C, «tabla aparte»**, con el argumento
«duplica estructura; al firmar hay que migrar la fila». Se eligió la B
(`contrato_numero` nullable) y se aplicó el DDL 016.

Hoy se vuelve a la opción C. Es legítimo —el argumento de entonces era de
implementación y el de ahora es de dominio— pero hay que registrarlo como
cambio de decisión, no dejar dos specs diciendo cosas contrarias.

**Y lo que arrastra es bueno:** la mitad del trabajo del spec 003 desaparece.

| Trabajo del spec 003 | Qué le pasa |
|---|---|
| Regla de conciliación (CLARIFY-3) | **Sobrevive**, cambia de sujeto |
| Crear contrato «en elaboración» | **Se reemplaza** por crear Formulación |
| Filtro `contrato_numero IS NOT NULL` en 17 sitios de plata | **Desaparece.** Lo formulado ya no es una fila de `contrato` |
| Los CHECK de equivalencia y el DDL 018 propuesto | **Se caen enteros** |
| Emparejamiento con SECOP | **Sobrevive y crece**: cierra Formulación → Proceso → Contrato |
| Pantalla de crear/emparejar | **Se reemplaza** por la sección Formulación en Meta |

---

## A · Estado contractual actual

### A.1 El catálogo, exacto

| código | nombre | orden | descripción |
|---|---|---|---|
| **5** | **En elaboración** | 0 | El área está estructurando el contrato. Todavía no se ha publicado en SECOP ni tiene número asignado |
| **1** | **Formulación** | 1 | Estructuración y trámite previo a la firma |
| 2 | Ejecución | 2 | El contrato está en curso |
| 3 | Liquidación | 3 | Cerrado el objeto, en trámite de liquidación |
| 4 | Sancionatorio | 4 | Con proceso de incumplimiento, multa o caducidad |

Constraints: `PRIMARY KEY (codigo)` · `UNIQUE (nombre)` · `UNIQUE (orden)
DEFERRABLE INITIALLY DEFERRED`.

### A.2 El rastro completo

**Una sola FK entrante en todo el esquema:** `contrato.etapa_codigo` con
`ON DELETE SET NULL`. Ninguna otra tabla lo referencia — verificado contra
`pg_constraint`: las únicas columnas `etapa%` del esquema son las tres de
`contrato`.

| Capa | Dónde |
|---|---|
| Modelo | `models/core.py:101` (`EtapaContrato`), `:170-183` (las tres columnas del contrato) |
| Servicio | `services/expediente_proyecto.py` — `MOTIVO_ETAPA:99`, `_etapas():166`, `_catalogo_etapas():322`, `catalogo_etapas():754`, `registrar_etapa():761`, `estado_etapa():843` |
| Endpoint 1 | `api/views.py:1532` `ContratoEtapaView` (GET/PATCH), ruta en `urls.py:196` |
| Endpoint 2 | `api/views.py:2019` `CapturarDatoContratoView`, rama `campo=="etapa"` en `:2119-2147` |
| Frontend | `expediente/expediente-proyecto.component.ts:142,238,455-479,528` (el stepper) |
| DDL | `010` crea y siembra 1-4 · `015` inserta la 5 · `017` el UNIQUE de orden · con sus tres rollbacks |
| Tests | 22 tests la tocan |

**La validación es 100 % data-driven.** Los dos endpoints validan contra
`EtapaContrato.objects`, y el stepper del expediente lee `etapas_catalogo` del
servidor y compara `orden` de forma **relativa**. Retirar filas no exige tocar
ni el modelo ni los endpoints.

---

## B · Impacto exacto de retirar los códigos 5 y 1

### B.1 En los datos: cero

```
contrato                        25 filas
  etapa_codigo IS NOT NULL       0
  etapa_codigo IN (5,1)          0
  etapa_fecha  IS NOT NULL       0
  etapa_usuario_id IS NOT NULL   0
auditoria_dato                   0 filas
```

**Nadie usó nunca el catálogo.** No hay un dato que migrar, ni una fila de
auditoría con `campo='etapa'`.

### B.2 En el código: un solo punto de rotura, y está bloqueado

**No hay ni un literal 5 o 1 cableado como código de etapa en el backend de
producción.** El barrido completo devuelve solo tests.

Pero hay una bomba en el frontend:

```ts
// frontend/src/app/features/area/completitud-expediente.component.ts:781-786
readonly ETAPAS = [
  {codigo: 1, nombre: 'Formulación'}, {codigo: 2, nombre: 'Ejecución'},
  {codigo: 3, nombre: 'Liquidación'}, {codigo: 4, nombre: 'Sancionatorio'},
];
```

Es el **único literal `1` cableado como etapa en todo el repo**. Alimenta un
`<select>` (`:190`) e **ignora el catálogo que el servidor sí le manda** — por
eso hoy ya miente por omisión: no ofrece «En elaboración» aunque existe desde
el 2026-08-26. Al retirar el código 1, la pantalla seguiría ofreciendo
«Formulación» y el backend respondería **400**.

> ⚠️ **Ese archivo lo tiene Anderson sin commitear.** Es uno de los 27 del árbol
> compartido. El arreglo es de una línea —leer el catálogo del servidor, que ya
> llega— pero **no se puede tocar sin coordinarlo con él**. Es una dependencia
> de personas, no de código.

### B.3 El UNIQUE de orden: no hay que reordenar

Con 5 y 1 fuera quedan los órdenes 2, 3, 4. No hay duplicados, el UNIQUE se
satisface, y el stepper compara relativamente: los huecos son inocuos.
Renumerar a 1, 2, 3 sería cosmético — y si se decide, el `DEFERRABLE` es
exactamente lo que permite hacerlo en un solo `UPDATE`.

### B.4 Los tests: 4 de 22 mueren, y tres son de una línea

`test_expediente_contrato.py:53-55` congela `ETAPAS_ESPERADAS` con las cinco
filas. Tres tests se arreglan cambiando esa constante. Los otros 18 sobreviven
intactos: usan el código 2 o afirman reglas de fondo (no inventar etapa, no
dejar rastro sin fecha ni autor, scope por área).

### B.5 El riesgo real del retiro

`ON DELETE SET NULL` significa que un `DELETE FROM etapa_contrato WHERE codigo
IN (5,1)` **pelado no falla**: pasa limpio y deja con etapa NULL a los
contratos que la tuvieran, indistinguibles de los nunca registrados. Hoy son
cero y es seguro, pero el retiro debe llevar la guarda que ya tiene
`rollback_015_etapa_en_elaboracion.sql:15-23`. **Para el código 1 no existe
rollback granular** — el `rollback_010` hace `DROP TABLE` completo. Hay que
escribirlo.

### B.6 El DDL 016: recomendación de revertirlo, y no como paso suelto

Cuatro hechos medidos:

1. **Su justificación desaparece.** El 016 dice literalmente «un contrato en
   elaboración todavía no tiene número», y esa etapa sale del dominio.
2. **La relajación nunca se completó.** `models/core.py:132` sigue siendo
   `contrato_numero = models.IntegerField()` — `null=False`, verificado por
   introspección. Ningún endpoint crea sin número. La capa ORM se comporta
   exactamente como si la columna siguiera siendo obligatoria.
3. **El 016 midió mal, y en la dirección peligrosa.** Afirmó que no había
   UNIQUE; hay dos (`uq_contrato_tripleta` y su gemelo) sobre la tripleta, con
   `indnullsnotdistinct = false`. Con número NULL, **la unicidad se evapora
   justo en las filas para las que se hizo el 016**.
4. **Tres pantallas imprimirían «None»** si el número fuera NULL de verdad
   (`core.py:213`, `panel_area.py:223`, `panel_subgrupo.py:143`,
   `completitud_expediente.py:159` interpolan sin guarda).

`rollback_016_contrato_numero_opcional.sql` **correría con éxito hoy mismo**:
su guarda solo aborta si hay NULLs, y hay cero.

**Recomendación:** sí volver a `NOT NULL`, pero **en el mismo cambio que retira
la etapa 5 y después de que exista el dominio FORMULACIÓN** — nunca antes, o se
queda sin dónde vivir el contrato que aún no tiene número.

**La conciliación con SECOP no depende de esto.** `_EN_INNOVAK_SQL` ya trae
`ci.contrato_numero IS NOT NULL`; bajo `NOT NULL` pasa a ser un no-op.

### B.7 Lo que se queda

Las tres columnas `etapa_codigo` / `etapa_fecha` / `etapa_usuario_id` **se
quedan**: sirven a los códigos 2, 3 y 4, que sí son ciclo de vida del contrato.
Ni se borran ni se migran.

### B.8 Dos defectos preexistentes que salieron de paso

- **`muro_subgrupos.py:413-418`** emite, para toda tarjeta con contratos, el
  pendiente «Etapa del contrato: no hay dónde registrarla · Falta el DDL». Es
  **incondicional** y falso desde que el DDL 010 se aplicó el 2026-08-23. El
  chip de la cabecera del mismo servicio sí consulta el catálogo: dos partes del
  mismo archivo se contradicen.
- **`muro_subgrupos.py:666-667`** emite un vocabulario congelado
  `{planeacion, contratacion, ejecucion, liquidacion, sin_dato}` y el frontend
  etiqueta `planeacion` como **«Formulación»**, sin ninguna relación con
  `etapa_contrato`. Cuando Formulación sea un dominio, esa etiqueta pasará a
  significar activamente otra cosa.

---

## C · Qué se reutiliza

### C.1 Reutilizable tal cual

| Pieza | Por qué sirve |
|---|---|
| **`auditoria_dato` + `registrar_cambio`** | `entidad` es `varchar(60)` **libre, sin CHECK ni FK**, y ya existe el índice `(entidad, entidad_id, fecha DESC)`. `entidad="formulacion"` entra hoy **sin una línea de DDL** |
| **`apps/documentos/`** | Librería de 4 servicios sin `urls.py` ni `models.py`. **Mongo cifrado está ACTIVO** (`ping()` → True). `guardar(bytes, mime, {"tipo":"formulacion","id":X,"campo":"estudio_previo"})` funciona hoy |
| **`pdf_consolidado.consolidar()`** | El expediente de formulación en un PDF ya está hecho, y tolera anexos rotos insertando una página de aviso |
| **El patrón de tres gates** | `CapturarDatoContratoView:2073-2110`: scope → rol → pertenencia. Se copia literal cambiando el tercer gate |
| **`aplicar_subgrupo(qs, user, campo)`** | `scope.py:130-140`. El scope llega a Formulación sin motor nuevo, si el queryset expone `subgrupo_id` |
| **El catálogo `modulo`** | Declarar el módulo `formulacion` es **una tupla en `seed_modulos.py` y correr el comando**. Sin DDL. El frontend lo recoge solo |
| **`rol_modulo` y su pantalla** | 112 filas, 13 roles, UI de asignación funcionando. Asignar el módulo es marcar casillas |
| **La regla del semáforo** | `muro_subgrupos.py:299-336` `_semaforo()`: tres guardas devuelven INCOMPLETO **antes** de calcular. Se copia la regla —no acusar sin fuente—, no la fórmula, que es financiera |
| **El contrato de datos de los pendientes** | `_chip(con, de, causa, detalle, accion)` ya trae origen y acción, y nunca devuelve un cero anónimo |
| **El stepper del expediente** | Data-driven de punta a punta. El de Formulación se calca, no se inventa |

### C.2 Adaptable

| Pieza | Qué le falta |
|---|---|
| **`completitud_expediente.py`** | Tiene la forma correcta (estado por campo, fuente, editable, bloques, pct) y los cuatro estados. Pero **`no_aplica` está muerto**: el único call site (`:134`) nunca pasa `aplica`. Y es **plano por decisión escrita** (ver §I.1) |
| **`contrato_actividad_plan`** | **Ya es la N:M entre lo formulado y lo contratado**, con `monto`, fechas, `meta_proyecto_id` y `concepto_gasto_id`. Cobertura: 0/15 con meta, 0/15 con concepto, 14/15 con monto en $0. El esqueleto está; el dato no |
| **`presupuesto_tiempo`** | 0 filas. Cuelga de `actividad_plan` con planeado-vs-real y `avance_pct`. «Cuándo se planeó formular vs cuándo se formuló» ya tiene dónde vivir |
| **`modalidad_seleccion`** | 0 filas, y **es el catálogo correcto**: su única FK viene de `crp`. Se siembra desde el espejo (§D.2) |
| **`EntregaEstadoView` de Jóvenes** | `jovenes_a_la_e/api/views.py:132-179`. El mejor patrón de cambio de estado del repo: `estado_anterior` + transacción + **efectos compensables**. Pero no valida el estado de origen |
| **`banco_rubrica`** | La TABLA tiene la forma exacta que pide el checklist: `(version PK, nombre, config jsonb, activa, created_at)` con peso y bloque por criterio. Pero **la fuente de verdad sigue siendo Python**: la config se genera en `puntaje.py` y la fila es una foto |

### C.3 No sirve — y por qué importa decirlo

| Pieza | Por qué no |
|---|---|
| **`documento_requisito`** (3 filas) | La idea es buena (catálogo + discriminador `requerido_para`) pero tiene 4 columnas: sin tipo, sin obligatorio/opcional, sin peso, sin evidencia. Y sus 3 filas son de *participante* y *evento*. **Cero código la lee** |
| **`validacion_documental`** (0 filas) | Es **el antipatrón escrito en DDL**: tiene a la vez el checklist normalizado (`documento_requisito_id` + `cumplido`) **y cinco requisitos cableados como columnas booleanas**. Es exactamente lo que este plan quiere evitar |
| **`tipo_proceso`** (0 filas) | **Falso amigo.** Su única FK entrante viene de `buen_trato` — no es de contratación |
| **`fase_proyecto`** (3 filas) | Ya se descartó por escrito en `010_etapa_contrato.sql:9`: es de proyecto, no de contrato. Su única FK viene de `presupuesto_tiempo`, que está vacía |
| **Cualquier máquina de estados existente** | **No hay ninguna.** Cinco `CharField` con `choices` y guardas ad-hoc. `choices` **no valida en `save()`** y las columnas son texto sin CHECK. El Banco permite saltar de «borrador» a «validada» sin pasar por «enviada» |
| **Cualquier motor de alertas** | **Cero absoluto**: cero tablas, cero modelos, cero endpoints |

### C.4 La prueba de por qué el checklist va en tabla

No es una opinión: está medida dentro de este repo. El catálogo de anexos del
Banco vive en **tres sitios que ya divergieron**:

```
CHECK ck_insc_banco_anexo_tipo (en la base) ....... 17 valores
forms/inscripcion.py:222 ANEXOS ................... 14 claves
models/documento_maestro.py:521 TIPO_CHOICES ...... 8 claves
```

Tres fuentes de verdad para la misma lista, y ya no coinciden. **El checklist
de Formulación tiene que ser una tabla**, no columnas ni listas en código.

---

## D · La formulación que ya existe, escondida

### D.1 El área ya está formulando — y lo escribe donde puede

`actividad_plan` tiene 54 filas. **41 tienen `actividad_id` y son etiquetas del
catálogo**, con erratas que delatan su origen: `Polimltor`, `AVTIVIDAD FISICA`,
`Futbol de alon`, `Parinaje`.

**Las 13 con `actividad_id` NULL son otra cosa.** Son enunciados de formulación:

- «Fortalecer 100 organizaciones comunitarias»
- «Implementar 4 acciones formativas diferenciales»

Una de ellas incluso nombra el convenio. **El área ya formula; lo está
escribiendo en el único campo de texto que tenía a mano.** No hay que
convencerla de empezar: hay que darle dónde.

### D.2 El proceso contractual ya está en casa, completo

`secop_contrato` lo trae desde el DDL 008 y **nadie lo ha mirado nunca**
(`proceso_de_compra` solo aparece en la ingesta y en el modelo):

```
proceso_de_compra .... 3.074/3.074 filas · 2.363 procesos distintos
url_proceso .......... 3.074/3.074 · modalidad: 10 valores · estado: 7 valores
procesos con >1 contrato ... 313 (el mayor, 34 contratos)
0 procesos con más de una modalidad · 0 con más de una URL
```

**La cardinalidad «una formulación → varios contratos» no es una hipótesis del
modelo: es lo que publica SECOP para Kennedy.** Y toca nuestros datos: los 24
contratos internos que empatan con el espejo salen de **solo 17 procesos** —
`CO1.BDOS.7776994` produjo 4 contratos, `CO1.BDOS.7759492` produjo 3.

> Si mañana se colgara el proceso del contrato en 1:1, esos 11 contratos
> obligarían a duplicar 4 procesos.

Las 10 modalidades ya están en casa y sirven para sembrar `modalidad_seleccion`
— con la advertencia de que vienen con la ortografía de la fuente
(«Contratación directa» 2.984 · «Licitación pública» 26 · «Mínima cuantía» 16 ·
«Concurso de méritos abierto» 15 …), no como catálogo limpio.

### D.3 El techo de SECOP para lo pre-contractual

`ingest_secop_contratos.py:65` filtra en la fuente:

```
estado_contrato NOT IN ('Borrador','Cancelado')
```

**El espejo solo ve procesos que ya parieron contrato.** Un proceso publicado y
todavía sin adjudicar —o uno que se cayó— nunca ha entrado. Construir el
seguimiento pre-contractual esperando que SECOP lo alimente **no va a funcionar
con la ingesta de hoy**.

### D.4 Dónde NO está

| Dónde se buscó | Qué hay |
|---|---|
| `contrato` | **Nada precontractual.** 25/25 con número: ningún contrato «en elaboración» pese al DDL 016. El único texto sobreviviente es `objeto` |
| `stg_beneficiarios` | **Las columnas que prometían proceso están vacías.** «TIPO DE PROCESO», «ESPACIO», «meta», «Proceso Contractual»: NULL en las 5.985 filas. El cargue trajo el encabezado, no el contenido |
| `cdp` | Los 4 marcadores no llevan información precontractual: su texto codifica el par proyecto↔contrato, que ya vive en `contrato_proyecto` |
| Documentos | **Cero absoluto.** `documento_evento` 0, `documento_participante` 0, `inscripcion_banco_anexo` 0, `festival_archivo` 0. No hay ni un soporte cargado en todo el sistema |
| `docs/`, `brain/`, `specs/` | Ningún diseño previo del dominio. Se diseña desde cero |

### D.5 Y el CRP guarda datos que son de la formulación

`crp` (0 filas, 48 columnas) modela `modalidad_seleccion_codigo`,
`descripcion_mod_selec`, `id_solicitante`, `nombre_solicitante`,
`id_responsable`, `responsable`. **Modalidad, solicitante y responsable son
datos de la FORMULACIÓN**, y están colgados del CRP, que ocurre mucho después.
El vocabulario existe; está en la tabla equivocada.

---

## E-0 · Decisiones de Alex del 2026-08-27 (mandan sobre lo de abajo)

**1 · Lo que se formula es la ACTIVIDAD.** Palabras de Alex: *«la formulación
es de contrato, o como lo llamamos acá, actividades»*. La formulación cuelga de
`actividad_plan`, no de la meta.

**2 · Una formulación POR VIGENCIA.** `actividad_plan` se queda como el
enunciado estable del plan —se escribe una vez— y cada año cuelga de ella una
formulación con su valor estimado, sus requisitos y su estado. No se toca el
`uq_actividad_plan` ni se duplica el enunciado.

**3 · Completitud con bloqueo, sin peso.** Cada requisito es obligatorio /
opcional / no aplica, y algunos BLOQUEAN el paso a contratación. Así se cumple
el §12 —«al 90 % y seguir bloqueada»— **sin** contradecir la decisión escrita
del 2026-08-24 sobre el motor del expediente.

**4 · Las disciplinas salen de `actividad_plan`.** Decisión de separarlas ya.

### E-0.1 · El caso que fija el modelo: el Banco de Deporte

Alex lo nombró como el mayor ejemplo vivo, y es el que corrige el diseño:

```
actividad_plan #108 · «Convocatoria de colectivos recreodeportivos al Banco»
   proyecto 2784 · Deporte · actividad_id 74 («Banco de Iniciativas Recreodeportivas»)
   indicador: «Colectivos recreodeportivos beneficiados» · meta 280 colectivos
   24 inscripciones enviadas · 24 evaluaciones calculadas
   CONTRATOS: 0        ← no está en SECOP; el contrato se está armando
```

Es una formulación en curso, con todo su expediente ya cargado y sin contrato.
**Y tiene `actividad_id`**, lo que tumba el discriminador que parecía obvio.

### E-0.2 · El discriminador real, medido

`actividad_id` NO separa nada. **Lo que separa es tener indicador:**

| en catálogo | con indicador | con contrato | n | Qué es |
|---|---|---|---|---|
| sí | no | no | **34** | Disciplinas: Boxeo, Polimotor, ARTES ESCÉNICAS, CLASES DE DANZA |
| no | sí | sí | **13** | Líneas del plan ya contratadas |
| no | sí | no | **5** | Formuladas y sin contrato todavía (Cultura) |
| **sí** | **sí** | **no** | **1** | **#108, el Banco de Deporte** |
| no | no | no | 1 | «mujeres caminando ver 1» — fila de prueba |

**19 formulables · 34 disciplinas · 1 prueba.**

Y las 34 disciplinas **no tienen nada colgando**: 0 eventos, 0 indicadores, 0
contratos, 0 filas en `presupuesto_tiempo`. Los tres «1» que aparecían al
medirlas por `actividad_id` eran el Banco. Separarlas no rompe nada.

> ⚠️ El discriminador es un **criterio de hoy**, no una columna. Una línea del
> plan recién creada no tiene indicador todavía y caería del lado equivocado.
> Por eso la separación se hace UNA vez, con DML revisado, y a partir de ahí
> manda dónde está la fila — no una heurística que se recalcula.

---

## E · Modelo mínimo propuesto

> **Conceptual. No implementado, no aprobado, sin DDL escrito.** Los nombres son
> de trabajo. Todo lo que sigue respeta la regla de la casa: aditivo, nullable
> por omisión, con rollback, y con aprobación explícita antes de tocar la base.

### E.1 Las siete piezas

```
actividad_plan (19 formulables, existe)   ← EL ANCLA (decisión E-0.1)
      │ 1:N — una formulación por vigencia
      ▼
┌─ formulacion ────────────────────────────────────────────────────────┐
│  id · codigo (F-001) · actividad_plan_id NOT NULL · vigencia NOT NULL │
│  meta_proyecto_id? (se deriva; se guarda si el área lo precisa)      │
│  objeto · descripcion · valor_estimado                               │
│  subgrupo_id (denormalizado, para que el scope funcione)             │
│  responsable_funcionario_id  ← «designamos responsable»              │
│  estado_codigo → formulacion_estado                                  │
│  creado_por · creado_en · actualizado_en                             │
│  cancelado_en · cancelado_por · cancelado_motivo (los tres o ninguno)│
└──────────────────────────────────────────────────────────────────────┘
      │                    │                        │
      │ N:1                │ 1:N                    │ 1:N
      ▼                    ▼                        ▼
formulacion_estado   formulacion_requisito_   formulacion_documento
  codigo · nombre      cumplido                  mongo_id · onedrive_item_id
  orden · es_final     requisito_codigo         nombre · mime · tamano
  es_bloqueante        estado · responsable     subido_por · created_at
      │                 evidencia_doc_id
      │ N:M              fecha · observacion
      ▼                        │ N:1
formulacion_transicion         ▼
  origen · destino      formulacion_requisito  (el catálogo CONFIGURABLE)
  rol_requerido           codigo · nombre · tipo · orden
  (tabla, no código)      obligatorio · peso · bloquea
                          aplica_a · activo · version
```

Y el puente al mundo contractual:

```
formulacion ──1:N──▶ contrato.formulacion_id   (FK nullable, aditiva)
```

### E.2 Por qué cada una, y qué se descartó

| Pieza | Justificación |
|---|---|
| `formulacion` | El sujeto del dominio. Cuelga de `actividad_plan` + `vigencia`, con UNIQUE sobre el par: una actividad se formula una vez por año. `subgrupo_id` va **denormalizado a propósito**: `aplicar_subgrupo(qs, user, "subgrupo_id")` ya existe y funciona sin motor nuevo |
| `formulacion_estado` | Catálogo, no `choices`. Medido: `choices` de Django **no valida en `save()`** y las columnas de estado del repo son texto sin CHECK — hoy se puede escribir cualquier cadena con un `.update()` |
| `formulacion_transicion` | **Tabla, no diccionario en Python.** El repo no tiene ninguna máquina de estados y sus cinco intentos validan la acción pero no el estado de origen. La guarda tiene que estar en el servicio **y** en el dato |
| `formulacion_requisito` | El checklist configurable. Va en tabla por la prueba de §C.4: el Banco escribió su catálogo en tres sitios y ya divergieron |
| `formulacion_requisito_cumplido` | Una fila por requisito cumplido, con evidencia y responsable. **Nunca una columna por requisito** — ese es el error de `validacion_documental` |
| `formulacion_documento` | No hay tabla genérica de documentos en el repo: cada dominio tiene la suya. Se calca el esqueleto de `festival_archivo`, que ya contempla Mongo **y** OneDrive |
| `contrato.formulacion_id` | Responde las dos preguntas del §15 con una columna aditiva y nullable |

**Descartado explícitamente:**

- **Tabla de historial propia.** `auditoria_dato` ya sirve: `entidad` es
  `varchar(60)` libre y el índice `(entidad, entidad_id, fecha DESC)` ya existe.
  `entidad="formulacion"` entra **sin DDL**. Solo hay que pasar `proyecto_id` y
  `subgrupo_id` explícitos, porque `_contexto_de_contrato()` solo sabe deducir
  desde un contrato.
- **Tabla de proceso contractual, por ahora.** La evidencia la pide (2.363
  procesos, 313 con más de un contrato) pero es una pieza aparte y con su propia
  fuente. Se difiere con su evidencia escrita, no se olvida.
- **Reutilizar `documento_requisito` o `validacion_documental`.** Ver §C.3.

### E.3 Lo que hay que resolver antes de escribir el DDL

1. ✅ **Resuelto (E-0):** cuelga de `actividad_plan`, una por vigencia.
2. ✅ **Resuelto (E-0):** completitud con bloqueo y sin peso.
3. **La vigencia del resto del ciclo sigue abierta.** La formulación la resuelve
   para sí misma, y es el primer sitio donde queda bien hecha — pero `proyecto`,
   `meta_proyecto` y `actividad_plan` siguen sin dimensión de año.
4. **Qué pasa con las 5 formulaciones que ya existen sin contrato** (las de
   Cultura) y con el Banco: nacen como filas de `formulacion` en la vigencia
   que les corresponda, o se dejan para que el área las cree. Es DML de
   arranque, no de estructura.

---

## F · El dashboard de Meta

Ruta: `/app/presupuesto/dashboard` → `Proyecto` → `Meta`.

```
╔══════════════════════════════════════════════════════════════════════════╗
║ PROYECTO 2377 · Kennedy Germinando Futuros              Vigencia 2026 ▾  ║
╠══════════════════════════════════════════════════════════════════════════╣
║ META 3 · Fortalecer 100 organizaciones comunitarias                      ║
║ Indicador: organizaciones fortalecidas · Meta 100 · Avance 35            ║
╚══════════════════════════════════════════════════════════════════════════╝

  ▸ PLANEACIÓN        ¿qué hay que lograr?          100 organizaciones
  ▸ PROGRAMACIÓN      ¿cuánto y cuándo?             Sin dato · no hay
                                                     programación anualizada

  ▼ FORMULACIÓN                                    8 · $2.400 M formulados
    ┌────────┬──────────────────────────┬───────────────────┬──────┬─────────┐
    │ Código │ Objeto                   │ Estado            │ Compl│ Estimado│
    ├────────┼──────────────────────────┼───────────────────┼──────┼─────────┤
    │ F-001  │ Actividades deportivas   │ 🟢 Lista          │ 100 %│  $500 M │
    │ F-002  │ Dotación                 │ 🟠 Con observac.  │  55 %│  $320 M │
    │ F-003  │ Jornadas comunitarias    │ 🔴 Bloqueada      │  90 %│  $180 M │
    │        │   └ falta: CDP (requisito crítico)                            │
    │ F-004  │ Formación de líderes     │ 🟡 En revisión    │  80 %│  $400 M │
    └────────┴──────────────────────────┴───────────────────┴──────┴─────────┘
      Listas 2 · En proceso 1 · Con observaciones 1 · Bloqueadas 1 · Contratadas 4
      Formulado $2.400 M  ·  Contratado $1.650 M  ·  Por convertir $750 M

  ▼ CONTRATOS                                      4 · $1.650 M
    ┌──────────────┬──────────────┬────────────┬───────────┬──────────────┐
    │ Contrato     │ Nace de      │ Etapa      │ Girado    │ Contratista  │
    ├──────────────┼──────────────┼────────────┼───────────┼──────────────┤
    │ CPS-267-2025 │ F-001        │ Ejecución  │  $180 M   │ …            │
    │ CPS-315-2025 │ F-001        │ Ejecución  │  $220 M   │ …            │
    └──────────────┴──────────────┴────────────┴───────────┴──────────────┘
      (F-001 produjo dos contratos: un proceso, varios contratos — §D.2)

  ▸ EJECUCIÓN         avance físico 35 · financiero $400 M de $1.650 M
  ▸ AVANCE ALCALDÍA   corte 2026-07 · 35 % · cargado por … · con evidencia
  ▸ SEGPLAN           corte 2026-06 · 32 %          ⚠️ corte más viejo
  ▸ CONCILIACIÓN      Diferencia menor · +3 pp · SEGPLAN pendiente de actualizar
  ▸ ALERTAS           2 · «F-003 bloqueada hace 41 días» · «sin corte de agosto»

  ── ¿POR QUÉ VA EN 35 % SI DEBERÍA IR EN 60 %? ────────────────────────────
     $750 M formulados que aún no se contratan · F-003 lleva 41 días
     bloqueada por el CDP · el corte de agosto de la Alcaldía no ha llegado
```

**Dos reglas de esa pantalla, heredadas de la casa:**

- Lo que no hay se publica vacío **con la causa al lado**. «Programación: Sin
  dato · no hay programación anualizada» — nunca un `0 %`.
- La diferencia con SEGPLAN **es información, no un error a esconder**. Se
  muestran los dos números y el motivo.

---

## G · Plan técnico, PR por PR

Cada PR: un objetivo, comprobable, con tests, reversible, sin mezclar dominios.

### Bloque 1 — Sin tocar la base (se puede empezar hoy)

| PR | Qué | Riesgo |
|---|---|---|
| **PR-1** | **Los dos defectos del muro.** Quitar el pendiente quemado de `muro_subgrupos.py:413-418` y renombrar la etiqueta «Formulación» del vocabulario congelado. Con test que falle antes | Bajo |
| **PR-2** | **`panel_area` a la unión de vías** (`panel_area.py:144`). Test: Seguridad pasa de 0 a 4 contratos, $6.944 M | Bajo |
| **PR-3** | **La discrepancia modelo↔base.** `contrato_numero` con `null=True` en el modelo, o revertir el 016. Decidir primero (§B.6) | Bajo |
| **PR-4** | **Spec, ADR y glosario.** Registrar «Formulación es un dominio previo a Contrato», el cambio de CLARIFY-2, y las dos decisiones abiertas de §I. En `brain/Decisiones/` y `docs/GLOSARIO.md` | Nulo |

### Bloque 2 — El catálogo de etapas (necesita coordinación, no DDL grande)

| PR | Qué | Riesgo |
|---|---|---|
| **PR-5** | **Arreglar el catálogo cableado del frontend** (`completitud-expediente.component.ts:781`): leer el que ya manda el servidor. **Bloqueado por Anderson** | Medio (personas) |
| **PR-6** | **Escribir el rollback granular del código 1** — hoy no existe. Con la guarda de `rollback_015` | Bajo |
| **PR-7** | **Retirar los códigos 5 y 1** + actualizar `ETAPAS_ESPERADAS` y los 3 tests + los docstrings que dicen «las 4 etapas». **Requiere aprobación de DDL/DML** | Medio |

### Bloque 3 — El dominio (cada uno con su DDL aditivo y su rollback)

| PR | Qué |
|---|---|
| **PR-8** | `formulacion_estado` + `formulacion_transicion`, sembradas. Sin UI: solo catálogo y test de que el grafo es coherente |
| **PR-9** | `formulacion` + el servicio de creación con los tres gates + auditoría con `entidad="formulacion"` |
| **PR-10** | El motor de transiciones: valida origen y destino contra la tabla, `estado_anterior`, transacción, auditoría. Test de que no se puede saltar un estado |
| **PR-11** | `formulacion_requisito` + `formulacion_requisito_cumplido` + la completitud. Sin peso mientras §I.1 no se decida |
| **PR-12** | `formulacion_documento` sobre `apps/documentos` (Mongo activo; OneDrive queda cableado y apagado) |
| **PR-13** | `contrato.formulacion_id` + el endpoint que liga una formulación a su contrato |
| **PR-14** | El módulo RBAC `formulacion` (una tupla en `seed_modulos.py`) + asignación a roles |

### Bloque 4 — La pantalla

| PR | Qué |
|---|---|
| **PR-15** | Sección Formulación de **solo lectura** en el detalle de Meta, antes de Contratos |
| **PR-16** | Alta y edición desde la pantalla |
| **PR-17** | El stepper de Formulación, calcado del de etapas (data-driven) |
| **PR-18** | El semáforo y los contadores formulado vs contratado |

### Estado al 2026-08-27

| Bloque | Estado |
|---|---|
| **1** — sin tocar la base | ✅ **cerrado** (PR-1 a PR-4) |
| **2** — catálogo de etapas | ⛔ **PR-5 y PR-7 bloqueados**: el `readonly ETAPAS` cableado en `completitud-expediente.component.ts:781` es de Anderson. El DDL 018 está escrito, ensayado en un Postgres desechable y **sin aplicar**. Handoff en `docs/operacion/TRABAJO_EN_PARALELO.md §6.2` |
| **3** — el dominio | ✅ **cerrado** (PR-8 a PR-14). DDL 019 aplicado: 7 tablas, 10 estados, 22 transiciones |
| **4** — la pantalla | ✅ **cerrado** (PR-15 a PR-18) |
| **5** — diferido | ⏸️ espera fuentes externas (SEGPLAN trimestral, POAI) |

Dos hallazgos que salieron **al escribir los tests**, no al mirar la pantalla:

- «Lista para contratación» era un **callejón sin salida** —no se podía cancelar
  ni devolver con observaciones—. Se añadieron las transiciones 9→6 y 9→10.
- El puente formulación↔contrato es N:N, así que sumar el valor recorriendo sus
  filas **contaría dos veces** un contrato que cubre dos formulaciones. Se suma
  sobre contratos distintos, y la comparación formulado/contratado se hace solo
  sobre las que tienen las dos cifras.

---

### Bloque 5 — Diferido, con su bloqueo declarado

| Qué | Bloqueado por |
|---|---|
| Proceso contractual como entidad | Decidir si SECOP alimenta lo pre-contractual (§D.3) |
| Programación anualizada | La decisión de vigencia del diagnóstico |
| Reporte mensual de la Alcaldía | La plantilla oficial no existe |
| Histórico de SEGPLAN por cortes | El formato trimestral no existe |
| Conciliación y alertas | Depende de los dos anteriores |
| PAA / apropiación | **Sin fuente definida** |
| BogData (CRP, compromiso, rubro) | Sin acceso técnico |

---

## H · Gobierno: Innovación manda, y se delega por dato

**Decisión de Alex (2026-08-26): Innovación es la dueña de la data; las áreas
reciben lo delegado, poco a poco, sin cambiar lo que hay.**

Lo bueno es que **el mecanismo ya existe y nunca se ha usado**:

```
usuario_pertenencia   usuario_id · group_id · objetivo_tipo · objetivo_id
                      activo · created_at · created_by_id
                      → 10 filas, TODAS 'global'. Cero de tipo 'subgrupo'
auditoria_pertenencia usuario_objetivo · actor · accion · objetivo_tipo
                      objetivo_id · detalle · ts        → 0 filas
```

Delegar un área a alguien es **una fila**: quién la creó, desde cuándo, y
revocable con `activo = false`. Y hay una bitácora dedicada solo a eso.

**Qué implica para el plan:**

1. **Innovación no necesita ningún cambio para empezar.** Como superusuario,
   `subgrupos_visibles` devuelve `None` y ve todo.
2. **Delegar es dato, no desarrollo.** Sin DDL, sin tocar `rol_modulo`.
3. **Dos cosas que suenan igual y no lo son:** *quién puede tocar* una
   formulación (permiso: pertenencia + rol, ya existe) y *quién responde* por
   ella (dato: `responsable_funcionario_id`, campo de la tabla nueva).
4. **Hay que distinguir en el rastro** «lo hizo el área» de «lo hizo Innovación
   por el área». `registrar_cambio` ya guarda el usuario; basta con que la
   pantalla lo muestre.

**Dos carencias, anotadas sin resolver:**

- `usuario_pertenencia` **no tiene fecha de fin**. Se revoca con `activo=false`,
  auditable, pero no hay delegación con vencimiento.
- El RBAC es **por módulo, booleano**. Los 13 permisos finos del §31 (ver,
  crear, revisar, observar, subsanar, aprobar…) **no son expresables hoy**: las
  únicas distinciones por acción están quemadas por nombre de rol en
  `permisos.py:135-139`. Con «sin cambiar lo que hay», la respuesta es **un
  módulo `formulacion` + las familias de rol que ya existen + el responsable
  como dato**. Los permisos finos se difieren.

---

## I · Decisiones que hay que tomar antes de escribir código

### I.1 🔴 La completitud ponderada contradice una decisión escrita hace dos días

El §12 del prompt maestro pide completitud con **peso por requisito**. Pero
`apps/presupuesto/services/completitud_expediente.py:11-14` registra la
decisión contraria, fechada el **2026-08-24** y firmada por Alex:

> «Plana, sin ponderaciones. Todos los campos aplicables pesan igual, **porque
> cualquier ponderación es una opinión disfrazada de número**.»

No es un obstáculo técnico: es que el sistema pasaría a decir dos cosas. **Hay
que reabrirla explícitamente o aceptar dos motores con reglas distintas.**

Lo que sí coincide sin conflicto: los **cuatro estados** (ok / pendiente /
sin_dato / no_aplica) y que `no_aplica` quede **fuera del denominador** ya
están decididos y escritos. Eso se reutiliza tal cual.

> Detalle de paso: hoy `no_aplica` **está muerto** — el único call site
> (`:134`) nunca pasa `aplica`. Si se reutiliza el contrato de salida, hay que
> arreglarlo antes.

### I.2 🟠 Este plan revierte CLARIFY-2 del spec 003

El spec 003 §4.2 evaluó «tabla aparte» y la descartó. Hoy se vuelve a ella.
**Hay que actualizar el spec 003**, no dejar dos documentos contradiciéndose —
lo pide la Constitución IX.

### I.3 🟠 ¿La formulación cuelga de la Meta o de la actividad del plan?

El prompt dice Meta. Los datos dicen que **el área ya formula en
`actividad_plan`** (13 filas). Hay que decidir si se migran, si conviven, o si
`actividad_plan_id` queda opcional.

### I.4 ✅ CERRADA el 2026-08-27 — y estaba mal planteada

**Lo que decía esta sección** (se conserva para que se vea el error): que
`contrato_actividad` (18 filas, 16 contratos) y `contrato_actividad_plan` (15
filas, 5 contratos) eran disjuntos, que `completitud_expediente.py:188` solo lee
el segundo, y que «por eso hoy reporta 20 de 25 contratos sin actividad del plan
cuando 16 sí tienen enganche». La conclusión era que había que unir las dos vías
antes de anclar Formulación.

**Medido, es falso, y el arreglo habría empeorado el dato.** Los dos puentes no
son dos formas de decir lo mismo:

| | apunta a | filas |
|---|---|---|
| `contrato_actividad_plan` | una **línea del plan** (`actividad_plan`) | 15 · 5 contratos |
| `contrato_actividad` | el **catálogo temático** `actividad`, 74 filas del tipo «ARTES ESCÉNICAS», «ACTIVIDAD FÍSICA ADULTO MAYOR» | 18 · 16 contratos |

Y la medición que lo decide: de las **13** entradas del catálogo que referencia
`contrato_actividad`, las que usa alguna línea del plan son **0**. Cero
intersección. Ese puente **no alcanza el plan por ningún camino**: es una
etiqueta de tema, no una traza presupuestal.

Así que el «20 de 25 contratos sin actividad del plan» que reporta hoy
`completitud_expediente` **es correcto**. Unir las dos vías —como se hizo en
`panel_area`, donde sí eran dos rutas al mismo destino— habría convertido un
número cierto en uno falso: habría dicho que 16 contratos tienen traza al plan
cuando ninguno la tiene.

`api/views.py:2290` ya documentaba la elección correcta. Nadie lee ese puente
para trazabilidad. **Formulación se ancla en `actividad_plan` y no hay nada que
resolver antes.**

> De paso, dos cosas que quedan anotadas sin ser de este plan: el catálogo
> `actividad` tiene duplicados por tilde (`2 ARTES ESCENICAS` y `3 ARTES
> ESCÉNICAS`), y los 4 contratos que no están en ninguno de los dos puentes
> siguen sin enganche de ninguna clase.
>
> La lección es la de la casa: *verificar no es hacer grep*. Esta sección nació
> de contar filas en dos tablas con nombres parecidos, sin preguntarle al
> sistema si esas filas llegaban al mismo sitio.

### I.5 🟡 ¿SECOP alimentará lo pre-contractual?

Con la ingesta de hoy, no: filtra `Borrador` y `Cancelado` en la fuente. Hay que
decidir si se amplía el filtro o si la formulación se sostiene sola hasta que
aparezca el contrato.

### I.6 🟡 El retiro de los códigos 5 y 1 exige aprobación de DML

Impacto en datos: cero. Pero es escritura sobre la base compartida y de
producción, y la Constitución VII no admite excepciones: backup < 24 h y
aprobación explícita.

---

## J · Pronóstico

### J.1 El camino crítico no es técnico

| | Freno | Estado |
|---|---|---|
| 1 | **La gente.** 13 usuarios, 3 en la familia Coordinador, 26 funcionarios en 15 de 46 subgrupos | Mitigado por §H: Innovación opera y delega poco a poco |
| 2 | **Anderson tiene 27 archivos sin commitear**, y uno de ellos es el que hay que arreglar (PR-5) | Coordinación, no código |
| 3 | **Cuatro fuentes sin definir**: PAA, POAI, plantilla mensual, formato trimestral de SEGPLAN | Bloquea el Bloque 5 entero |
| 4 | **BogData sin acceso técnico** | Bloquea CRP, compromiso, rubro |
| 5 | **Dos decisiones abiertas** (§I.1 y §I.3) | Bloquea PR-9 y PR-11 |

### J.2 Qué se puede hacer sin depender de nadie

**Los cuatro PR del Bloque 1 son autónomos y arreglan defectos vivos.** No
necesitan DDL, ni aprobación de base, ni decisiones pendientes, ni tocar
archivos de Anderson. Son el sitio por donde empezar.

### J.3 Tamaño esperado

Calibrado contra dominios comparables ya construidos en este repo:

| Dominio | Backend | Frontend |
|---|---|---|
| Educación | 2.240 | 1.364 |
| Festivales | 3.321 | 2.442 |
| Jóvenes a la E | 4.338 | 1.598 |
| Banco de Iniciativas | 12.033 | 2.599 |

Formulación —workflow con transiciones validadas, requisitos configurables,
completitud, documentos y trazabilidad— cae en la **banda media-alta**: del
orden de Jóvenes o Festivales, no de Educación. Por eso sale en 18 PR y no en
una entrega.

### J.4 Lo que este plan promete y lo que no

**Promete** que al final se puede recorrer Meta → Formulación → Contrato →
Ejecución sin perder trazabilidad, y explicar por qué una meta va como va.

**No promete** conciliación con SEGPLAN ni alertas: las dos dependen de fuentes
que hoy no existen. Prometerlas con la información de hoy sería inventar una
fecha.

---

## Anexo · Qué NO se hizo

- **No se implementó nada.** Sin código, sin DDL, sin migraciones, sin tocar
  modelos ni el catálogo de etapas.
- **No se escribió en la base.** Solo `SELECT`.
- **No se resolvieron las decisiones de §I.** Están planteadas con su evidencia
  para decidirlas con Alex.
- **No se reprodujo ningún dato personal.** El repositorio es público.

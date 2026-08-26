# Spec 003 · Contratos «en elaboración» y captura del área

**Estado:** borrador · **Creada:** 2026-08-26
**Constitución:** `.specify/memory/constitution.md`

---

## 1 · Lo que se pidió, y lo que resultó al medirlo

Son **cuatro cosas distintas** que llegaron juntas. Tres son defectos con
arreglo conocido; una sola es la etapa nueva.

| # | Lo reportado | Lo que es en realidad | Tamaño |
|---|---|---|---|
| A | «Contratista sin dato» en el 773 | **Defecto**: el dato existe, el dashboard no lo lee | 🟢 pequeño |
| B | No salen los responsables de Innovación | **Dato faltante**, no código: 0 funcionarios en ese subgrupo | 🟢 pequeño |
| C | Al guardar dice que falta algo | **Consecuencia de B** + mensaje poco claro | 🟢 pequeño |
| D | Etapa «En elaboración» | Etapa nueva **+ crear contratos** | 🟠 el trabajo real |

---

## 2 · A · El contratista existe pero no se ve

**Medido:** `Contrato(105).proveedor_id = 9`, y el `Proveedor` existe con el
nombre completo — «AGENCIA DISTRITAL PARA LA EDUCACIÓN SUPERIOR… ATENEA».

**La causa:** `apps/presupuesto/services/expediente_proyecto.py` devuelve **24
campos por contrato** y ninguno es el contratista. La precarga de ayer llenó la
base, y yo lo verifiqué en el servicio **nuevo** (`completitud_expediente.py`,
que sí lo lee) sin comprobar el **viejo**, que es el que alimenta el dashboard.

Es defecto propio, y deja una lección para el resto de la fase: **precargar un
dato no es mostrarlo.** Hay que verificar en la pantalla donde el usuario lo
espera, no en el servicio que uno acaba de escribir.

**Arreglo:** agregar `contratista` (y de paso `forma_pago`) a lo que devuelve
el expediente. Sin DDL.

**Riesgo de alcance:** hay que revisar si `panel_area` y `muro_subgrupos`
tienen el mismo hueco con otros campos precargados.

---

## 3 · B y C · Nadie de Innovación puede ser responsable

**La cadena completa, medida:**

```
Despacho (2) → Innovación (47)        ← el subgrupo SÍ existe
      ↓
GET /api/funcionarios/?subgrupo_id=47 → 0 resultados
      ↓
no hay a quién elegir como responsable
      ↓
al guardar: «El responsable es obligatorio»   (apps/login/api/views.py)
```

**Por qué está vacío** (medido 2026-08-26, corrigiendo lo que decía antes esta
misma línea):

`Funcionario` exige `persona_id` (NOT NULL), y **`usuario` no tiene columna
`persona_id`**. El único puente entre un usuario y una persona es a través de
`funcionario` — que es justo la fila que falta. O sea: estar en `usuario` no
alcanza para salir en el desplegable, y no hay forma automática de saber qué
`persona` corresponde a cada usuario.

`persona.usuario_id` **no sirve** como ese puente: no es identidad sino autoría
—quién registró a esa persona—. Comprobado: un solo usuario tiene 131 personas
colgando. Nadie es 131 personas. Usarlo para emparejar habría producido
funcionarios con la identidad de otro.

En todo el sistema hay **26 funcionarios** repartidos en 15 subgrupos (más uno
sin subgrupo). Innovación no es uno de los 15; en total, **31 de los 46
subgrupos no tienen ninguno**.

Hay además un estado incoherente que la base permite: un usuario con
`es_funcionario = True` y `funcionario_id = None`. El sistema afirma que es
funcionario y no hay fila que lo sostenga.

**No falta código.** El camino existe y está en dos pasos:

1. `/app/admin/personas` → crear la Persona
2. `/app/admin/org` → pestaña **Funcionarios** → crear el Funcionario con
   subgrupo Innovación

`funcionario.id` **sí tiene secuencia** (`funcionario_id_seq`), así que no hace
falta el truco de `MAX(id)+1`.

**Lo que sí hay que arreglar:**

- **El mensaje de error.** «El responsable es obligatorio» no dice que *no hay
  ninguno registrado en esa área*, que es lo que pasa. Debería decirlo, y
  enlazar a donde se crea.
- **El selector vacío.** Un desplegable sin opciones no explica nada. Debería
  decir «Esta área no tiene funcionarios registrados» con el enlace.

**Pregunta abierta (CLARIFY-1):** ¿el responsable de un evento tiene que ser
`Funcionario`, o bastaría un `Usuario`? Antes de tocarlo hay que ver dónde se
usa `evento.funcionario_id` después. **No se cambia sin esa evidencia.**

---

## 4 · D · La etapa «En elaboración»

Un contrato que el área está estructurando y **todavía no está en SECOP**.

### 4.1 · La etapa en sí: barata

El catálogo `etapa_contrato` tiene 4 filas con `orden` 1..4. Agregar una quinta
es **una fila**, no un rediseño:

| orden | código | nombre |
|---|---|---|
| **0** | **5** | **En elaboración** ← nueva, antes de todo |
| 1 | 1 | Formulación |
| 2 | 2 | Ejecución |
| 3 | 3 | Liquidación |
| 4 | 4 | Sancionatorio |

> El **código** es 5 (el siguiente libre) y el **orden** es 0 (va primero). El
> DDL 010 separó las dos cosas a propósito: *«`orden` manda en el stepper; no se
> infiere del código»*. Es exactamente el caso que esa decisión anticipaba.

**El stepper del frontend ya es data-driven**: `pasos()` lee
`catalogoEtapas()` del servidor y ordena por `orden`. Una etapa nueva entra sola.

> ⚠️ **Salvo el CSS.** `.stepper` tiene `grid-template-columns: repeat(4, 1fr)`
> cableado. Con cinco etapas la quinta se va a un segundo renglón. Arreglo de
> una línea, pero hay que hacerlo.

### 4.2 · Crear el contrato: ahí está el trabajo

Para registrar un contrato en elaboración hay que **crearlo**, y eso topa con
dos cosas medidas:

**`contrato` exige número y vigencia.** Sus únicas cuatro columnas NOT NULL son
`id`, `contrato_tipo`, `contrato_numero`, `contrato_vigencia`. Un contrato en
elaboración **todavía no tiene número** — se asigna al firmar.

**`contrato.id` no tiene secuencia** (deuda S5). Insertar exige el patrón
`crear_con_fallback_id`, que ya existe y se usa en `seed_contratos_infra.py`.

**Tres caminos, y hay que elegir uno (CLARIFY-2):**

| | Cómo | A favor | En contra |
|---|---|---|---|
| **A** | Número provisional que el área asigna | sin DDL; la fila ya cabe | el número provisional puede chocar con el real |
| **B** | Hacer `contrato_numero` nullable | el dato refleja la verdad: aún no hay número | DDL sobre una columna existente — el único de esta fase que **no** es aditivo |
| **C** | Tabla aparte de «procesos en elaboración» | no ensucia `contrato` | duplica estructura; al firmar hay que migrar la fila |

**Recomendación: A.** Es la única sin DDL, y el número provisional se reemplaza
por el real cuando SECOP lo publique — que es justo lo que la conciliación por
(número, año) ya sabe hacer.

### 4.3 · El riesgo que hay que resolver antes de construir

**Un contrato creado a mano que después aparece en SECOP se duplicaría.** El
espejo tiene 3.074 filas y la conciliación empata por (número, año). Si el área
crea el «CPS 1200/2026» y SECOP publica ese mismo contrato, quedarían dos.

Hay que definir qué pasa al publicarse: ¿se empareja solo? ¿se avisa? ¿queda
una tarea pendiente de conciliar? **Sin esa regla, esta funcionalidad crea el
problema que la precarga vino a resolver.**

---

## 5 · Orden propuesto

Los tres pequeños primero: desbloquean a Alex **hoy** y no dependen de ninguna
decisión.

| # | Qué | Estado al 2026-08-26 |
|---|---|---|
| 1 | **A** · el contratista se ve en el expediente | ✅ hecho (`6ccb9f1`) |
| 2 | **B/C** · mensaje y selector cuando no hay funcionarios | ✅ hecho (`d87b17e`) |
| 3 | Enganchar los funcionarios de Innovación *(dato, no código)* | ⛔ **espera a Alex** |
| 4 | **D.1** · la etapa «En elaboración» + el CSS del stepper | ✅ hecho (DDL 015/016/017) |
| 5 | **D.2** · crear contratos en elaboración | 🔜 **lo siguiente** |
| 6 | La regla de conciliación al publicarse | 🔜 va con el 5 |

El paso 3 no es código: el camino existe y está probado de punta a punta
(`GET /api/admin/personas/?q=` → `POST /api/admin/org/funcionarios/`). Lo que
falta es saber **qué `persona` es cada quién**, y eso no se deduce — ver §3.

---

## 6 · Preguntas abiertas

Las cuatro quedaron **respondidas por Alex el 2026-08-26**. Se dejan escritas
con su respuesta para que nadie las vuelva a preguntar.

| # | Pregunta | Respuesta |
|---|---|---|
| **CLARIFY-1** | ¿El responsable debe ser `Funcionario` o basta `Usuario`? | **Funcionario.** |
| **CLARIFY-2** | ¿Número provisional, columna nullable, o tabla aparte? | **B · nullable.** DDL 016 aplicado. |
| **CLARIFY-3** | Al aparecer en SECOP, ¿se empareja solo o se avisa? | **«Se empareja con lo formulado»** — el contrato en elaboración se ata a la actividad del plan, y por ahí empata. Falta escribir la regla exacta. |
| **CLARIFY-4** | ¿Quién lo crea y quién lo aprueba? | Lo **revisan** el admin, el alcalde, contratación y el coordinador del área. |

**Ojo con CLARIFY-2:** se eligió B, no la recomendación A del cuadro de §4.2.
La razón está medida y escrita en `016_contrato_numero_opcional.sql`: no hay
UNIQUE ni índice sobre `contrato_numero`, la conciliación ya filtra
`WHERE ci.contrato_numero IS NOT NULL`, y los 57 usos del backend son
SELECT/ORDER BY. El costo del DDL resultó ser menor que el de un número
inventado sobre información contractual.

**CLARIFY-3 sigue siendo el riesgo vivo.** «Se empareja con lo formulado» dice
por dónde, no qué pasa exactamente cuando SECOP publica el mismo contrato. Sin
esa regla escrita, esta funcionalidad puede crear el duplicado que la precarga
vino a eliminar. Es lo primero que hay que cerrar del paso 5.

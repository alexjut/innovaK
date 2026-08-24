# Contrapeso · dónde el plan y la realidad medida no coinciden

El plan de la Fase de completitud es sólido en su dirección. Pero **ocho de sus
supuestos no sobreviven a la base de datos**, y tres de ellos cambiarían el
trabajo si se implementan como están escritos.

Esto no es objetar el plan: es lo que el propio plan pidió en §3 —
*«no inventes relaciones antes de descubrir las reales»*.

Todo lo de acá está medido el 2026-08-24 contra la BD y el repositorio.

---

## 1 · «Forma de pago no existe» — **existe, y trae más de lo que se pedía**

**El plan (§16)** manda buscar `forma_pago`, `modalidad_pago`, `periodicidad`,
y dice: si no existe, captura manual.

**Existe:** `crp.forma_pago_codigo`. Y la tabla `crp` trae, además, casi toda la
ficha financiera que se iba a construir a mano:

```
contrato_id · plazo_dias · periodo_codigo · fecha_inicial · fecha_final
valor_crp · valor_neto · autorizacion_giro · numero_de_cdp · numero_de_crp
rubro_codigo · concepto_gasto_codigo
```

**Por qué nadie la veía:** el modelo Django `Crp` mapea **4 de ~42 columnas**.
No declara `contrato_id` **ni** `forma_pago_codigo`. Desde el ORM, esos campos
no existían.

**Qué cambia:** no se crea ningún campo. Se amplía un modelo (aditivo, sin DDL)
y se consigue la fuente que llena CRP — hoy **0 filas** y sin comando de ingesta.

> **Efecto secundario que conviene mirar aparte:** `metrics.py` ya calcula
> «comprometido» leyendo esa tabla vacía. Ese indicador está computando sobre
> cero filas ahora mismo.

---

## 2 · «Educación: 3 proyectos, 5 contratos» — **es 1 y 1**

**El plan (§7)** dibuja la pantalla de Educación con 3 proyectos, 5 contratos y
8 pendientes.

**Medido:** un proyecto (`2805`, «Kennedy Germinando Futuros») y **un** contrato
(`105`, CIA 773/2025, $23.168.769.452).

**Por qué importa, y no es un detalle:** Educación es el **único** de los cinco
contratos enganchados cuya meta se resuelve sin ambigüedad. Los otros cuatro
tocan 3, 7, 2 y 2 metas.

> Si el piloto se valida sólo con Educación, **el caso difícil no se ve nunca**.
> El segundo subgrupo no es una validación opcional al final: es donde se prueba
> lo que de verdad cuesta. Debería ser **Seguridad** (3 proyectos).

---

## 3 · «Determina la cardinalidad Contrato → Meta» — **es N, y no se puede pedir**

**El plan (§12-§13)** pide determinarla y, si no se puede derivar, dejar que el
usuario elija entre las metas del proyecto.

**Medido, sobre los 5 contratos que llegan al plan:**

| Contrato | Metas distintas |
|---|---|
| 97 | **3** |
| 98 | **7** |
| 99 | **2** |
| 100 | **2** |
| 105 | 1 ✓ |

**Cuatro de cinco tocan varias.** Y eso **no es un defecto del dato**: un
contrato financia varias actividades que aportan a varios indicadores.

**Qué cambia:** pedirle al funcionario que elija «la» meta lo obligaría a
inventar una respuesta que no existe — y a descartar seis metas reales en el
caso del contrato 98. No se persiste `contrato_meta`, no se pregunta: **se
muestran todas**.

---

## 4 · «Etapa: buscar fuente automática» — **no hay, y SECOP tiene una trampa**

**El plan (§14)** dice buscar primero una fuente automática.

**No existe.** Y hay un falso positivo peligroso: `SecopContrato.estado_contrato`
dice **«Modificado» en 20 de nuestros 25 contratos**. Eso significa que hubo
**otrosí**, no una etapa contractual. Usarlo como fuente pondría a 20 contratos
en una etapa inventada.

Lo demás del §14 ya está hecho: el catálogo `EtapaContrato` existe con las
cuatro etapas (DDL 010, aplicado el 2026-08-23), y no duplica `fase_proyecto`
—que es de proyecto y tiene 3 filas— precisamente por lo que pide el plan.

Está en 0/25 porque **nadie la ha capturado**, no porque falte dónde.

---

## 5 · «Ejecución técnica: revisar si puede derivarse» — **hoy no hay de qué**

**El plan (§20)** pide revisar si se deriva de avances, KPI, actividad o
indicador.

**Se revisó.** `AvanceIndicador` tiene **9 filas en todo el sistema**, y cuatro
de los cinco contratos con KPI tienen **cero** avances registrados.

Derivar un porcentaje de ahí daría **0 %** para casi todos. Y `0 %` significa
«no ha avanzado», no «no sabemos» — sería inventar un dato, justo lo que
prohíbe el §19 del propio plan.

Los 4 contratos que sí tienen `ejecucion` son los de infraestructura
(VIAS/PARQUES/INTERVENTORIA). Uno de ellos marca **0 %**, y ése **sí** es un
cero real.

---

## 6 · «Los cambios no cascadean entre ambientes» — **los ambientes no existen**

**El plan (§44)** parte de que Desarrollo, Pruebas y Producción tienen
inconsistentemente los cambios.

**Medido:** las tres ramas comparten el **mismo hash de árbol**
(`0831ed0f…`). `git diff` entre cualquier par da **cero diferencias**. Hay **un**
checkout del repositorio en el host y **un** contenedor, que monta el working
tree (`volumes: .:/app`).

**La causa real del síntoma es otra:** `frontend/dist` está gitignored —**0**
archivos en el índice, 147 en disco— y `spa.py` lo sirve del filesystem. **El
frontend no viaja con el repositorio.**

Por eso lo que «no aparece» es siempre lo mismo —dashboard, Mi Área, estilos,
accesibilidad— y el backend sí: está bind-mounteado.

> **Qué cambia:** la lista de causas del §46 (ramas divergentes, migraciones sin
> aplicar, imágenes viejas, caché) no aplica. Ninguna. Es un solo problema, y es
> de empaquetado.

---

## 7 · «Migraciones para etapa, plan de pago, contrato↔meta, auditoría» — **sólo una**

**El plan (§50)** anticipa migraciones para cinco cosas.

**Medido:**

| | Estado |
|---|---|
| Etapa contractual | ✅ DDL 010 aplicado el 2026-08-23 |
| Plan de pago | ✅ `SecopPlanPago`, 36.210 filas, cubre 20/25 |
| Contrato ↔ Meta | ❌ **no se debe crear** — ver §3 |
| Forma de pago | ✅ `crp.forma_pago_codigo` — ver §1 |
| **Auditoría** | ⚠️ **la única que falta** |

**Esta fase necesita un solo DDL**, y es aditivo. Eso reduce mucho el riesgo
sobre la base compartida.

---

## 8 · «Prueba al menos otro subgrupo» — **sólo 8 de 45 tienen plan**

**El plan (§25)** pide que funcione para todos los subgrupos.

**Medido:** hay **45 subgrupos** y sólo **8 tienen proyectos**. Los otros 37 no
tienen plan.

**Qué cambia:** que el panel de un subgrupo sin proyectos salga vacío **no es un
defecto** — es la verdad. Pero la pantalla tiene que decir *«esta área no tiene
plan asignado»*, no un cero mudo. Es exactamente la distinción del §19 aplicada
a la estructura, no al dinero.

---

## Lo que el plan acierta y conviene subrayar

- **§11** — el faltante contrato↔proyecto se resuelve desde Mi Área, no con
  mappings. Correcto, **y el mecanismo ya existe**
  (`VincularContratoActividadPlanView`). Sólo hay que cerrarle el hueco de scope.
- **§19** — `$0` ≠ `Sin dato`. Es la regla que más veces salvó este análisis.
- **§21** — precedencia de fuentes. Es lo que convierte «llenar huecos» en algo
  defendible.
- **§42** — reconocer que los −168 px **no** son medición de navegador. Lo son:
  salen de valores declarados. El intento con Chromium falló por red.
- **§43** — no lanzar 25 agentes. Confirmado: 14 de 25 murieron por límite de
  sesión.

---

## Consecuencia práctica

El trabajo real de esta fase es **más pequeño de lo que el plan supone** en
modelo de datos —un solo DDL— y **más grande** en dos frentes que el plan trata
de pasada:

1. **La precarga.** Los 25/25 contratos tienen espejo en SECOP. De ahí salen 25
   contratistas, 3 valores, 5 fechas y 1 objeto **sin un solo formulario**. Es
   el mayor golpe de completitud disponible y el plan lo menciona en §10 como si
   fuera un detalle de presentación.

2. **El hueco de scope.** `VincularContratoActividadPlanView` no valida el
   contrato. El §23 lo pide explícitamente —*«un usuario no debe poder cambiar
   un `contract_id` para modificar otro Subgrupo»*— y hoy **sí puede**. Va
   primero, antes de abrir más escritura.

# De dónde salen las cifras de innovaK

**Informe para Camilo · 10 de septiembre de 2026**
Alcaldía Local de Kennedy · Sistema de información innovaK

---

## Para qué sirve este documento

innovaK es el sistema de información interno de la Alcaldía Local de Kennedy.
Muestra en qué va el Plan de Desarrollo Local 2025-2028: cuánto se apropió,
cuánto se comprometió, cuánto se giró, cuántas metas van cumplidas y quién
recibió qué en el territorio.

Ninguna de esas cifras nace en innovaK. Casi todas llegan de afuera, de cuatro
fuentes que **no miden lo mismo, no se actualizan al mismo ritmo y no cubren el
mismo universo**. Este documento explica qué trae cada una, qué NO trae, cómo
está hoy y qué vamos a hacer con ellas.

La regla que ordena todo el trabajo la fijó Alex el 7 de septiembre: **«la base
de todo es la Matriz; todo debe estar coherente con eso»**. Lo que sigue es
cómo se aterriza esa regla fuente por fuente.

Todas las cifras de este informe están medidas contra los datos reales al
10 de septiembre de 2026.

---

## Las cuatro fuentes principales, de un vistazo

| Fuente | Quién la produce | Cómo entra | Corte de hoy | Qué aporta que nadie más da |
|---|---|---|---|---|
| **Matriz de Seguimiento PDL 2025-2028** | La Alcaldía Local de Kennedy | Excel, se carga a mano | Vigencias 2025 y 2026 | Avance físico de metas, apropiación POAI, alertas |
| **SEGPLAN / Datos Abiertos SDP** | Secretaría Distrital de Planeación | Descarga automática | **Congelada** | Contraste externo del catálogo del Plan |
| **BogData / CRP** | Secretaría de Hacienda Distrital | Excel de corte, se carga a mano | 7 de septiembre de 2026 | El libro presupuestal real: registros, giros, terceros |
| **SECOP II** | Colombia Compra Eficiente | Descarga automática | Sincronizado el 10 de septiembre | El hecho contractual: quién, cuánto, en qué estado |

---

# 1. La Matriz de Seguimiento PDL 2025-2028

## Qué es y quién la produce

Es el instrumento oficial de seguimiento del Plan de Desarrollo Local. Lo
elabora la propia Alcaldía Local de Kennedy —Planeación local— en un archivo de
Excel, y lo actualiza cuando reprograma metas o cierra un período. Es el
documento con el que la Alcaldía se reporta a sí misma y a Planeación
Distrital.

**Es la única fuente que baja hasta la meta.** Todo lo demás llega, en el mejor
de los casos, hasta el proyecto.

## Qué trae exactamente

Para cada una de las **78 metas** del Plan, cruzadas con las cuatro vigencias
del cuatrienio —**312 combinaciones de meta y año**—, trae cuatro columnas de
plata y tres de magnitud:

- **Presupuesto proyectado PDL**: lo que el Plan aspiraba a invertir en esa meta
  durante el cuatrienio. Total medido: **$682.024.660.000**.
- **Apropiación POAI inicial**: lo que de verdad se asignó en el presupuesto
  anual. 2025: **$187.520.585.000**. 2026: **$188.937.712.000**. Total
  **$376.458.297.000**.
- **Comprometido** por vigencia: 2025 **$185.820.742.244**, 2026
  **$39.032.923.611**. Total **$224.853.665.855**.
- **Girado** por vigencia: 2025 **$92.481.417.935**, 2026 **$8.664.588.032**.
  Total **$101.146.005.967**.
- **Magnitud programada, contratada y ejecutada**, y el **porcentaje de
  cumplimiento** de cada meta: presente en **76 de las 78 metas**.
- La **alerta** ya resuelta por la propia Alcaldía —Crítico, En ejecución,
  Ejecutada, Desierta, Sin magnitud contratada—. innovaK la importa tal cual;
  no la recalcula.

Sobre lo apropiado, la Alcaldía se reporta a sí misma **59,7 % comprometido y
26,9 % girado**.

## Qué NO trae

Esta es la parte que produce todos los malentendidos:

- **No trae contratos.** Ni un número de contrato, ni un contratista, ni una
  fecha de firma. Su «comprometido» es una cifra por meta y por año; no se puede
  cruzar contra un contrato porque el contrato no está ahí.
- **No trae registros presupuestales.** No hay CRP, ni CDP, ni terceros.
- **No trae beneficiarios.** Dice «700 estudiantes» como meta; no dice quiénes.
- **No trae 2027 ni 2028 en plata.** Esas dos vigencias vienen con el proyectado
  pero **sin apropiación**, porque el POAI se apropia año a año. No es un vacío
  que haya que llenar: llegará con la matriz del año que viene.

## Cada cuánto y cómo entra

**A mano.** Alguien sube el archivo de Excel y lo carga. La carga es **seca por
defecto** (primero muestra qué haría, sin escribir), queda **firmada** con el
usuario que la hizo y es **idempotente**: subir dos veces el mismo archivo no
duplica nada. Todo lo que escribe queda en la auditoría del sistema.

No hay periodicidad pactada: llega cuando la Alcaldía la actualiza.

## Cómo está hoy

- **Cobertura del Plan: 28 de 28 proyectos.** Antes de la carga del 1 de
  septiembre eran 12 de 28. La carga creó 18 proyectos, 56 metas nuevas y
  completó los metadatos de 22 metas que estaban a medias.
- **30 proyectos** con plata cargada, sobre los 31 que existen en el sistema.
- **76 de 78 metas** con porcentaje de cumplimiento.

Un hallazgo que solo apareció al medir: **la apropiación es MAYOR que el
proyectado, no menor.** 2025 apropió un 15 % por encima de lo que el Plan
proyectaba, y 2026 un 12 %. Se financió por encima de lo planeado.

## Para qué la usamos, y para qué no

**Sí:** es la base del avance físico de metas en todo el sistema, de la
apropiación que encabeza el tablero presupuestal, del semáforo de cada proyecto
y de las listas oficiales del Plan.

**No:** su «proyectado PDL» no debe usarse nunca como denominador de un
porcentaje de ejecución. Es la meta aspiracional del cuatrienio, no la plata
disponible. La cadena real es **Apropiación → Comprometido → Girado**, y por eso
el tablero encabeza con la apropiación.

Ese cambio, hecho el 1 de septiembre, movió el porcentaje de ejecución de 6,2 %
comprometido y 0,7 % girado a **11,0 % y 1,3 %** — porque el cálculo anterior
dividía dos años de plata real entre cuatro años de meta aspiracional.

## Qué le falta

1. **Es manual.** Depende de que alguien mande el archivo y de que alguien lo
   suba. No hay canal automático.
2. **Diez indicadores reprogramados sin decidir.** La Alcaldía reprogramó la
   magnitud de 2026 en diez metas, y la magnitud viva en el sistema quedó con
   otro número. La carga los **reporta y no los toca**: cambiar la meta de un
   área en curso sin que nadie lo vea es un error que ya costó una corrección.
   Hay que decidirlos uno por uno.
3. **Un proyecto sin área asignada.** El proyecto 2740 (comunidades étnicas: rom,
   negras, raizales, indígenas) no encaja en ningún área existente; quedó en
   Participación por descarte y marcado para revisar.

---

# 2. SEGPLAN / Datos Abiertos de la Secretaría Distrital de Planeación

## Qué es y quién la produce

Es la publicación oficial del Distrito sobre los proyectos de desarrollo local:
el archivo de Datos Abiertos que la Secretaría Distrital de Planeación pone en
línea con lo programado, comprometido y girado de cada meta de cada localidad.
Es lo que cualquier ciudadano puede consultar sobre Kennedy sin pedirle nada a
la Alcaldía.

En innovaK funciona como **espejo de contraste**: no manda, pero permite
comparar lo que decimos contra lo que el Distrito publica de nosotros.

## Qué trae

280 filas para Kennedy, cubriendo **28 proyectos** en las cuatro vigencias:
programado, comprometido y girado por meta y actividad, más las magnitudes y los
porcentajes que calcula el Distrito.

## Qué NO trae

- **No trae los proyectos que la Alcaldía creó después.** Le faltan dos que sí
  son reales y están auditados: **2556 (Mujeres sin Barreras)** y **2643
  (Ecomanos en Acción)**. No cruzan porque la publicación se quedó atrás.
- **No es una lista sumable de frente.** Publica una fila por meta y actividad,
  y **repite el total del proyecto en cada una** —hasta siete filas por proyecto
  y año—. Sumar la columna tal como viene multiplica la cifra por el número de
  filas. Deduplicada correctamente, el proyectado del cuatrienio da
  **$667.578 M**, contra los **$682.025 M** que reporta la Matriz para 30
  proyectos.

## Cada cuánto y cómo entra

**Automático.** Un proceso nocturno descarga el archivo, filtra Kennedy y
actualiza el espejo sin duplicar nada.

## Cómo está hoy — 🔴 parada

**La última lectura exitosa fue el 23 de julio de 2026.** El proceso corre, pero
el archivo publicado **no se ha movido desde el 18 de febrero de 2026**: no es
que falle la descarga, es que la fuente no publica.

Esto ya se escaló a Planeación Distrital y **sigue sin resolver**.

**Esa parálisis es la razón de que la Matriz exista como carga manual.** La
Alcaldía siguió reprogramando metas de 2026 igual, y como el canal automático no
las trae, las manda a mano en Excel. La Matriz no es un capricho: es el
reemplazo de un canal roto.

## Para qué la usamos, y para qué no

**Sí:** para contrastar. La pantalla de comparación con el Distrito **debe** leer
este espejo — comparar contra lo que publica el Distrito es su razón de ser.
También sirve para marcar qué metas nuestras no tienen par oficial.

**No:** como base de ninguna cifra que se publique. Hoy dos pantallas todavía lo
hacen —una página se titula «Fuente: Matriz de Seguimiento PDL» y su recuadro de
presupuesto sale en realidad de este espejo congelado— y está en la lista de
corrección.

## Qué le falta

Que Planeación Distrital vuelva a publicar. Es lo único. Mientras tanto, cada
mes que pasa el espejo se aleja más de la realidad y su valor como contraste se
degrada.

---

# 3. BogData / CRP

## Qué es y quién la produce

BogData es el sistema presupuestal del Distrito, administrado por la Secretaría
de Hacienda. El **CRP** —Certificado de Registro Presupuestal— es el documento
con el que se compromete formalmente una plata contra un rubro: es el acto
presupuestal, anterior y distinto al contrato.

El reporte que recibimos es el **estado de cuenta completo del Fondo de
Desarrollo Local de Kennedy**: cada registro presupuestal vivo, con su valor, sus
anulaciones, lo que ya tiene giro autorizado, el tercero beneficiario, el rubro y
las fechas.

**Es la única fuente que dice, con respaldo presupuestal, cuánta plata está
efectivamente comprometida y cuánta girada.**

## Qué trae exactamente

Corte del 7 de septiembre de 2026, **2.630 registros**:

| | Registros | Valor neto | Giro autorizado |
|---|---:|---:|---:|
| **Estado de cuenta completo** | 2.630 | $226.744.982.139 | $126.648.571.200 |
| **Del PDL 2025-2028** | 2.054 | **$184.839.187.185** | $110.606.018.880 |
| Anterior al PDL (2013 a 2024) | 576 | $41.905.794.954 | $16.042.552.320 |

**innovaK publica solo el tramo del PDL.** Los $41.906 M restantes son contratos
de 2013 a 2024 que la Alcaldía sigue pagando —ejecución de otra administración—
y se muestran aparte, visibles, en vez de desaparecer. Es una decisión de Alex
del 9 de septiembre.

**El corte va por el año del compromiso, y esa distinción vale plata.** Hay 1.688
registros marcados como «obligación por pagar» por **$135.078.206.163**. Si se
cortara por esa marca, se irían todos. Pero **$93.209.948.593 de ellos
corresponden a compromisos de 2025** — dentro del Plan, ejecución legítima suya.
Solo $41.906 M vienen de 2024 hacia atrás. Los 140 registros cuyo año no se puede
leer se quedan dentro: son del ejercicio en curso, y no tener año no los vuelve
viejos.

## Qué NO trae

- **No llega a la meta.** Un CRP se registra contra un rubro y un elemento del
  Plan; no dice a cuál de las 78 metas del PDL pertenece. La atribución a meta no
  existe en esta fuente y no se puede deducir de ella.
- **No llega al proyecto en dos tercios de los casos.** Medido hoy: **876 de los
  2.630 registros** ($86.603.918.854) sí se atribuyen a un proyecto. Los otros
  **1.754** ($140.141.063.285) no, y no por descuido:
  - **1.688 son obligaciones por pagar** ($135.078.206.163), registradas contra un
    rubro genérico —«Obligaciones por pagar Inversión vigencia anterior»— que por
    definición no identifica proyecto.
  - **66 son gastos de funcionamiento** ($5.062.857.122), que no pertenecen a
    ningún proyecto de inversión.
- **No trae el objeto contractual ni el estado del contrato.** Eso es SECOP.
- **No trae avance físico.** Ni una magnitud, ni un beneficiario.

## Cada cuánto y cómo entra

**A mano, por corte.** Alguien recibe el Excel de Hacienda y lo sube. Como en la
Matriz: seco por defecto, firmado, idempotente, con historial de cargas.

Cada carga **reemplaza el libro entero**, no edita filas sueltas. Por eso la
autorización para cargar no depende de tener un módulo, sino de **tener alcance
sobre toda la localidad**: quien solo ve una parte de Kennedy no puede reemplazar
el libro de toda. Hoy son siete cuentas.

## Cómo está hoy

Cargado y conciliado. Los totales del sistema cuadran contra los totales del
propio archivo de Hacienda. Las dos cosas que la especificación traía mal —cómo
se calcula el valor neto y de dónde se lee el proyecto dentro del rubro— las
detectaron las pruebas, no la lectura del documento.

Una revisión adversarial encontró 19 observaciones; **seis no sobrevivieron a la
verificación** y quedaron escritas con su motivo, porque son lecturas razonables
que van a volver a proponerse. De las reales, las dos que importaban:

1. **Faltaba el control de escritura.** Un rol provisionado para administrar un
   solo contrato podía subir un archivo y dejar el comprometido de toda la
   localidad en $56 M, sin forma de deshacerlo desde la pantalla. Corregido.
2. **Siete entidades distritales compartían identidad.** El NIT 899999061 es el
   de Bogotá D.C. y lo llevan siete entidades distintas en el archivo; el sistema
   las colapsaba en una sola, atribuyendo **$34.771 M a quien no los recibió** —
   entre ellos **$31.127.780.186 de la Secretaría Distrital de Integración
   Social** que aparecían a nombre de Cultura. Corregido.

## Para qué la usamos, y para qué no

**Sí:** es la fuente del comprometido y el girado presupuestal de la localidad, y
del estado de cuenta por rubro y por tercero.

**No:** no se puede usar para hablar de metas ni de avance del Plan, porque no
llega ahí. Y su total completo ($226.745 M) no es «lo que la Alcaldía comprometió
en este Plan» — eso son $184.839 M.

## Qué le falta

- **Que 23 registros por $11.200 M recuperen su proyecto.** El sistema ya sabe
  hacerlo por la vía del contrato; el arreglo corre en la carga y entra solo en
  el corte de octubre.
- **Que llegue con periodicidad conocida.** Hoy llega cuando llega.

---

# 4. SECOP II

## Qué es y quién la produce

SECOP II es la plataforma de contratación pública del Estado colombiano,
administrada por Colombia Compra Eficiente. Es donde queda el hecho contractual:
qué se firmó, con quién, por cuánto, en qué estado y con qué plan de pagos.

## Qué trae exactamente

**3.123 contratos** de la Alcaldía Local de Kennedy, de 2024 a 2026:

| Año | Contratos | Valor contratado | Valor pagado |
|---|---:|---:|---:|
| 2024 | 1.135 | $124.817.485.111 | $100.224.091.080 |
| 2025 | 1.184 | $157.245.732.779 | $57.522.208.333 |
| 2026 | 804 | $42.216.853.058 | $21.536.820.188 |
| **Total** | **3.123** | **$324.280.070.948** | **$179.283.119.601** |

Más **36.626 líneas de plan de pagos**, con fechas y estados.

Trae además el número de contrato, la referencia, el objeto, la modalidad, el
estado, el proveedor con su documento, y las fechas de firma, inicio y fin.

## Qué NO trae

- **No mide ejecución del PDL.** Mide la realidad contractual. No sabe qué es una
  meta, ni un proyecto del Plan, ni un objetivo estratégico.
- **No tiene dimensión de vigencia en el pago.** Su «valor pagado» es el **pago
  acumulado del contrato**, de principio a fin. Un contrato firmado en 2025 y
  pagado en 2026 lo trae completo en una sola cifra; la Matriz reparte ese mismo
  dinero entre las dos vigencias. Es la causa de la discrepancia del proyecto
  2790, explicada más abajo.
- **No distingue «no se pagó» de «nadie lo registró».** Ver la sección 6.

## Cada cuánto y cómo entra

**Automático**, sin intervención de nadie.

## Cómo está hoy — ✅ al día

Sincronizado el **10 de septiembre de 2026**, con contratos firmados hasta el
**4 de septiembre**. Es la fuente más fresca de las cuatro.

## Para qué la usamos, y para qué no

**Sí:** para el expediente del contrato, el panel de cada área, la conciliación
contra el registro presupuestal y el plan de pagos.

**No:** para calificar la ejecución de un área ni de un proyecto. Ni para
contradecir a la Matriz sin antes homologar universo y vigencia. Y **nunca para
pintar de rojo a nadie con un valor pagado en cero** — ver sección 6.

## Qué le falta

Que las entidades diligencien el valor pagado. **152 contratos de 2025 en
adelante, por $70.204.144.158 contratados, están reportados en cero.** No es un
problema de SECOP: es un campo que alguien no llenó.

---

# 5. Lo que innovaK captura por sí mismo

## Qué es

Todo lo que ocurre en el territorio y **ninguna fuente externa registra**: quién
asistió a un curso, quién recibió una beca, quién se inscribió al banco de
iniciativas, qué opinó un ciudadano de un festival, quién recibió qué insumo y
firmó por él.

Se captura por formulario público con código QR: el ciudadano lo llena desde su
celular, sin usuario ni contraseña, y el organizador lo valida después.

## Qué hay hoy

| | |
|---|---:|
| Personas registradas | 7.121 |
| Beneficiarios | 5.598 |
| Participantes en actividades | 2.545 |
| Actividades y eventos | 55 |
| Entregas de beca (Jóvenes a la E) | 174 |
| Inscripciones al Banco de Iniciativas | 24 |
| Encuestas de percepción de festivales | 24 |

## Qué NO trae

No trae plata. No trae metas. Es la evidencia de ejecución en el territorio, no
el reporte presupuestal.

## Qué le falta

**Que se use.** Varios módulos están construidos y probados de punta a punta pero
todavía sin datos reales: las entregas de insumos, la captura genérica de Cultura
y las caracterizaciones por sector están todas en cero. La infraestructura existe
y funciona; falta que las áreas la usen en campo.

También: cuando una entrega se valida, suma automáticamente al indicador
correspondiente. Ese es el único camino por el que el avance de una meta se
alimenta desde el territorio, y hoy alcanza a 6 de los 77 indicadores activos.

---

# 6. El registro interno de contratos de las áreas

## Qué es

Antes de que existiera el espejo de SECOP y la carga de BogData, cada área
cargaba sus contratos a mano en innovaK, y los vinculaba a un proyecto y a una
actividad del plan. Ese registro sigue vivo.

## Cómo está hoy

**25 contratos, por $41.264.386.430, en 3 de las 18 áreas:**

| Área | Contratos |
|---|---:|
| Cultura | 15 |
| Infraestructura | 4 |
| Educación | 1 |

Además hay **5 CDP internos por $52.000.000** — un registro prácticamente vacío.

## Por qué importa que esté tan incompleto

Porque **16 de las 18 áreas tienen plata comprometida según la Matriz**, y solo
3 tienen contratos cargados. Varias pantallas siguen calculando su cifra de plata
sobre este registro, y por eso **12 áreas abren su panel y leen «Contratado $0»**
al lado de una lista llena de proyectos y actividades. Un área que apropió
$18.450 M y comprometió $9.858 M lee que no tiene un peso.

No es que el dato esté mal. Es que la pantalla está preguntándole a la fuente
equivocada.

## Para qué sirve y para qué no

**Sí:** es el único lugar donde un contrato queda atribuido a un proyecto y a una
actividad concreta del plan. Esa atribución no la trae ni SECOP ni BogData, y es
la que permite conectar un contrato con una meta.

**No:** no sirve como registro de cuánto contrató la Alcaldía. Para eso está
SECOP (3.123 contratos) y BogData (2.630 registros presupuestales).

---

# 7. Por qué dos cifras con el mismo nombre no son la misma cifra

Este es el corazón del asunto. Cinco proyectos aparecían con una diferencia
grande entre lo que decía SECOP y lo que decía la Matriz. Al medirlas una por
una, **no eran cinco desacuerdos: eran tres cosas distintas, y solo una era una
diferencia real** — y ni siquiera era el error de nadie.

## Caso 1 · El proyecto 2790: la vigencia

**Kennedy Mi Parque Mi Espacio.** SECOP dice que se pagaron **$3.220.703.509**.
La Matriz reporta girados **$32.080.900**. Cien veces menos.

**Las dos tienen razón.**

El proyecto tiene dos contratos y **los dos están en SECOP**: cubren el 84,1 % de
lo que la Matriz da por comprometido. Así que no es que falte información.

Lo que pasa es esto: los tres registros presupuestales de esos contratos son de
**ejercicio 2026 con año de compromiso 2025**, y están cargados contra el rubro
«Obligaciones por pagar Inversión vigencia anterior». O sea: **el dinero se giró,
y se giró como obligación por pagar de la vigencia anterior.**

- **La Matriz** mide el giro **contra la apropiación de cada vigencia**. Para las
  metas de este proyecto son $35.700 en 2025 y $32.045.200 en 2026 — lo que se
  giró contra la plata apropiada en cada uno de esos dos años.
- **SECOP** mide el **pago acumulado del contrato**, de principio a fin, sin
  preguntar contra qué vigencia salió.
- **BogData** confirma los giros: $2.751.497.273 y $653.229.520 de un contrato,
  $125.963.766 del otro.

Homologada la vigencia, **las tres fuentes concuerdan**. No se le escribió al
área, porque no hay discrepancia que reportar.

**Cómo explicarlo en una reunión:** «SECOP nos dice cuánto se le ha pagado al
contratista en total. La Matriz nos dice cuánto salió de la plata de este año.
Cuando un contrato de 2025 se paga en 2026 como obligación por pagar, SECOP lo
cuenta entero y la Matriz lo cuenta contra el año que lo apropió. Son dos
preguntas distintas con dos respuestas correctas».

## Caso 2 · El proyecto 2780: la cobertura

**Kennedy Proyecta Talento.** SECOP muestra un **99,2 % pagado**. La Matriz
reporta un **28,4 % girado** sobre lo que ese mismo proyecto tiene comprometido.
Las dos cifras son de plata, así que leídas de frente parece que una miente.

No. **Están hablando de universos de distinto tamaño:**

| | |
|---|---:|
| Comprometido según la Matriz | $7.794.984.904 |
| Contratos del proyecto que innovaK conoce (los 15 cruzan con SECOP) | $713.221.534 |
| **Cuánto de ese comprometido alcanza a ver SECOP** | **9,1 %** |
| Pagado sobre esa novena parte | $707.721.534 → **99,2 %** |

Los 15 contratos son prestaciones de servicios de $33 M a $63 M cada una. El
grueso de los $7.795 M del proyecto **no está cargado como contrato en innovaK**,
así que el porcentaje de SECOP se calcula sobre una novena parte del proyecto.

Es como decir «me comí el 99 % del plato» cuando el plato tenía una novena parte
de la comida.

**Cómo explicarlo en una reunión:** «El 99,2 % es cierto, pero es el 99,2 % de
$713 millones, no de los $7.795 millones del proyecto. Antes de comparar dos
porcentajes hay que preguntar sobre qué se calculó cada uno».

**Qué cambió en el sistema:** ahora la anotación dice **primero cuánto alcanza a
ver el espejo** y después qué porcentaje reporta. El número no cambió; cambió que
ya no se puede leer mal.

## Caso 3 · El comprometido de la localidad: dos libros legítimos

Este no venía en la lista de las cinco discrepancias, pero se ve al medir y hay
que decidirlo:

| Fuente | Comprometido | Qué está midiendo |
|---|---:|---|
| **La Matriz** | $224.853.665.855 | Lo que la Alcaldía reporta comprometido contra la apropiación de cada meta y cada año |
| **BogData** | $184.839.187.185 | Los registros presupuestales efectivamente expedidos con año de compromiso dentro del Plan |

**Diferencia: $40.014.478.670.** Las dos son legítimas y miden actos distintos —
un reporte de gestión contra un libro presupuestal. **No están conciliadas meta
por meta, y no se pueden conciliar así**, porque BogData no llega a la meta.

Es una decisión de negocio, no técnica: hay que definir cuál de las dos es la
cifra que la Alcaldía publica cuando le preguntan «cuánto ha comprometido».

## La regla general

Antes de decir que dos fuentes discrepan, hay que homologar cuatro cosas:

1. **La métrica** — ¿es plata o son unidades? ¿es pago acumulado o giro del año?
2. **El universo** — ¿sobre cuántos contratos, cuántas metas, cuántos proyectos?
3. **La vigencia** — ¿contra qué año se está midiendo?
4. **La fecha de corte** — ¿de cuándo es cada dato?

**Solo lo que sobreviva a las cuatro es una discrepancia real.** De cinco, quedó
una, y resultó ser consistente.

---

# 8. Un cero no siempre es un cero

Tres de los cinco proyectos «en desacuerdo» aparecían con SECOP marcando 0,0 % de
pago: **2377 (Kennedy Germinando Futuros)**, **2574 (Kennedy Crecimiento y
Conexión)** y **2706 (Kennedy en Alianza por la Seguridad)**. La Matriz les
reportaba 78,9 %, 37,1 % y 40,0 % de avance.

**Ese cero no era una medición.**

## Lo medido

SECOP **nunca deja vacío** el campo de valor pagado: las 3.123 filas del espejo
lo traen con un número. Así que **«no se giró» y «nadie cargó el pago» son
exactamente el mismo cero**, y no hay forma de distinguirlos mirando el campo.

**152 contratos de 2025 en adelante, por $70.204.144.158 contratados, están en
cero.**

## El caso que lo prueba

El contrato **CIA-773-2025**, del proyecto 2377:

| Fuente | Dice |
|---|---:|
| SECOP II | $0 pagado |
| BogData | **$8.818.769.452 girados** |

El dinero salió. Simplemente nadie lo registró en SECOP.

## La regla que adoptamos

> **Sin fuente no se califica. Un vacío no se pinta de rojo. Y $0 no es «sin
> dato»: un cero medido sí es una cifra y se muestra como tal.**

En la práctica:

- El sistema **dejó de anotar** discrepancia contra esos tres proyectos.
- Cuando no hay Matriz con qué contrastar, el resultado es **«incompleto», con el
  motivo escrito** — «SECOP no reporta giros» — en vez de un cero rojo.
- Lo mismo aplica al avance físico: donde no hay con qué medir, se dice «sin
  dato», no «0 %».

**Por qué importa tanto:** sin esta regla, un área quedaba pintada de rojo —
públicamente, en su propio panel — por un campo que su contratista no diligenció.
El sistema estaba acusando de no ejecutar a áreas que sí ejecutaron.

Es exactamente el mismo defecto que ya se corrigió en el avance de metas: el
tablero clasificaba **73 de las 78 metas como «sin avance»** cuando la Matriz
reportaba 21 metas al 100 % o más, sencillamente porque leía un registro interno
que cubría 6 de 77 indicadores.

---

# 9. Quién manda para cada dato

| Dato | Manda | Se contrasta con | Nunca decide |
|---|---|---|---|
| **Avance físico de metas** | La **Matriz** | El avance registrado a mano en innovaK, que se muestra al lado | SECOP, BogData |
| **Alerta de cumplimiento** (Crítico / En ejecución / Ejecutada…) | La **Matriz** — se importa ya resuelta, no se recalcula | — | — |
| **Apropiación** | La **Matriz** (Apropiación POAI inicial) | El proyectado PDL de la misma Matriz | — |
| **Plata comprometida de la localidad** | **BogData** | La Matriz, agregada por proyecto | SECOP, el registro interno |
| **Plata girada** | **BogData** | SECOP, sabiendo que mide otra cosa | El registro interno |
| **Comprometido y girado por meta** | La **Matriz** (es la única que baja a la meta) | BogData por proyecto | — |
| **Contratos: número, objeto, valor, estado, contratista** | **SECOP II** | El registro interno de las áreas | — |
| **Plan de pagos del contrato** | **SECOP II** | — | — |
| **A qué proyecto y actividad pertenece un contrato** | **innovaK** (registro interno) | El rubro y el elemento del Plan en BogData | — |
| **Catálogo del Plan** (objetivos, programas, metas, proyectos) | La **Matriz** | El espejo de SEGPLAN, con las metas sin par marcadas | — |
| **Beneficiarios, eventos, entregas, caracterizaciones** | **innovaK** | — | Ninguna fuente externa los trae |

---

# 10. Qué vamos a hacer

## El problema de fondo, en una frase

**Hoy no existe una sola forma de responder «cuánta plata tiene esto».**

Conviven **seis registros distintos de plata**, y cada pantalla eligió el suyo:

| # | Registro | Qué dice hoy |
|---|---|---|
| 1 | La Matriz, por meta y vigencia | Comprometido $224.853.665.855 |
| 2 | BogData / CRP | Comprometido del PDL $184.839.187.185 |
| 3 | Contratos de SECOP II | Firmado $324.280.070.948 · pagado $179.283.119.601 |
| 4 | Plan de pagos de SECOP II | 36.626 líneas por $492.694.245.687 netos |
| 5 | El registro interno de contratos de las áreas | $41.264.386.430 en 25 contratos |
| 6 | El espejo congelado de SEGPLAN | Proyectado $667.578 M sobre 28 proyectos |

*(Y un séptimo prácticamente vacío: los CDP internos, 5 registros por
$52.000.000, que todavía alimentan el recuadro «Asignado» de la pantalla de
programas.)*

El síntoma más visible: **la fila de recuadros que encabeza el tablero
presupuestal encadena tres fuentes distintas** —apropiación de la Matriz,
comprometido del registro interno de contratos, girado de SECOP—. Leída de
corrido dice que la Alcaldía comprometió el **11,0 %** y giró el **1,3 %** de lo
que apropió, cuando su propia Matriz dice **59,7 %** y **26,9 %**.

Ninguna de las cifras está mal. Están puestas una al lado de la otra como si
fueran la misma cadena, y no lo son.

## Ya lo hicimos una vez, y funcionó

**Esto mismo pasaba con el avance físico de metas.** El proyecto 2706 salía
«Ejecutada» en una pantalla y «Crítico» en otra: no era un dato malo, eran
**siete lugares del sistema calculando el avance cada uno por su lado**, todos
sobre un registro interno que cubría 6 de 77 indicadores.

Se cerró con **una sola implementación**. El resultado, medido:

| Cobertura del avance físico | Antes | Después |
|---|---:|---:|
| Áreas con avance calculable | 3 de 17 | **17 de 17** |
| Sectores | 3 de 19 | **13 de 13** |
| Indicadores | 6 de 77 | **75 de 77** |
| Proyectos | pocos | **30 de 30** |

Y el muro de áreas pasó de **14 tarjetas acusando** al área de «no haber
reportado ningún avance» a **cero**. El pendiente no desapareció: cambió de
sentido. Ahora dice que lo que falta es registrar aquí lo que la Alcaldía ya
reportó, para poder seguirlo entre cortes.

El cálculo interno no se botó: viaja al lado como contraste. Donde existen las
dos cifras, difieren siempre —en Cultura, 0,7 % contra 109 %— y esa diferencia es
conciliación pendiente, no un error.

**Las siete implementaciones del avance físico ya están cerradas. Las de la plata
son las siguientes.**

## Las fases

### Fase 1 · Una sola forma de decir cuánta plata tiene esto

**Qué cambia para el usuario:** los cuatro recuadros que encabezan el tablero
salen de la misma fuente y de la misma fecha de corte. Las otras fuentes siguen
apareciendo, pero **al lado y rotuladas como contraste**, no mezcladas dentro del
mismo número. El porcentaje de ejecución que se lee arriba cierra con las cifras
que tiene debajo.

**Alcance:** las doce pantallas donde hoy se mezclan fuentes dentro del mismo
recuadro. Están identificadas una por una, con la cobertura de cada fuente
medida.

### Fase 2 · Ninguna pantalla dice $0 cuando lo que pasa es que no tiene con qué medir

**Qué cambia para el usuario:** las **12 áreas que hoy abren su panel y leen
"Contratado $0"** pasan a ver su plata real de la Matriz, con la etiqueta de
dónde viene. Donde de verdad no haya fuente, la pantalla lo dice —«sin dato» y
por qué— en vez de mostrar un cero que se lee como «acá no hay nada».

La regla ya está aplicada al avance de metas y a las anotaciones de SECOP. Falta
aplicarla a la plata.

### Fase 3 · El año que se elige manda en toda la pantalla

**Qué cambia para el usuario:** hoy, al pulsar «2026» en el tablero, **solo uno
de los cuatro recuadros reacciona**; los otros tres siguen mostrando todas las
vigencias juntas, con un subtítulo que contradice al año seleccionado. Después,
los cuatro responden al año elegido, y si un año no tiene dato lo declara vacío
en vez de mostrar 0 %.

### Fase 4 · Un solo árbol del Plan

**Qué cambia para el usuario:** hoy **26 de 31 proyectos** dicen «Sin programa
asociado» en su ficha —y dos de los cinco que sí muestran algo, muestran el
programa equivocado—. El usuario navega Objetivo → Programa → Proyecto, abre el
proyecto y la ficha le dice que no pertenece a ningún programa.

Además, la fila de cada programa dice «N metas» cuando en realidad está contando
proyectos: **la pantalla suma 30 donde el gráfico de la misma página dice 76**.

Después: una sola jerarquía, la del catálogo oficial del Plan, y el mismo número
en todas partes.

### Fase 5 · Cada cifra dice de dónde viene, de cuándo es y cuánto alcanza a ver

**Qué cambia para el usuario:** toda cifra publicada lleva su fuente, su fecha de
corte y —cuando aplica— su cobertura. El modelo ya está en producción en la
anotación del proyecto 2780, que ahora dice primero «SECOP alcanza a ver el 9,1 %
de lo comprometido» y solo después el porcentaje.

Es la fase más barata y la que más malentendidos evita.

---

# 11. Qué necesitamos, y de quién

## De la Secretaría Distrital de Planeación — 🔴 escalado, sin resolver

**Que vuelva a publicar Datos Abiertos del PDL.** La última lectura útil fue el
**23 de julio de 2026**, y el archivo publicado no se mueve desde el **18 de
febrero de 2026**. Ya se escaló y sigue igual.

**Consecuencia directa:** dos proyectos reales de Kennedy —**2556 Mujeres sin
Barreras** y **2643 Ecomanos en Acción**— no tienen par en la publicación oficial
del Distrito. No es que estén mal cargados: es que la fuente se quedó atrás. Se
resuelven solos el día que Planeación se ponga al día.

Mientras tanto, la Matriz manual es el único canal por el que entran las
reprogramaciones de 2026.

## De la Alcaldía Local (Planeación local)

1. **La Matriz con las vigencias 2027 y 2028 apropiadas**, cuando el POAI las
   apropie. Hoy vienen vacías, y por eso el tablero rotula «2025-2026» y no
   «2025-2028».
2. **Decisión sobre 10 indicadores reprogramados.** La Alcaldía cambió la
   magnitud de 2026 y el sistema tiene otra. No se toca ninguno hasta que se
   decidan uno por uno.
3. **El área responsable del proyecto 2740** (comunidades étnicas).
4. **Una respuesta sobre las obligaciones por pagar** — ver preguntas para
   Camilo.

## De la Secretaría de Hacienda

**El corte del CRP con periodicidad conocida.** Hoy tenemos el del 7 de
septiembre. No hay acuerdo sobre cada cuánto llega el siguiente, y el sistema
está construido para recibirlo mensualmente.

## De las áreas de la Alcaldía

**Que carguen sus contratos.** Hoy hay 25 contratos cargados en 3 de 18 áreas,
mientras SECOP conoce 3.123 y BogData 2.630 registros presupuestales. Esa
atribución —qué contrato paga qué actividad de qué meta— **no la trae ninguna
fuente externa**: es el eslabón que conecta la plata con el Plan, y solo lo puede
poner quien administra el contrato.

**Y que usen los módulos de captura en campo.** Entregas de insumos, captura de
Cultura y caracterizaciones están construidos, probados de punta a punta y en
cero.

## De supervisión de contratos

**Que se diligencie el valor pagado en SECOP.** 152 contratos de 2025 en
adelante, por $70.204 millones, están reportados en cero. Mientras eso siga así,
esa fuente no sirve para calificar a nadie — y por eso el sistema dejó de usarla
para hacerlo.

---

# 12. Lo que ya funciona bien

No todo está por hacer. Esto está cerrado y verificado:

**Cobertura del Plan completa.** Los **28 de 28 proyectos** del PDL están en el
sistema, con sus 78 metas. Antes de septiembre eran 12 de 28.

**El avance físico tiene una sola implementación**, con la Matriz como base, y
cubre 17 de 17 áreas, 13 de 13 sectores, 75 de 77 indicadores y 30 de 30
proyectos. Ninguna pantalla contradice a otra sobre el avance de una meta.

**El libro presupuestal completo está cargado y cuadra.** 2.630 registros,
$226.744.982.139, conciliados contra los totales del propio archivo de Hacienda.

**El corte del cuatrienio está bien hecho.** Se cortó por año del compromiso y no
por la marca de «obligación por pagar», y eso preserva **$93.209.948.593** de
ejecución legítima de 2025 que el criterio fácil habría botado.

**SECOP está al día**, sincronizado el mismo día de este informe.

**La regla de no calificar sin fuente está aplicada** en todo el sistema: al
avance de metas, a las anotaciones de contraste y al semáforo. Ninguna área queda
en rojo por un campo que otro no diligenció.

**Los rótulos de la pantalla son los del Excel de la Matriz.** La palabra
«Programado» nombraba cuatro cosas distintas —la meta aspiracional del PDL, una
magnitud en unidades, el plan de pagos de un contrato y el respaldo de un CDP— y
salió de la interfaz. Cada una se llama ahora como la llama su propia fuente, para
que un área reconozca su cifra sin tener que traducirla.

**Las cargas son auditables y reversibles en sentido práctico.** Secas por
defecto, firmadas por quien las hace, idempotentes, con historial. Y quien no ve
toda la localidad no puede reemplazar el libro de toda: el permiso de carga
depende del alcance territorial, no de un módulo.

**innovaK captura lo que ninguna fuente externa trae:** 7.121 personas, 5.598
beneficiarios, 2.545 participantes, 174 entregas de beca y 24 encuestas de
percepción ciudadana, todo por formulario público con código QR y firma.

---

# 13. Preguntas para Camilo

1. **¿Cuál es la cifra oficial de «comprometido» de la localidad?** La Matriz
   dice $224.853.665.855 y BogData $184.839.187.185. Las dos son legítimas y
   miden actos distintos; la diferencia es de **$40.014 millones**. Necesitamos
   saber cuál se publica cuando alguien de afuera pregunta.

2. **¿La Matriz va a reflejar en alguna vigencia los giros hechos como obligación
   por pagar de la vigencia anterior, o quedan por definición fuera de su
   reporte?** Es el caso del proyecto 2790: mientras queden fuera, su semáforo de
   plata seguirá diciendo 0,6 % con razón, y el contraste con SECOP seguirá
   apareciendo.

3. **¿Con quién en Planeación Distrital se destraba la publicación de Datos
   Abiertos?** Está escalado y sin respuesta. Es la fuente que, si volviera,
   quitaría la dependencia de una carga manual.

4. **¿Cada cuánto y por qué canal llega el corte del CRP de Hacienda?** Hoy es el
   del 7 de septiembre y no hay periodicidad pactada.

5. **¿Se le puede pedir a supervisión que diligencie el valor pagado de los 152
   contratos que SECOP reporta en cero?** Son $70.204 millones contratados sin
   información de pago.

6. **¿Quién decide los 10 indicadores reprogramados** y **el área responsable del
   proyecto 2740** (comunidades étnicas)? Ambas cosas están frenadas esperando
   una decisión, no un desarrollo.

7. **¿Las áreas van a cargar sus contratos en innovaK?** Es el único eslabón que
   conecta un contrato con una meta del Plan, y hoy existe en 3 de 18 áreas.
   Si la respuesta es no, hay que decidir con qué se reemplaza esa atribución.

---

*Documento preparado el 10 de septiembre de 2026. Las cifras están medidas
contra los datos reales del sistema en esa fecha; los cortes de cada fuente están
indicados en su sección.*

# Mapa de fuentes: Matriz, SEGPLAN, SECOP y BogData

**2026-09-10.** Qué aporta cada fuente, quién manda para cada dato y por qué
dos cifras con el mismo nombre no son comparables hasta demostrar que miden lo
mismo, sobre el mismo universo y a la misma fecha.

Nace de la regla de Alex —*«la base de todo es la Matriz; todo debe estar
coherente con eso»*— y de las cinco discrepancias SECOP contra Matriz, que al
medirlas resultaron ser **tres cosas distintas y solo una discrepancia real**.

---

## 1. La tabla

| Dato | Fuente primaria | Fuente de contraste | Uso en innovaK |
|---|---|---|---|
| **Avance físico de metas** | Matriz (`cumplimiento_pct`, `magnitud_ejecutada`, `magnitud_contratada`) | El cálculo interno de `presu_avance_ind_periodo`, que viaja como `pct_interno` | `avance_matriz.py`, **única implementación**. Muro de áreas, expediente, sectores, top sectores, donut de metas, KPI del 360°, catálogo de metas |
| **Alerta de cumplimiento** (Crítico / En ejecución / Ejecutada / Desierta / Sin magnitud contratada) | Matriz, hoja «Alertas» — se importa el valor YA resuelto, no se recalcula | — | Filtro de proyectos por estado, semáforo de metas |
| **Apropiación POAI** | Matriz (`apropiacion_poai` por meta × vigencia) | `proyectado_pdl` de la misma Matriz, que es la meta aspiracional | Encabeza el cockpit. La cadena es Apropiación → Comprometido → Girado |
| **Proyectado PDL del cuatrienio** | Matriz (`proyectado_pdl`) | Espejo SEGPLAN (`total_programado`) | Contraste, nunca base de un % de ejecución |
| **Comprometido y girado por meta** | Matriz (`comprometido`, `girado` por vigencia) | BogData para el comprometido; SECOP para el pago del contrato | Semáforo de plata del proyecto y del área |
| **Comprometido presupuestal de la localidad** | **BogData / CRP** (`valor_neto`) | La Matriz, agregada por proyecto | $184.839 M del PDL 2025-2028. Corte por **año del compromiso** |
| **Girado presupuestal** | **BogData / CRP** (`autorizacion_giro`) | SECOP (`valor_pagado`), que mide otra cosa | Estado de cuenta, resumen por rubro |
| **Contratos: número, objeto, valor, fechas, estado, contratista** | **SECOP II** (espejo `secop_contrato`) | `contrato` de innovaK, cargado a mano por las áreas | Expediente del contrato, conciliación, panel de área |
| **Plan de pagos del contrato** | **SECOP II** (`secop_plan_pago`) | — | Fechas y estados de pago del expediente |
| **Catálogo del Plan** (objetivos, programas, metas, proyectos) | Matriz | Espejo SEGPLAN, con las metas sin par marcadas | Listas oficiales, jerarquía, `plan_matriz.py` |
| **Beneficiarios, eventos, entregas** | innovaK | — | Captura propia; ninguna fuente externa la trae |

**Lo que NINGUNA fuente externa aporta hoy:** la ejecución física por evento
—eso lo captura innovaK— y la atribución de un CRP a una meta concreta. El CRP
llega hasta el proyecto (por rubro o por PEP) y no baja a la meta.

---

## 2. Lo que cada fuente NO es

### La Matriz no trae contratos

Trae plata y magnitudes **por meta y vigencia**, no por contrato. Su
`comprometido` es lo que la ALK reporta comprometido contra la apropiación de
esa vigencia; no se puede cruzar con un número de contrato porque la Matriz no
lo tiene.

### SECOP no mide ejecución del PDL

Mide la **realidad contractual**: qué se firmó, con quién, por cuánto y en qué
estado. Su `valor_pagado` es el **pago acumulado del contrato**, sin dimensión
de vigencia: un contrato firmado en 2025 y pagado en 2026 lo trae completo, y
la Matriz lo reparte entre las dos vigencias.

Y tiene un hueco que hay que conocer antes de usarlo para calificar a nadie:

> **SECOP dice 0 también cuando no sabe.** `valor_pagado` no llega nunca en
> NULL —3.123 de 3.123 filas del espejo lo traen—, así que «no se giró» y
> «nadie cargó el pago» son el mismo cero. Medido: **152 contratos de 2025 en
> adelante, por $70.204 M de valor contratado, están en cero**, y entre ellos
> el CIA-773-2025, que BogData reporta con **$8.818.769.452 girados**.

Por eso, desde hoy, un cero de SECOP no califica ni contradice: es ausencia de
fuente, y la regla de la casa vale igual para el espejo que para la Matriz.

### BogData no trae la meta

Es la fuente presupuestal: CRP, valor, anulaciones, giro autorizado, tercero,
rubro, PEP, fechas y año del compromiso. Llega al **proyecto** (por el rubro o
por el PEP, y como respaldo por el contrato cuando ese contrato está en
innovaK) y no baja a la meta. Su universo es el **estado de cuenta completo**,
que incluye compromisos de 2013 en adelante; el módulo publica solo el tramo
del PDL 2025-2028.

---

## 3. Las cinco discrepancias, medidas

No eran cinco decisiones. Eran tres cosas.

| Proyecto | Matriz | SECOP | Qué resultó ser |
|---|---:|---:|---|
| 2377 · Kennedy Germinando Futuros | 78,9 % | 0,0 % | SECOP en cero sin fuente |
| 2574 · Kennedy Crecimiento y Conexión | 37,1 % | 0,0 % | SECOP en cero sin fuente |
| 2706 · Kennedy en Alianza por la Seguridad | 40,0 % | 0,0 % | SECOP en cero sin fuente |
| 2780 · Kennedy Proyecta Talento | 28,4 % | 99,2 % | Cobertura: dos universos |
| 2790 · Kennedy Mi Parque Mi Espacio | 0,6 % | 76,4 % | **Vigencia: obligaciones por pagar** |

### Los tres de cero — regla aplicada

El caso que lo prueba: el CIA-773-2025 del proyecto 2377 aparece en SECOP con
`valor_pagado = 0.00` y en BogData con **$8.818.769.452** de giro autorizado.
El cero no era una medición.

`_semaforo` ya no anota cuando SECOP no reporta ni un giro, y —del otro lado—
tampoco califica con ese cero cuando no hay Matriz: devuelve `incompleto` con
base `secop_sin_giros`. Sin eso, un área quedaba en rojo por un campo que su
contratista no diligenció.

### 2780 — es cobertura, no desacuerdo

| | |
|---|---:|
| Comprometido según la Matriz | $7.794.984.904 |
| Contratos del proyecto en innovaK (los 15 cruzan con SECOP) | $713.221.534 |
| **Cobertura** | **9,1 %** |
| Pagado según SECOP sobre esa parte | $707.721.534 (99,2 %) |

**Numerador y denominador, confirmados contra los datos:** el numerador es la
suma de `contrato.valor` de los contratos del proyecto —que es exactamente la
base sobre la que se calcula el porcentaje de SECOP— y el denominador es el
comprometido de la Matriz para ese proyecto. Los 15 contratos son de prestación
de servicios por $33 M a $63 M cada uno; el grueso de los $7.795 M del proyecto
no está cargado como contrato en innovaK.

Las dos cifras eran ciertas. «99,2 % contra 28,4 %» leído de frente sugería que
una de las dos mentía.

### 2790 — la única diferencia real, y no es un error de nadie

Conciliación contrato por contrato:

| Contrato | Valor | SECOP `valor_pagado` | BogData: CRP y giro |
|---|---:|---:|---|
| COP-816-2025 (Modificado) | $3.583.922.940 | $3.220.703.509 | CRP 866 → $2.751.497.273 girados · CRP 1687 → $653.229.520 |
| CON-993-2025 (Suspendido) | $629.818.832 | $0 | CRP 871 → $125.963.766 girados |

Los dos contratos cruzan con SECOP (2 de 2) y cubren el 84,1 % del comprometido
de la Matriz, así que **no es un problema de cobertura**. Lo que separa las
cifras es la vigencia:

- Los tres CRP son de **ejercicio 2026**, con **año de compromiso 2025**, rubro
  **O230689 «Obligaciones por pagar Inversión vigencia anterior»** y PEP
  genérico `PO/0008/0001/OBLI_INV_VI`. Su `proyecto_id` está en NULL porque ese
  rubro no identifica proyecto.
- La Matriz reporta el girado **contra la apropiación de cada vigencia**: para
  las metas 27901 y 27902 son $35.700 en 2025 y $32.045.200 en 2026.
- SECOP reporta el **pago acumulado del contrato**, sin vigencia.

O sea: el dinero se giró, y se giró como obligación por pagar de la vigencia
anterior. Las tres fuentes son consistentes una vez homologada la vigencia.

**Y se corrige solo.** El respaldo por contrato que ya corre en la carga
atribuye esos tres CRP al proyecto 2790 en el corte de octubre: 3 filas,
$4.213.741.772 de valor neto y $3.530.690.559 de giro. (El proyecto 2780 recibe
otras 13 filas por $62.978.333.)

**Qué falta antes de escribirle al área.** Nada por el lado del dato: la
conciliación cierra. Lo que sí conviene preguntar, y no es una discrepancia, es
si la Matriz va a reflejar esos giros de obligaciones por pagar en alguna
vigencia o si por definición quedan fuera de su reporte — porque mientras
queden fuera, el semáforo de plata de 2790 seguirá diciendo 0,6 % con razón, y
la anotación de SECOP seguirá saliendo.

---

## 4. Quién manda, en una línea

- **Metas, magnitudes y avance físico:** la Matriz. Sin excepción, y con una
  sola implementación.
- **Plata comprometida y girada de la localidad:** BogData.
- **Contratos:** SECOP para el hecho contractual, innovaK para la atribución a
  proyecto y meta.
- **Cuando dos fuentes discrepan:** primero se homologa métrica, universo,
  vigencia y fecha de corte. Solo lo que sobreviva a eso es una discrepancia.

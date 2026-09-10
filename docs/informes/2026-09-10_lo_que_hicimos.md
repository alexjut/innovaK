# 10 de septiembre de 2026 · qué se hizo, dónde quedó y qué falta

Índice de la jornada. Todo lo de acá está en producción salvo lo que diga otra
cosa, y cada cifra está medida contra la base ese día.

Rama de trabajo: `fix/crp-endurecimiento-corte-octubre`.

---

## 1. En una frase

El sistema no tenía **una** forma de responder «cuánta plata tiene esto»:
convivían seis registros y cada recuadro eligió el suyo sin decir cuál. Se
cerró con un módulo único, igual que se había cerrado antes el avance físico.
De paso se endureció la carga del CRP antes del corte de octubre, se escribieron
los dos informes que pidió Alex, y se desdobló la meta agrupada de posmedia.

---

## 2. Lo que se entregó, en orden

| # | Qué | Commit |
|---|---|---|
| 1 | Las dos llaves naturales del CRP, el corte que mentía y el cero de SECOP | `ecdce30` |
| 2 | Informe de fuentes para Camilo + informe de falencias y plan | `ac1790d` |
| 3 | **Fase 1** · `plata_matriz`, única implementación, con el contraste adentro | `2de2294` |
| 4 | **Fase 3** · las doce áreas dejan de ver «$0» | `22fecbd` |
| 5 | **Fase 2** · el tablero encabeza con la Matriz y el año lo mueve entero | `87fb92e` |
| 6 | **Fase 4** · Objetivos deja de contradecirse consigo mismo | `de58d55` |
| 7 | **Fase 5** · Festivales deja de contradecir a su propio expediente | `4218f9a` |
| 8 | **Fase 6** · el programa del proyecto sale del Plan | `d762fbb` |
| 9 | **Fase 7** · el rótulo deja de nombrar una cosa y contar otra | `34fb1f7` |
| 10 | La meta agrupada de posmedia, desdoblada | `35ed791` |
| 11 | La sección pasa a llamarse **Plan de Desarrollo** y su hub se ordena por preguntas | `832988e` |
| 12 | La ruta pasa a `/app/plan`, con la vieja viva como alias | `b3c53cd` |

### Lo que cambió en pantalla

| | antes | ahora |
|---|---:|---:|
| Tablero · comprometido sobre lo apropiado | 11,0 % | **59,7 %** |
| Tablero · girado | 1,3 % | **26,9 %** |
| Áreas con cifra de plata en su panel | 3 de 18 | **16** |
| Objetivos · presupuesto | $667.578 M | **$376.458 M** |
| Objetivos · ejecución financiera | 29,7 % | **59,7 %** |
| Festivales · proyecto 2780 apropiado | $0 | **$12.392.980.000** |
| Fichas de proyecto con su programa | 5 de 31 | **30 de 31** |
| Metas que suma la página de Objetivos | 30 | **78** |
| Metas ejecutadas | 21 | **23** |
| Secciones del hub de la sección | 3, por proceso interno | **4, por pregunta** |

---

## 3. Documentos escritos hoy

| Documento | Para quién | Qué dice |
|---|---|---|
| [`diagnosticos/mapa_fuentes_matriz_secop_bogdata.md`](../diagnosticos/mapa_fuentes_matriz_secop_bogdata.md) | equipo | Qué aporta cada fuente, qué NO aporta, y quién manda para cada dato |
| [`informes/2026-09-10_fuentes_de_informacion.md`](./2026-09-10_fuentes_de_informacion.md) (+ PDF) | **Camilo** | Lo mismo en lenguaje de gestión, con los tres casos donde dos cifras del mismo nombre no son la misma cifra |
| [`informes/2026-09-10_falencias_y_plan_dashboard.md`](./2026-09-10_falencias_y_plan_dashboard.md) (+ PDF) | equipo | Dónde falla cada pantalla, qué se arregla programando y qué no, y el plan por fases |
| `ESTADO.md` §3.13, §3.14, §3.15 | equipo | El estado por frente |
| `CLAUDE.md` §11 | la próxima sesión | Las reglas que quedaron fijadas |

Los dos PDF están al lado de sus `.md` y se regeneran del texto.

---

## 4. Las reglas que quedaron fijadas

Están escritas en el código, no solo acá, y conviene no volver a discutirlas.

**En `plata_matriz`** (y son distintas de las de `avance_matriz`, a propósito):

1. **La plata SE SUMA.** El cumplimiento se promedia, porque motos, sedes y
   personas no hacen un denominador. La plata no tiene ese problema.
2. **`None` nunca es `0`.** 2027 y 2028 no tienen ni una fila con valor, así
   que elegir 2027 dice «sin dato», no «$0».
3. **La vigencia filtra; sin ella, se acumula.**
4. **Ninguna cifra viaja sin su cobertura.**

**Del contraste:** lo produce el mismo módulo que la cifra oficial. Un contraste
que cada pantalla arma por su cuenta vuelve a ser un sexto libro en seis meses.

**De los rótulos:** la unidad y la fuente se escriben donde se calcula la cifra,
no donde se imprime. El frontend armaba siempre «N de M contratos», y al
cambiar la fuente eso puso «78 de 78 contratos» debajo de un número de metas.

---

## 5. Las cosas que solo aparecieron al medir

- **BogData no atribuye a un proyecto toda su plata.** Atribuye
  $86.603.918.854 de los $184.839.187.185 del Plan: las obligaciones por pagar
  de vigencias anteriores traen un rubro que no identifica proyecto
  ($92.160.547.878 en 1.056 filas). Sumando las filas visibles, la diferencia
  contra la Matriz salía $138.249 M en vez de los $40.014 M reales — y ese
  exceso no es un desacuerdo.
- **El selector de año nunca movió nada, y no por falta de plomería.** El bucle
  de contratos desempaqueta cada fila en una variable llamada `vigencia`, que
  pisaba el parámetro de la función. Al terminar valía la del último contrato.
  Sin un solo error a la vista.
- **SECOP dice 0 también cuando no sabe.** 152 contratos de 2025 en adelante,
  por $70.204 M, con pago en cero — entre ellos uno que BogData reporta con
  $8.818.769.452 girados.
- **El contenedor no recarga siempre los módulos.** Tras cambiar una vista,
  `manage.py check` y los tests pasan con el código nuevo mientras el proceso
  sirve el viejo. Si una medición sobre HTTP no coincide con la del shell,
  reinicia antes de buscar el error en otra parte.

---

## 6. Decisiones tomadas hoy

| Decisión | Quién | Qué implicó |
|---|---|---|
| Una sola fuente para los indicadores; las demás al lado como contraste | Alex | Es la forma de todo el trabajo del día |
| El comprometido de la Matriz encabeza; el de BogData baja a contraste | Alex | El tablero pasó a $224.854 M |
| Los rótulos pueden cambiar con la fuente | Alex | «Asignado» → «Apropiado», «Ejecutado» → «Comprometido» |
| Una pestaña nueva para el contraste de fuentes | Alex | Endpoints listos; falta la pantalla |
| Crear las dos metas de posmedia y retirar la agrupada | Alex | Ver §7 |

---

## 7. La meta agrupada de posmedia — desdoblada

La Matriz reporta 78 metas. Dos —**23771** acceso y **23772** permanencia, las
dos del proyecto 2377— no existían como fila propia: las cubría una sola meta
agrupada, la 8, con los dos indicadores adentro. Como todo el catálogo se
llavea por el código SEGPLAN y la agrupada no tenía código, esas dos se caían
de cada pantalla que cuenta metas — y en la peor dirección, porque las dos
están **Ejecutadas al 100 %**.

Se desdobló con `desdoblar_meta_agrupada`, seco por defecto y firmado. Los dos
indicadores se **movieron**, no se recrearon: mover conserva su id y con él los
avances y las vinculaciones a actividades que ya colgaban de ellos.

    metas con código SEGPLAN     76  ->  78   (las 78 de la Matriz, sin huérfanas)
    metas ejecutadas             21  ->  23
    perspectiva «potencial»       5  ->   7
    la página de Objetivos suma  30  ->  78

Y la distribución por perspectiva quedó idéntica a la de la Matriz:
16 · 25 · 7 · 16 · 14.

**Una cosa quedó anotada al pasar:** la fila vieja `presu_indicador` 4
(«becas») colgaba de la meta agrupada y su vínculo es obligatorio, así que se
movió a la meta 23771 en vez de borrarla o dejarla huérfana. Esa tabla tiene 3
filas en toda la base y **ningún código la lee**. Si el área prefiere otra
meta, moverla es un UPDATE de una línea.

---

## 7 bis. El nombre y el orden

«Presupuesto» prometía solo plata cuando adentro vive el Plan entero. El módulo
se llama ahora **Plan de Desarrollo**, que es el nombre del instrumento y el que
el código y la Matriz ya usaban.

Dos de los nombres que se barajaron no servían, y conviene dejarlo escrito para
que no vuelvan a proponerse: **POT ya está tomado** —es el Plan de Ordenamiento
Territorial, y este proyecto lo usa: las nueve UPL de Kennedy salen del POT
2022— y **POP no existe** en el vocabulario de planeación de Bogotá, además de
quedar a una letra de POAI, que sí existe y ya vive en el sistema.

**La ruta pasó a `/app/plan`**, y la vieja quedó viva **como alias, no como
redirección**: Angular no sabe redirigir `presupuesto/**` conservando el resto
del camino, así que una redirección solo salvaría `/app/presupuesto` y dejaría
rotos los enlaces profundos, que son los que la gente tiene guardados. El mismo
módulo se monta en las dos rutas y no se rompe ninguno.

**La trampa que había que esquivar:** la API de Django vive también bajo
`/presupuesto/` —47 llamadas del frontend—. Un renombrado a ciegas las rompe
todas, y el síntoma son pantallas vacías sin error. El reemplazo excluyó `/api`
y quedó comprobado: cero rotas.

El hub pasó de tres secciones que nombraban el proceso interno a cuatro que
responden una pregunta: **El Plan** (qué se prometió), **La plata** (cuánto se
apropió, comprometió y giró), **La ejecución** (qué se ha hecho) y **Las
fuentes** (de dónde sale cada cifra). Las 17 tarjetas se conservan íntegras.

Queda pendiente el rótulo de la tarjeta del menú principal, que vive en un
archivo que otra persona tiene modificado. Es un cambio de una línea.

---

## 8. Qué falta

| Qué | De quién depende |
|---|---|
| La pestaña de **Fuentes**: los dos endpoints están, falta la pantalla. Va en la sección «Las fuentes» | desarrollo |
| Si la pantalla de **Programas** todavía tiene razón de ser (CRUD sobre una tabla vieja de 7 filas, 3 llamadas «prueba») | decisión de Alex |
| El proyecto de código **7895**, sin metas en el catálogo: ¿basura o mal codificado? | decisión de Alex |
| La meta **10** «camino seguro las mujeres», sin código ni proyecto ni sector | decisión de Alex |
| Conciliar el comprometido: la Matriz dice $224.854 M y BogData $184.839 M, y son **$40.014 M** sin explicar | Alcaldía / Hacienda |
| El espejo de **Planeación**, parado desde el 23 de julio | Planeación Distrital |
| Los **152 contratos** que SECOP reporta con pago en cero, por $70.204 M | supervisión |
| N+1 preexistente: la tabla de proyectos abre 31 consultas por página | desarrollo, cuando se quiera |

---

## 9. Cómo quedó verificado

- **1622 pruebas OK** (7 omitidas) en cada entrega.
- Cada publicación con `cd frontend && npm run build -- --base-href=/app/`, con
  el base href comprobado en el `index.html` y los assets en 200.
- La carga del CRP probada contra el archivo real en transacción revertida.
- El desdoble de la meta ensayado entero en transacción revertida antes de
  escribir, con backup del día a las 02:00 verificado.

# Banco de Iniciativas II — 2 decisiones abiertas, con nuestra recomendación

**Fecha:** 10 de agosto de 2026
**De:** Equipo de Innovación — innovaK · Alcaldía Local de Kennedy
**Para:** Subdirección de Deportes / Recreación
**Asunto:** Cerrar los 2 supuestos que quedan de la Matriz Oficial

> **Actualizado el 2026-08-10** contra el Documento Guía: la decisión del
> arraigo (§4.2) quedó cerrada ahí y ya no se pregunta. Reemplaza al documento
> del 29 de julio (*Decisiones pendientes de Deportes*). Aquel preguntaba sin proponer; este trae **una recomendación por
> decisión**, y explica qué está corriendo hoy mientras ustedes responden.
> Respondan sobre este y descarten el anterior.

---

## 0. Qué cambió desde el 29 de julio

Aquel documento decía que el motor calculaba **2 de 13 criterios** y que la
Matriz Oficial estaba *"sembrada en el sistema pero no calificando"*. Las dos
cosas ya se cerraron:

| | 29 de julio | Hoy |
|---|---|---|
| Criterios programados | 2 de 13 | **12 de 12** — los 100 puntos completos |
| Quién califica | el modelo viejo (65 auto + 35 comité + 5 bono = 105) | **la Matriz Oficial** |
| Ranking que ve el usuario | el del modelo viejo | el del Documento Maestro |
| Comité de evaluación | todavía en pantalla | retirado (el documento lo elimina) |

**Lo que falta no es programación: son estas decisiones.** El motor las tiene
como parámetros, así que ratificar cualquiera de ellas es cambiar un valor —
no reprogramar ni volver a probar la matriz.

---

## 1. Arraigo territorial (§4.2) — CERRADO, no hace falta que respondan

El Documento Guía resolvió esta pregunta por una **tercera vía** que no era
ninguna de las dos que estaban sobre la mesa. Ya no se trata de si los 4.0
puntos son para los espacios barriales o para los dotacionales: **el tipo de
espacio dejó de puntuar en la caracterización** —el documento lo dice
explícito— y los 4.0 pasaron a la **vulnerabilidad socioeconómica del entorno
real de práctica**:

| Estrato del entorno | Puntos |
|---|---|
| 1 y 2 | 4.0 |
| 3 | 2.0 |
| 4 | 0.0 |

El tipo de espacio se sigue capturando y **sigue puntuando en el criterio 11**
(§7.9.1, hasta 9.0 puntos), que evalúa la propuesta y no la organización. Con
eso la contradicción entre la página 11 y la página 22 dejó de existir.

**Una salvedad, y es la única de este punto.** El Documento Guía lista un
**Estrato 0** con 4.0 puntos y **no se implementó**, por decisión de la Alcaldía
del 10 de agosto. Dos razones que apuntan al mismo lado:

1. Los cuatro controles de estrato de la base de datos admiten 1 a 4. Un 0 no
   haría que la propuesta puntuara mal: haría que **la radicación completa
   fuera rechazada**.
2. El soporte que el propio documento exige para el estrato 0 —un recibo de
   servicio público que lo certifique— **no existe**: el estrato 0 es
   precisamente el predio sin estratificar, el que no tiene recibo.

Los estratos 1 y 2 conservan los 4.0 puntos, así que ninguna organización en
territorio vulnerable pierde puntaje por esta decisión.

---

## 2. Tope presupuestal (§8.5): por puntaje, no por posición

**El problema.** El documento amarra el tope máximo financiable al **puesto en
el ranking**: 1–31 → \$17 M, 32–62 → \$14 M, 63–93 → \$11 M. Eso **no se puede
programar**, y no por una limitación técnica:

El tope se tiene que evaluar **cuando el proponente diligencia el formulario**,
para poder bloquearlo si pide de más. En ese momento su posición **todavía no
existe**: depende de cuántos se postulen después y con qué puntaje. Un mismo
formulario cambiaría de tope cada vez que entra otro proponente, y el bloqueo de
radicación sería distinto según la hora en que alguien abra la página.

**Nuestra recomendación: topes por banda de puntaje absoluto.**

| Puntaje obtenido | Tope financiable | Equivale a |
|---|---|---|
| 75 a 100 | \$17.000.000 | el tramo de las posiciones 1–31 |
| 60 a 74,9 | \$14.000.000 | el tramo de las posiciones 32–62 |
| 0 a 59,9 | \$11.000.000 | el tramo de las posiciones 63–93 |

**Por qué.** Conserva íntegra la intención del documento —más mérito, más
tope— pero lo vuelve una función del puntaje propio: se evalúa en tiempo real,
da el mismo resultado siempre y es explicable ante cualquier reclamo.

**Lo único que decide Deportes son los dos cortes (75 y 60).** Los pusimos donde
caerían aproximadamente los tercios si la distribución de puntajes fuera pareja,
pero es una estimación nuestra: **ustedes pueden moverlos**, y solo se toca ese
número.

**Corriendo hoy:** las bandas 75 / 60 / 0 de la tabla.
**Sin esta decisión, §8.5 no se puede activar.**

---

## 3. Qué pasa si llegan menos de 93 postulaciones

**El problema.** El documento fija 93 ganadoras y amarra los topes a tramos de
31, pero no dice qué hacer si la convocatoria cierra con menos. Sin regla
escrita, el sistema tendría que improvisar justo donde se reparte la plata.

**Nuestra recomendación: se adjudican todas las que radicaron válidamente.**

**Por qué.** Poner un puntaje mínimo dejaría recursos sin ejecutar sin que el
documento lo autorice, y esa es una decisión política que no nos corresponde
tomar por omisión. Si Deportes **sí** quiere un piso de calidad, hay que
escribirlo con su número (el sistema ya lo soporta; hoy está preparado en 60
puntos pero **desactivado**).

**Corriendo hoy:** se adjudican todas.

---

## 4. El desempate: no es decisión suya, pero deben saberlo

**El documento no dice cómo desempatar.** Solo ordena por
`puntaje_total DESC`. Con 100 puntos repartidos en escalones de 0,5 los empates
son prácticamente seguros, y sin una regla el orden lo terminaría decidiendo el
motor de la base de datos — es decir, al azar, y sin forma de defenderlo.

**Lo resolvimos así, y se los informamos para que lo ratifiquen o lo cambien:**

1. Gana el mayor **puntaje total**.
2. Si empatan, gana el mayor **Bloque 2** (la propuesta técnica, que es lo que
   el documento pesa 70 de 100).
3. Si siguen empatadas, gana **la que radicó primero**; y si dos radicaciones
   comparten el mismo instante, el número de radicación menor.

---

## 5. Advertencia sobre las 24 del piloto de mayo

Las 24 organizaciones del piloto (evento 62, mayo de 2026) **se diligenciaron
con el formulario anterior**. Medido el 10 de agosto: ninguna de las 24 trae un
solo campo de la sección 7.

**Consecuencia:** los **70 puntos del Bloque 2 les son inalcanzables**. Su techo
real es 30, no 100, y hoy puntúan entre 2 y 12. **Eso no significa que sean
malas propuestas: significa que nunca se les hicieron esas preguntas.**

El sistema las marca explícitamente como «formulario anterior» en la pantalla y
en el ranking, para que nadie las lea como comparables. **No se les puede armar
un ranking de adjudicación contra postulaciones nuevas.**

**Lo que hay que decidir con ustedes** (no lo decidimos nosotros): si esas 24
organizaciones **vuelven a postularse** con el formulario nuevo, o si el piloto
se cierra como ejercicio de prueba y no entra a la convocatoria.

---

## 6. Lo que necesitamos de ustedes

Basta con responder este correo con cuatro líneas:

| | Pregunta | Respondan |
|---|---|---|
| 1 | Topes §8.5 | ¿Aprueban bandas por puntaje? ¿Con qué cortes (75 / 60)? |
| 2 | Menos de 93 | ¿Se adjudican todas, o hay puntaje mínimo? ¿Cuál? |
| 3 | Piloto de mayo | ¿Las 24 se repostulan, o el piloto se cierra aparte? |
| 4 | Estrato 0 (§4.2) | Confirmar que se descarta, por lo explicado en el punto 1. |

Mientras tanto la convocatoria **puede operar**: el motor corre con los valores
recomendados y cada pantalla muestra qué supuesto está aplicando. Lo que **no**
debe hacerse es publicar un ranking definitivo antes de que las 2 primeras estén
ratificadas por escrito: cualquier supuesto que asumamos nosotros altera el
orden de la lista y no sería defendible ante una impugnación.

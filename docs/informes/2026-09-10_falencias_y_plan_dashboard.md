# Falencias del tablero: dónde están, de qué tipo son y en qué orden se cierran

**10 de septiembre de 2026 · documento interno del equipo de desarrollo**

Acompaña a [`2026-09-10_fuentes_de_informacion.md`](./2026-09-10_fuentes_de_informacion.md),
que explica las fuentes en lenguaje de gestión. Éste dice dónde falla el sistema,
por qué, y en qué orden se arregla para que el tablero quede cierto primero.

Todas las cifras están medidas contra la base el 2026-09-10, no tomadas de
documentos anteriores.

---

## 1. En una frase

**El sistema no tiene una sola forma de responder «cuánta plata tiene esto».**
Conviven seis registros y cada pantalla eligió el suyo sin declararlo, así que el
tablero publica $41.264 M de comprometido sobre una Matriz que dice $224.854 M, y
doce áreas abren su panel y leen «$0» teniendo $147.541.561.007 comprometidos.

Es la misma forma que tenía el avance físico de metas antes de unificarlo, y se
cierra igual.

| Registro | Comprometido que declara |
|---|---:|
| Matriz PDL de la ALK | $224.853.665.855 |
| CRP de BogData (tramo del PDL) | $184.839.187.185 |
| Contratos cargados en innovaK | $41.264.386.430 |
| SECOP II, pagado sobre lo conciliado | $4.769.318.038 |
| Espejo de SEGPLAN, programado | $667.578.460.000 |
| `programa_cdp` | cero filas |

---

## 2. Panorama: dónde está cada falencia

| Pantalla | Qué muestra hoy | Qué debería | Plata fuera |
|---|---|---|---:|
| **Cockpit** `/app/presupuesto/dashboard` | 11,0 % comprometido · 1,27 % girado | 59,7 % y 26,9 % | $183.589 M · $96.377 M |
| **Cockpit · chip de vigencia** | mueve 1 de 4 recuadros | los cuatro | — |
| **Objetivos** `/app/presupuesto/objetivos` | «Fuente: Matriz» con $667.578 M del espejo · ejecución 29,7 % | $376.458 M · 59,7 % | — |
| **Perspectivas** | la tarjeta padre dice $667.578 M y sus hijos suman $376.458 M | la misma cifra arriba y abajo | — |
| **Mi Área** `/app/mi-area` | «Contratado $0» en 12 de 16 áreas | su comprometido de la Matriz | $147.542 M |
| **Panel de subgrupo** `/app/subgrupo/:id` | «$0» y contradice a Mi Área en Seguridad | la misma cifra que Mi Área | incluido arriba |
| **Programas** `/app/presupuesto/programas` | Asignado $0 (tabla vacía) · comprometido 1,1 % de la Matriz en Justicia | apropiación y comprometido de la Matriz | — |
| **Festivales · insights** | proyecto 2780: Asignado $0 · Ejecutado $3.252.859.424 | $12.392.980.000 y $7.794.984.904, como su expediente | $4.542 M |
| **Ficha y 360° del proyecto** | «Sin programa asociado» en 26 de 31, y 2 con uno falso | el catálogo resuelve 30 de 31 | — |
| **Fila de programa** | «1 meta» donde hay 7; la pantalla suma 30 y su gráfico dice 76 | metas, no proyectos | — |
| **Catálogo de metas** | 76 de 78 · 21 ejecutadas de 23 | las 78 | $52.517 M proyectado |

---

## 3. Las tres raíces

### R1 · No hay una implementación única de la plata — 9 de 12 hallazgos

Cuatro consultas distintas leen hoy la misma tabla de la Matriz, ninguna acepta
vigencia y ninguna devuelve las tres columnas juntas. Cada pantalla completó lo
que le faltaba con la fuente que tenía a mano, y de ahí salen todos los síntomas:
el recuadro que mezcla apropiación de la Matriz con comprometido de contratos, el
porcentaje cuyo numerador y denominador vienen de libros distintos, el «$0» de las
áreas sin contratos cargados y el chip de vigencia que solo alcanza a una tabla.

**Se cierra con `plata_matriz.py`**: una única implementación con la firma
completa `(codigos, subgrupo_ids, vigencia)`, que devuelve apropiación,
comprometido y girado con su cobertura, y `None` —nunca `0.0`— cuando no hay
filas. Es literalmente lo que hizo `avance_matriz.py` con el avance físico, que ya
está probado en producción.

### R2 · El programa del proyecto sale de una llave muerta — 2 hallazgos

Dos lectores resuelven «¿de qué programa es este proyecto?» contra una tabla de
siete filas, tres de ellas de prueba, en vez del catálogo del Plan que usa todo lo
demás. Resultado medido: 26 de 31 proyectos sin programa y 2 con una etiqueta que
no existe en el Plan. El catálogo resuelve 30 de 31 sin ambigüedad.

### R3 · El rótulo se escribe lejos del número, y deriva — 3 hallazgos

La unidad, la fuente y el formato se deciden donde se imprime, no donde se
calcula. Por eso una fila dice «1 meta» contando proyectos, una página se titula
«Fuente: Matriz» mostrando el espejo, y dos formateadores del frontend convierten
«sin dato» en «$0», deshaciendo en pantalla el arreglo honesto del backend.

---

## 4. Lo que se arregla programando y lo que no

Es la separación que más tiempo ahorra, porque confundirlas cuesta meses.

**Se arregla programando.** Las tres raíces completas. Ninguna necesita que nadie
cargue nada: la Matriz ya cubre 30 de 30 proyectos con apropiación y comprometido,
y el catálogo del Plan ya resuelve 30 de 31 programas. La plata que hoy no se ve
**ya está en la base**.

**No se arregla programando.**

| Hueco | Medido | Qué falta |
|---|---|---|
| Las dos metas de posmedia | 23771 y 23772, ejecutadas al 100 %, sin fila propia | decisión sobre la meta agrupada |
| Matriz contra BogData | $40.014.478.670 de diferencia | conciliación, es decisión de negocio |
| Espejo de SEGPLAN | parado desde el 23-jul, 49 días | destrabarlo con Planeación Distrital |
| Valor pagado en SECOP | 152 contratos en cero, $70.204 M | que supervisión lo diligencie |
| Contratos de las áreas | 3 de 18 áreas los cargan | decisión sobre si se cargan |

**Advertencia sobre el último.** Cargar contratos NO es la vía para llenar el
tablero: el comprometido debe salir de la Matriz y de BogData, que ya lo tienen
completo. Los contratos hacen falta por otra razón —poder abrir el expediente de
cada uno y atribuirlo a una meta—, y perseguirlos para arreglar una cifra que se
arregla cambiando la fuente es meses de digitación mal gastados.

---

## 5. El plan

Ordenado para que el tablero quede cierto primero, que es de donde se arranca.

### Fase 1 · El módulo único de plata

Nace `plata_matriz.py`. No cambia ninguna pantalla por sí solo, y por eso se
escribe con calma y se prueba entero. Va primero porque las fases 2, 3 y 5
escribirían si no tres consultas nuevas que en seis meses vuelven a divergir.

**Se verifica** con que la suma por subgrupo dé exactamente $224.853.665.855 de
comprometido y $101.146.005.967 de girado, que es lo que hoy suman las 17
tarjetas del muro. **Esfuerzo:** un día. **Bloqueo:** ninguno, es backend puro.

### Fase 2 · El tablero queda cierto

El ledger del cockpit pasa a la Matriz y el chip de vigencia se propaga a los
cuatro recuadros. Es la pantalla que abre el dueño y la que hoy publica el error
más grande.

**Queda bien:** comprometido y girado dejan de ser los de 25 contratos, la
cobertura deja de decir «25 de 25 contratos» debajo de una cifra de 78 metas, y
elegir 2026 mueve la pantalla entera. **Se verifica** con que el recuadro diga
59,7 % y 26,9 %. **Bloqueo:** toca frontend, y el árbol compartido tiene los
componentes de presupuesto modificados por otra persona. Necesita que ese trabajo
esté commiteado antes de compilar.

### Fase 3 · Las doce áreas dejan de ver «$0»

Los dos paneles de área toman la plata de la Matriz. Es el paso de mayor
cobertura: las áreas con cifra pasan de 4 a 16 y salen de la invisibilidad
$147.541.561.007. Es la pantalla del coordinador, y hoy le dice a Salud, Mujer,
Deporte y Ambiente que no tienen un peso.

De paso se cierra la contradicción de Seguridad, que dice $0 en una pantalla y
$6.944.742.446 en la otra el mismo día. **Esfuerzo:** un día. **Bloqueo:**
ninguno, es backend.

### Fase 4 · Objetivos deja de contradecirse consigo mismo

Tres líneas de Angular, cero backend: los campos correctos ya viajan en el
payload y nadie los está usando. La cifra pasa de $667.578 M a los $376.458 M que
ya publica el ledger de la misma pantalla, y la ejecución de 29,7 % a 59,7 %.

**Esfuerzo:** horas. **Bloqueo:** el mismo build compartido de la fase 2.

### Fase 5 · Programas y Festivales

`metrics.py` y los insights de Festivales cambian de fuente. Es el más delicado
porque cambia rótulos y no solo cifras: «Asignado» pasa a «Apropiado (POAI)» y
«Ejecutado» a «Comprometido». **Se verifica** con que el proyecto 2780 diga lo
mismo en Festivales y en su expediente. **Esfuerzo:** un día.

### Fase 6 · Un solo árbol del Plan

El programa del proyecto sale del catálogo en los dos lectores. Hay que hacerlos
juntos o el mismo proyecto seguirá dando dos respuestas según la pantalla.
Independiente de todo lo anterior: puede ir en paralelo desde el primer día.
**Trampa:** el serializador de la lista necesita un diccionario precalculado o
abre una consulta por fila.

### Fase 7 · Cada cifra declara su fuente, su corte y su cobertura

La más barata y la que más malentendidos evita. El modelo ya está en producción
en la anotación del 2780, que ahora dice primero cuánto alcanza a ver el espejo y
después el porcentaje.

---

## 6. El primer paso, hoy

**Escribir `plata_matriz.py`.** Es backend puro, no necesita compilar el frontend,
no depende de ninguna decisión pendiente y desbloquea las fases 2, 3 y 5. Todo lo
visible pasa por él.

La alternativa tentadora —las tres líneas de Objetivos, que son horas y se ven de
inmediato— está bloqueada por el árbol compartido: cualquier compilación publica
el trabajo a medias de otra persona.

---

## 7. Decisiones que necesito

1. **La meta agrupada.** Si se crean las filas de 23771 y 23772 y se retira la
   agrupada, o si se enseña a las pantallas a expandirla. Lo primero es más limpio
   y toca datos; lo segundo no toca datos y deja la rareza viva.
2. **Cuál es el comprometido oficial**, el de la Matriz o el de BogData. Hasta que
   se decida, cualquier porcentaje de ejecución que publiquemos es discutible.
3. **Si los rótulos pueden cambiar** en la fase 5. «Asignado» y «Ejecutado» dejan
   de ser exactos cuando la fuente cambia.

---

## 8. Lo que ya está bien

No es poco, y el informe no debe leerse como que todo está roto.

- **El avance físico tiene una sola implementación** y cubre 17 de 17 subgrupos,
  13 de 13 sectores, 75 de 77 KPIs y 30 de 30 proyectos.
- **La apropiación del tablero es exacta**: $376.458.297.000, verificada contra el
  Excel al millón.
- **Las alertas del Plan son exactas** en las cinco categorías.
- **El semáforo ya califica con la Matriz** y anota a SECOP solo cuando de verdad
  discrepa: de cinco desacuerdos quedaron dos, y los dos están explicados.
- **La carga del CRP quedó endurecida** para el corte de octubre.
- **El expediente del proyecto y el muro de áreas** ya leen la Matriz.

---

## 9. Lo que no se midió

- **Qué pruebas fijan cifras que van a moverse.** Hay siete archivos de prueba
  sobre estos servicios y no se revisó cuáles clavan números. Precedente: en la
  carga de la Matriz quince pruebas se pusieron en rojo y ninguna era un defecto.
  Regla a aplicar: donde el número ERA el punto se re-mide; donde era proxy de una
  invariante, se reemplaza por la invariante.
- **El rendimiento del módulo nuevo.** Tres servicios ya consultan esa tabla en la
  misma respuesta. Si `plata_matriz` no comparte el patrón de caché de proceso de
  `avance_matriz`, una pantalla podría hacer tres pasadas de más.
- **El proyecto con código `000007895`**, que queda sin programa incluso con el
  catálogo. No se averiguó si es basura, una prueba o un proyecto mal codificado.
- **El inventario exhaustivo pantalla por pantalla** quedó a medias: el barrido de
  las doce zonas se cayó por límite de sesión. Este documento sale del análisis de
  los doce hallazgos de mezcla de fuentes, que sí se completó y se verificó.

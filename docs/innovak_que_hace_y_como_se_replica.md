# innovaK — qué hace, qué absorbe y qué pasaría si se multiplica

**Alcaldía Local de Kennedy · documento al 13 de octubre de 2026**

Toda cifra de este documento está medida contra las fuentes oficiales o contra
la base del sistema el día que se escribió. Ninguna es una estimación.

---

## 1. En una frase

innovaK es la intranet de la Alcaldía Local de Kennedy: **baja todos los días
los datos oficiales que ya existen sobre la localidad, los cruza, y muestra lo
que falta con nombre y dueño en vez de mostrar un cero anónimo.**

Lo que lo distingue de un tablero no es la gráfica: es que **cada cifra puede
rastrearse hasta la fila del dataset de donde salió**, y cuando un dato no se
puede saber, el sistema lo dice en lugar de poner cero.

---

## 2. Qué absorbe

Catorce fuentes oficiales, todas públicas y gratuitas, que entran solas a las
**03:30** cada día. Nadie descarga nada a mano.

| Fuente | De dónde | Qué trae |
|---|---|---|
| **SECOP II · contratos** | `jbjy-vk9h` | Los contratos de la localidad: valor, plazo, contratista, estado. 95 columnas disponibles |
| **SECOP II · plan de pagos** | `uymx-8p3j` | Lo programado a pagar por contrato |
| **SECOP II · modificaciones** | `u8cx-r425` + `cb9c-h8sn` | Prórrogas, adiciones, cesiones, terminaciones |
| **SECOP II · suspensiones** | `u99c-7mfm` | Los actos de suspensión y reanudación, con su texto |
| **PAA · ítems** | `9sue-ezhx` | El Plan Anual de Adquisiciones: qué se planeó contratar y con cuánto |
| **PAA · encabezado** | `b6m4-qgqv` | Presupuesto del plan, versión, estado |
| **Planeación (SDP-PDL)** | datos abiertos SDP | Proyectos y metas del Plan de Desarrollo Local |
| **Presupuesto participativo** | CKAN de la SDP | Lo priorizado por la ciudadanía |
| **Estratificación** | IDECA | Estrato y vigencia **por manzana** (45.051 manzanas en Bogotá) |
| **Sectores catastrales** | IDECA | Geometría de los sectores |
| **Barrios legalizados** | IDECA | Geometría de los barrios |
| **Colegios y matrícula** | SED + IDECA | 48 colegios, 79 sedes, 95.909 estudiantes en Kennedy |
| **CAI** | Secretaría de Seguridad | 15 CAI en Kennedy |
| **Malla vial** | IDU | Geometría de los tramos |
| **Placas domiciliarias** | Catastro | 1,77 millones de filas (se corre aparte, es la pesada) |

A eso se suma lo que **ninguna fuente publica** y el área carga a mano por
pantalla propia: los soportes, el CDP, las actas, las asistencias. El tablero
no inventa esos datos: muestra el pendiente **con el nombre del área
responsable**.

### El espejo hoy

```
contratos ..................  3.211   (2024 en adelante, vigencia del PDL)
modificaciones .............  4.304
actos de suspensión ........  1.474
ítems del PAA ..............  6.333   (2017-2026)
procesos del PAA ...........  6.579
```

---

## 3. Qué hace con eso

Catorce módulos sobre una sola base. Los que más se usan:

| Módulo | Para qué sirve |
|---|---|
| **Presupuesto** | El núcleo: proyectos, metas, matriz del PDL, contratos, CDP/CRP, y la formulación contractual. 34 archivos de servicio |
| **Tablero (Dashboard)** | Los KPIs presupuestales y **Kenny**, el asistente que responde preguntas en lenguaje natural sobre el propio dato |
| **Banco de Iniciativas** | Inscripción ciudadana y calificación con la matriz oficial de 100 puntos; los soportes condicionan el puntaje |
| **Caracterización** | Seis sectores: cultura, deporte, mujer, salud, poblacional, participación |
| **Georreferenciación** | El mapa de Kennedy con las capas de IDECA y los lugares del plan |
| **Educación** | Colegios, matrícula y educación posmedia |
| **Jóvenes a la E / Entregas** | Becas y entrega de beneficios |
| **Festivales** | Los actos ejecutados de cada festival (publicar ≠ ejecutar) |
| **Votaciones** | Eventos de votación, candidatos, resultados |
| **Documentos** | Los soportes y su espejo en OneDrive |
| **Usuarios y permisos** | Roles por módulo, grupos, auditoría de cada cambio. 27 archivos de servicio |
| **API pública** | 9 rutas abiertas, sin credenciales, para que un tercero consuma lo mismo |
| **Recorrido guiado** | El arranque del usuario nuevo y su progreso |

### La API pública

Es la única superficie pensada para que la lea cualquiera, y existe porque la
Oficina de Innovación necesitaba alimentar el **certificado contractual** y el
**paz y salvo** sin pedirnos un informe cada vez.

```
/api/publica/v1/contratos/                        lista y filtros
/api/publica/v1/contratos/{id}/                   la ficha
/api/publica/v1/contratos/{id}/modificaciones/    prórrogas, cesiones, suspensiones
/api/publica/v1/contratos/modificaciones/lote/    hasta 200 contratos por petición
/api/publica/v1/paa/                              el Plan Anual de Adquisiciones
/api/publica/v1/paa/cobertura/                    qué cubre y qué no, por año
/api/publica/v1/agregados/                        totales
/api/publica/v1/metadatos/                        corte, cobertura y diccionario
/api/publica/v1/esquema/                          OpenAPI 3, para generar el cliente
```

---

## 4. Cómo funciona por dentro

Cinco decisiones que explican casi todo:

**1 · El sistema no es dueño de la base.** Lee una base externa compartida y
ningún modelo la administra. Los cambios de estructura van en **40 scripts
numerados, cada uno con su rollback**, y se aplican a mano con respaldo del día.

**2 · La ingesta escribe solo lo que cambió.** Cada fila lleva un hash; si no
cambió, no se toca. Así «3.147 filas sin tocar» significa *no cambiaron*, no
*la ingesta no corrió*. Y un consumidor externo puede pedir solo lo nuevo con
`actualizado_desde`.

**3 · Nada se descarga en caliente.** Lo recurrente va al cron (03:30 la
ingesta, 04:00 el recálculo). Si un día no corre, el siguiente se pone al día
solo.

**4 · El permiso es por módulo, no por pantalla.** Un rol habilita un módulo; la
pantalla no decide nada. Cada cambio queda auditado con autor, y desde este mes
también puede quedar auditado con **autor máquina** —qué modelo, qué versión,
qué confianza— para que una clasificación automática sea registrable sin
disfrazarse de persona.

**5 · Todo gratis.** La IA corre en la capa libre de Groq (200.000 tokens al
día). El mapa usa baldosas de OpenStreetMap con caché propio en nginx. No hay
una sola licencia pagada en el camino del dato.

### Escala

```
106.900 líneas de Python   ·   63.974 de TypeScript/HTML
14 módulos   ·   61 comandos   ·   268 rutas   ·   293 tablas
1.865 pruebas automáticas, que corren en cada push y lo bloquean si fallan
```

---

## 5. Las reglas que sostienen el dato

Esto es lo que haría distinto a innovaK en cualquier localidad, y no es
tecnología: es disciplina sobre el dato.

> **`null` nunca es `0`.** Un cero que en realidad significa «no sabemos» es una
> afirmación falsa sobre gasto público. Cada dato ausente viaja con su motivo.

Ejemplo real: SECOP reporta `valor_pagado = 0` y no distingue «no se giró» de
«no se reportó». Hay contratos con giro probado en BogData que SECOP reporta en
cero. Durante un tiempo el tablero mostraba **$0 en 240 contratos**, lo que leído
de buena fe decía que no se les había pagado nada. Hoy esos salen en `null` con
el motivo al lado.

> **Un campo del origen que miente se declara, no se reenvía callando.**

Ejemplo real: en las modificaciones de SECOP, el campo `tipo` del par
suspensión/reactivación **viene invertido en el 99,3 % de los casos** —las filas
marcadas «SUSPENSIÓN» son los reinicios—. Medido contra un tercer dataset,
1.055 de 1.062 pares. Usarlo habría fechado la suspensión de un contrato el día en que el
contrato se reactivó, **en un paz y salvo**. Hoy la clase sale del dataset
dedicado y viaja con el texto del acto para que cualquiera la compruebe a mano.

> **Toda cobertura se mide en las dos direcciones.**

Ejemplo real: del PAA al espejo de contratos el cruce es del **96,4 %**; de
nuestros contratos al PAA es del **70,5 %**, y en 2024 del **30,3 %**. Son dos
cifras distintas y publicar solo la primera haría leer que el plan cubre casi
todo lo contratado. Confundir las dos direcciones ya produjo una vez una
cobertura del 160 % en este proyecto.

> **Lo que no se puede saber no se escoge a la suerte.**

Ejemplo real: cuando un contrato tiene una suspensión y una reanudación fechadas
el mismo día, el orden no está en el dato. Son 17 casos. El sistema declara la
ambigüedad en vez de elegir: acertar la mitad de las veces en un dato que
alimenta un certificado no es acertar.

---

## 6. Si se multiplica a las 20 alcaldías locales

Esta es la parte que importa, y la respuesta corta es: **el dato de las otras 19
localidades ya está ahí.** No hay que conseguirlo, ni pedirlo, ni convenirlo.

### Lo que está publicado hoy, medido

| | |
|---|---|
| Alcaldías locales con **PAA 2026 publicado** | **20 de 20**, y con 10 años de historia cada una |
| Presupuesto sumado de los **PAA 2026 de las 20** | **$1,99 billones** |
| Alcaldías locales con **contratos en SECOP II** | **20 de 20** |
| Contratos de las 20 localidades (histórico) | **81.978** |
| Valor de esos contratos | **$8,9 billones** |
| La más grande en contratos | Ciudad Bolívar (7.045) |
| Kennedy | 6.225 en SECOP; 5.558 en nuestro espejo, que arranca en 2020 |

Las mismas catorce ingestas, sin una línea nueva, ya **ven** a las veinte. Hoy
solo las filtran.

### La llave: una constante por localidad

Lo que cambia entre una localidad y otra es **un número**:

```python
CODIGO_ENTIDAD = "702292459"   # Kennedy
```

Y está comprobado que ese código **es el mismo en los dos mundos** —el PAA y
SECOP—, incluso donde todo lo demás difiere:

| Localidad | código (PAA) | código (SECOP) | |
|---|---|---|---|
| Kennedy | 702292459 | 702292459 | ✅ |
| Suba | 702230251 | 702230251 | ✅ |
| Bosa | 702187444 | 702187444 | ✅ |

### Las tres trampas que hay que evitar al replicar

Las encontramos midiendo, y cada una habría costado una localidad entera:

**1 · Filtrar por NIT pierde a Bosa.** Diecinueve localidades publican bajo el
NIT `899999061`; **Bosa publica bajo `8999990615`** —el mismo NIT con el dígito
de verificación pegado—. Son 5.054 contratos y $752 mil millones que
simplemente no aparecen.

**2 · Filtrar por nombre pierde a Suba y a Barrios Unidos.** Las dos se
registran como **«ALCALDÍA» con tilde**, así que un filtro por `ALCALDIA LOCAL`
las deja fuera: 8.413 contratos. Hoy la ingesta de contratos de innovaK filtra
justamente por nombre —`nombre_entidad = 'ALCALDIA LOCAL DE KENNEDY'`—, y para
replicar eso hay que cambiarlo por el código.

**3 · Los nombres del origen vienen sucios.** En los datos oficiales hay
`ALCALDIA LOCAL DE CIUDAD BOLIVAR //`, `ALCALDIA LOCAL DE TEUSAQUILLO(oficial)`
y una entidad llamada `ALCALDIA LOCAL CONTINENTE EL PAILON DEL DISTRITO`. No se
puede construir nada sobre el nombre.

Y una advertencia de calidad que vale para cualquier tablero que se arme con
esto: bajo ese mismo NIT hay una secretaría distrital cuyos contratos suman
**$605 billones** en el dataset, unas diez veces el PIB de Colombia. El dato
oficial trae filas corruptas, y por eso el sistema declara y contrasta en vez de
confiar.

### Dos formas de montarlo

**A · Una instancia por alcaldía.** Cada localidad con su base y su dominio.
Cambia la constante, el nombre y las capas geográficas (UPZ y barrios de esa
localidad, que ya están en IDECA). Es lo más simple y lo más aislado: nadie ve
el dato del vecino. Veinte despliegues que no se estorban.

**B · Una instancia para todas, con la localidad como dimensión.** Una sola
ingesta trae las veinte —ya las trae, solo habría que dejar de filtrar—, y el
permiso por módulo que ya existe decide quién ve qué. Sale **una** sincronización
nocturna en lugar de veinte, y abre algo que hoy no existe: **comparar**
localidades con el mismo método y la misma fecha de corte. Es más trabajo de
permisos y menos de operación.

Para la Secretaría Distrital de Gobierno la opción B es la que tiene sentido:
las veinte alcaldías con la misma definición de «ejecutado», la misma regla de
`null`, el mismo corte. Hoy cada localidad lo calcula a su manera, y los números
no se pueden sumar.

### Qué hay que tocar, concretamente

| Qué | Esfuerzo |
|---|---|
| Cambiar el filtro de entidad de **nombre a `codigo_entidad`** en las ingestas | Pequeño. Es la corrección que además arregla Suba, Barrios Unidos y Bosa |
| Parametrizar la localidad (una tabla de entidades en lugar de una constante) | Mediano |
| Capas geográficas por localidad | Pequeño: IDECA ya publica las 20 |
| Convención del código interno del área | **Variable.** En Kennedy es `K-0528`; cada localidad usa la suya, y el sistema ya guarda *cuál convención* reconoció junto al código, precisamente porque cambia |
| Permisos por localidad (si es la opción B) | Mediano: el modelo de roles por módulo ya existe, hay que añadirle la dimensión |
| Lo que el área carga a mano | **Lo mismo en cada localidad.** No se hereda: cada una carga sus soportes |

### Qué no se multiplica solo

Hay que decirlo con claridad:

- **El PAA no sirve para cruzar antes de 2024.** De 2017 a 2023, los planes de
  Kennedy no declaran ni un proceso: 3.292 ítems, cero. No es un defecto del
  sistema ni se arregla replicándolo.
- **El código de SIPSE solo existe desde 2025.**
- **No hay historial de versiones del PAA.** La fuente publica solo la última de
  cada año. Lo que cambió entre la versión 30 y la 31 no está publicado en
  ninguna parte.
- **El dato que el área carga a mano sigue siendo trabajo del área.** El sistema
  reduce el trabajo de recolectar lo que ya es público; no reemplaza al que
  tiene que subir el acta.

---

## 7. Lo que costaría

```
Licencias de software ....................... $0
Servicios de datos (todas las fuentes) ...... $0
IA del asistente (capa libre, 200k/día) ..... $0
Mapa (OpenStreetMap con caché propio) ....... $0
```

Lo que cuesta es **el servidor y la persona que lo sostenga**. Todo lo demás del
camino del dato es público y gratuito, y así se diseñó desde el principio.

---

## 8. La conclusión

El trabajo difícil de innovaK no fue conectarse a los datos abiertos: fue
descubrir, uno por uno, **en qué miente cada fuente** —un campo invertido en el
94 % de los casos, un cero que significa «no sé», un NIT con un dígito de más,
un nombre con tilde, una cobertura que se mide al revés— y dejar cada hallazgo
escrito, medido y con una prueba automática que falla si alguien lo vuelve a
hacer mal.

Ese conocimiento **no hay que volverlo a descubrir veinte veces**. Es lo que se
multiplica mejor.

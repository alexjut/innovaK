# A3 · Los 32 eventos sin actividad del plan — propuesta de mapeo

> **Estado:** borrador para las áreas, 2026-08-06. **Nada de esto se ejecutó.**
> Los beneficiarios sí se crearon (ver §4); el mapeo evento→actividad **no**,
> porque no es una decisión técnica.

---

## 1. El problema, en una línea

Hay **2.545 personas** atendidas en 32 eventos que **no le suman a ninguna
meta**, porque ninguno de esos eventos cuelga de una actividad del plan. El
tablero presupuestal los cuenta como cero. No es que no hayamos atendido a
nadie: es que la cadena está partida en el último eslabón.

```
Proyecto → Meta → KPI ← ActividadPlan ← Evento → Beneficiarios
                              ↑
                        acá está el corte
```

---

## 2. 🔴 Lo primero, porque cambia la pregunta

La versión anterior de este análisis decía que Relacionamiento
Interinstitucional tenía **una** actividad candidata y que bastaba con
confirmarla. **Al abrirla, no sirve.**

| | |
|---|---|
| `actividad_plan` 107 | «mujeres caminando ver 1» |
| Proyecto | `000007895` — cuyo **nombre es su propio código** |
| KPIs vinculados | **0** |
| Eventos que ya cuelgan de ella | **0** |
| Contratos que la financian | **0** |

Es un registro de prueba. Colgar ahí las 2.408 personas de las Novenas sería
peor que dejarlas sin mapear: quedarían sumando a una meta que no existe, y el
número se vería bien en el tablero sin significar nada. Para comparar, así se
ve una actividad de verdad: `ARTES ESCÉNICAS`, `CLASES DE DANZA`, en el
proyecto 2780 **KENNEDY PROYECTA TALENTO**.

Y **Desarrollo Estratégico y Mejora no tiene ninguna** actividad en el plan.

**Conclusión: los dos subgrupos necesitan actividad nueva.** No hay nada
correcto a lo cual enganchar hoy.

---

## 3. Los 32 eventos, con propuesta

La propuesta agrupa por **naturaleza de la intervención**, que es lo único que
se puede leer del dato sin preguntarle al área. La columna «en qué me baso» dice
exactamente eso, para que se pueda contradecir.

### 3.1 Relacionamiento Interinstitucional — 17 eventos, 2.408 personas

| Evento | id | Fecha | Inscritos | Con beneficiario |
|---|---|---|---|---|
| Novena Cumpleaños de Kennedy | 33 | 2025-12-18 | 833 | 551 |
| Novena Vegas de Santa Ana | 34 | 2025-12-19 | 338 | 260 |
| Novena Prados de Kennedy - Porvenir | 35 | 2025-12-19 | 43 | 29 |
| Novena Timiza I Sector | 36 | 2025-12-20 | 34 | 24 |
| Novena Ayacucho | 37 | 2025-12-20 | 109 | 82 |
| Novena Marsella | 38 | 2025-12-20 | 70 | 47 |
| Novena Valladolid | 39 | 2025-12-21 | 87 | 65 |
| Novena Casablanca | 40 | 2025-12-21 | 139 | 81 |
| Novena San Andrés II Sector | 41 | 2025-12-21 | 122 | 87 |
| Novena Las Vegas | 42 | 2025-12-22 | 56 | 29 |
| Novena Las Acacias | 43 | 2025-12-22 | 89 | 74 |
| Novena Villa de la Torre | 44 | 2025-12-22 | 113 | 57 |
| Novena Santa Catalina | 45 | 2025-12-23 | 81 | 43 |
| Novena Quintas de Santa Cecilia - Las Margaritas | 46 | 2025-12-23 | 46 | 43 |
| Novena La Igualdad | 47 | 2025-12-23 | 101 | 80 |
| Novena San Martín de Porres y Villas de Kennedy | 48 | 2025-12-24 | 130 | 97 |
| Recorrido Ayacucho | 32 | 2025-11-15 | 17 | 10 |

**Propuesta: UNA actividad para las 16 Novenas.** En qué me baso: son el mismo
tipo de intervención repetida en 16 barrios entre el 18 y el 24 de diciembre de
2025 — una jornada navideña de la Alcaldía por territorio. Tratarlas como 16
actividades distintas convierte el plan en un calendario; tratarlas como una
sola con 16 ejecuciones es exactamente para lo que existe la separación entre
`ActividadPlan` y `Evento`.

**El Recorrido Ayacucho (32) va aparte.** Es de noviembre, no es una novena, y
su nombre coincide con los «Recorridos» del otro subgrupo. Puede que esté en el
subgrupo equivocado. **Esto lo tiene que decir el área**, no yo.

### 3.2 Desarrollo Estratégico y Mejora — 15 eventos, 137 personas

| Evento | id | Fecha | Inscritos | Con beneficiario |
|---|---|---|---|---|
| Tecnologías de asistencia tecnológica para personas… | 6 | 2025-07-21 | 3 | 2 |
| Recorrido Barrio Monterrey | 15 | 2025-08-02 | 37 | 0 |
| Recorrido Barrio Américas Central | 17 | 2025-08-08 | **0** | 0 |
| Recorrido Gran Colombiano | 19 | 2025-08-24 | 11 | 0 |
| Reunión Tierra Buena Gerona del Porvenir 2 | 20 | 2025-09-05 | 4 | 0 |
| Recorrido Santa Catalina | 21 | 2025-09-06 | 18 | 0 |
| Recorrido Las Brisas | 22 | 2025-09-13 | 15 | 0 |
| Recorrido Floresta Sur | 23 | 2025-09-13 | **0** | 0 |
| Recorrido Villa Anita | 24 | 2025-09-13 | 11 | 0 |
| Recorrido Roma 4 Sector | 25 | 2025-09-13 | 8 | 0 |
| Barrio Las Vegas | 27 | 2025-10-10 | **0** | 0 |
| Recorrido Las Vegas 1 | 28 | 2025-10-10 | **0** | 0 |
| Recorrido Las Vegas 1 | 29 | 2025-10-10 | 13 | 12 |
| Barrio Patio Bonito II | 30 | 2025-10-10 | 13 | 10 |
| Barrio Las Margaritas | 31 | 2025-10-10 | 4 | 2 |

**Propuesta: UNA actividad para los 13 recorridos/reuniones territoriales.** En
qué me baso: son visitas a barrio entre agosto y octubre de 2025, con el mismo
patrón (nombre = barrio, asistencia pequeña de 4 a 37 personas). El evento 6
(«Tecnologías de asistencia…») **no encaja** — es un tema distinto, con 3
personas: va aparte o se retira.

**Tres cosas que el área tiene que resolver, y que el dato deja ver:**

1. **`Recorrido Las Vegas 1` está DUPLICADO** (28 y 29), mismo nombre y misma
   fecha; uno tiene 13 inscritos y el otro cero. Casi seguro es el mismo
   recorrido cargado dos veces.
2. **Cuatro eventos con cero inscritos** (17, 23, 27, 28): o no se hicieron, o
   se hicieron y no se registró a nadie. Son cosas muy distintas y solo el
   área sabe cuál.
3. **`Barrio Las Vegas` (27) y `Recorrido Las Vegas 1` (28/29)** podrían ser lo
   mismo con dos nombres.

---

## 4. Lo que SÍ se hizo el 2026-08-06 (y no necesitaba a las áreas)

Se crearon **1.684 beneficiarios** para las personas atendidas que eran
identificables. Ahora **1.685 de las 2.545** tienen su ficha de beneficiario.

Esto es independiente del mapeo: un beneficiario es «esta persona recibió algo
de la Alcaldía», y eso ya era cierto. El mapeo es «a qué meta le suma», que es
lo que sigue pendiente.

**El tipo de documento se infirió de la edad, no se asumió.** Es la decisión
que vale la pena revisar:

| Tipo inferido | Personas | Criterio |
|---|---|---|
| 1 · Cédula de ciudadanía | 1.587 | 18 años o más a la fecha del evento |
| 2 · Tarjeta de identidad | 57 | entre 7 y 17 años |
| 6 · Otro | 69 | menores de 7 (el registro civil no está en el catálogo) |

Asumir cédula para todos —que es lo que hace el 99,87 % de la tabla— habría
sido **falso para 126 personas**, el 7,4 %.

**Quedaron fuera, a propósito:**

| | |
|---|---|
| 657 | sin ningún documento registrado: se capturaron solo con nombre |
| 9 | documento con forma imposible (largos de 1 y de 23 caracteres, o con letras) |
| 2 | fecha de nacimiento imposible (una da edad **negativa** contra la fecha del evento, otra da más de 110 años) |
| 166 | filas de `persona` que comparten documento con otra: se creó **una** ficha por documento |

Las 657 sin documento **no se pueden recuperar por código**. No se pueden
deduplicar, ni verificar, ni cruzar con otro sistema. Inventarles un documento
sería mucho peor que no tenerlas.

**Para revertir esta carga**, si algo estuvo mal:

```sql
DELETE FROM beneficiario WHERE id > 3765 AND id <= 5849;
```

---

## 5. Ficha BORRADOR de las actividades faltantes — **NO CREADAS**

Se dejan escritas para que el área las corrija, no para ejecutarlas. Faltan
tres datos que solo el área tiene: a qué **meta** aporta cada una, con qué
**contrato** se pagó, y cuál es la **magnitud** comprometida.

### 5.1 Relacionamiento Interinstitucional

| Campo | Valor propuesto | Quién lo confirma |
|---|---|---|
| `subgrupo` | Relacionamiento Interinstitucional (id 7) | — |
| `proyecto_id` | ⚠️ **sin definir** — el único proyecto del subgrupo es `000007895`, que no tiene nombre real | **el área + Planeación** |
| `descripcion` | `NOVENAS NAVIDEÑAS COMUNITARIAS` | el área |
| Eventos que colgarían | 16 (ids 33–48) | — |
| Personas que entrarían al KPI | 2.391 | — |
| Meta / KPI al que aporta | ⚠️ **sin definir** | **el área** |
| Contrato que la financia | ⚠️ **sin definir** | **el área** |

### 5.2 Desarrollo Estratégico y Mejora

| Campo | Valor propuesto | Quién lo confirma |
|---|---|---|
| `subgrupo` | Desarrollo Estratégico y Mejora (id 25) | — |
| `proyecto_id` | ⚠️ **sin definir** — el subgrupo **no tiene proyecto** | **el área + Planeación** |
| `descripcion` | `RECORRIDOS TERRITORIALES POR BARRIO` | el área |
| Eventos que colgarían | 13 (ids 15, 19–25, 27–31) | — |
| Personas que entrarían al KPI | 134 | — |
| Meta / KPI al que aporta | ⚠️ **sin definir** | **el área** |
| Contrato que la financia | ⚠️ **sin definir** | **el área** |

> **La actividad no se crea hasta que las áreas respondan por escrito.** Sin
> proyecto y sin meta, una `actividad_plan` nueva sería otro registro como el
> 107: existe, no aporta a nada, y en seis meses alguien tiene que volver a
> averiguar para qué era.

---

## 6. Qué falta, en orden

1. Las dos áreas responden el correo del §7 (o su equivalente en reunión), **por
   escrito**.
2. Planeación confirma proyecto y meta de cada actividad.
3. Se crean las dos `actividad_plan` con los datos confirmados.
4. Se asigna `evento.actividad_plan_id` a los 29 eventos que apliquen.
5. El cockpit pasa de **0 a 2.545** por sí solo: cuenta participantes, no
   beneficiarios.

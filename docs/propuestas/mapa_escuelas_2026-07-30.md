# Mapa de escuelas (Cultura y Deportes) — diagnóstico y plan

Fuentes: `escuelas_cultura.json` (85), `escuelas_deportes_sedes.json` (193 sedes)
y `escuelas_deportes_detalle.json` (247 filas). Diagnóstico del 2026-07-30, solo
lectura, sin escribir nada.

---

## 1. Hallazgo principal: no es completar, es reconciliar

La premisa era "faltan registros por cargar". No es eso. **Los dos conjuntos casi
no se solapan.**

| | Archivo | En BD hoy | Coinciden por nombre | Solo en el archivo | Solo en la BD |
|---|---|---|---|---|---|
| **Cultura** | 85 | 86 | **17** | 68 | 68 |
| **Deportes** | 193 sedes | 155 | **88** | 105 | 67 |

Todo lo que hay en la BD tiene `origen='csv'`: viene del cargue de abril de 2026.
Los archivos de julio son **otro censo**, no una versión ampliada del mismo.

Y entre los que sí coinciden por nombre, la dirección cambió en **17 de 17**
(Cultura) y en **23 de 88** (Deportes). El patrón típico: la BD trae la
nomenclatura vieja (`CARRERA … BIS A … SUR`) y el archivo de julio la nueva
(`CALLE … SUR # …`) — misma sede, dos direcciones que no se parecen ni por
prefijo, así que no hay forma de casarlas por texto.

**Esto hay que decidirlo antes de tocar nada** (ver §5), porque de ahí depende si
se borra, se marca de baja o se conserva lo de abril.

---

## 2. Dos bloqueos técnicos para las tareas 3 y 4

### 2.1 PostGIS no está instalado

La tarea pide resolver el barrio con `ST_Contains`. **La base no tiene la
extensión PostGIS**; las geometrías viven como JSONB (así se cargaron en abril).

No hace falta instalarla. El cruce punto-en-polígono se hace en Python sobre el
JSONB: son 278 escuelas contra 325 barrios, cómputo trivial, y evita pedir una
extensión sobre una base compartida y externa. El fallback de 80 m al borde
también sale en Python.

### 2.2 Solo 75 de 325 barrios tienen geometría

Este es el límite real, y afecta a las dos tareas:

- **Tarea 4:** solo se puede resolver el barrio por geometría donde hay polígono.
  Para el resto no hay contra qué cruzar.
- **Tarea 3:** el hover de barrio solo va a responder en esos 75. En el resto del
  mapa el cursor no encontrará polígono, porque no está pintado.

Las UPZ sí están completas: **12 de 12 con geometría**. El hover de UPZ y la
resolución de UPZ por geometría funcionan en toda la localidad.

Es la deuda M22 documentada en abril: 79 barrios quedaron sin geometría por
desajuste de códigos con IDECA. Traer los que faltan es un trabajo aparte —
descargar la capa de IDECA y reconciliar códigos— y conviene decidir si entra
en este alcance o va después.

---

## 3. Calidad de la fuente

Confirmado sobre las 247 filas de detalle de Deportes:

| | |
|---|---|
| Sin dirección | 31 |
| Sin horario | 11 |
| Sin edades | 17 |
| Sedes con más de una escuela | 27 (hoy se apilan en el mismo punto) |
| Barrio declarado en Deportes | 0 de 247 |
| Barrio declarado en Cultura | mayoría, pero con conflictos |

Los 31 sin dirección **no se pueden ubicar en el mapa**: quedan cargados como
registro pero sin marcador, y hay que reportarlos al área para que los completen.

Las normalizaciones que señalaste (UPZ 79 mal asignada, variantes de nombre,
typos, los 12 horarios con "12:00 AM") ya vienen resueltas en los JSON: el campo
`upz_original` conserva lo que decía la fuente, para auditoría.

---

## 4. Plan de trabajo

Todo en worktree aparte, sin tocar producción, y con backup etiquetado de
`escuela` antes de la primera escritura.

**Fase 1 — Reconciliación (media jornada).** Según lo que decidas en §5: cargar
lo nuevo, marcar de baja lo que ya no reporta el área, y actualizar direcciones
de los que coinciden. Se conserva el registro de abril con su `origen` para poder
auditar qué cambió y por qué.

**Fase 2 — Geocodificación.** Resolver coordenada de cada dirección nueva. Las
sedes de Deportes traen `url_maps`, que da la coordenada directa sin geocodificar.
Para el resto, el servicio de direcciones contra Catastro que ya usa el proyecto.

**Fase 3 — Barrio y UPZ por geometría.** Cruce punto-en-polígono en Python.
Se guarda el barrio declarado aparte del resuelto, y se marca `discrepancia=True`
cuando no coinciden — que es justo lo que destapa los casos que reportaste (una
misma dirección con dos barrios distintos). Requiere DDL: tres columnas nuevas
en `escuela`.

**Fase 4 — Popup enriquecido.** Actividad, horarios, edades, UPZ, barrio y
formador. Un marcador por sede, con todas las disciplinas listadas, que resuelve
el apilamiento de las 27 direcciones repetidas. Lo que falte queda como
"Sin horario registrado" / "No registrado", nunca inventado.

**Fase 5 — Hover de barrio y UPZ.** `bindTooltip` con `sticky`, resaltado en
mouseover, barra de estado abajo a la izquierda, etiquetas permanentes desde
zoom 13 (UPZ) y 15 (barrio), y `bringToBack()` para que los polígonos no roben
el clic de los marcadores.

---

## 5. Lo que necesito que decidas

**1. Qué manda: ¿el archivo de julio o lo cargado en abril?**

- *El archivo manda* — se carga lo nuevo y los 68 de Cultura y 67 de Deportes que
  no vienen en la fuente se marcan inactivos. Riesgo: si el área no incluyó una
  escuela que sí existe, desaparece del mapa.
- *Se suman* — queda la unión (153 de Cultura, 260 de Deportes). Riesgo: quedan
  duplicados de la misma escuela con dos direcciones distintas, y el mapa muestra
  dos puntos para lo mismo.
- *Solo agregar los nuevos, sin tocar lo viejo* — lo más conservador, pero deja
  las direcciones desactualizadas de los que sí coinciden.

**2. Los 79 barrios sin geometría, ¿entran en este alcance?**
Sin ellos, el hover y la resolución de barrio funcionan solo en el 23% del
territorio. Traerlos de IDECA es trabajo aparte y conviene saber si se hace ahora
o después.

**3. Los 31 sin dirección**, ¿se cargan igual (sin marcador) o se dejan fuera
hasta que el área los complete?

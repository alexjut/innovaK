# Manual de uso — Mapa de Kennedy

**Alcaldía Local de Kennedy · Módulo de georreferenciación territorial**

> Este documento es la **guía operativa** del Mapa de Kennedy. Explica
> qué hace cada control de la pantalla, con URL exacta y captura
> sugerida, pensado para que el equipo de **comunicaciones** produzca el
> video tutorial y para orientar a cualquier usuario nuevo.
>
> Lenguaje: directo, paso a paso, sin tecnicismos.

> **⚠️ La interfaz es Angular.** Todo el sistema se usa desde
> `http://<servidor>/app/`. El mapa vive en `http://<servidor>/app/mapa`.
> Las direcciones viejas (como `/geo/mapa-kennedy/`) redirigen solas a la
> nueva app.

---

## 0. Glosario rápido

| Término | Qué es |
|---------|--------|
| **Evento / Actividad** | Un hecho georreferenciado (curso, entrega, banco, festival, obra…) que aparece como punto en el mapa |
| **Capa** | Un grupo de elementos que se prende o apaga (parques, barrios, UPZ, escenarios, obras…) |
| **UPZ** | Unidad de Planeamiento Zonal (subdivisión del suelo urbano) |
| **Subgrupo** | Área temática dentro de Inversión Local (Cultura, Deporte, Educación, Mujer…) |
| **KPI** | Indicador de meta al que aporta la actividad |
| **Equipamiento** | Escenarios de Cultura y Deporte (canchas, salones, parques con dotación) |
| **Malla vial / obras** | Tramos viales y parques en obra con su % de avance |

---

## 1. Abrir el mapa

**Quién:** Cualquier usuario con sesión (todos los roles tienen acceso
al módulo `mapa_kennedy`).

### Paso a paso

1. Iniciar sesión en `http://<servidor>/app/auth/login`.
2. En el hub principal (`/app/`) o en el menú lateral, click en
   **"Mapa de Kennedy"** → `http://<servidor>/app/mapa`.
3. El mapa carga centrado en la localidad de Kennedy con los eventos
   georreferenciados y el contorno de la localidad.

### Lo que ves al abrir

- **Encabezado** con el título "Mapa de Kennedy" y 3 KPIs rápidos:
  - **Eventos** (visibles en la vista actual).
  - **Hoy** (eventos del día).
  - **Próximos** (eventos futuros).
- **Panel lateral izquierdo** con dos secciones: **Filtros** y **Capas**.
- **Pestañas superiores** por subgrupo de Inversión Local (Todos /
  Cultura / Deporte / Educación / …) con un contador por cada uno.
- El **mapa** (Leaflet) con los puntos de colores.
- Debajo: sección de **Análisis de actividades** (gráficas) y una
  **tabla de eventos**.

### Captura sugerida

- Vista inicial completa: panel lateral + mapa + KPIs arriba.

---

## 2. Filtrar los eventos

**Dónde:** panel lateral, sección **"Filtros"**.

Los filtros reducen qué eventos se muestran (puntos + tabla + gráficas):

- **Tipo de evento** — chips que se prenden/apagan (Banco, Curso,
  Entrega, Festival, Caracterización, etc.). Click en un chip lo activa
  o desactiva.
- **Dependencia** — lista desplegable (— Todas — / INVERSIÓN LOCAL / …).
- **Subgrupo** — chips por área temática (Cultura, Deporte, Educación…).
- **Buscar** — caja de texto libre: filtra por **nombre, dirección o
  dependencia** del evento.
- Botón **"Limpiar"** — resetea todos los filtros a su estado inicial.

> Los filtros y las pestañas de subgrupo (arriba del mapa) trabajan
> juntos: la pestaña activa acota a un subgrupo y los chips afinan
> dentro de esa selección.

### Captura sugerida

- Panel de Filtros con un tipo y un subgrupo seleccionados + caja de
  búsqueda con texto.

---

## 3. Prender y apagar capas

**Dónde:** panel lateral, sección **"Capas"**.

Cada capa es una casilla ✅ que muestra u oculta un grupo de elementos:

**Capas de eventos (por tipo):**
- Una casilla por cada **tipo de evento**, con su punto de color
  (verde/azul/naranja/morado…). Apagar un tipo oculta esos puntos.

**Capas de referencia territorial:**
- 🟩 **Parques** — polígonos de parques de la localidad.
- ▫️ **Barrios** — límites de barrios.
- ▫️ **UPZ** — límites de las UPZ.
- ➖ **Localidad** — contorno de Kennedy.

**Capas especiales:**
- 🫧 **Oferta formativa (cursos por sede)** — burbujas con la cantidad
  de cursos por sede/escenario.
- ★ **Festivales** — eventos tipo festival marcados con estrella.
- ➖ **Malla vial / obras** — tramos viales en obra, coloreados por
  avance.
- 🌳 **Parques (obras)** — parques en obra, coloreados por avance.

**Leyenda de avance** (aparece al prender Malla vial u Obras):
- 🔴 **0%** (sin iniciar) · 🟡 **Parcial** · 🟢 **100%** (terminado).

> **Equipamiento (escenarios de Cultura y Deporte):** se muestra según
> el **subgrupo seleccionado** en las pestañas de arriba del mapa, no
> con una casilla propia. Selecciona el subgrupo Cultura o Deporte para
> verlos.

### Captura sugerida

- Sección de Capas con varias casillas activas + la leyenda de avance
  visible (con Malla vial prendida).

---

## 4. Pestañas por subgrupo (Inversión Local)

**Dónde:** franja de pestañas justo encima del mapa.

- **"Todos"** muestra todo; cada pestaña (Cultura, Deporte, Educación,
  Mujer…) acota el mapa a ese subgrupo.
- Cada pestaña trae un **contador** con el total de actividades de ese
  subgrupo.
- Al elegir un subgrupo, además de acotar los eventos se muestra el
  **equipamiento** (escenarios) correspondiente a esa área.

### Captura sugerida

- Franja de pestañas con "Deporte" activa y su contador visible.

---

## 5. Ver el detalle de un punto

**Quién:** cualquier usuario.

- Click en un **punto de evento** abre un **popup** con: nombre, fecha,
  dependencia, funcionario, dirección y (si aplica) el KPI al que aporta.
- Click en un **tramo vial** u **obra** muestra su información y % de
  avance.
- Los polígonos (parques, barrios, UPZ) resaltan el área al pasar.

### Captura sugerida

- Popup de un evento abierto sobre el mapa.

---

## 6. Análisis de actividades (gráficas)

**Dónde:** debajo del mapa, sección **"Análisis de actividades"**.

Las gráficas se recalculan según los filtros activos:

**Tarjetas resumen (stat cards):**
- **En vista** — eventos actualmente mostrados.
- **Ejecutados** — eventos ya realizados.
- **Próximos** — eventos futuros.
- **Con KPI** — cuántos aportan a un indicador.

**Gráficas:**
- **Por tipo de actividad** (dona).
- **Por subgrupo (top 8)** (barras).
- **Evolución mensual** (línea).

### Captura sugerida

- Sección de análisis con las 4 tarjetas + las 3 gráficas.

---

## 7. Tabla de eventos

**Dónde:** al final de la página, sección **"Eventos en el mapa"**.

Tabla con los eventos visibles (respeta los filtros):
- **Nombre · Fecha · Tipo · Dependencia · Dirección.**

Sirve como listado navegable de lo que hay en el mapa en ese momento.

### Captura sugerida

- Tabla con varias filas de eventos.

---

## 8. Cómo llegan los eventos al mapa

Para que una actividad aparezca georreferenciada:

- Al **crear el evento** (`/app/eventos/nueva`) se le asigna un **Lugar
  de incidencia** (coordenadas).
- Si se crea **sin coordenadas**, el sistema lo ubica automáticamente en
  la **Alcaldía** para que igual salga en el mapa.
- Las obras (tramos viales / parques) y la oferta formativa se alimentan
  de sus propios módulos y catálogos.

> Si un evento no aparece donde debería, revisar su Lugar de incidencia
> en la edición del evento (`/app/eventos/<id>/editar`).

---

## 9. Roles y permisos

| Rol | Ver el mapa | Filtros y capas | Análisis y tabla |
|-----|-------------|-----------------|-------------------|
| **Admin** | ✅ | ✅ | ✅ |
| **Líder** | ✅ | ✅ | ✅ |
| **LiderParticipacion** | ✅ | ✅ | ✅ |
| **Coordinador** | ✅ | ✅ | ✅ |
| **CoordinadorDeportes** | ✅ | ✅ | ✅ |
| **Docente** | ✅ | ✅ | ✅ |
| **UsuarioGeneral** | ✅ | ✅ | ✅ |

> El mapa (módulo `mapa_kennedy`) está disponible para **todos los
> roles** con sesión. No hay versión pública sin login del mapa
> completo.

---

## 10. Flujo recomendado para grabar el video tutorial

Sugerencia de guion (6-8 minutos):

| Minuto | Sección | Pantallas |
|--------|---------|-----------|
| 0:00-0:45 | Intro: qué es el mapa, para qué sirve | `/app/mapa` vista inicial |
| 0:45-2:00 | Recorrido: KPIs, panel de filtros, capas | Panel lateral |
| 2:00-3:30 | Filtrar por tipo/subgrupo + búsqueda | Chips + caja Buscar |
| 3:30-4:30 | Prender/apagar capas + leyenda de avance | Sección Capas |
| 4:30-5:15 | Pestañas por subgrupo + equipamiento | Franja de pestañas |
| 5:15-6:15 | Click en un punto (popup) + análisis | Popup + gráficas |
| 6:15-7:00 | Cierre: dónde pedir ayuda | Logo Alcaldía + URL |

---

## 11. URLs consolidadas

> Todo bajo `http://<servidor>/app/`. Las URLs viejas redirigen solas.

### Interfaz
- Mapa de Kennedy: `http://<servidor>/app/mapa`
- Iniciar sesión: `http://<servidor>/app/auth/login`
- Hub principal: `http://<servidor>/app/`

### Endpoints de datos (uso técnico — el mapa los consume solo)
- Catálogos del mapa: `/geo/api/mapa/catalogos/`
- Eventos (GeoJSON): `/geo/api/eventos/`
- Contorno localidad: `/geo/api/kennedy/contorno/`
- UPZ: `/geo/api/kennedy/upz/`
- Barrios: `/geo/api/kennedy/barrios/`
- Parques: `/geo/api/kennedy/parques/`
- Escuelas: `/geo/api/kennedy/escuelas/`
- Tramos viales (obras): `/geo/api/mapa/tramos-viales/`
- Parques en obra: `/geo/api/mapa/parques-obras/`

---

## 12. Soporte

- **Soporte técnico**: equipo de sistemas (ing. Alex Aguilar).
- **Errores del sistema**: reportar con captura de pantalla.
- **Un evento no aparece / aparece en el lugar equivocado**: revisar su
  Lugar de incidencia en `/app/eventos/<id>/editar`.

---

> Documento generado el **2026-07-08** para la interfaz Angular
> (`/app/mapa`). Si el sistema cambia (nuevas capas, filtros o reglas),
> actualizar este manual.

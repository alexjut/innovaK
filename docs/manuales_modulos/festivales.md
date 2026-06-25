# Manual de uso — Módulo de FESTIVALES

**Proyecto 2780 "Kennedy Proyecta Talento" · Meta 4 (eventos culturales)**
**Alcaldía Local de Kennedy · Subgrupo Cultura (Inversión Local)**

> Este documento es para el **equipo de Cultura**: explica cómo manejar
> el módulo de Festivales de innovaK de principio a fin — crear el
> festival, armar su programación por días, registrar el lineup y los
> jurados, calificar artistas, subir evidencias, contar el aforo con QR,
> ver el avance de la meta y publicar la ficha pública.
>
> Lenguaje: directo, paso a paso, sin tecnicismos.

---

## ¿Para qué sirve este módulo?

Un festival no es un solo evento: dura varios días, tiene varios actos,
artistas, jurados, público y evidencias. Este módulo organiza **todo eso
en un solo lugar** y, lo más importante, **conecta cada festival con la
meta del proyecto**: cada acto que se ejecuta suma al indicador de eventos
de la Meta 4 del proyecto 2780, y se ve reflejado en el tablero de
seguimiento (avance, aforo y presupuesto).

## ¿Quién puede entrar?

Tienen acceso los roles **Administrador**, **Líder** y **Coordinador de
Cultura**. Se entra desde el menú con el usuario y contraseña del sistema.

**Cómo llegar:** menú **Actividades → Festivales**, o directamente en
`/app/festivales`.

---

## Paso a paso

### 1. Crear o editar la ficha del festival

1. En el listado de Festivales, botón **"Nuevo festival"**.
2. Llena: **nombre**, **tipo** (Rock, Salsa, Vallenato…), **vigencia**
   (el año), **número de edición**, **fechas** de inicio y fin,
   **descripción** y **responsable**.
3. **Ubícalo en el mapa:** haz clic en el minimapa para fijar el punto;
   así el festival sale en el Mapa de Kennedy.
4. Guarda. El festival nace en estado **Planeado**.

> **Regla:** máximo 15 festivales activos por año (es el tope de la meta).
> Para crear uno más, primero hay que cerrar otro.

### 2. Programar los días (la agenda)

Entra al festival (clic en su tarjeta) → sección **"Programación por
días"**.

1. Botón **"Agregar día"**: pon la **fecha**, un **título** (ej. "Día de
   apertura"), el **escenario** y el **responsable del día**.
2. Repite por cada día del festival. Se ven como una agenda en orden.
3. **Los actos** (cada concierto/novena/presentación) son eventos del
   sistema tipo *Festival*. Cuando un acto está creado pero sin ubicar,
   aparece abajo en **"Actos sin día"**: usa el selector para asignarlo
   a la jornada que corresponde.

> Borrar un día **no borra los actos**: quedan disponibles para
> reubicarlos.

### 3. Lineup, jurados y evaluación

En el detalle del festival → sección **"Lineup y evaluación"**, con tres
columnas:

- **Lineup:** agrega los artistas, grupos o invitados (con su día).
- **Jurados:** agrega los jurados (nombre y perfil). *El jurado no entra
  al sistema:* el funcionario transcribe sus notas.
- **Criterios:** define los criterios de calificación y su **peso**
  (ej. "Calidad artística" peso 3, "Pertinencia" peso 2).

**Para calificar:** abajo, en **"Planilla de calificación"**, elige un
jurado y escribe la nota de cada artista por cada criterio. El sistema
calcula el **ranking** automáticamente (promedio ponderado por el peso de
los criterios). El podio se resalta.

> Cuando el festival se marca como **Cerrado**, la evaluación queda en
> solo lectura (ya no se puede cambiar).

### 4. Biblioteca de evidencias

En el detalle → sección **"Biblioteca / evidencias"**.

1. Elige el **tipo** (Foto, Video, Acta, Listado de asistencia, Soporte),
   opcionalmente el **día**, una **descripción** y el archivo.
2. Botón **"Subir evidencia"**.

Reglas importantes:
- **Las fotos se optimizan solas** (se reducen y comprimen) para no pesar.
- **Máximo 3 fotos por festival** por ahora (para subir otra, borra una).
- Todo se guarda **cifrado y seguro**; las fotos se ven en la galería y
  los documentos se descargan con un clic.

### 5. Aforo por QR (contar el público)

Cada **acto** tiene su propio **código QR** (se genera desde el evento del
acto, igual que los demás QR del sistema).

- El público escanea el QR y cae en una pantalla móvil con un **contador
  en vivo**.
- Un toque en **"Sumar 1 asistente"** cuenta a una persona (anónimo).
- Si se quiere, la persona puede dejar datos mínimos (documento, sexo,
  edad, localidad). *Un mismo documento no se cuenta dos veces.*

Desde el detalle del festival, en cada acto puedes fijar el **aforo
proyectado** (la meta de público) haciendo clic en el número de aforo.
El aforo real vs. proyectado se ve en el tablero.

### 6. Cómo suma a la meta

El indicador de la Meta 4 cuenta **eventos (actos)**. Funciona así:

- Mientras el festival está **Planeado**, no suma nada.
- Cuando cambias el estado a **Ejecutado** o **Cerrado**, **cada acto
  del festival suma +1** al indicador automáticamente.
- Si te equivocas y lo devuelves a **Planeado**, se revierte solo.

No hay que registrar nada a mano en presupuesto: el avance fluye desde
aquí hacia el tablero del proyecto 2780.

### 7. Tablero de seguimiento

Botón **"Seguimiento"** en el listado (o `/app/festivales/insights`).

Muestra, por año:
- Festivales por estado y **actos contabilizados**.
- **Aforo total** registrado.
- **Avance real del indicador** (cuánto se lleva de la meta) con barras.
- **Presupuesto del 2780**: asignado, ejecutado y disponible.
- Detalle por festival (actos, días, evidencias, aforo).

### 8. Publicar la ficha web pública

En el detalle del festival, botón **"Publicar"**.

- Genera una **página pública** (sin login) con la programación, la
  galería de fotos y el aforo: ideal para difundir.
- Sale el botón **"Ver ficha pública"** con el enlace para compartir
  (`/app/p/festival/<nombre>`).
- Se puede **Despublicar** en cualquier momento.

---

## Flujo recomendado (de principio a fin)

1. **Crear la ficha** del festival (datos + ubicación en el mapa).
2. **Armar la agenda**: crear los días.
3. **Crear los actos** (eventos tipo Festival) y asignarlos a su día.
4. **Registrar lineup, jurados y criterios**; fijar aforo proyectado.
5. Durante el festival: **contar aforo con el QR** de cada acto y **subir
   evidencias**.
6. **Calificar** artistas en la planilla (el ranking se arma solo).
7. Marcar el festival como **Ejecutado** → **suma a la meta**.
8. Revisar el **tablero de seguimiento**.
9. **Publicar la ficha pública** para difusión.
10. Al terminar todo, marcar como **Cerrado** (congela la evaluación).

---

## Preguntas frecuentes

**¿Por qué no me deja subir una 4ª foto?**
Hay un tope de 3 fotos por festival por ahora. Borra una para subir otra
(videos, actas y listados no tienen ese límite).

**¿Por qué un acto no suma a la meta?**
El acto suma cuando el festival está en **Ejecutado** o **Cerrado** y el
acto está ligado a su actividad del plan. Si está **Planeado**, no suma.

**El mismo asistente puede registrarse dos veces en el aforo?**
Si deja documento, no: el sistema lo evita. Si es conteo anónimo, cada
toque cuenta.

**¿El jurado necesita usuario?**
No. El funcionario transcribe las notas de los jurados en la planilla.

---

*Dudas o ajustes: contactar al área de sistemas / Líder Técnico de
Innovación.*

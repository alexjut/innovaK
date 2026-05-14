# Manual de uso — Banco de Iniciativas Recreodeportivas

**Proyecto 2784 · Alcaldía Local de Kennedy · Meta 280 organizaciones**

> Este documento es la **guía operativa** del módulo Banco de
> Iniciativas. Está pensado para el equipo de **comunicaciones** que va
> a producir el video tutorial: cada sección explica qué hace cada
> pantalla, con URL exacta y captura sugerida.
>
> Lenguaje: directo, paso a paso, sin tecnicismos.

---

## 0. Glosario rápido

| Término | Qué es |
|---------|--------|
| **Inscripción** | Postulación de una organización al Banco (1 evento → muchas inscripciones) |
| **Evento Banco** | La convocatoria abierta en una fecha. Tiene un QR que se comparte. |
| **Beneficiario** | Persona u organización registrada en el sistema de la Alcaldía |
| **UPL** | Unidad de Planeación Local (Kennedy tiene 9) |
| **Wizard** | Formulario público que llena la organización sin necesidad de login |
| **Insights** | Tablero de gráficas tipo Power BI para análisis |

---

## 1. Crear el evento de la convocatoria

**Quién:** Coordinador de Deportes o Administrador.
**Cuándo:** Antes de abrir la convocatoria al público.

### Paso a paso

1. Iniciar sesión en `http://<servidor>/login/`.
2. Ir al hub principal: `/dashboard/`.
3. Click en card **"Actividades"** → `/dashboard/hub/actividades/`.
4. Click en **"Crear actividad"** → `/evento/crear/`.
5. En el formulario:
   - **Tipo de evento:** elegir `BANCO_INICIATIVAS` (clave para que se
     genere QR público y se acepten inscripciones de organizaciones).
   - **Nombre:** descriptivo (ej. "Convocatoria Banco 2026 — Cultura").
   - **Fecha inicio** y **Fecha fin:** rango en que la convocatoria
     acepta postulaciones.
   - **Dependencia:** INVERSIÓN LOCAL.
   - **Subgrupo:** el tema (Cultura / Deporte / Mujer / etc.).
   - **Funcionario titular:** el responsable.
   - **Lugar de incidencia:** opcional.
6. **Guardar.** El sistema genera automáticamente la URL pública con QR.

### Captura sugerida

- Pantalla del formulario `crear_evento.html` resaltando el campo
  "Tipo de evento" con `BANCO_INICIATIVAS` seleccionado.

---

## 2. Compartir el QR con las organizaciones

**Quién:** Coordinador o equipo de comunicaciones.

### Paso a paso

1. Ir a la lista de actividades: `/eventos/`.
2. Buscar el evento creado.
3. Click en el botón **"QR"** (icono azul) → muestra el código QR del
   formulario público.
4. La URL pública es: `http://<servidor>/banco-iniciativas/<id>/inscribir/`
   (donde `<id>` es el número del evento).
5. **Descargar el QR como imagen** o **copiar la URL** y enviar por
   WhatsApp, redes sociales, correo a las organizaciones interesadas.

### Captura sugerida

- Pantalla con el QR visible en grande + la URL pública debajo.

---

## 3. Las organizaciones llenan el formulario (público, sin login)

**Quién:** Cualquier organización con el QR o el link directo.
**Tiempo estimado:** 15-25 minutos completando todas las secciones.

### Estructura del formulario público

Cuando la organización abre el link, ve un **wizard de 8 pasos**:

1. **Información de la organización**
   - Nombre, NIT, tipo (persona jurídica, club avalado, etc.),
     correo, teléfono, **redes sociales** (Facebook, Instagram, TikTok,
     YouTube, etc.).

2. **Representante legal**
   - Tipo y número de documento.
   - **4 campos separados** de nombre/apellido (primer/segundo).
   - **Autollenado por cédula**: cuando la organización escribe la
     cédula del representante y este YA está registrado en la
     Alcaldía (porque participó en otra actividad), los 4 campos se
     llenan solos con sus datos previos.
   - Años de experiencia, nivel educativo, títulos obtenidos.
   - Soporte legal (URL al PDF de existencia y representación).

3. **Escenarios actuales y solicitados**
   - Selección múltiple de escenarios donde la organización **ya
     desarrolla** sus actividades (uso actual).
   - Selección múltiple de escenarios que **necesita** para la
     propuesta (lo que solicita).

4. **Implementos requeridos**
   - Lista de 35 implementos clasificados por categoría (deportivo,
     tecnológico, logístico).

5. **Población a atender**
   - Rango de cuántas personas (1-50, 50-100, 100+, etc.).
   - Estrato socioeconómico.
   - Característica de población.
   - Rangos etarios (infancia, juventud, adulto, mayor).
   - Enfoques diferenciales (mujer, LGBTI, víctima, indígena, etc.).

6. **Beneficios previos de la Alcaldía**
   - ¿Ya recibió apoyo antes? ¿Qué tipo?
   - Justificación.

7. **Disciplina principal + propuesta**
   - Disciplina deportiva principal (Fútbol, Futsala, Baloncesto,
     etc. — son 14 disciplinas catalogadas).
   - URL de la propuesta (PDF en Drive, Dropbox, OneDrive).
   - Descripción libre.

8. **Compromisos y firma**
   - 3 compromisos a aceptar:
     - 📱 Mantener redes sociales activas.
     - 📄 Entregar carta de informe a 1 año.
     - 🔄 Actualizar datos cuando cambien.
   - **Firma digital obligatoria**: foto de la firma manuscrita
     desde la cámara del celular, O URL externa a una foto. El
     archivo se cifra automáticamente y se guarda seguro.

Al **enviar**, la organización ve una pantalla de éxito con el ID de
su postulación.

### Captura sugerida

- Una pantalla por cada paso del wizard (las 8 secciones).

---

## 4. El organizador revisa las inscripciones

**Quién:** Coordinador o Administrador con módulo `banco_iniciativas`.

### Lista de inscripciones

**URL:** `/banco-iniciativas/inscripciones/`

Lo que ves:
- Tabla paginada con todas las inscripciones recibidas.
- **Filtros**: por estado (borrador / enviada / validada / rechazada),
  por evento, búsqueda por nombre de organización.
- Botones de acción superiores derechos:
  - **⬇️ Descargar CSV** — descarga todas las inscripciones filtradas
    como hoja de cálculo con 51 columnas (análisis completo).
  - **📊 Insights** — abre el dashboard analítico (ver §6).

### Detalle de una inscripción

**URL:** `/banco-iniciativas/inscripciones/<id>/`

Muestra todos los datos capturados + acciones:
- **Validar** ✅: la inscripción cumple requisitos → estado `validada`.
- **Rechazar** ❌: NO cumple → estado `rechazada`.
- **Ver firma**: imagen descifrada del consentimiento.

### Captura sugerida

- Lista con varias inscripciones en distintos estados (badges de color).
- Detalle de una inscripción mostrando la firma cargada.

---

## 5. Descargar datos para análisis externo

### 5.1 Descargar inscripciones del Banco (51 columnas)

**URL botón:** `/banco-iniciativas/inscripciones/` → botón
**"⬇️ Descargar CSV"**.

Endpoint directo: `/banco-iniciativas/inscripciones/exportar/`

Contiene:
- Cabecera: ID, estado, fechas, proyecto.
- Organización: ID, NIT, tipo, contacto.
- Representante completo.
- Datos del formulario (UPL, barrio, disciplina, etc.).
- Compromisos asumidos.
- Calidad del dato (firma, soporte legal, propuesta).
- Conteos de M2M (cuántos escenarios, cuántos implementos, etc.).
- Beneficiario vinculado.

### 5.2 Descargar beneficiarios globales (Excel)

**URL botón:** `/org/beneficiarios/` → botón **"📊 Descargar Excel"**.

Endpoint directo: `/org/beneficiarios/exportar/excel/`

Es un Excel real (.xlsx) con:
- Hoja **"Beneficiarios"**: 16 columnas con header rojo institucional,
  filas alternadas, anchos ajustados, header congelado.
- Hoja **"Resumen"**: total + cantidad por tipo + fecha de descarga.
- Filtros respetados (si filtras por `?tipo=PERSONA`, solo descarga
  personas).

### Captura sugerida

- Excel abierto mostrando las 2 hojas (Beneficiarios + Resumen).
- Cabecera roja con texto blanco visible.

---

## 6. Dashboard Insights del Banco (análisis Power BI)

**URL botón:** `/banco-iniciativas/inscripciones/` → botón
**"📊 Insights"**.

Endpoint directo: `/banco-iniciativas/inscripciones/insights/`

Lo que muestra:

### KPIs principales (4 cards arriba)
- **Total inscripciones** + barra de avance vs meta 280.
- **Validadas** (verde).
- **Pendientes** (amarillo).
- **Rechazadas** (rojo).

### Gráficas
1. **Funnel de estados** (donut)
2. **Tipo de organización** (donut)
3. **Cobertura territorial UPL** (bar horizontal) — qué UPLs están
   más representadas y cuáles faltan.
4. **Disciplinas deportivas top** (bar multicolor).
5. **Enfoques diferenciales** (donut) — qué poblaciones priorizan.
6. **Beneficios ALK previos** (donut).
7. **Gap de escenarios** (stacked bar) — qué escenarios necesitan
   más vs los que ya usan. Detecta infraestructura faltante.
8. **Impacto en políticas** (polar area).

### Calidad del dato (gauges)
- % con firma cifrada.
- % con soporte legal.
- % avance vs meta.

### 🔍 Insights no obvios
- **Inequidad ALK**: ¿se validan más rápido las organizaciones que ya
  recibieron apoyo antes? Detecta sesgo institucional.
- **Sobre-dimensionamiento**: implementos por inscripción
  (promedio/máximo). Detecta organizaciones inflando solicitudes.
- **Cobertura territorial**: cuántas UPLs sin postulación.

**Botón:** "📥 Descargar data del Banco" en el header del dashboard
descarga el mismo CSV de 51 columnas.

### Captura sugerida

- Pantalla del dashboard scroll-to-top mostrando KPIs + primeras 2
  gráficas.
- Scroll medio mostrando Gap escenarios + Calidad del dato.
- Scroll inferior con cards de Insights no obvios.

---

## 7. Roles y permisos (quién puede hacer qué)

| Rol | Puede ver inscripciones | Puede validar | Insights | Descargar | Beneficiarios |
|-----|------------------------|---------------|----------|-----------|---------------|
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Líder** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **CoordinadorDeportes** (Daniel) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Docente** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **UsuarioGeneral** | ❌ | ❌ | ❌ | ❌ | ❌ |

> Cualquier persona, con o sin cuenta, puede llenar el formulario
> público vía QR — no requiere login. Solo el **organizador**
> requiere cuenta para revisar.

---

## 8. Flujo recomendado para grabar el video tutorial

Sugerencia de guion (10-12 minutos):

| Minuto | Sección | Pantallas |
|--------|---------|-----------|
| 0:00-1:00 | Intro: qué es el Banco, meta 280, proyecto 2784 | Logo Alcaldía + diagrama del flujo |
| 1:00-2:30 | Cómo el coordinador crea el evento de convocatoria | `/evento/crear/` con `BANCO_INICIATIVAS` |
| 2:30-3:30 | Cómo se comparte el QR | Lista `/eventos/` → botón QR → pantalla QR |
| 3:30-5:30 | Demo del formulario público (los 8 pasos) | `/banco-iniciativas/<id>/inscribir/` |
| 5:30-6:30 | Pantalla final + email/whatsapp de confirmación | Pantalla `inscripcion_exitosa` |
| 6:30-8:00 | Organizador revisa: lista, detalle, validar/rechazar | `/banco-iniciativas/inscripciones/` |
| 8:00-9:30 | Dashboard Insights con todas las gráficas | `/banco-iniciativas/inscripciones/insights/` |
| 9:30-10:30 | Descarga de datos a Excel/CSV | Botones de descarga |
| 10:30-12:00 | Cierre: dónde pedir ayuda + meta del proyecto | Logo Alcaldía + URL del sistema |

---

## 9. URLs consolidadas

### Para organizaciones (público, sin login)
- Formulario de inscripción: `http://<servidor>/banco-iniciativas/<id>/inscribir/`
- Pantalla exitosa: `http://<servidor>/banco-iniciativas/exitoso/<id>/`

### Para organizadores (requiere login + módulo `banco_iniciativas`)
- Lista de inscripciones: `http://<servidor>/banco-iniciativas/inscripciones/`
- Detalle: `http://<servidor>/banco-iniciativas/inscripciones/<id>/`
- Validar/rechazar: botones en detalle.
- Ver firma cifrada: `http://<servidor>/banco-iniciativas/inscripciones/<id>/firma/`
- **Insights dashboard**: `http://<servidor>/banco-iniciativas/inscripciones/insights/`
- **Descargar CSV (51 cols)**: `http://<servidor>/banco-iniciativas/inscripciones/exportar/`

### Para gestión de beneficiarios (requiere módulo `org_admin`)
- Lista global: `http://<servidor>/org/beneficiarios/`
- **Descargar Excel**: `http://<servidor>/org/beneficiarios/exportar/excel/`
- Descargar CSV: `http://<servidor>/org/beneficiarios/exportar/`

### Para gestión del evento (requiere módulo `eventos`)
- Lista de eventos: `http://<servidor>/eventos/`
- Crear evento: `http://<servidor>/evento/crear/`
- Editar evento: `http://<servidor>/evento/<id>/editar/`
- QR del evento: `http://<servidor>/qr/<id>/`
- **Dashboard Insights de Eventos**: `http://<servidor>/eventos/insights/`

---

## 10. Soporte

- **Soporte técnico**: contactar al equipo de sistemas
  (ing. Alex Aguilar).
- **Errores del sistema**: reportar con captura de pantalla.
- **Datos faltantes** (catálogos, etc.): el administrador puede
  agregarlos desde `/admin/` (Django admin).

---

> Documento generado el **2026-05-14** · Última actualización con la
> versión actual del módulo. Si el sistema cambia (nuevos campos,
> nuevas reglas), actualizar este manual.

# Manual de uso — Banco de Iniciativas Recreodeportivas

**Proyecto 2784 · Alcaldía Local de Kennedy · Meta 280 organizaciones**

> Este documento es la **guía operativa** del módulo Banco de
> Iniciativas. Está pensado para el equipo de **comunicaciones** que va
> a producir el video tutorial: cada sección explica qué hace cada
> pantalla, con URL exacta y captura sugerida.
>
> Lenguaje: directo, paso a paso, sin tecnicismos.

> **⚠️ Importante — la interfaz ahora es Angular.** Todo el sistema se usa
> desde una sola aplicación web bajo `http://<servidor>/app/`. Las
> direcciones viejas (como `/dashboard/` o `/banco-iniciativas/...`) ya
> **no** se navegan a mano: el sistema redirige automáticamente a la nueva
> app. En este manual las URLs empiezan por `/app/`. Los enlaces y QR
> impresos con las direcciones antiguas **siguen funcionando** (redirigen
> solos), pero para grabar el tutorial usa siempre las nuevas.

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
| **Token del QR (`?t=`)** | Firma de seguridad que lleva cada enlace público generado por el sistema. No hace falta escribirlo: viene incluido en el QR y la URL que copies desde el sistema. |

---

## 1. Crear el evento de la convocatoria

**Quién:** Coordinador de Deportes o Administrador.
**Cuándo:** Antes de abrir la convocatoria al público.

### Paso a paso

1. Iniciar sesión en `http://<servidor>/app/auth/login`.
2. Entras al hub principal: `http://<servidor>/app/`.
3. Click en card **"Actividades"** → `/app/actividades`.
4. Click en **"Crear actividad"** (botón "Crear actividad" del hub) →
   `/app/eventos/nueva`.
5. En el formulario:
   - **Tipo de evento:** elegir `BANCO_INICIATIVAS` (clave para que se
     genere QR público y se acepten inscripciones de organizaciones).
   - **Nombre:** descriptivo (ej. "Convocatoria Banco 2026 — Cultura").
   - **Fecha inicio** y **Fecha fin:** rango en que la convocatoria
     acepta postulaciones.
   - **Dependencia:** INVERSIÓN LOCAL.
   - **Subgrupo:** el tema (Cultura / Deporte / Mujer / etc.).
   - **Funcionario titular:** el responsable.
   - **Lugar de incidencia:** opcional. Si lo dejas vacío, el evento se
     ubica automáticamente en la Alcaldía para que salga en el mapa.
6. **Guardar.** El sistema genera automáticamente la URL pública con QR
   (que ya incluye el token de seguridad `?t=`).

### Captura sugerida

- Pantalla del formulario de crear actividad (`/app/eventos/nueva`)
  resaltando el campo "Tipo de evento" con `BANCO_INICIATIVAS`
  seleccionado.

---

## 2. Compartir el QR con las organizaciones

**Quién:** Coordinador o equipo de comunicaciones.

### Paso a paso

1. Ir al hub de Actividades → card **"Banco de Iniciativas"** → elegir el
   **subgrupo** → verás la lista de eventos de ese tipo.
   (También llegas por la lista general de eventos: `/app/eventos`.)
2. Buscar el evento creado en la tabla.
3. En la fila del evento, botones **"Formulario"** y **"QR"**:
   - **"Formulario"** abre el formulario público en una pestaña nueva
     (el mismo que llena la organización).
   - **"QR"** → `/app/eventos/<id>/qr` muestra el código QR para
     compartir/descargar.
4. La URL pública tiene esta forma:
   `http://<servidor>/app/p/banco/<id>?t=<token>`
   (donde `<id>` es el número del evento; el `?t=` lo agrega el sistema
   solo).
5. **Descargar el QR como imagen** o **copiar la URL** y enviar por
   WhatsApp, redes sociales o correo a las organizaciones interesadas.

> El QR debe generarse/copiarse **desde el sistema** para que lleve el
> token. No armes la URL a mano.

### Captura sugerida

- Fila del evento mostrando los botones "Formulario" y "QR".
- Pantalla `/app/eventos/<id>/qr` con el QR visible en grande + la URL
  pública debajo.

---

## 3. Las organizaciones llenan el formulario (público, sin login)

**Quién:** Cualquier organización con el QR o el link directo.
**Tiempo estimado:** 15-25 minutos completando todas las secciones.
**URL:** `http://<servidor>/app/p/banco/<id>?t=<token>` (sin necesidad de
cuenta).

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

**URL:** `/app/banco`

Cómo llegar: desde **Actividades → card "Banco de Iniciativas" →
subgrupo → evento → botón "Beneficiarios"** (abre la lista filtrada por
ese evento). También puedes ir directo a `/app/banco` para ver todas.

Lo que ves:
- Tabla paginada con todas las inscripciones recibidas.
- Tarjetas de resumen (Insights rápidos) arriba de la tabla.
- **Filtros**: por estado (borrador / enviada / validada / rechazada),
  por evento, búsqueda por nombre de organización.
- Botones de acción superiores:
  - **⬇️ Exportar CSV** — descarga todas las inscripciones filtradas
    como hoja de cálculo con 51 columnas (análisis completo).
  - **📊 Insights** — abre el dashboard analítico (ver §6).

### Detalle de una inscripción

**URL:** `/app/banco/<id>`

Muestra todos los datos capturados + acciones:
- **Validar** ✅: la inscripción cumple requisitos → estado `validada`.
- **Rechazar** ❌: NO cumple → estado `rechazada`.
- **Ver firma**: imagen descifrada del consentimiento.

### Captura sugerida

- Lista `/app/banco` con varias inscripciones en distintos estados
  (badges de color).
- Detalle `/app/banco/<id>` mostrando la firma cargada.

---

## 5. Descargar datos para análisis externo

> Las descargas se generan desde el sistema (Excel/CSV real) y bajan
> autenticadas con tu sesión — no expongas los archivos en carpetas
> públicas.

### 5.1 Descargar inscripciones del Banco (51 columnas)

**Dónde:** `/app/banco` → botón **"⬇️ Exportar CSV"**.

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

**Dónde:** `/app/admin/org` → pestaña **"Beneficiarios"** → botón
**"📊 Excel"** (requiere módulo `org_admin`).

Es un Excel real (.xlsx) con:
- Hoja **"Beneficiarios"**: 16 columnas con header rojo institucional,
  filas alternadas, anchos ajustados, header congelado.
- Hoja **"Resumen"**: total + cantidad por tipo + fecha de descarga.
- Filtros respetados (si filtras por tipo `PERSONA`, solo descarga
  personas).

### Captura sugerida

- Excel abierto mostrando las 2 hojas (Beneficiarios + Resumen).
- Cabecera roja con texto blanco visible.

---

## 6. Dashboard Insights del Banco (análisis Power BI)

**URL:** `/app/banco/insights`
**Cómo llegar:** `/app/banco` → botón **"📊 Insights"**.

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
| 1:00-2:30 | Cómo el coordinador crea el evento de convocatoria | `/app/eventos/nueva` con `BANCO_INICIATIVAS` |
| 2:30-3:30 | Cómo se comparte el QR | Actividades → evento → botones "Formulario"/"QR" → `/app/eventos/<id>/qr` |
| 3:30-5:30 | Demo del formulario público (los 8 pasos) | `/app/p/banco/<id>?t=...` |
| 5:30-6:30 | Pantalla final de confirmación | Pantalla de éxito con el ID de postulación |
| 6:30-8:00 | Organizador revisa: lista, detalle, validar/rechazar | `/app/banco` y `/app/banco/<id>` |
| 8:00-9:30 | Dashboard Insights con todas las gráficas | `/app/banco/insights` |
| 9:30-10:30 | Descarga de datos a Excel/CSV | Botones "Exportar CSV" / "Excel" |
| 10:30-12:00 | Cierre: dónde pedir ayuda + meta del proyecto | Logo Alcaldía + URL del sistema |

---

## 9. URLs consolidadas

> Todo el sistema vive bajo `http://<servidor>/app/`. Las URLs viejas
> redirigen solas, pero estas son las vigentes.

### Para organizaciones (público, sin login)
- Formulario de inscripción: `http://<servidor>/app/p/banco/<id>?t=<token>`
  (el `?t=` viene incluido en el QR/enlace que genera el sistema).

### Para organizadores (requiere login + módulo `banco_iniciativas`)
- Lista de inscripciones: `http://<servidor>/app/banco`
- Detalle: `http://<servidor>/app/banco/<id>`
- Validar/rechazar: botones en el detalle.
- Ver firma cifrada: botón "Ver firma" en el detalle.
- **Insights dashboard**: `http://<servidor>/app/banco/insights`
- **Exportar CSV (51 cols)**: botón "Exportar CSV" en la lista.

### Para gestión de beneficiarios (requiere módulo `org_admin`)
- Padrón global: `http://<servidor>/app/admin/org` → pestaña "Beneficiarios"
- **Descargar Excel / CSV**: botones en esa pestaña.

### Para gestión del evento (requiere módulo `eventos`)
- Lista de eventos: `http://<servidor>/app/eventos`
- Crear evento: `http://<servidor>/app/eventos/nueva`
- Editar evento: `http://<servidor>/app/eventos/<id>/editar`
- QR del evento: `http://<servidor>/app/eventos/<id>/qr`
- **Dashboard Insights de Eventos**: `http://<servidor>/app/eventos/insights`

### Acceso al sistema
- Iniciar sesión: `http://<servidor>/app/auth/login`
- Hub principal: `http://<servidor>/app/`

---

## 10. Soporte

- **Soporte técnico**: contactar al equipo de sistemas
  (ing. Alex Aguilar).
- **Errores del sistema**: reportar con captura de pantalla.
- **Datos faltantes** (catálogos, etc.): el administrador puede
  agregarlos desde `/admin/` (Django admin, uso técnico interno).

---

> Documento generado el **2026-05-14** · Actualizado el **2026-07-08**
> a la interfaz Angular (`/app/*`) con formularios públicos con token de
> seguridad en el QR. Si el sistema cambia (nuevos campos, nuevas
> reglas o rutas), actualizar este manual.

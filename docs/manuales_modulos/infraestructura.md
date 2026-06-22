# Manual de uso — Módulo INFRAESTRUCTURA

**Proyectos 2574 "Kennedy Crecimiento y Conexión" (vías) y 2790 "Kennedy Mi Parque Mi Espacio" (parques)**
**Alcaldía Local de Kennedy · Subgrupo Infraestructura (Inversión Local)**

> Este documento es para el **equipo de Infraestructura**: explica el
> módulo nuevo del sistema innovaK para hacer **seguimiento de los
> contratos de obra** (vías y parques), cómo registrar el avance y cómo
> todo se refleja solo en el mapa y en los indicadores.
> Lenguaje: directo, paso a paso, sin tecnicismos.

---

## Para empezar: correo de solicitud de responsables

> Texto sugerido para enviar (correo/WhatsApp al área):

> **Asunto:** innovaK — Designar responsables del seguimiento de obra (Infraestructura)
>
> Buen día.
>
> Ya está listo en el sistema **innovaK** el módulo de **Infraestructura**,
> para hacerle seguimiento a los contratos de obra de la localidad (vías y
> parques de los proyectos 2574 y 2790), registrar el avance de cada
> intervención con evidencia fotográfica (antes/después) y ver todo
> reflejado automáticamente en el **Mapa de Kennedy** y en los indicadores.
>
> Para ponerlo a operar necesitamos que **designen las personas
> responsables** y nos pasen, de cada una, estos datos:
>
> | Dato | Para qué |
> |------|----------|
> | Nombre completo | Crear su usuario |
> | Número de cédula | Identificación / vincular a funcionario |
> | Correo institucional | Acceso y notificaciones |
> | Celular | Contacto |
> | **Perfil** (ver abajo) | Definir qué puede hacer |
> | **Contrato(s) que maneja** | CIA-807, COP-816, CON-993, CON-791 (interventoría) |
>
> **Perfiles que necesitamos asignar:**
> - **Líder / Coordinador de Infraestructura** — ve todo el panorama,
>   administra los contratos, revisa insights y reportes.
> - **Responsable de seguimiento (interventoría / supervisor)** — es quien
>   **registra el avance** de cada vía/parque en terreno, con fotos
>   antes/después. Puede ser la persona de la **interventoría** (contrato
>   CON-791) o el supervisor del contrato.
>
> Apenas nos confirmen los responsables y sus datos, creamos los usuarios
> con su perfil y les pasamos el instructivo para que empiecen a cargar los
> cortes de avance.
>
> Quedamos atentos.

---

## 1. Qué es el módulo y quién lo usa

El módulo **Infraestructura** centraliza los **contratos de obra** de la
localidad y su avance:

- **Vías** (contrato CIA-807-2025): 30 tramos viales intervenidos.
- **Parques** (contratos COP-816-2025 y CON-993-2025): 13 parques.
- **Interventoría** (contrato CON-791-2015): hace seguimiento a la
  estabilidad y calidad de las obras (no tiene vías ni parques propios).

Dos roles principales:

- **Líder/Coordinador**: consulta, administra y reporta.
- **Seguimiento**: registra el avance de cada obra (los "cortes").

---

## 2. Cómo entrar

1. Ingresa a innovaK con tu usuario.
2. En el inicio, abre la tarjeta **"Infraestructura"** (o el ítem
   **Infraestructura** del menú lateral).

---

## 3. El panel (lo primero que ves)

Arriba, 5 indicadores rápidos:

- **Contratos** · **Valor total** · **% Avance global** · **Tramos (vías)** · **Parques**.

Abajo, la **lista de contratos** con su categoría (Vías / Parques /
Interventoría), proyecto, valor y barra de **% ejecución**. Haz clic en un
contrato para ver su detalle.

Botón **"Insights"**: gráficas de avance (tramos por estado 🔴🟠🟢, valor
por categoría, avance por contrato).

---

## 4. Crear un contrato nuevo

> El formulario se adapta a la **categoría** que elijas (no son iguales).

1. En el panel, **"Nuevo contrato"**.
2. Llena: **Número** (ej. `CIA-808-2026`), **Categoría** (Vías / Parques /
   Interventoría), **Proyecto** (2574 o 2790), **Objeto**, **Valor**,
   **Fechas**, **% Ejecución**, **Interventoría** (si aplica).
3. Guarda. Según la categoría, en el detalle podrás agregar **vías** o
   **parques** (o nada, si es interventoría).

---

## 5. Agregar VÍAS (categoría Vías)

En el detalle del contrato de vías, **"Agregar vía"**. Campos (los mismos
de su planilla):

- **Valor Intervención** · **CIV** · **PK ID** · **Eje Vial** · **Desde** ·
  **Hasta** · **% Avance Intervención**.

> Al guardar, el sistema **busca solo la ubicación real de la vía** por su
> **CIV** (en la Malla Vial oficial de Bogotá) y la pinta en el mapa
> automáticamente. No hay que dibujar nada.

---

## 6. Agregar PARQUES (categoría Parques)

En el detalle del contrato de parques, **"Agregar parque"**. Campos:

- **Código Parque** (lo eliges de la lista; al elegirlo se completa el
  **Nombre** solo) · **Dirección** · **% Avance Intervención**.

> El parque ya tiene su ubicación cargada, así que **aparece en el mapa de
> una vez**.

---

## 7. Registrar AVANCE — los "cortes" (lo más importante para seguimiento)

Así es como el responsable de seguimiento **"aumenta" el avance** de la
obra en el tiempo. Cada vez que hay un avance, se registra un **corte**:

1. En el detalle del contrato:
   - Para una **vía** o un **parque**: botón **"Registrar avance"** en su fila.
   - Para un contrato de **interventoría** (que no tiene vías/parques):
     botón grande **"Registrar avance"** del contrato.
2. En la ventana de corte, llena:
   - **Fecha** del corte.
   - **% Avance**.
   - **Observación** (qué se hizo).
   - **Foto ANTES** y **Foto DESPUÉS** (📷 tomar con el celular o subir).
3. Guarda.

Qué pasa automáticamente al guardar:

- Se actualiza el **% de esa vía/parque** (o del contrato en interventoría).
- Se **recalcula la ejecución** del contrato.
- Sube al **indicador (KPI)** del proyecto → se ve en los **dashboards y
  matrices**.
- El **color en el mapa** cambia según el avance (🔴 sin iniciar · 🟠 en
  proceso · 🟢 terminado).
- Las **fotos se guardan reducidas y seguras**, y quedan en el
  **historial** del ítem (puedes ver cómo iba en cada corte).

> El **historial de cortes** te deja ver, vía por vía y parque por parque,
> cómo ha ido avanzando en el tiempo, con sus fotos antes/después. Eso es
> el seguimiento minucioso.

---

## 8. El mapa

- En el **detalle del contrato** hay un **mini-mapa** con sus vías y
  parques, coloreados por avance.
- En el **Mapa de Kennedy** general, activa en **Capas** las opciones
  **"Malla vial / obras"** y **"Parques (obras)"** para ver todo junto, con
  leyenda de color por avance.

> Regla de oro: **todo lo que registres aparece solo en el mapa.** No hay
> que ubicar nada a mano.

---

## 9. Indicadores (KPI) y matrices

Cada proyecto tiene su meta:

- **2574** — *Tramos viales intervenidos* (meta 30).
- **2790** — *Parques intervenidos* (meta 13).

A medida que las vías/parques llegan al 100%, el indicador sube solo y se
refleja en los dashboards y en las dos matrices estándar del sistema.

---

## 10. Qué revisar y reportar (checklist para el área)

- [ ] ¿Los campos de **vías** y **parques** son los correctos para su operación?
- [ ] ¿El registro de **avance con fotos antes/después** les sirve como evidencia?
- [ ] ¿El **mapa** muestra las obras donde deben estar?
- [ ] ¿Falta alguna categoría de contrato o algún campo?
- [ ] ¿Quién será el **responsable de seguimiento** que cargará los cortes?

Con eso ajustamos lo que falte y dejamos el módulo a punto para la
operación real.

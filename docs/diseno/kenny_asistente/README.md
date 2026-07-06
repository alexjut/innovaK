# Handoff: Asistente virtual KENNY (innovaK)

## Overview
KENNY es la mascota oficial de la Alcaldía Local de Kennedy. Este handoff
especifica cómo convertirla en un **asistente virtual flotante** (burbuja de
chat) dentro de innovaK: una presencia persistente en el chrome de la SPA que
abre un panel de chat guiado y ayuda al ciudadano/funcionario con 5 tareas
(trámites, PQRS, citas, navegación, noticias), con expresiones que cambian
según el contexto y entrada por texto + voz.

**innovaK ya tiene la mitad hecha.** La app de onboarding (`apps/onboarding/`)
introdujo `MascotPresenterComponent`, `MascotStateService`, `TourService`,
`OnboardingHostComponent` y el video `frontend/public/kenny/mascota-innovak.mp4`.
El asistente **reutiliza esa infraestructura** — no se construye una mascota
nueva. Ver §Integración con lo existente.

---

## About the Design Files
Los archivos en `prototipo/` son una **referencia de diseño creada en HTML**
(`KENNY Asistente.dc.html`): un prototipo que muestra el aspecto y el
comportamiento buscados. **No es código de producción para copiar.** La tarea
es **recrear este diseño en el entorno existente de innovaK** (Angular
standalone + los patrones ya establecidos: servicios desacoplados, HttpClient
con Bearer JWT, tokens de marca, rutas `/app/*`), no incrustar el HTML.

Para verlo: abre `prototipo/KENNY Asistente.dc.html` en un navegador. El
portal de fondo es solo contexto de demostración; **lo que se implementa es la
burbuja + el panel de chat** (el fondo ya lo tienes: es el hub real de innovaK).

## Fidelity
**Alta fidelidad (hi-fi).** Colores, tipografía, medidas, radios, sombras y
animaciones son finales y están detallados en §Design Tokens. Recréalos con
precisión usando los tokens de marca que ya existan en innovaK; si un token no
existe, créalo con el valor exacto de aquí.

---

## Integración con lo existente (LEER PRIMERO)

innovaK ya tiene, en `apps/onboarding/` (Angular
`frontend/src/app/features/onboarding/`):

| Pieza existente | Rol | Cómo la usa el asistente |
|---|---|---|
| `MascotPresenterComponent` | Render de la mascota por estado (video idle/saludo/senalando/celebrando). Aislado, expone solo `setEstado()`. | Es el avatar de KENNY en el header del panel y en la burbuja. Se le manda el estado según el contexto del chat. |
| `MascotStateService` | Desacople motor↔render del estado de la mascota. | El motor del chat publica el estado aquí; el presenter lo consume. |
| `TourService` (envuelve driver.js) | Tours guiados como DATA (`tours.data.ts`). | Referencia de patrón: los **flujos del chat** se definen igual, como DATA. Además el quick-reply "Cómo llego / navegar" puede **disparar un tour** existente. |
| `OnboardingHostComponent` | Monta la mascota flotante en el `LayoutComponent`. | El panel de chat se monta en el MISMO host (una sola presencia flotante). |

**Decisión de arquitectura obligatoria (con Alex):** hoy la mascota de
onboarding ya flota abajo-derecha (visible en el hub). **No pongas dos
mascotas.** Unifica: KENNY es una sola presencia que hace onboarding (tours) y
asistente (chat). El `OnboardingHostComponent` pasa a ser el host de ambos, o
se crea un `KennyHostComponent` que agrupe presenter + tour + chat.

### Mapeo de expresiones
El prototipo usa 3 expresiones. Mapéalas a los estados del video existente:

| Expresión del chat | Cuándo | Estado `MascotStateService` |
|---|---|---|
| **alegre** | Saludo, estado por defecto, listado de noticias | `saludo` (o `idle`) |
| **atento** | Mientras KENNY "escribe", pregunta o escucha (voz) | `senalando` |
| **orgulloso** | Al confirmar (radicado, cita agendada, éxito) | `celebrando` |

> Si prefieres imágenes estáticas en vez del video (más ligero en el panel),
> usa los recortes en `prototipo/crops/exp_{alegre,atento,orgulloso}.png`.
> Lo ideal: video en la burbuja/host, imagen en las burbujas de mensaje.

### Assets de KENNY
- **Recortes incluidos** (sacados de la lámina oficial): `exp_alegre.png`,
  `exp_atento.png`, `exp_orgulloso.png` (cabezas circulares) y `cuerpo.png`
  (cuerpo completo, pulgar arriba). Tienen **fondo blanco de recorte** — para
  producción, pídele a Alex los PNG oficiales **con fondo transparente**.
- **Lámina de marca completa** en `assets_marca/mascota_lamina_kenny.png`
  (turnaround, expresiones, poses, paleta oficial).
- Colócalos en `frontend/public/kenny/` y sírvelos como `/kenny/*`.

---

## Screens / Views

Hay **un** componente con varios estados. Todo vive abajo-derecha, fixed,
z-index alto, sobre la SPA.

### 1. Launcher (chat cerrado)
- **Propósito:** invitar a abrir el chat.
- **Layout:** contenedor `position:fixed; right:24px; bottom:24px;` en
  `flex-direction:column; align-items:flex-end; gap:12px`.
- **Componentes:**
  - **Burbuja de saludo** (opcional, descartable): tarjeta blanca, borde
    `1px #ececef`, `border-radius:16px` con esquina inferior-derecha a `4px`,
    padding `13px 34px 13px 15px`, sombra `0 12px 30px rgba(0,0,0,.14)`,
    `max-width:230px`. Título "¡Hola! Soy KENNY" (Poppins 700, 13.5px) +
    "¿Te ayudo con algún trámite?" (Nunito Sans 600, 12.5px, `#6b7280`).
    Botón "×" arriba-derecha (20×20, círculo `#f0f0f2`). Animación de entrada
    `kfade .4s`.
  - **Botón mascota:** círculo 66×66, fondo rojo `#E41E26`, sombra
    `0 12px 28px rgba(228,30,38,.4)`. Contiene el avatar de KENNY (video o
    `exp_alegre.png`) en círculo blanco de 2px borde amarillo `#FFC20E`.
    Anillo de pulso detrás (`kpulse 2.4s`) + leve bob (`kbob 3s`).

### 2. Panel de chat (abierto)
- **Propósito:** conversación guiada.
- **Layout:** `position:fixed; right:24px; bottom:24px;`
  `width:min(392px, calc(100vw - 32px)); height:min(636px, calc(100vh - 96px));`
  fondo blanco, `border-radius:22px`, sombra `0 24px 60px rgba(0,0,0,.3)`,
  `display:flex; flex-direction:column; overflow:hidden`.
  Entrada `kslide .28s cubic-bezier(.22,1,.36,1)`.
- **Header** (flex none): franja roja degradada
  `linear-gradient(120deg,#E41E26,#c8161d)`, padding `14px 16px`, gap 12.
  - Avatar KENNY 46×46 (círculo blanco, borde 2px amarillo) — refleja la
    expresión actual.
  - Título "KENNY" (Poppins 800, 16px, blanco) + estado "Asistente · En línea"
    (12px, `#ffd9da`) con punto verde `#37e07a`.
  - Botón "Reiniciar" (icono refresh) + botón "Minimizar" (chevron abajo),
    32×32, fondo `rgba(255,255,255,.16)`, radio 9.
- **Área de mensajes** (flex:1, `overflow-y:auto; overflow-x:hidden`),
  fondo `#f5f5f7`, padding `18px 16px 8px`, `flex-direction:column; gap:12px`:
  - **Mensaje bot:** fila con avatar 30×30 (expresión del mensaje) + burbuja
    blanca, borde `1px #ececef`, `border-radius:16px` (esquina inf-izq 4px),
    padding `10px 13px`, texto Nunito Sans 600, 14px, `line-height:1.45`,
    `white-space:pre-line`.
  - **Mensaje usuario:** alineado a la derecha, burbuja roja `#E41E26`, texto
    blanco 700, mismos radios (esquina inf-der 4px).
  - **Indicador de escritura:** avatar atento + 3 puntos rojos que rebotan
    (`ktype 1.2s`, desfases .2s/.4s).
  - **Cards ricas** (p. ej. trámites): botón full-width, texto a la izquierda,
    borde `1.5px #ececef`, radio 14, padding `12px 14px`, título Poppins 700
    13.5px + descripción 12.5px `#6b7280`. Hover: borde rojo, fondo `#fff8f8`.
    Sangría izquierda 39px (alineadas con las burbujas del bot).
  - **Noticias:** card horizontal con placeholder de imagen 58×58 (rayas
    diagonales grises + label mono "foto noticia"), fecha (rojo, 10.5px,
    uppercase), título Poppins 700 13px, descripción 12px `#6b7280`.
  - **Quick replies (chips):** fila `flex-wrap`, gap 8, sangría 39px. Chip
    normal: pill `border-radius:999px`, borde `1.5px #ececef`, fondo blanco,
    Nunito Sans 700 13px, padding `9px 15px`; hover borde/texto rojo, fondo
    `#fff5f5`. Chip primario: fondo rojo, texto blanco 800.
- **Barra de entrada** (flex none): borde superior `1px #ececef`, fondo blanco,
  padding `11px 12px`.
  - **Normal:** input pill (borde `1.5px #ececef`, radio 999, padding
    `11px 16px`) + botón micrófono 42×42 (círculo, borde gris, icono rojo,
    solo si hay soporte de voz) + botón enviar 42×42 (círculo rojo, icono
    avión, sombra). Pie "KENNY · Alcaldía Local de Kennedy" (10.5px `#b3b3ba`).
  - **Escuchando (voz):** 5 barras verticales rojas animadas (`klisten .7s`,
    desfases .12s) + "Escuchando…" (Poppins 700, rojo) + botón "Cancelar".

---

## Interactions & Behavior

Los flujos están **definidos como DATA** (igual que `tours.data.ts`). El motor
solo interpreta: cada acción del usuario empuja un mensaje suyo y dispara la
respuesta del bot (con typing simulado ~720ms), fijando la expresión y el
widget (chips/cards/news) correspondiente.

### Menú principal (chips iniciales)
`Trámites y servicios` · `Radicar PQRS` · `Agendar cita` ·
`Cómo llego / navegar` · `Noticias y eventos`

### Flujo 1 — Trámites
1. Bot (atento): "Estos son los trámites más solicitados en Kennedy. Toca el
   que necesitas:" → **cards**: Certificado de residencia · Impuesto predial ·
   Licencia de construcción · Registro de mascotas.
2. Al elegir uno → mensaje usuario + bot (orgulloso) con los requisitos +
   chips `[Ir al trámite (primario)] [Volver al menú]`.
3. "Ir al trámite" → en producción: **navegar a la ruta Angular real** del
   trámite (deep-link), no un mock.

### Flujo 2 — PQRS
1. Bot (atento): "¿Qué tipo de solicitud deseas presentar?" → chips
   `Petición · Queja · Reclamo · Sugerencia`.
2. Al elegir tipo → bot pide describir; el **input cambia a modo "pqrs-asunto"**
   (placeholder "Describe tu {tipo}…").
3. Al enviar texto → bot (orgulloso): "¡Listo! Radiqué tu {tipo}. Número de
   radicado: {n}…" + chips `[Radicar otra] [Volver al menú]`.
   - **Producción:** POST al endpoint real de PQRS y muestra el radicado
     devuelto por el backend.

### Flujo 3 — Cita
1. Dependencia (chips: Atención al ciudadano · Planeación · Ambiente · Cultura)
2. → Día (chips de fechas disponibles) → 3. Hora (chips) → 4. bot (orgulloso)
   confirma con dependencia · día · hora · código + chips
   `[Agendar otra] [Volver al menú]`.
   - **Producción:** las opciones de día/hora vienen del backend de citas.

### Flujo 4 — Navegar
1. Bot (atento): "¿Qué sección buscas?" → chips: Trámites en línea · Directorio
   de sedes · Pagos y PSE · Sede electrónica.
2. Al elegir → bot (orgulloso) "Te llevo a {X}…" + `[Volver al menú]`.
   - **Producción:** `router.navigate(['/app/...'])` a la ruta real. Este
     flujo puede además **lanzar un tour** de `TourService` para guiar en la
     pantalla destino.

### Flujo 5 — Noticias
1. Bot (alegre): "Esto es lo más reciente en la localidad:" → **cards de
   noticias** (fecha, título, descripción) + `[Volver al menú]`.
   - **Producción:** trae noticias reales del backend si existe la fuente.

### Texto libre (fallback)
Al enviar texto que no es "pqrs-asunto", se hace match por palabras clave
(pqrs/queja/petición/reclamo → PQRS; cita/agenda/turno → cita; trámite/
certificado/predial/licencia/mascota → trámites; noticia/evento → noticias;
llego/ir/navegar/sede/directorio/pago → navegar). Si no hay match → bot ofrece
el menú principal.
- **Mejora recomendada en producción:** en vez del fallback estático, reenvía
  el texto libre al endpoint de **Consulta IA** que ya existe en
  `apps.dashboard` (OpenAI) y muestra la respuesta como mensaje del bot.

### Voz
- Botón micrófono → estado "Escuchando…" (barras animadas), expresión atento.
- Prototipo: a los 2.4s "reconoce" una frase demo y enruta.
- **Producción:** usar **Web Speech API** (`SpeechRecognition`, `lang='es-CO'`).
  Al obtener transcripción, pásala por el mismo `send()`/routeText. Si el
  navegador no soporta la API, **oculta el botón** (el prototipo lo controla
  con la prop `voz`).

### Expresiones (regla)
alegre por defecto → **atento** mientras pregunta/escribe/escucha → **orgulloso**
al confirmar un éxito. Publica el estado en `MascotStateService`.

---

## State Management
Modelar como un servicio (motor) + componentes (render), Angular-ready:

- `open: boolean` — panel abierto/cerrado.
- `showGreeting: boolean` — burbuja de saludo visible.
- `messages: {role:'bot'|'user', text:string, expr?:string}[]`
- `typing: boolean`
- `widgets`: `chips[]` / `cards[]` / `news[]` (solo uno o combinables; noticias
  + chip "Volver").
- `input: string`, `inputMode: 'free' | 'pqrs-asunto'`, `inputPlaceholder`
- `listening: boolean`
- `expr: 'alegre'|'atento'|'orgulloso'` → espejo a `MascotStateService`.
- Estado de flujo: `pqrs.tipo`, `cita.{dep,date,time}`.
- Auto-scroll al fondo tras cada mensaje (`scrollTop = scrollHeight`; **no**
  `scrollIntoView`).

Transiciones: cada handler empuja mensaje de usuario → `setTyping(true)` +
expr atento → tras delay, push del mensaje del bot + fija widgets/expr/inputMode.

## Design Tokens

**Colores** (paleta oficial):
- Rojo `#E41E26` (primario) · Rojo oscuro `#b31419` / `#c8161d` (degradados)
- Amarillo `#FFC20E` (acento) · Tinta `#1A1A1A` · Blanco `#FFFFFF`
- Texto atenuado `#6b7280` · Línea/borde `#ececef` · Fondo panel `#f5f5f7`
- Verde estado "en línea" `#37e07a`

**Tipografía:**
- Títulos/UI fuerte: **Poppins** (600, 700, 800)
- Cuerpo: **Nunito Sans** (400, 600, 700, 900)
- (Si innovaK ya tiene una fuente de UI, prioriza la del sistema y usa estas
  solo si difieren mucho; el peso/tamaño de aquí es lo importante.)

**Radios:** panel 22 · cards 14 · burbujas 16 (cola 4) · chips/inputs 999 ·
botones header 9 · icono launcher círculo.

**Sombras:** panel `0 24px 60px rgba(0,0,0,.3)` · launcher
`0 12px 28px rgba(228,30,38,.4)` · saludo `0 12px 30px rgba(0,0,0,.14)` ·
botón enviar `0 6px 14px rgba(228,30,38,.32)`.

**Animaciones (keyframes):**
- `kslide` .28s cubic-bezier(.22,1,.36,1) — entrada del panel
- `kfade` .3–.4s — mensajes y saludo
- `ktype` 1.2s — puntos de escritura
- `klisten` .7s — barras de voz
- `kbob` 3s / `kpulse` 2.4s — launcher

**Espaciado:** offset flotante 24px; padding header `14px 16px`; mensajes
`18px 16px 8px`; sangría de widgets del bot 39px; gap mensajes 12, chips 8.

## Iconos (tarea adicional pedida por el cliente)

En el hub (`/app/`) y otras vistas, los módulos usan **cuadros de color como
placeholder** en lugar de iconos. Reemplázalos por un set consistente.
**Recomendado: `lucide` (lucide-angular)** — line icons que combinan con los
del asistente. Conserva el color por módulo y el borde de acento izquierdo.

Mapeo sugerido (módulo → icono lucide):
- Mi área → `layout-dashboard` · Actividades → `calendar-check` ·
  Presupuesto → `wallet` · Festivales → `party-popper` ·
  Infraestructura → `hard-hat` · Mapa Kennedy → `map-pin` ·
  Votaciones → `vote` · Consulta IA → `sparkles` ·
  (Banco de iniciativas → `hand-heart` · Caracterización → `clipboard-list` ·
  Entregas → `package` · Jóvenes a la E → `graduation-cap` · Roles → `shield`).

Iconos usados dentro del asistente (line, stroke ~2): documento (trámites),
burbuja (PQRS), calendario (cita), pin (navegar), periódico (noticias),
micrófono, avión de envío, refresh, chevron. Todos disponibles en lucide.

---

## Backend (opcional, según alcance)
El asistente **no requiere backend nuevo** para la versión guiada (flujos como
DATA + navegación a rutas existentes). Si Alex quiere:
- **Persistir conversaciones / PQRS creadas por KENNY:** nueva app
  `apps/asistente/` con modelos `managed=False`; el **DDL lo aplica Alex** con
  backup (patrón del proyecto). Endpoints DRF con `IsAuthenticated` /
  `@jwt_or_session_required`.
- **Texto libre inteligente:** reusar el pipeline de Consulta IA de
  `apps.dashboard` (OpenAI). No dupliques la integración.
- **Gating por rol:** agrega módulo `asistente` a `seed_modulos` y asígnalo en
  `ASIGNACION_INICIAL` (probablemente a todos los roles). Invalida caché de
  permisos. Si es para todos los autenticados, basta el `authGuard`.

## Files
- `prototipo/KENNY Asistente.dc.html` — prototipo hi-fi (ábrelo en navegador).
  Contiene el portal-demo (contexto) + la burbuja + el panel + los 5 flujos.
- `prototipo/crops/exp_{alegre,atento,orgulloso}.png` — expresiones (fondo
  blanco de recorte; pedir transparentes a Alex).
- `prototipo/crops/cuerpo.png` — KENNY cuerpo completo.
- `prototipo/support.js` — runtime del prototipo (no es de producción).
- `assets_marca/mascota_lamina_kenny.png` — lámina oficial (paleta, turnaround,
  poses, expresiones).

## Checklist de implementación
- [ ] Decidir con Alex: unificar mascota onboarding + asistente (una sola
      presencia flotante).
- [ ] `feat/asistente-kenny` desde `desarrollo`.
- [ ] Servicio motor de chat con **flujos como DATA** + estado.
- [ ] Componente(s) standalone: host, launcher, panel, mensajes, entrada.
- [ ] Reusar `MascotPresenterComponent` + `MascotStateService` para expresiones.
- [ ] Deep-links de los 5 flujos a rutas `/app/*` reales.
- [ ] Voz con Web Speech API (`es-CO`), oculta si no hay soporte.
- [ ] (Opc.) texto libre → Consulta IA existente.
- [ ] Reemplazar iconos placeholder del hub por lucide (mapa de arriba).
- [ ] Assets a `frontend/public/kenny/` (pedir PNG transparentes a Alex).
- [ ] Tests de humo del servicio de flujos; suite completa en verde.
- [ ] `npx ng build --base-href=/app/`.
- [ ] Cascada feat → desarrollo → Pruebas → produccion con OK de Alex.

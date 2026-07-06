# PROMPT para Claude Code — Asistente virtual KENNY en innovaK

> Copia y pega este bloque en Claude Code, dentro del repo de innovaK.
> Adjunta también `README.md` (spec detallada) y la carpeta `prototipo/`
> (referencia visual). Lee tu `CLAUDE.md` antes de empezar.

---

Vas a implementar **KENNY**, un asistente virtual flotante (burbuja de chat)
dentro de innovaK. Ya existe la infraestructura de la mascota en
`apps/onboarding/` (`MascotPresenterComponent`, `MascotStateService`,
`TourService`) y el video en `frontend/public/kenny/`. **Reúsala, no la
dupliques.**

El diseño de referencia está en `prototipo/KENNY Asistente.dc.html` (ábrelo
en un navegador). Es un **prototipo en HTML** que muestra el look & feel y el
comportamiento esperados — NO es código para copiar. Recréalo en Angular con
los patrones ya establecidos en innovaK (componentes standalone, servicios
desacoplados, HttpClient con Bearer JWT, tokens de marca, `/app/*`).

## Qué es KENNY asistente
Una burbuja flotante en el chrome de la SPA (junto al `OnboardingHostComponent`,
mismo lugar donde hoy aparece la mascota) que abre un panel de chat guiado.
KENNY ayuda con 5 cosas, y cada una **navega a las pantallas Angular que YA
existen** (no reinventes flujos):

1. **Trámites y servicios** → cards → deep-link a la sección correspondiente.
2. **Radicar PQRS** → mini-flujo → endpoint/pantalla real de PQRS.
3. **Agendar cita** → flujo dependencia → día → hora.
4. **Cómo llego / navegar** → atajos a rutas del portal (`/app/...`).
5. **Noticias y eventos** → tarjetas de novedades.

Las **expresiones** de KENNY cambian según el contexto (alegre al saludar,
atento mientras pregunta/escucha, orgulloso al confirmar). Mapéalas a los
estados del `MascotStateService` existente. Entrada por **texto + voz** (el
micrófono usa Web Speech API; si no hay soporte, se oculta).

## Alcance y decisiones que debes tomar con Alex ANTES de codear
1. **¿Una sola presencia de mascota o dos?** Hoy la mascota de onboarding ya
   flota abajo-derecha. Lo correcto es **unificar**: KENNY es una sola mascota
   que hace onboarding (tours) *y* asistente (chat). Propón a Alex fusionar
   `OnboardingHostComponent` + el nuevo panel en un solo host. No pongas dos
   pájaros flotando.
2. **Respuestas: ¿guiadas o con IA?** El prototipo usa flujos guiños (quick
   replies) — implementa eso primero (determinista, sin backend nuevo). Para
   **texto libre**, enruta a lo que ya existe: `apps.dashboard` (Consulta IA /
   OpenAI). Es decir, si el usuario escribe libremente y no hace match con
   palabras clave, reenvía la pregunta al endpoint de Consulta IA existente.
3. **¿Necesita módulo en `seed_modulos`?** El asistente es transversal y va
   dentro de `/app` (usuario autenticado). Si quieres gatearlo por rol,
   agrega módulo `asistente` a `seed_modulos` y asígnalo (probablemente a
   todos los roles). Si es para todos, basta el `authGuard`. Confírmalo.

## Reglas del proyecto que aplican (de CLAUDE.md)
- **Frontend Angular-ready**: lógica separada de presentación. El "motor" del
  chat (flujos, estado) va en un servicio; el render en componentes. Mismo
  principio que `TourService` (tours como DATA) — define los flujos como DATA.
- **Nada de sesión pura**: si tocas endpoints, usa `@jwt_or_session_required`
  y en Angular llama con HttpClient + Bearer (NUNCA `fetch` con cookies).
- **`managed=False` + DDL**: si necesitas persistir conversaciones/PQRS, el
  cambio de schema lo aprueba y aplica **Alex** (backup previo). No migres.
- **Build**: `npx ng build --base-href=/app/` SIEMPRE.
- **Assets** en `frontend/public/kenny/`. Sirve `/kenny/*`.
- **Flujo git**: rama `feat/asistente-kenny` desde `desarrollo`. Cascada
  feat → desarrollo → Pruebas → produccion, con luz verde de Alex. Corre la
  suite de smoke tests (hook pre-push).

## Tarea extra pedida por el cliente: mejorar iconos
Los cards del hub (`/app/`) y varias vistas usan **cuadros de color como
placeholder** en vez de iconos reales (se ve en el screenshot del hub).
Reemplázalos por un set de iconos consistente (recomendado: **lucide** —
line icons, encaja con los del asistente). Mapea un icono por módulo (ver
README §Iconos). Mantén el borde de acento y el color por módulo.

## Entregable
1. `feat/asistente-kenny` con el asistente funcionando en `/app` (burbuja +
   panel + 5 flujos guiados + voz + expresiones vía MascotState).
2. Iconos del hub reemplazados por lucide (o el set que Alex apruebe).
3. Tests de humo nuevos para el servicio de flujos.
4. Sin cascada hasta OK de Alex.

Lee `README.md` para medidas exactas, tokens, estados, copy y el detalle de
cada flujo.

# Onboarding guiado con la mascota Kenny — Propuesta

> **Estado (2026-07-06):** PROPUESTA — sin implementar. Capturada a partir de
> la especificación de Alex. Arrancar como iniciativa propia (rama `feat/*`,
> PRs pequeños) cuando se decida.
> **Regla de diseño:** NO acoplar el motor de tour con el render de la mascota.

---

## 1. Objetivo

Onboarding guiado para usuarios nuevos de KennedyConecta: un tour paso a paso
sobre la UI, acompañado por la mascota **Kenny**, que se muestra una sola vez
por usuario (o hasta que lo complete/omita). El asset base de Kenny ya está en
el repo: [`frontend/public/kenny/mascota-innovak.mp4`](../../frontend/public/kenny/mascota-innovak.mp4).

---

## 2. Entregables

### 2.1 `TourService` (Angular)
Envuelve **driver.js**. API pública mínima:

- `startTour(tourId)`, `next()`, `prev()`, `skip()`.
- Persiste "completado" por usuario vía endpoint Django: `POST /api/onboarding/completado`.
- Al login, **lee el estado** para no repetir el tour a quien ya lo hizo.

El servicio consume la **definición de tours como data** (ver 2.3); no conoce
el DOM concreto más allá de los selectores que recibe.

### 2.2 `MascotPresenterComponent` (standalone)
- Inputs: `[estado]` con valores `'idle' | 'saludo' | 'senalando' | 'celebrando'`,
  y `[texto]` para el globo de diálogo.
- **Fase 1:** renderiza un `<video muted loop playsinline>` por estado, dentro
  de una tarjeta con fondo (los `.mp4` no tienen canal alfa).
- Assets servidos en `/assets/kenny/*.mp4` → en el repo van en
  `frontend/public/kenny/` (Angular sirve `public/` como raíz de assets;
  ajustar la ruta o crear `frontend/public/assets/kenny/` según convenga al
  build). Hoy existe un solo video; hay que producir los 4 estados.
- **Restricción de aislamiento:** el componente expone únicamente `setEstado()`.
  El motor de tour **nunca** sabe si Kenny es video, Lottie o 3D — así se puede
  cambiar la tecnología de render sin tocar el motor.

### 2.3 Definición de tours como data (no hardcodeada)
Cada tour es data (JSON/TS), no lógica embebida en componentes. Cada paso:

```ts
{ selector: string, texto: string, estadoMascota: EstadoKenny, posicion: 'top'|'bottom'|'left'|'right' }
```

### 2.4 Backend Django — persistencia del progreso
Tabla `onboarding_progreso`: `usuario_id` (FK), `tour_id`, `completado` (bool),
`fecha`. Endpoint DRF `POST /api/onboarding/completado` (autenticado) que
marca el tour como completado, y lectura del estado al cargar el hub.

---

## 3. Adaptaciones obligatorias a las convenciones de innovaK

Estas difieren de una spec Angular genérica y **hay que respetarlas**:

1. **`managed=False` — sin migraciones Django.** El modelo `OnboardingProgreso`
   se declara `managed=False` y la tabla `onboarding_progreso` se crea con un
   **script DDL** que aplica Alex en la BD externa (con backup previo), NO con
   `makemigrations/migrate`. La PK debe tener `DEFAULT nextval()` (secuencia en
   BD), no `MAX(id)+1`. Ver [`../../CLAUDE.md`](../../CLAUDE.md) §3.
2. **Sin DRF nuevo si no aporta** — el proyecto ya usa DRF; el endpoint encaja
   como APIView autenticada bajo `/api/onboarding/`.
3. **SSR:** la spec original menciona guardar el render con `isPlatformBrowser`
   y `@defer` "para no ejecutar en SSR". **innovaK hoy NO usa Angular SSR** (el
   SPA se sirve como build estático desde Django bajo `/app/*`). La guarda es
   una defensa correcta y barata de todos modos; dejarla puesta por si se
   adopta SSR, pero no es un requisito activo hoy.
4. **Angular-ready / datos como JSON** — encaja con la regla de oro del proyecto.
5. **Permisos:** el onboarding es transversal; no necesita módulo RBAC propio
   (cualquier usuario autenticado lo ve). Confirmar con Alex si algún rol lo
   omite.

---

## 4. Plan de PRs sugerido

| PR | Alcance |
|----|---------|
| PR-1 | DDL `onboarding_progreso` (script para Alex) + modelo `managed=False` + endpoint DRF `POST /api/onboarding/completado` + GET de estado. |
| PR-2 | `MascotPresenterComponent` standalone (Fase 1: video por estado) + producir/renombrar los 4 assets de Kenny. |
| PR-3 | `TourService` (driver.js) + definición de tours como data + wiring con el hub. |
| PR-4 | Primer tour real (hub principal) + persistencia "una vez por usuario" + QA. |

---

## 5. Pendientes / decisiones de Alex

- Producir los **4 videos de estado** de Kenny (`idle`, `saludo`, `senalando`,
  `celebrando`) — hoy solo hay uno.
- ¿Tarjeta con fondo (Fase 1, sin alfa) o invertir en un formato con
  transparencia (WebM alfa / Lottie) en Fase 2?
- ¿Qué tours iniciales? (hub principal, presupuesto, actividades…).
- Confirmar la ruta final de assets en el build de Angular.

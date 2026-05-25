# Plan de Evolución del Frontend — KennedyConecta

> **Camino híbrido con destino Angular.** Documento operativo de
> seguimiento — Agente de Frontend. Alcaldía Local de Kennedy · Proyecto
> Kennedy Transparente y Eficiente.
>
> **Versión 1.0** · Mayo 2026 · Vive en paralelo a
> [`DEUDA_TECNICA.md`](./DEUDA_TECNICA.md) y [`ARQUITECTURA.md`](./ARQUITECTURA.md).

---

## 1. Propósito y regla de oro

Este documento es la guía de trabajo para evolucionar el frontend de
KennedyConecta de forma incremental, sin reescrituras grandes, sin
detener la operación en producción y sin asumir riesgos que un equipo
de una sola persona no pueda sostener. Está pensado tanto para sesiones
cooperativas con el agente (Claude) como para ejecución asistida en el
servidor (Claude Code).

La estrategia **no es saltar a Angular de golpe**. Es subir la escalera
un peldaño a la vez: primero mejorar la experiencia de usuario sobre el
Django que ya existe, en paralelo ordenar el backend hacia API REST, y
solo entonces decidir Angular con datos reales en la mano. Cada paso es
útil por sí mismo y reversible.

> ### 🔑 Regla de oro
>
> **Todo lo nuevo nace Angular-ready.**
>
> Cualquier funcionalidad nueva debe construirse separando lógica de
> negocio de la presentación, exponiendo o pudiendo exponer datos como
> JSON, y pensando en "fragmentos que se actualizan", no en "páginas
> que recargan". Lo viejo se mejora cuando duele; lo nuevo ya viene
> con el ADN correcto.

---

## 2. Punto de partida (inventario)

Fotografía técnica del frontend tal como está hoy (2026-05-25). Sirve
de línea base para medir avance.

| Componente | Estado actual |
|------------|---------------|
| Templates HTML (SSR Django) | ≈ 160 archivos · ~22.000 líneas |
| JavaScript propio | ≈ 102 archivos · ~5.000 líneas |
| SCSS (sistema `.ui-*` BEM) | ≈ 19 archivos · ~11.000 líneas |
| Endpoints | 232 totales · solo 11 devuelven JSON · 221 sirven HTML |
| Vendor por CDN | Leaflet (+plugins), Chart.js, Bootstrap 5, Select2, Font Awesome |
| Calidad | Deuda técnica **0** · 128 tests pasando · módulos en producción |

**Lectura clave:** el sistema funciona y está limpio. El "cuello de
botella" para cualquier SPA no es el frontend, es que el backend hoy
entrega HTML, no datos. Por eso el orden del plan empieza por mejorar
UX y, en paralelo, ir convirtiendo el backend en API.

---

## 3. Las cuatro etapas del camino

La evolución se organiza en cuatro etapas. Las dos primeras corren en
paralelo y son la base del trabajo continuo. Las dos últimas son
**condicionales**: solo se ejecutan si se cumplen los disparadores
definidos en la sección 6.

| Etapa | Qué es | Para qué sirve | Estado |
|-------|--------|----------------|--------|
| **A** | UX híbrida sobre Django (HTMX + Alpine + Tom Select) | Mejor experiencia HOY, sin tocar backend. Enseña a pensar en fragmentos. | Activa |
| **B** | Backend → API REST (DRF), módulo por módulo | Ordena el sistema. Sirve para Angular, móvil o nada. Inversión sin arrepentimiento. | Activa / continua |
| **C** | Decisión informada sobre Angular | Evaluar disparadores con datos reales antes de comprometerse. | Pendiente |
| **D** | Migración a Angular (strangler) | Solo si la Etapa C lo aprueba. Híbrido Django+Angular tras nginx. | Condicional |

### Etapa A — UX híbrida sobre Django

Orden de ataque por **ROI dividido entre opacidad** (cuánta carga
mental permanente deja cada pieza).

1. **Tom Select** — reemplaza Select2 en 3 formularios (Beneficiario,
   Funcionario, Banco). Riesgo casi cero, sin tocar lógica. Quick win
   que valida el flujo cascada+tests. ~1 hora.
2. **HTMX en 2-3 endpoints** — empezar pequeño, NO con 5-10. Atacar
   primero el formulario del Banco que más duele. Forms y tablas se
   actualizan sin recargar; el server devuelve HTML parcial. Aquí se
   aprende el patrón y se empieza a separar lógica de presentación.
3. **Alpine.js** — estado de UI local: sidebar, modales, dropdowns,
   tabs. Declarativo en el HTML, fácil de leer y mantener.
4. **Vite y Tailwind: EN PAUSA** — no por inútiles, sino por la carga
   cognitiva permanente que dejan. Vite es el más opaco para depurar;
   Tailwind masivo se descarta si Angular está en el horizonte (los
   componentes se reestilizan al migrar). Entrar solo con justificación
   clara.

**Criterio de cierre de Etapa A:** los 3 formularios usan Tom Select,
al menos 3 endpoints responden con HTMX sin recargar página, y el
sidebar/modales corren con Alpine. Todo con los 128 tests en verde.

### Etapa B — Backend hacia API REST

Esta es la inversión que de verdad importa. Se hace módulo por módulo,
exponiendo JSON con Django REST Framework **junto** a las vistas HTML
que ya existen (no se borra nada). Ventaja: ya conoces DRF del proyecto
SRNI.

- Por cada módulo migrado: definir serializers, paginación, filtros y
  permisos. La vista HTML sigue viva; el endpoint JSON nace al lado.
- Resolver autenticación de forma pensada: hoy sesiones Django;
  planear el paso a tokens (JWT o cookie-based) para cuando un cliente
  JS consuma la API.
- Refactor que ocurre naturalmente: al devolver partials HTMX y
  serializers, la lógica de negocio se va sacando de las vistas. Ese
  es exactamente el trabajo de la Fase 0 de Angular, hecho de forma
  gradual y segura.
- Empezar por un módulo pequeño y autocontenido (no el Banco, que es
  el más crítico) para aprender el patrón.

**Criterio de avance de Etapa B:** número de módulos con API REST
disponible / total de módulos. Meta intermedia razonable: **30-40% de
módulos con endpoint JSON** antes de tocar la decisión de Angular.

### Etapa C — Decisión informada sobre Angular

**Punto de control, no de ejecución.** Cuando la Etapa B esté avanzada,
se revisan los disparadores (sección 6). Si ninguno se cumple, NO se
migra: se siguió mejorando UX y backend, sin pérdida. Si al menos uno
se cumple, se pasa a la Etapa D.

### Etapa D — Migración a Angular (condicional)

Solo si la Etapa C lo aprueba. **Patrón strangler:** Django sirve lo
viejo, Angular lo nuevo, conviviendo tras nginx. Nunca un big-bang.

| Fase | Trabajo | Aprendizaje clave | Riesgo |
|------|---------|-------------------|--------|
| D.0 | Backend ya en API REST (heredado de Etapa B) | DRF (ya conocido) | Bajo — ya hecho |
| D.1 | Andamiaje Angular: routing, guards, interceptors, estado (Signals/NgRx), librería UI (Material/PrimeNG) | TypeScript, RxJS, change detection | Medio — curva real |
| D.2 | Migración módulo por módulo, empezando por uno pequeño | Estructura de módulos Angular | Bajo — incremental |
| D.3 | Recrear lo complejo: Leaflet, dashboards Chart.js/Plotly, wizards, cards de presupuesto | Wrappers Angular + reescritura de wizards | Medio-alto |
| D.4 | Apagar templates Django, ajustar CI/CD y deploy doble | Angular CLI, pipeline | Medio |

---

## 4. Tablero de seguimiento

Marca el avance aquí. La idea es que este tablero se actualice al final
de cada sesión de trabajo con el agente.

| # | Tarea | Etapa | Estado | Notas / sesión |
|---|-------|-------|--------|----------------|
| 1 | Tom Select en BeneficiarioForm | A | **Hecho** | 2026-05-25 — reemplaza Select2+jQuery (ahorro ~140kb), HTTP 200, 128 tests OK |
| 2 | Tom Select en FuncionarioForm | A | Pendiente | |
| 3 | Tom Select en formularios del Banco | A | Pendiente | |
| 4 | HTMX — endpoint piloto (form Banco) | A | Pendiente | |
| 5 | HTMX — 2.º endpoint | A | Pendiente | |
| 6 | HTMX — 3.er endpoint | A | Pendiente | |
| 7 | Alpine — sidebar reactivo | A | Pendiente | |
| 8 | Alpine — modales y tabs | A | Pendiente | |
| 9 | API REST — módulo piloto pequeño | B | Pendiente | |
| 10 | API REST — definir estrategia de auth (tokens) | B | Pendiente | |
| 11 | API REST — 2.º módulo | B | Pendiente | |
| 12 | API REST — 3.er módulo | B | Pendiente | |
| 13 | Revisión de disparadores Angular | C | Pendiente | |

**Estados sugeridos:** Pendiente · En curso · En revisión · Hecho · Pausado.

---

## 5. Reglas de trabajo para el agente

Estas reglas aplican tanto a sesiones cooperativas como a ejecución con
Claude Code en el servidor. Son la barrera de seguridad de un sistema
en producción operado por una sola persona.

### Siempre

- **Confirmar antes de:** DDL en base de datos, push a producción,
  cambios a `docker-compose`, y cualquier rotación o exposición de
  credenciales/tokens.
- **Mantener los 128 tests en verde.** Si un cambio rompe un test, se
  detiene y se reporta — los tests son la red de seguridad, no un
  obstáculo.
- **Trabajar respetando la cascada de las 4 ramas** y dejar el cambio
  cascadeado correctamente.
- **Explicar el patrón, no solo entregar el código.** El objetivo es
  que Alex pueda mantener y replicar lo escrito sin el agente
  presente.
- **Aplicar la regla de oro:** todo lo nuevo, Angular-ready (lógica
  separada de presentación, datos exponibles como JSON, mentalidad de
  fragmentos).

### Nunca

- **Meter Vite o Tailwind masivo** sin justificación explícita y
  aprobación de Alex.
- **Hacer reescrituras grandes** de una sola vez. Siempre incremental
  y reversible.
- **Pegar credenciales, tokens o secretos en el chat.** Si aparecen,
  marcar para rotación.
- **Asumir decisiones de diseño** (paleta, qué endpoint primero,
  mantener o sustituir Bootstrap). Eso lo decide Alex; cada decisión
  = 1 pregunta concreta.

---

## 6. Disparadores para activar Angular (Etapa C → D)

Angular se justifica solo si se cumple **AL MENOS UNO** de estos. Si
ninguno aplica, el camino híbrido es la decisión correcta y definitiva.

1. **Entra equipo.** KennedyConecta deja de ser "Alex solo" y suma 2-3
   devs frontend. La estructura opinionada de Angular se paga sola con
   equipo; para una persona es solo overhead.
2. **App móvil real.** Si surge necesidad de app nativa, una API REST
   limpia sirve para web Angular y móvil a la vez. Ojo: esto ya está
   pasando con SRNI (React Native); vale la pena vigilar si
   KennedyConecta toma ese rumbo.
3. **Interactividad pesada / real-time.** Dashboards en vivo,
   colaboración simultánea, websockets constantes. Ahí SSR+HTMX se
   queda corto y una SPA brilla.

**Si ninguno se cumple: no migrar.** Se gana mejor UX y mejor backend,
sin asumir doble mantenimiento permanente.

---

## 7. Skills a desarrollar

Habilidades que conviene ir dominando, ordenadas por cuándo se
necesitan. La columna "Fluidez" indica cuánto cuesta llegar a operarla
con soltura en solitario.

| Skill | Etapa | Fluidez | Por qué / nota |
|-------|-------|---------|----------------|
| HTMX | A | ~1 día | Atributos en el HTML, partials del server. El de mayor ROI y más fácil de leer. |
| Alpine.js | A | ~1 día | Estado de UI declarativo. Fácil de mantener. |
| Tom Select | A | Una tarde | Reemplazo directo de Select2, sin jQuery. |
| Django REST Framework | B | Ya conocido | Heredado de SRNI. Serializers, viewsets, permisos. Es el pilar de todo. |
| Diseño de API REST | B | 1-2 sem | Pensar recursos, paginación, versionado, contratos JSON estables. |
| Autenticación por tokens (JWT) | B | Pocos días | Para que un cliente JS consuma la API de forma segura. |
| TypeScript | D | 1-2 sem | Base de Angular. Tipado estricto. |
| Angular (core) | D | 3-4 sem | Componentes, routing, guards, inyección de dependencias. |
| RxJS / Signals | D | 2-3 sem | Manejo de estado y flujos asíncronos. Lo más opaco al inicio. |
| Angular Material / PrimeNG | D | 1 sem | Librería de componentes UI. |
| Vite / build pipeline | Opcional | 1 sem | **EN PAUSA** salvo justificación. El más opaco para depurar. |

---

## 8. Principio rector

> **No optimizar para terminar rápido.**
> **Optimizar para que en 6 meses sigas entendiendo tu propio código.**

La velocidad de la IA es una herramienta para ti, no un sustituto de
tu comprensión. Cada paso de este plan es reversible y útil por sí
solo: si en la Etapa C decides no ir a Angular, no perdiste nada. Y si
decides que sí, llegas con medio camino andado.

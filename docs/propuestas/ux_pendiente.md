# Propuestas UX pendientes — innovaK

> Documento vivo con las 3 propuestas mayores de UX que **no se han
> ejecutado** y siguen siendo válidas. Extraídas de planes históricos
> archivados al consolidar `docs/` el 2026-04-29 (PR-A→PR-H4 ya
> entregaron las propuestas de hub, breadcrumb, sidebar y sub-hubs).
>
> Cada ítem cita su origen archivado para contexto completo.

---

## 1. Accesibilidad WCAG 2.2 AA — auditoría completa

**Origen:** `docs/_historico/2026-04-24_plan_integral_innovak.md`

**Estado al 2026-04-29:** Parcialmente abordado en PR-J1 (sesión
2026-04-27): 50 `<th scope="col">` agregados, 118 emojis envueltos en
`<span aria-hidden="true">`, 1 hint color subido a contraste AA. Falta
auditoría sistemática + remediación priorizada.

**Tareas pendientes:**

- [ ] Auditoría con `axe-core` o `pa11y` sobre las 8 vistas más usadas
  (login, hub, crear evento, lista contratos, detalle proyecto, mapa
  Kennedy, banco-iniciativas inscribir, login).
- [ ] Reemplazar `<div onclick>` por `<button>` o agregar `role="button"
  tabindex="0"` + handler `keydown`.
- [ ] Verificar contraste **4.5:1 mínimo** en todos los `text-muted`
  sobre fondos coloreados (cards, alertas).
- [ ] Etiquetar todos los iconos FontAwesome decorativos con
  `aria-hidden="true"` y los semánticos con `aria-label`.
- [ ] Skip-links en `base.html` (`<a href="#main">Saltar al contenido</a>`).
- [ ] Probar con NVDA/VoiceOver: flujo crear evento + flujo de
  inscripción Banco de Iniciativas.

**Esfuerzo estimado:** L (1-2 semanas dedicadas).

**Skill disponible:** `wcag-audit-patterns` y `accessibility` (instaladas
en sesión 2026-04-27).

---

## 2. Árbol presupuestal D3.js — visualización en /dashboard/

**Origen:** `docs/_historico/2026-04-24_plan_integral_innovak.md` +
`docs/_historico/2026-04-23_plan_redisenio_dashboard.md`

**Idea:** representar la cadena financiera como árbol jerárquico
interactivo en lugar de cards anidadas:

```
Proyecto 2784
├─ CDP 1 ($X disponible)
│  └─ Contrato A → ActividadPlan "Banco Iniciativas"
│     └─ Evento 62 (4 colectivos inscritos)
└─ Meta 100010 → KPI 7 (4/280 colectivos)
```

Permite explorar el flujo dinero→meta→KPI→evento sin tener que
navegar entre múltiples vistas.

**Tareas pendientes:**

- [ ] Endpoint `/dashboard/api/proyecto/<id>/arbol/` que retorne el
  árbol como JSON anidado.
- [ ] Componente D3 `tree` o `treemap` en
  `apps/dashboard/static/dashboard/js/arbol_presupuestal.js`.
- [ ] Tooltips con saldos, % avance, link a vista 360° del proyecto.

**Esfuerzo estimado:** M (3-5 días).

**Dependencias:** ninguna externa; D3.js v7 vía CDN.

---

## 3. "Tableros de Control" — grilla de 8 botones tipo Power BI

**Origen:** `docs/_historico/2026-04-23_plan_redisenio_dashboard.md`

**Idea:** rediseño del hub `/dashboard/` con 8 tarjetas grandes tipo
"botón cuadrado" (4×2) en vez de cards densas. Cada botón es un
"tablero de control" temático: Presupuesto, Personas, Eventos del Mes,
Mapa, Indicadores Críticos, etc.

**Estado al 2026-04-29:** PR-C ya implementó el hub con 5-6 cards
top-level + sub-hubs. **No equivale** al diseño Power BI propuesto.
La pregunta es si el rediseño aporta más valor que la estructura
actual ya en producción.

**Decisión pendiente con Alex:** ¿el hub actual cumple? ¿O conviene
explorar el Power-BI-style?

**Esfuerzo estimado:** M (3-5 días) si se decide ejecutar.

---

## Cómo se decidió priorizar

Todas son MEDIA-baja en impacto inmediato:

- (1) accesibilidad — obligatoria para gov.net, no urgente hoy.
- (2) árbol presupuestal — feature de visualización; mejora UX pero
  funcionalidad ya existe en vista 360°.
- (3) Power BI hub — alternativa estética al hub actual; no rompe nada.

Recomendación: cuando termine el ciclo del Banco de Iniciativas piloto
y la cadena financiera, atacar (1) accesibilidad WCAG primero (es
deuda con timeline regulatorio) y luego evaluar (2) y (3) según
feedback de usuarios reales.

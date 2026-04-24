# Plan de rediseño Dashboard Ejecutivo — innovaK

> **Fecha**: 2026-04-23 (plan diferido para ejecución en próxima sesión).
> **Rama actual**: `feat/mapa-kennedy-dashboard`.
> **Objetivo**: transformar el dashboard lineal actual en un sistema
> multi-pantalla estilo "Tableros de Control" con hub de botones y
> vistas dedicadas.

---

## 1. Estado actual del dashboard

**URL**: `https://intranet-public-alk.ngrok.app/dashboard/presupuesto/`

Secciones de arriba a abajo (todas en una sola página scrolleable):

1. **Hero** con título "Dashboard Presupuestal" + botones rápidos.
2. **6 KPI cards ejecutivas**: Proyectos, Metas PDD, Indicadores, Eventos del mes, Avances, En riesgo.
3. **3 gráficos operativos**: eventos/mes (barras), eventos/tipo (dona), top sectores (barras horizontales).
4. **Tabla "Objetivos por Proyecto"** (histórico, preexistente).
5. **Metas del Plan** — 20 cards con rollup de progreso (PR2 de hoy).
6. **Avance de KPIs** — 34 KPIs con barras coloreadas (PR1 de hoy).

Commits de la sesión 2026-04-23 (dashboard ejecutivo):

```
7801cd9 feat(dashboard): sección de Metas del Plan con progreso agregado
505bdc1 feat(dashboard): reemplaza cards y gráficos superiores con data operativa
e6f5cb5 feat(demo): siembra data robusta para dashboard ejecutivo
f0e48be docs: plan detallado de siembra demo + roadmap PRs dashboard
a9d296b feat(dashboard): sección de KPIs del Plan con avance físico
d4f3918 docs: inventario completo del proyecto para UX (Fase 1)
```

Datos actualmente visibles: **10 proyectos DEMO + 20 metas + 34 KPIs + 101 eventos + 62 avances**.

---

## 2. Visión del rediseño (según imágenes de Alex)

### Imagen 1 — "Tableros de Control" (hub de botones)

Grilla de 8 botones grandes de colores distintos. Cada botón entra a un dashboard temático:

- Presupuesto Secretaría Desarrollo Económico (azul oscuro)
- Seguimiento Metas (verde claro)
- Articulado Plan Bogotá Camina Segura (rojo oscuro)
- SUIM Unidades Productivas (ocre)
- Presupuesto Sector Desarrollo (azul claro)
- Seguimiento Metas UNCSAB (verde oscuro)
- SISE Personas Empleo (rosa)
- *(y más que apararezcan al scrollear)*

Cada botón = **una puerta a una pantalla dedicada**. UX tipo "landing de tableros".

### Imagen 2 — "Presupuesto Árbol"

Visualización tipo tree diagram horizontal:
- **Raíz**: "Presupuesto Inversión $1.994.349.244.111"
- Ramifica a **planes** (06-Bogotá Camina Segura, 05-Contrato Social, …)
- Cada plan ramifica a **años** (2024, 2025, 2026, 2027)
- Cada año muestra monto con **barra horizontal proporcional**

Se entiende la jerarquía y la magnitud de un vistazo. Muy limpio.

---

## 3. Arquitectura propuesta

```
/dashboard/                      → Hub de botones (NUEVO)
/dashboard/presupuesto/          → Dashboard actual (se mantiene, quizás simplificado)
/dashboard/metas/                → Pantalla dedicada "Metas del Plan"
/dashboard/indicadores/          → Pantalla dedicada "KPIs detallados"
/dashboard/eventos/              → Pantalla dedicada "Eventos" (listado + mini-mapa + timeline)
/dashboard/arbol-presupuesto/    → Gráfico árbol tipo imagen 2
/dashboard/mapa/                 → Redirect a /geo/mapa-kennedy/
/dashboard/consulta-inteligente/ → Ya existe, incluir en el hub
```

### Componentes nuevos

1. **Hub** (`templates/dashboard/hub.html`):
   - Grid responsive (4 cols desktop, 2 tablet, 1 móvil).
   - Cada botón: icono + título + subtítulo corto + color distintivo.
   - Efecto hover: elevación + sombra suave.
   - Un "breadcrumb" global que sirve para navegar de cualquier pantalla al hub.

2. **Plantilla "pantalla dedicada"** (layout reusable):
   - `<nav>` con link "⟵ Hub" y título actual.
   - Filtros si aplica (vigencia, sector, rango fecha).
   - Contenido principal (reusa APIs existentes).

3. **Árbol presupuestal** (nuevo):
   - Librería candidata: **D3.js tree layout** (poder total) o **Mermaid** (setup mínimo).
   - Data: service Python que arma JSON anidado plan → año → monto.
   - Interactivo: click expande/colapsa nodos; tooltip con monto formateado.

---

## 4. Plan en 6 PRs

| PR | Descripción | Tiempo | Bloqueos |
|---|---|---|---|
| **A** | Hub de botones (`/dashboard/` como landing) | 1–1.5 h | Ninguno — puede arrancar de inmediato |
| **B** | Mover sección "Metas del Plan" a `/dashboard/metas/` | 30 min | Requiere PR A |
| **C** | Mover sección "Avance de KPIs" a `/dashboard/indicadores/` | 30 min | Requiere PR A |
| **D** | Pantalla nueva "Eventos" (listado + mini-mapa + timeline) | 1.5 h | APIs `/geo/api/eventos/` ya existen |
| **E** | Árbol presupuestal | 2–3 h | Depende de data real de presupuesto por plan/año |
| **F** | Refinamiento visual (responsive, transiciones, accesibilidad) | 1 h | Después de A–E |

**Total estimado**: 6–8 horas concentradas.

---

## 5. Decisiones pendientes para próxima sesión

1. **Hub vs Dashboard actual**: ¿`/dashboard/` se convierte en el hub (y el actual se mueve a `/dashboard/presupuesto/` donde ya está)? O ¿`/dashboard/presupuesto/` se vuelve hub y las otras vistas cuelgan como `/dashboard/presupuesto/metas/`?
2. **Pantallas separadas vs anchors**: ¿cada botón lleva a URL propia (mejor UX, más mantenible) o usa `#anchor` en la misma página (más rápido de implementar)?
3. **Librería del árbol**: D3.js (más poderoso, curva de aprendizaje) vs Mermaid (más simple, menos flexible) vs **plotly-hierarchies** (rápido, con zoom).
4. **Data del árbol**: ¿hay datos reales de presupuesto por plan × año en BD hoy, o sembramos mock adicional DEMO_?
5. **Pantalla Eventos**: ¿incluir mini-mapa Leaflet embebido, o solo listado + filtros + botón a `/geo/mapa-kennedy/`?

---

## 6. Riesgos

- **Mantener compatibilidad**: el dashboard actual funciona y está para demo. El rediseño no debe romperlo durante la transición. Posible: mantener `/dashboard/presupuesto/` y agregar las pantallas nuevas en paralelo.
- **D3.js vs Chart.js**: ambas pueden coexistir pero hay que tener cuidado con colisiones de event listeners y estilos.
- **Data insuficiente para el árbol**: si en BD no hay `apropiacion × plan × año`, el árbol queda vacío. Mitigación: sembrar DEMO_ adicional si Alex confirma que no hay data real.
- **Regresiones de la demo**: cualquier cambio post-demo debe respetar que la URL `/dashboard/presupuesto/` siga sirviendo lo que Alex mostró.

---

## 7. Out of scope (explícitamente NO)

- Integración con Power BI externo.
- Reemplazo del sistema de permisos (hoy es single rol).
- Limpieza de catálogos vacíos preexistentes (programa, objetivo con pocos datos).
- Eliminación de secciones legacy (tabla Objetivos por Proyecto).
- Migración de data real masiva (esperar a que Alex cargue o se importe).

---

## 8. Siguiente acción

**Próxima sesión empieza con:**

1. Alex confirma respuestas a las 5 decisiones de §5.
2. Se arranca con **PR A (Hub de botones)** que es el que destraba los demás.
3. Se agenda cierre con PRs B, C, D en la misma sesión si el tiempo alcanza; PR E y F en sesión separada.

Mientras tanto: el dashboard actual en `/dashboard/presupuesto/` está 100% listo para la demo a jefes. Data sembrada, gráficos con data real, metas y KPIs con rollup correcto.

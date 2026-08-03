# Estado de innovaK

**Al 2026-08-03.** Un solo archivo, en la raíz, sobre la rama `produccion`.

Antes había un `ESTADO.md` por worktree y se contradecían entre sí: el de
`home-publico` seguía diciendo *"nada commiteado"* varios días después de que su
código estuviera en producción. Un estado que miente es peor que no tenerlo, así
que ahora hay uno solo y vive donde vive el código desplegado.

Para el detalle histórico de cada entrega, la bitácora está en `CLAUDE.md` §11.
Para el estado de un módulo, su propio `README.md` (p. ej.
`apps/georeferenciacion/README.md`).

---

## 1. Cómo se trabaja: ramas, no worktrees

El flujo es el de `CLAUDE.md` §5 — `feat/*` → `desarrollo` → `Pruebas` →
`produccion` — sobre **ramas normales en el árbol principal**.

Entre julio y agosto de 2026 se usaron worktrees de git (`.claude/worktrees/`).
Se retiraron el 2026-08-03. No fallaron técnicamente: fallaron por falta de
cierre. Cada uno costaba ~100 MB de copia del árbol y **ninguno se borró al
cascadear**, así que se acumularon 4 vivos + 5 zombis que git ya ni reconocía —
496 MB y cuatro ramas que parecían trabajo pendiente sin serlo.

Costos concretos que se pagaron y no se recuperan trabajando sobre ramas:

- El contenedor `innova_k` monta el árbol principal, no el worktree. Correr
  tests o comandos con el código de un worktree exigía levantar un contenedor
  efímero con `--add-host` y montajes a mano.
- Cada worktree tenía su propio `ESTADO.md` sin trackear. Al mergear no se
  actualizaban, y quedaban afirmando cosas falsas.
- Ver cuatro ramas en `git branch` sugiere trabajo en vuelo. Las cuatro estaban
  100 % mergeadas en `produccion`.

Si vuelve a hacer falta aislamiento real (dos cambios incompatibles sobre los
mismos archivos, a la vez), la regla es: **el worktree se borra en el mismo
paso en que se cascadea la rama**, no después.

---

## 2. Qué está vivo en producción

Las tres troncales están sincronizadas y con el mismo árbol. Todo lo que estaba
en worktrees ya entró:

| Entrega | Dónde |
|---|---|
| Home público en la raíz (`/app/` sin sesión → bienvenida, mapa, encuestas abiertas) | `features/publico/home-publico.component.ts` |
| Censo de escuelas de julio 2026 + resolución territorial | `apps/georeferenciacion/` |
| UX y accesibilidad del mapa público (las 5 fases del plan) | `features/mapa/` |
| Diagnóstico IA NL→consulta de beneficiarios | `docs/propuestas/ia_nl2sql_diagnostico.md` |

---

## 3. Qué queda abierto

### 3.1 Scope por subgrupo en la consulta IA — riesgo real, sin cerrar

El motor de consulta de beneficiarios **no aplica `aplicar_subgrupo`** sobre las
filas. Verificado el 2026-08-03: el símbolo no aparece en ninguna parte de
`apps/dashboard/`. La única barrera es el permiso de módulo `dashboard_ia`, así
que cualquier usuario que lo tenga ve el universo completo de personas, sin
importar su subgrupo.

Lo detectó el diagnóstico del 2026-07-14 y sigue igual. No lo resuelve ningún
modelo de lenguaje: se resuelve en el endpoint. Detalle en
`docs/propuestas/ia_nl2sql_diagnostico.md` §0.4.

### 3.2 Los tres CSV con el área de escuelas

Entregados y revisados el 2026-08-03, en `/home/innova/Proyectos/`
(`REVISION_*.csv` + `LEEME_reporte_escuelas_area.txt`). Cada fila trae una
columna *"Qué necesitamos de ustedes"*.

**Viven fuera del repo a propósito**: llevan direcciones reales. El repo es
público y eso es habeas data (Ley 1581). No se mueven adentro.

Falta la respuesta del área sobre las **43 sedes activas sin ubicación** — 31 sin
dirección y 12 con dirección que no se pudo encontrar. Sin eso no se pintan en
el mapa.

### 3.3 Decisiones que esperan a Alex

- **`QR_TOKEN_ENFORCE` fase 2.** El HMAC de los QR públicos sigue en modo suave:
  sin token registra un warning pero no bloquea. Activarlo exige reimprimir los
  QR vigentes primero.
- **Las 13 actividades con ubicación aproximada.** Hoy se apilan en la sede de
  la Alcaldía, marcadas como aproximadas. Son pocas: o se re-georreferencian a
  mano, o se dejan así.
- **`sudo rm -rf apps/kordial apps/VitalK`** (deuda L4). Scaffolds muertos que
  solo dejan `.pyc` de root; el borrado necesita sudo del host.

---

## 4. Verificación al cierre del 2026-08-03

- Tres troncales con árbol idéntico, sincronizadas con `origin`.
- `.claude/worktrees/` borrado por completo (496 MB, 9 carpetas).
- Ramas locales: solo las tres troncales.
- Suite de smoke tests corrida por el hook `pre-push`.

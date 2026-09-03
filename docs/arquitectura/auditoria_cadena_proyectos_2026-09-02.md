# Auditoría de cadena — los 31 proyectos, eslabón por eslabón (2026-09-02)

> Documento de **estado**, no de deuda nueva por defecto. Pedido explícito:
> "que quedemos todos los proyectos bien enlazados con todo, y si hay que
> crear cosas dejarlas anotadas". Nada de lo que sigue se ejecutó — es
> 100 % lectura, contra `apps.presupuesto.services.expediente_proyecto`
> (`expediente_lista()` para lo agregado, `_construir()` para el detalle de
> contratos por proyecto) más 6 queries puntuales de `information_schema`
> y conteo. Ni un DDL, ni un `--write`, ni un `UPDATE`.

## La cadena que se auditó

```
Proyecto → MetaProyecto → Meta (KPI)
   ↓           ↓
   CDP → Contrato → ContratoActividadPlan → ActividadPlan
                                               ↓
                                          Evento → Beneficiarios
```

Acordada con Alex el 2026-05-21 (ver `CLAUDE.md`, sesión "Jóvenes a la E").
Lo que **no** se reabre porque ya se resolvió en esta misma conversación:

- **Apropiación POAI** (DDL 020) y **Alerta de cumplimiento** (DDL 021) — ya
  cargadas. 29/31 proyectos con `alerta`; los 2 sin ella se documentan abajo
  sin re-investigar.
- **Área PLANIG**: 10/31 sin área es **correcto por diseño** — esos 10
  subgrupos (Relacionamiento Interinstitucional, Subsidio tipo C, Buen trato,
  Espacio Público, Innovación, CPS y Planta, Participación ×2, TIC,
  Paz-Memoria-Reconciliación) no pertenecen a ninguna de las 10 áreas
  oficiales del PLANIG. Confirmado por el usuario en esta conversación. **No
  tocar.**
- **Dependencia y Subgrupo**: 31/31 completos — es el "dueño" real dentro de
  la Alcaldía.

## Tabla resumen — 31 proyectos × 5 eslabones

`m/k` = metas / KPIs activos. `con_cdp` y `con_vínculo` son *de los contratos
que tiene ese proyecto*, no del total del sistema — un proyecto sin contratos
sale `✗ 0/0` en ambos, no es lo mismo que "todos sus contratos están rotos".

| Código | Nombre | Meta/KPI | CDP | Contrato | …con `cdp_id` | …con vínculo a Act.Plan | Act. Plan | Evento | Alerta |
|---|---|---|---|---|---|---|---|---|---|
| 000007895 | 000007895 | ✗ 0/0 | ✓ 1 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | — |
| 0002377 | Kennedy Germinando Futuros | ✓ 2/3 | ✗ 0 | ✓ 1 | ✗ 0/1 | ✓ 1/1 | ✓ 1 | ✓ 1 | Crítico |
| 2491 | Kennedy Hogares Seguros Familias Protegidas | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2492 | Kennedy Destino de Oportunidades | ✓ 2/2 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2517 | Kennedy Territorio de Progreso | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2551 | Kennedy Infraestructura para el Futuro | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2556 | Kennedy Mujeres sin Barreras | ✓ 3/3 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2574 | Kennedy Crecimiento y Conexión | ✓ 1/1 | ✗ 0 | ✓ 2 | ✗ 0/2 | ✗ 0/2 | ✓ 1 | ✗ 0 | — |
| 2610 | Kennedy Ingreso con Propósito | ✓ 3/3 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✓ 1 | ✗ 0 | En ejec. cronograma |
| 2612 | Kennedy Guardianes del Bienestar Animal | ✓ 3/3 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Ejecutada |
| 2616 | Kennedy Respira Verde | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Ejecutada |
| 2626 | Kennedy Juntos Nos Preparamos Para el Cambio | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Ejecutada |
| 2643 | Kennedy Ecomanos en Acción | ✓ 5/5 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2646 | Kennedy Espacios de Buen Trato | ✓ 5/5 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2684 | Kennedy Espacios Públicos Seguros | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2688 | Kennedy Camina Segura | ✓ 3/3 | ✓ 1 | ✓ 1 | ✓ 1/1 | ✓ 1/1 | ✓ 3 | ✓ 3 | Crítico |
| 2705 | Bogotá se Vive en Kennedy | ✓ 2/2 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Desierta |
| 2706 | Kennedy en Alianza por la Seguridad | ✓ 2/2 | ✓ 2 | ✓ 2 | ✓ 2/2 | ✓ 2/2 | ✓ 2 | ✓ 2 | Ejecutada |
| 2711 | Fortalecimiento institucional | ✓ 3/2 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✓ 1 | ✗ 0 | Crítico |
| 2729 | Kennedy Segura y en Paz | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Ejecutada |
| 2733 | Voces De Kennedy | ✓ 3/3 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2740 | Kennedy Trazos de Identidad | ✓ 4/4 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2745 | Kennedy Camina Hacia la Convivencia | ✓ 7/7 | ✓ 1 | ✓ 1 | ✓ 1/1 | ✓ 1/1 | ✓ 7 | ✓ 8 | Crítico |
| 2767 | Kennedy en Línea | ✓ 2/2 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Sin magnitud contratada |
| 2780 | Kennedy Proyecta Talento | ✓ 4/4 | ✗ 0 | ✓ 15 | ✗ 0/15 | ✗ 0/15 | ✓ 4 | ✓ 7 | En ejec. cronograma |
| 2784 | *(sin nombre — ver hallazgo)* | ✓ 4/4 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✓ 1 | ✓ 1 | Crítico |
| 2788 | Kennedy Impulso Creativo | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✓ 1 | ✓ 1 | En ejec. cronograma |
| 2790 | Kennedy Mi Parque Mi Espacio | ✓ 2/2 | ✗ 0 | ✓ 2 | ✗ 0/2 | ✗ 0/2 | ✓ 1 | ✗ 0 | Crítico |
| 2793 | Kennedy Espacio que Inspira | ✓ 1/1 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | Crítico |
| 2794 | Kennedy Respira Bienestar | ✓ 5/5 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✗ 0 | ✗ 0 | En ejec. cronograma |
| 2818 | Kennedy Caminos de Reconciliación | ✓ 4/3 | ✗ 0 | ✗ 0 | ✗ 0/0 | ✗ 0/0 | ✓ 1 | ✗ 0 | Crítico |

**Ninguno de los 31 está "completo" contando el CDP como eslabón obligatorio**
— pero eso no es un hallazgo nuevo: la tabla `cdp` tiene **5 filas en todo el
sistema** (ya documentado en el docstring de `expediente_proyecto.py`), así
que exigirlo por proyecto no mide nada real. Contando los 4 eslabones que sí
son alcanzables hoy (Meta/KPI, Contrato, Contrato↔ActividadPlan, Evento),
**3 de 31 están completos: 2688, 2706 y 2745.**

## Huecos reales (con acción concreta, sin ejecutar)

### H1 — 18 proyectos son "cáscara de planeación": meta + KPI + apropiación, y CERO ejecución

`2491, 2492, 2517, 2551, 2556, 2612, 2616, 2626, 2643, 2646, 2684, 2705, 2729,
2733, 2740, 2767, 2793, 2794` — sin un solo contrato, ni una actividad_plan,
ni un evento. Juntos suman **~$100.500 M** de apropiación 2025-2026 sin
ninguna huella de ejecución en innovaK.

**Por qué es real y no cosmético como el área PLANIG:** coincide casi 1:1 con
los "18 proyectos creados" por `importar_matriz_pdl_alk` el 2026-09-01 (ver
`ESTADO.md` §3.11) — son proyectos que la Matriz PDL trajo por primera vez
ese día. No existían en innovaK antes, así que su ejecución (si la hay) vive
en SECOP/papel y todavía no se cargó acá.

**Tensión que vale la pena que Alex revise:** 4 de estos 18 (`2612, 2616,
2626, 2729`) ya tienen `alerta: Ejecutada` —el Excel dice que la meta se
cumplió al 100 % o más— con cero contratos registrados. No es necesariamente
un error: pueden ejecutarse por una vía que innovaK no cubre (convenio,
recursos de otra entidad). Pero una meta "Ejecutada" sin ni un contrato detrás
es exactamente el tipo de afirmación que conviene poder sustentar si alguien
pregunta de dónde sale la plata.

**Acción:** no hay DDL ni comando que resuelva esto — es carga operativa. A
medida que el área reporte los contratos/CDPs reales de estos 18 proyectos,
se cargan por la UI ya existente (`/app/presupuesto` → CDPs, Contratos,
vinculación a ActividadPlan). Ningún dato se puede inventar acá.

### H2 — 2 proyectos sin nombre real (`nombre` = su propio `código`)

- **000007895** (id 2807): `nombre='000007895'`. Tampoco tiene metas, KPIs,
  contratos, actividades ni eventos — su ÚNICO dato es 1 CDP de $52.000.000
  ("cdp 2025"). Subgrupo 7, sin dependencia propia (cae a DESPACHO por el
  subgrupo). Este código (9 dígitos) no tiene la forma de los demás (4
  dígitos) — vale la pena confirmar con Alex si es un proyecto real sin
  terminar de cargar, o un registro de prueba que no se limpió.
- **2784**: `nombre='2784'`. Sí tiene cadena real (4 metas/KPI, 1 actividad
  plan, 1 evento, alerta Crítico) — solo le falta el nombre. Por la bitácora
  del Banco de Iniciativas (`CLAUDE.md`, sesión 2026-04-28/29) su nombre real
  es **"Kennedy Fuerza Local Pasión por el Deporte"**.

**Acción:** para 2784, un `UPDATE proyecto SET nombre='Kennedy Fuerza Local
Pasión por el Deporte' WHERE codigo='2784'` — un DML de una fila, trivial,
pero **requiere confirmación de Alex** (regla del proyecto: sin excepción
para escritura en la BD compartida). Para 000007895, primero hay que saber
qué es antes de tocarlo.

### H3 — 2 proyectos sin `alerta` cargada

Ya identificado en esta conversación, sin novedad:

- **000007895** — no aparece en la hoja «Alertas» del Excel en absoluto.
- **2574** — sí está (fila 111, "Intervenir 22 Kilómetros-carril de malla
  vial urbana…"), pero su mejor candidata interna dio 0.40 de similaridad,
  por debajo del umbral 0.55 de `importar_alerta_metas_pdl`. Engancha a mano
  si Alex confirma cuál `meta` interna es, corriendo el importador con
  `--umbral` más bajo O actualizando la fila directo una vez confirmado el
  `codigo_meta`.

## Deuda ya conocida — citada, no reabierta

Estos tres patrones aparecen en la tabla pero **no son hallazgos nuevos**:
ya están documentados en otro lado, y el propio `DEUDA_TECNICA.md` dice que
la deuda vive ahí o no existe como tal.

- **CDP casi inexistente (5 filas en todo el sistema)** y **contratos sin
  `cdp_id`** (4 de 25 en el corte de 2026-04-30, hoy 4 de 25 sigue siendo la
  cuenta real). Documentado en el docstring de `expediente_proyecto.py` y en
  la bitácora de `CLAUDE.md` (sesión 2026-04-28/29: "96 contratos legacy con
  `cdp_id`/`valor` NULL pendientes de migración manual"). **Nota de higiene
  de documentación, no un hallazgo de datos:** esa cifra vive solo en
  `CLAUDE.md`, y la regla propia de `DEUDA_TECNICA.md` dice *"si un defecto
  conocido no está en este archivo, no existe como deuda"* — valdría la pena
  moverla ahí para que no se pierda entre bitácoras.
- **`contrato_actividad_plan.meta_proyecto_id` NULL en las 15 filas activas**
  (ya en el docstring de `expediente_proyecto.py`, punto 3). Por eso el
  vínculo contrato↔meta hoy solo puede leerse por la cadena
  `actividad→indicador→meta`, no directo.
- **Proyecto 2740, subgrupo dudoso** (comunidades étnicas, quedó en
  Participación "por descarte") y **2556/2643 sin par en el espejo oficial**
  — ambos ya listados como pendientes de decisión de Alex en `ESTADO.md`
  §3.11.

## Resumen numérico

| | |
|---|---|
| Proyectos auditados | 31 |
| Completos (Meta/KPI + Contrato + Vínculo + Evento) | 3 — `2688`, `2706`, `2745` |
| Proyectos "cáscara" (meta+apropiación, cero ejecución) | 18 (H1) |
| Con contrato pero sin `cdp_id` en ninguno | 4 — `0002377, 2574, 2780, 2790` |
| Con contrato pero sin vínculo a ActividadPlan en ninguno | 3 — `2574, 2780, 2790` |
| Con actividad+evento pero sin contrato | 2 — `2784, 2788` |
| Sin nombre real (`nombre` = código) | 2 (H2) |
| Sin `alerta` cargada | 2 (H3) |
| Sin meta/KPI en absoluto | 1 — `000007895` |

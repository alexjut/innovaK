# Dashboard 360° / Explorador

`/app/presupuesto/dashboard` — la vista gerencial. **La lee el Alcalde.**

Orden: vigencia → dinero → tabs [PDL | Metas] → **EXPLORADOR** (abierto) →
acordeones cerrados con sus cifras reales.

## Regla de la vista gerencial

> No muestra información técnica. Ni nombres de tabla, ni «falta DDL», ni
> conteos de filas. Lo que no hay se dice **`Sin dato`** o
> **`Pendiente por diligenciar`**.

Y `$0` **no** es `Sin dato`: ver [[CDP-CRP]].

## Decisiones de estilo cerradas (2026-08-24)

No revertir. Detalle en `docs/operacion/dashboard_presupuesto_estado_2026-08-24.md`.

- **Presupuesto SCSS:** error a **32 kB**, aviso en 12. El límite anterior ya
  había costado la jerarquía visual una vez: seis contenedores perdieron fondo,
  borde y sombra en una consolidación por bytes.
- **Identidad ≠ dato.** Rojo `#D6001C` y amarillo `#FFC72C` son **marca**. La
  fila de KPI: 4 tonos + 1 neutro.
- **Colores de texto:** `$color-{success,warning,danger,info}-hondo`. El verde
  del token estaba en 5,02:1 —un escalón más claro que sus hermanos— y por eso
  alguien había escrito `#166534` a mano 7 veces en 5 pantallas.
- **`aria-live`** sólo envuelve mensajes concretos. Envolvía el expediente
  entero (772 líneas, 86 condicionales) y el lector recitaba el panel completo
  cada vez que se abría un contrato.
- El explorador arranca **cuanto antes**: −168 px ganados, sobre todo bajando el
  `max-height` del panel de pestañas de 340 a 200 px.

## Etapa contractual

El stepper lee `Contrato.etapa`. **Un solo dato, sin copias**: lo que se
registra en [[Mi-Area]] aparece acá. Ver [[Contrato]].

Relacionado: [[Mi-Area]] · [[Contrato]] · [[Contraste-y-accesibilidad]]

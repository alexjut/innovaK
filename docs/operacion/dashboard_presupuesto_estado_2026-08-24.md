# Dashboard presupuestal — dónde quedó (2026-08-24)

Rama **`feat/expediente-contrato-completo`**, commit `f8b4f4e`.
**SIN cascadear**: desarrollo, Pruebas y produccion siguen sin este trabajo.
1361 tests OK · build limpio · contenedor reiniciado y sirviendo.

La pantalla es `/app/presupuesto/dashboard`. **No hay otra**: todo se hizo sobre
ella, nunca en una vista paralela.

---

## Lo que quedó funcionando

**Explorador maestro/detalle por PROYECTO.** Panel izquierdo con buscador +
Área ejecutora + Subgrupo en cascada + contador `X/Y`; panel derecho con el
expediente del proyecto elegido. La unidad es el proyecto, no el área.

**Dentro de cada contrato** —también en los que no cuelgan de una meta—:
etapa contractual (stepper de 4), ejecución presupuestal en franja horizontal,
ejecución técnica y financiera, y plan de pago.

**Orden de la página:** vigencia → dinero → tabs [PDL | Metas del Plan] →
EXPLORADOR (abierto, fuera de acordeón) → acordeones cerrados que muestran sus
cifras reales en la cabecera.

---

## Decisiones que NO hay que volver a discutir

| | |
|---|---|
| **Área ejecutora = Dependencia**, provisional | El campo `Entidad` de SEGPLAN trae UN valor para Kennedy («FONDO DE DESARROLLO LOCAL DE KENNEDY»): en un plan LOCAL el ejecutor siempre es el FDL. Hasta que exista tabla propia. Ver `area-ejecutora-provisional` en memoria |
| **Identificador canónico = `id`**, no `codigo` | `2784` es el código de `id=2802`. En `2788` coinciden, así que el bug se ve intermitente. Hay test que lo fija |
| **Atribución contrato→área = UNIÓN de las dos vías** | `contrato_proyecto` (20) ∪ `contrato_actividad_plan` (5) = **24 de 25**, cero contradicciones. Usar solo la primera mandaba $2.117.962.446 de Seguridad a un cajón de «sin subgrupo» |
| **La etapa NO se deriva** | De 25 contratos, SECOP dice «Modificado» en 20 — eso es un otrosí, no una etapa. Se captura, y nace NULL |
| **`$0` real ≠ «sin dato»** | 21 celdas con cero real, 30 con null, cada una con su motivo |
| **El permiso lo decide el servidor** | `puede_registrar_etapa` viaja en el payload. No reimplementarlo en el frontend: la atribución usa dos vías |

---

## Lo que sigue: ESTILOS E ICONOGRAFÍA

Es lo único que Alex dejó pendiente. La data ya está.

**Puntos concretos que quedaron abiertos:**

1. **Margen del presupuesto de estilos.** `presupuesto-dashboard.component.scss`
   compila a **22,32 kB** y el build **falla en 24** (`anyComponentStyle
   maximumError` en `angular.json`). Quedan 1,68 kB. Si se pasa, el build no
   avisa: revienta. `expediente-proyecto.component.scss` va en 20,38 kB.
2. **Altura hasta el explorador.** Arrancaba a ~783 px; se apretaron márgenes y
   se puso tope de 340 px con scroll al panel de tabs. **El número final está
   sin medir en navegador.** Si sigue justo, lo siguiente es comprimir la franja
   de dinero.
3. **Iconografía**: el proyecto usa `lucide-angular` (registrado global en
   `app.config`) y quedan restos de Font Awesome. No mezclar.
4. **Paleta**: rojo `#D6001C` SOLO como marca —nunca estructura—, teal `#0D9488`
   como acento. Las 4 etapas tienen sus pares ya auditados por contraste y
   ninguna usa el rojo institucional, para que «sancionatorio» no se lea
   «alcaldía».

---

## Riesgos vivos

- **Los 5 SCSS** cerca del límite: dashboard 22,32 / expediente 20,38 de 24 kB.
- **El catálogo `Objetivo` tiene 4 de 6 filas llamadas «prueba»**; solo 3 de 12
  proyectos tienen objetivo asignado. La pantalla `/app/presupuesto/objetivos`
  existe y funciona, pero muestra ese vacío.
- **`metas.proyecto_id` está NULL en las 24 filas** — columna de enganche
  muerta; el vínculo real va por `meta_proyecto`.
- El proyecto **`000007895`** es un registro de prueba confirmado. No se borró:
  espera respuesta del Despacho sobre su CDP 1486 ($52M, 23-09-2025), el único
  dato suyo que parece real.

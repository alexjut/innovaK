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

## ESTILOS E ICONOGRAFÍA — hecho el 2026-08-24 (tarde)

Los cuatro puntos que estaban abiertos, con lo que resultó al medirlos. Dos se
cerraron, uno cambió de diagnóstico y uno sigue sin poder medirse.

### 1 · Contraste: 12 parejas arregladas, cero bytes de coste

Se midió el ratio WCAG 2.1 real de las 223 parejas color/fondo de las tres
hojas del dashboard. Fallaban 12. Las doce están arregladas y **el CSS
compilado pesa exactamente lo mismo** (22,32 y 20,38 kB): todos los cambios son
de un hex por otro del mismo largo.

| Dónde | Antes | Ahora |
|---|---|---|
| `.hero__subtitle` | 3,89:1 | 4,54:1 |
| `.proy__marca` (marca el proyecto abierto) | 3,74:1 | 5,47:1 |
| `.acc__flecha` (dice si el acordeón está abierto) | 2,54:1 | 4,83:1 |
| icono de búsqueda del filtro | 2,54:1 | 4,83:1 |
| icono de cabecera de gráfica | 2,54:1 | 4,83:1 |
| `.kpi-card__icon` | 4,36:1 | 6,81:1 |
| icono del estado vacío | 1,40:1 | 2,41:1 |
| `.meta__pct` y `.kpi__pct` en ok/medio | 3,30 y 2,15:1 | 5,02 y 7,09:1 |
| etiquetas de pasos futuros del stepper | 2,54:1 | 4,83:1 |
| `.paso--actual .paso__estado` | 3,30:1 | 5,02:1 |
| `.nota--error` título | 3,95:1 | 6,80:1 |
| `.codigo__rot` (9 px) | 4,39:1 | 6,87:1 |
| `.tarjeta__naturaleza` y `.ledger__pie` del muro | 2,54 y 3,90:1 | 4,83 y 6,10:1 |

**El hero se medía mal, y por eso el error era invisible.** Es un degradado
(`#D6001C → #B00017`) y el contraste hay que medirlo en su extremo CLARO. El
subtítulo al 82 % daba 5,19:1 en el extremo oscuro —donde cualquiera lo
comprueba— y 3,89:1 en el claro. Al 90 % da 4,54:1 en el peor punto.

### 2 · Cuatro colores que no tenían nombre

`#15803D`, `#92400E`, `#991B1B` y `#1D4ED8` estaban escritos a mano **22 veces
en tres hojas**. Son la variante oscura de los cuatro semánticos de tokens, que
como RELLENO cumplen (3:1 contra lo adyacente) pero como TEXTO no: el verde
`$color-success` da 3,30:1 sobre blanco y el naranja `$color-warning`, 2,15:1.

Ahora viven en `_tokens.scss` como `$color-{success,warning,danger,info}-hondo`,
medidos sobre blanco y sobre la superficie cálida `#FAF9F8`. Se llaman «hondo»
y no «text» porque también son el tono correcto para un riel de 3 px o un
borde, y escribir «text» dentro de un `box-shadow` diría una mentira.

Sin nombre, la regla «un acento por métrica» **no se podía verificar**: no había
forma de saber si dos verdes distintos eran el mismo verde.

### 3 · Iconografía: el diagnóstico anterior estaba al revés

Este documento decía «el proyecto usa lucide-angular y quedan restos de Font
Awesome». Es al contrario, y la cuenta lo dice sin discusión:

| | archivos | usos |
|---|---|---|
| Font Awesome | **81** | **658** |
| lucide-angular | 7 | — |

**Font Awesome es la base y lucide es la excepción** (los hubs y el panel de
Kenny). Migrar el dashboard a lucide lo dejaría fuera de sistema respecto a los
otros 80 archivos, no dentro. La decisión de fondo —unificar en uno de los dos—
sigue abierta, pero es una migración de 658 iconos, no una limpieza de restos.
Ya existe `npm run iconos:mapeo-lucide` para dimensionarla.

**Los 4 iconos rotos tampoco eran lo que parecía.** El verificador decía «NO
existen» y mandaba a buscar otro nombre en fontawesome.com. Los cuatro existen
—`arrow-right-long \f178`, `circle-question \f059`, `file-import \f56f`,
`sack-dollar \f81d`—; lo que estaba viejo era `fa-subset.css`, generado el 6 de
agosto, antes de que esos iconos entraran al código. Bastó regenerarlo
(`npm run iconos:subset`): entraron 4 y salieron 4 que ya nadie usa.

`verificar_iconos_fa.js` ahora **separa las dos causas**, que necesitan arreglos
opuestos: nombre que existe pero falta en el subset → regenerar; nombre que no
existe en ninguna parte → es un typo. Ambas ramas probadas.

Y los 9 iconos decorativos del dashboard que no llevaban `aria-hidden` ya lo
llevan. Los otros 11 no lo necesitaban: viven dentro de un `<span aria-hidden>`
que ya oculta el subárbol.

### 4 · El presupuesto de estilos: no hay nada que comprimir

Se midió el archivo bloque por bloque, recompilando sin cada uno para ver
cuántos bytes valía. El resultado cierra la discusión:

- **Código CSS muerto: cero.** De 151 clases del dashboard, 139 se usan directo
  y las 12 restantes se construyen con `[class]="'x--' + valor"`. En el
  expediente, 120 de 137, y las 17 restantes igual. Ninguna sobra.
- **Ningún bloque gordo.** El más pesado (`.meta`) son 1.807 B de 22.140. El
  peso está repartido entre 49 piezas de interfaz reales.
- **Casi nada que extraer a un partial compartido.** Las dos hojas grandes solo
  comparten `.rotulo` y `.sin-dato`; `.meta` y `.bloque` son homónimos que
  significan cosas distintas en cada una.

Es decir: **la hoja no está inflada, la pantalla es grande.** El tope de 24 kB
es la restricción equivocada, no el CSS. Las tres salidas, con su número:

| Salida | Qué cuesta | Qué deja |
|---|---|---|
| **Subir el error a 32 kB** y dejar el aviso en 12 como señal | 1 línea en `angular.json` | 9,7 kB de aire. El aviso ya lo incumplen 7 componentes: como límite duro no está funcionando de todos modos |
| **Partir el explorador** en su propio componente | refactor real (`.maestro` + `.filtros` + `.proy` = 4,4 kB) | dashboard a ~17,7 kB + un componente nuevo de 4,4. Mejora la arquitectura, no se ve en pantalla |
| **Dejarlo** | nada | 1,68 kB. Se revienta el build el día que alguien agregue una tarjeta |

Recomendación: la primera. La segunda es correcta pero es trabajo de
arquitectura disfrazado de trabajo de estilos, y conviene decidirla aparte.

### 5 · La altura hasta el explorador SIGUE sin medir

No hay navegador en el entorno (ni Chrome, ni Puppeteer, ni Playwright), así
que **no se pudo cerrar este punto y no se cerró.** Lo que sí se puede afirmar:

- El cromo fijo más el hero más la vigencia suman **257 px** calculados de las
  cajas declaradas (topbar 70 + hero 102 + vigencia 45 + margen de tabs 12).
- Lo que falta —el interior de la franja de dinero y el panel de pestañas— no
  se puede calcular del CSS: dependen del contenido. El panel tiene tope de
  **340 px** y el canvas de la franja, **104 px**.
- El peor caso realista queda por encima de 800 px, que es justo el número que
  había que bajar.

Para cerrarlo hace falta abrir la pantalla en un navegador y medir. El primer
recorte candidato sigue siendo el tope de 340 px del panel de pestañas: es el
único bloque grande de arriba que es un número y no contenido.

---

## Herramienta nueva: `npm run contraste`

`frontend/scripts/verificar_contraste.js`, mismo patrón que
`verificar_iconos_fa.js` y por el mismo motivo: **el modo de falla es
silencioso.** Un gris de 2,5:1 no rompe el build, no sale en ningún log y en la
pantalla del que lo escribió se ve bien.

Compila las 99 hojas del proyecto —los `.scss` sueltos **y** los `styles:`
incrustados en los `.ts`, que son 93 de las 99— resuelve el fondo subiendo por
el selector, entiende el anidamiento BEM (`.hero__subtitle` hereda de `.hero`),
mezcla los alfas, evalúa los degradados contra su peor extremo y calcula el
ratio WCAG.

Tiene **línea base** (`scripts/_contraste_base.json`): las 198 parejas que ya
estaban por debajo quedan selladas, así que el script sale en verde hoy y falla
solo si aparece algo NUEVO. Sirve en CI desde el primer día sin tener que
arreglar antes toda la app. Probado metiendo un `#D1D5DB` a mano: lo caza.

Lo que **no** puede ver, y está escrito en su cabecera: fondos puestos desde el
TypeScript, imágenes de fondo, y fondos que vienen de una clase hermana que no
sigue BEM. Esos salen como «indeterminados» (16) y no cuentan como fallo.

**Las 198 de la línea base están marcadas `PENDIENTE DE REVISAR` salvo dos.**
Eso no es deuda nueva: es deuda que antes no se veía. Reparto por área:
`publico` 65, `presupuesto` 17 (todas en pantallas distintas del dashboard),
`banco-iniciativas` 16, `caracterizacion` 10, `subgrupo` 8, y una cola de 12
áreas más.

---

## Riesgos vivos

- **El tope de 24 kB sigue a 1,68 kB del dashboard** (22,32) y a 3,62 del
  expediente (20,38). Medido: no hay nada que comprimir —cero CSS muerto, cero
  bloque gordo, cero duplicación entre las dos hojas—, así que el próximo
  cambio de estilos revienta el build sin avisar. Decisión pendiente arriba,
  §4: subir el error a 32 kB (recomendado), partir el explorador, o nada.
- **El catálogo `Objetivo` tiene 4 de 6 filas llamadas «prueba»**; solo 3 de 12
  proyectos tienen objetivo asignado. La pantalla `/app/presupuesto/objetivos`
  existe y funciona, pero muestra ese vacío.
- **`metas.proyecto_id` está NULL en las 24 filas** — columna de enganche
  muerta; el vínculo real va por `meta_proyecto`.
- El proyecto **`000007895`** es un registro de prueba confirmado. No se borró:
  espera respuesta del Despacho sobre su CDP 1486 ($52M, 23-09-2025), el único
  dato suyo que parece real.

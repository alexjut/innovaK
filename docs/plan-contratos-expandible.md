# Plan — `/app/plan/contratos`: la ficha del contrato

*Medido el 2026-09-21 contra la base y el servicio. Versión 2: incorpora las
correcciones aprobadas por Alex sobre el plan del 2026-09-21. Sigue siendo un
plan — no se ha tocado código.*

---

## El diagnóstico en una línea

**La pantalla tiene los 3.189 contratos y está enseñando el 40 % de lo que ya
sabe de ellos**, mientras dedica su espacio más visible a una cifra que no
habla de los contratos sino de nuestra contabilidad interna.

---

## 1. Lo que se quita: «en innovaK»

Hoy los cuatro recuadros de arriba dicen:

```
3.189 contratos   ·   24 en innovaK   ·   3.165 faltan   ·   0,8 % conciliado
```

Ese 0,8 % es el mensaje más grande de la pantalla y **no dice nada del
contrato**: dice cuántos de los 3.189 de SECOP tienen además una fila en
nuestra tabla `contrato`. No es una propiedad del contrato, es un pendiente
nuestro de digitación — y empuja a una tarea (cargar 3.165 contratos a mano)
que nadie va a hacer y que ya no hace falta, porque el espejo de SECOP los trae
todos con más campos de los que el formulario interno pide.

**Se retira:** los recuadros `en innovaK` / `faltan` / `% conciliado`, los chips
«En innovaK» / «Faltan por cargar», la columna «N por completar» y la barra de
áreas con sus pendientes.

**Se conserva:** el enganche con el Plan, que no es «conciliación» sino la
cadena contrato → actividad → meta, lo único que Kennedy tiene y SECOP no. Esos
24 contratos valen $40.567 M de $326.688 M: **el 12,4 % de la plata**.

**Y no queda ningún texto que diga «falta cargar».** Un contrato que está en
SECOP y no en nuestra tabla no está incompleto: está completo en su fuente. La
pantalla no vuelve a insinuar lo contrario en ningún rótulo.

### Correcciones de la lista (punto 6 del encargo)

Van en el mismo paso porque son la misma pantalla y el mismo archivo:

| | |
|---|---|
| **La regla del cero, también en la lista** | Hoy la columna «Pagado» pinta `$0` para 240 contratos (8 %) en los que SECOP no distingue «no se giró» de «no se reportó». Pasa a **«Sin dato»** con su motivo en el `title`, igual que en el expediente y en la API pública. |
| **Formato `es-CO` + `enMillones()`** | Las cifras se leen con el mismo formato del resto del módulo, no con el `| number` por defecto. |
| **Cabecera nueva** | Sin el marco de conciliación, el título y el subtítulo dicen qué es la pantalla: el espejo de SECOP II de los contratos de la Alcaldía. |
| **«Volver» y migaja a Gestión** | Hoy la pantalla no tiene salida. La migaja queda `Inicio › Plan de Desarrollo › Gestión › Contratos`, coherente con el reparto Visual/Gestión que ya está en producción. |
| **Página de 25** | En vez del tamaño actual. Con 3.189 filas, 25 es el tamaño con el que se navega sin esperar. |

---

## 2. Lo que se muestra: el dato que ya tenemos y no se usa

Medido sobre los 3.189 contratos:

| Dato | Cobertura | ¿Se muestra hoy? |
|---|---|---|
| Fecha de fin · duración · valor pendiente · proceso de compra · descripción | **100 %** | ❌ |
| Fecha de inicio | 99 % | ❌ |
| **Plan de pagos** | **94 %** (3.009) | ❌ |
| Valor pagado > 0 | 92 % (2.949) | ✅ |
| `valor_pagado = 0` (ambiguo) | 8 % (240) | sale como «$0» ❌ |
| **Modificaciones** | **71 %** (2.252 contratos · 4.304 filas) | ❌ |
| Días adicionados > 0 | 31 % (984) | ❌ |
| CRP de BogData | 21 contratos | ❌ |

**Lo más desaprovechado son las modificaciones.** 2.252 contratos —siete de cada
diez— tienen al menos una, y ahí está lo que la gente pregunta: si se prorrogó,
cuántos días, si se cedió, si se adicionó valor. Hoy la única pista es la
columna «Estado», que dice «Modificado» en 1.005 contratos sin decir en qué.

Tipos de modificación en el espejo: `MODIFICACION GENERAL` 2.098 · `No definido`
865 · `CONCLUSION` 763 · `REACTIVACIoN` 247 · `SUSPENSIoN` 185 · `CESION` 132 ·
`ADICION EN EL VALOR` 14.

---

## 3. Los KPIs nuevos, y todos filtran (punto 3)

Los cuatro recuadros de conciliación se reemplazan por **seis que sí hablan del
contrato**, y **cada uno es un filtro**: hacer clic en «Prorrogados» deja la
lista en esos 984.

```
  3.189          $326.688 M      92 %            2.252          984           N
  contratos      valor total     con pago        modificados    prorrogados   vencen
                                 reportado                                    en 30 días
```

- **% con pago reportado** y no «% pagado»: el denominador son los contratos con
  dato, no los 3.189. Decir «92 % pagado» sobre una base que incluye 240
  contratos sin medición sería inventar una cifra.
- **«Vencen en 30 días»** sale de `fecha_fin` (cobertura 100 %) contra hoy,
  contando solo los que no están cerrados ni terminados.

**Una sola consulta agregada**, no una por recuadro: un `GROUP BY` sobre el
espejo más un agregado de `secop_modificacion` por contrato. Sin abanicar filas
—la lección de los 4.304 renglones de modificación contra 2.252 contratos.

---

## 4. Filtros y orden (punto 4)

Sobre la lista, y combinables entre sí:

| Filtro | De dónde sale |
|---|---|
| **Año** | `fecha_firma` — el espejo arranca en 2024 por decisión ya tomada |
| **Estado** | `En ejecución` 1.015 · `Modificado` 1.005 · `Cerrado` 820 · `terminado` 153 · `cedido` 85 |
| **Modalidad** | proceso de compra, cobertura 100 % |
| **Modificados** · **Prorrogados** · **Por vencer** | los mismos predicados de los KPIs |
| **Enlazados al Plan** | los 24 con cadena a actividad → meta. Es el enganche, **no** «conciliación» |

**Orden** por valor, fecha de fin y días adicionados, ascendente y descendente.

**Las pestañas General / Jurídica / Natural se quedan como están.** Ya existen,
ya traen su conteo y su valor, y son el corte que más usa la gente. Los filtros
nuevos se aplican **dentro** de la pestaña activa.

---

## 5. La ficha: UNA sola, la que ya existe (puntos 1, 2 y 5)

### Dónde vive hoy

El panel rico del contrato —el que ya tiene el stepper de etapa, la franja de
plata multi-fuente, los medidores y la tabla de plan de pagos— **ya está
escrito** en:

```
frontend/src/app/features/presupuesto/expediente/expediente-proyecto.component.html   (983 líneas)
                                                  ├─ línea 625   <li class="contrato">  ← la fila plegable
                                                  ├─ línea 668   .contrato__etapa       ← etapa con el panel cerrado
                                                  ├─ línea 714   <ol class="stepper">   ← 1. ETAPA
                                                  ├─ línea 797   .franja-plata--contrato ← 2. EJECUCIÓN PRESUPUESTAL
                                                  └─ …            plan de pagos, veredicto
frontend/src/app/features/presupuesto/expediente/expediente-proyecto.component.ts     (825 líneas)
                                                  ├─ celdasPlata()  ~línea 592
                                                  └─ veredicto()    ~línea 692
```

Es el panel que se ve, por ejemplo, al abrir el contrato 983 dentro del
expediente de su proyecto.

### Qué se hace con él

**Se extrae a un componente compartido `contrato-ficha`, y el expediente pasa a
consumirlo.** No se crea una ficha paralela: tener dos fichas del mismo contrato
es garantizar que se contradigan, que es exactamente el problema que ya se cerró
con `avance_matriz` y `plata_matriz`.

La ficha tiene **dos niveles**, y el nivel lo decide el dato, no la pantalla:

| | **Nivel base** — los 3.189 | **Nivel enganchado** — los 24 |
|---|---|---|
| Identificación | referencia, proceso de compra, modalidad, objeto completo, descripción | ídem |
| Contratista | nombre · naturaleza · documento (ver §6) | ídem |
| Plazo | firma, inicio, fin inicial → fin actual, días adicionados | ídem |
| Plata | valor, pagado (regla del cero), pendiente | **+ franja multi-fuente** (Matriz · SECOP · BogData) y medidores |
| Modificaciones | las `n`, con tipo, fecha y `en_firme` | ídem |
| Plan de pagos | los 12 registros, con cuántos tienen pago real | ídem |
| Etapa | — | **stepper de etapa** |
| Cadena | — | **actividad → meta → proyecto**, con enlace al expediente |

Lo que el nivel base no tiene, **no se anuncia**: no hay stepper apagado ni
franja vacía ni la palabra «pendiente». Un bloque sin dato no se pinta.

### La barra de tiempo contra plata (punto 5)

Un solo gráfico, porque es la pregunta que la gente hace mirando un contrato:

```
  inicio          fin inicial                    fin actual
  20-05-2025      20-01-2026                     20-05-2026
  ├──────────────────────┼─────────▲──────────────────┤
                                  hoy                         ⏱ +122 días
  plata   ████████████████░░░░░░░░░░░░░░░░░░░░░░░░   38 % pagado
```

Dos reglas:

1. **Si el pagado es «Sin dato», la barra de plata no se dibuja.** No se pinta
   una barra al 0 % para los 240 contratos ambiguos: se dice que no se sabe.
2. **`fin inicial` y `fin actual` se separan solo cuando difieren.** En los 2.205
   contratos sin días adicionados hay un solo hito de fin, y dibujar dos
   superpuestos sugiere una prórroga que no hubo.

### Cómo se abre (punto 2)

- **La fila se expande en su sitio**, con el mismo patrón `estaExpandida()` /
  `toggleDetalle()` que ya usa `actividades-subgrupo`. La ficha se **carga
  perezosamente**: se pide al abrir, no con la lista.
- **Ruta propia** `/plan/contratos/:idContrato`, registrada **antes** de
  `contratos` y del catch-all `:entidad` en `presupuesto.routes.ts` — si queda
  después, `:entidad` se la come, que es exactamente lo que ya pasó con
  `contratos-fuentes` y `cdps` y está anotado en ese archivo.
- Dentro de la ficha: **«Abrir en página»** (a esa ruta) y **«Copiar enlace»**,
  para que un contrato se pueda mandar por correo.
- **«Ver en SECOP ↗» no se pierde.** Sigue siendo el enlace de la referencia y
  además un botón al pie de la ficha.

### Los otros sitios que hablan de contratos

Para enlazar a la ruta nueva cuando exista (**no en este plan**, se anota para
no perderlos):

| Sitio | Qué muestra hoy |
|---|---|
| `expediente/expediente-proyecto.component` | **el panel rico** — pasa a consumir `contrato-ficha` |
| `contratos-fuentes.component` | el mismo contrato visto por SECOP, BogData e innovaK |
| `muro/muro-subgrupos.component` | los contratos por subgrupo |
| `proyecto-360.component` · `presupuesto-detail.component` | contratos del proyecto / detalle por entidad |
| `area/completitud-expediente.component` · `subgrupo-detalle.component` | lo que le falta al área |
| `infraestructura/infra-detalle.component` | contratos de obra en el mapa |

---

## 6. El documento del contratista, y que las dos puertas digan lo mismo (punto 7)

**Regla, y es la misma para la lista, el buscador y la ficha:**

- **El NIT de las jurídicas es visible** en todas partes. Es dato de la
  organización, no de una persona.
- **El documento de las personas naturales sale SOLO dentro de la ficha.**
  Nunca en la lista, nunca en el resultado del buscador, nunca en una
  exportación de la lista.

Esto es coherente con lo que **ya hace la API pública hoy**, y conviene decirlo
con nombres para que nadie lo cambie por un lado sin el otro
(`apps/publico/services/contratos.py`, `core/settings.py:194-195`):

```
PUBLICA_DOCUMENTO_NATURALES = 1    → el documento de las naturales SÍ se publica
PUBLICA_NOMBRE_NATURALES    = 1    → el nombre de las naturales SÍ se publica
```

`tipo_documento` viaja siempre, y `proveedor_ref` —un seudónimo HMAC— se
conserva aunque el documento sea público, porque es la llave estable para
agrupar los contratos de un mismo proveedor. Es decir: **la API pública es hoy
más abierta que lo que esta pantalla va a mostrar en la lista**, por decisión
tomada («los datos son públicos… por eso los traemos de datos abiertos»). La
ficha interna no abre nada nuevo; solo evita el escaparate de cédulas que sería
una tabla de 3.189 filas.

**El «Por completar →»** queda como **un enlace discreto dentro de la ficha, y
solo cuando el contrato está enganchado al Plan**. No es un recuadro, no está en
la lista, y no aparece en los 3.165 que no tienen cadena — porque a esos no les
falta nada.

---

## 7. El backend: casi nada nuevo

**El dato ya está ensamblado.** `apps/publico/services/contratos.py` arma
exactamente esta ficha —contrato, plazo con fin inicial vs actual, plata con la
regla del cero, modificaciones con su tipo y su `en_firme`, plan de pagos— y
`apps/publico/services/modificaciones.py` hace la parte de las modificaciones.

Hace falta **un endpoint interno que sirva esa ficha por `id_contrato`**,
reusando esos servicios en lugar de reescribirlos:

```
GET /dashboard/api/v2/presupuesto/contratos-oficiales/<id_contrato>/
    → ModuloRequiredPermission('presupuesto_proyectos')
    → apps.publico.services.contratos.detalle(id)      ← ya existe
    + el enganche con el Plan (los 24)                 ← ya lo calcula la lista
```

La lista vive en `apps/dashboard/api/views.py:196` y su servicio en
`apps/dashboard/services/kpis_presupuesto.py`; ahí salen los KPIs nuevos y los
agregados de modificación.

---

## 8. Orden de trabajo — rama `feat/contratos-ficha`, un commit por paso

| Paso | Qué entra | Tamaño |
|---|---|---|
| **1** | **Quitar la conciliación + las correcciones del punto 6** (regla del cero en la lista, es-CO/`enMillones()`, cabecera, «Volver»/migaja a Gestión, página de 25) | pequeño |
| **2** | Señales de modificación y prórroga en la fila · KPIs nuevos clicables · filtros y orden | mediano |
| **3** | Endpoint interno reusando `apps/publico/services` | pequeño |
| **4** | `contrato-ficha` compartido (extraído del expediente) · fila expandible · ruta `/plan/contratos/:idContrato` · barra tiempo/plata | mediano |

**Tests**, en el paso que corresponda: la regla del cero (que un `valor_pagado=0`
sin reporte no se pinte como `$0` ni dibuje barra), los borradores (una
modificación con `en_firme=false` no cuenta como hecha) y la cesión sin
proveedores (no se deduce el contratista nuevo del texto libre).

**Se para al terminar el paso 1** para que Alex lo vea antes de seguir.

# Font Awesome self-hosted — hecho el 2026-08-06

> Cierra la mitad urgente de la deuda **F8**. La migración a lucide queda como
> tarea aparte, dimensionada en el §5.

---

## 1. El problema

**Font Awesome no estaba instalado.** El proyecto tenía `<i class="fa …">` en
80 archivos y la única dependencia de iconos era `lucide-angular`. Ninguno de
esos iconos pintaba nada.

Lo que lo hacía difícil de ver es el **modo de falla**: un icono que no existe
no lanza error, no rompe el build, no aparece en ningún log. Solo deja un hueco.
Un botón de borrado cuyo único contenido era el icono se veía como un botón en
blanco, y así estuvo hasta que alguien lo miró de cerca.

## 2. Qué se hizo

`@fortawesome/fontawesome-free` 7.3.1 como dependencia, servido **desde el
propio servidor**. Nada de CDN: la red de la Alcaldía no siempre sale, y un
icono que depende de `cdnjs` es un icono que desaparece cuando se cae el
enlace. Es también la razón de no usar un *kit* de Font Awesome.

### Lo que se despacha

| | Crudo | gzip |
|---|---|---|
| `fa-solid-900.woff2` | 117 KB | — (woff2 ya viene comprimido) |
| `fa-regular-400.woff2` | 20 KB | — |
| CSS del bundle **antes** del subset | 148 KB | 30 KB |
| CSS del bundle **con** el subset | **76 KB** | **14 KB** |

**`fa-brands-400.woff2` (113 KB) no se despacha**: el proyecto no usa un solo
icono de marca. Llegaba arrastrado por `v4-font-face.css`, que tampoco hace
falta — en Font Awesome 7 la clase `.fa` a secas ya resuelve a *solid*, así que
`class="fa fa-arrow-left"` funciona con `fontawesome.css` + `solid.css`.

### El subset

`src/styles/fa-subset.css` lo genera un script y **no se edita a mano**:

```bash
npm run iconos:subset       # regenera el subset
npm run iconos:verificar    # falla si algún icono usado no está en él
```

Lleva **199 iconos de los 2.307** que trae el paquete, más la base de
`fontawesome.css` (la regla `.fa`, el `::before` que pinta el glifo, tamaños y
animaciones), que hay que conservar entera porque sin ella los 199 `--fa` no
pintan nada.

### El guardián, que es la parte importante

Un subset introduce el mismo problema que veníamos de arreglar: quien agregue
el icono 200 y no regenere, vuelve a tener un hueco mudo. Por eso
`verificar_iconos_fa.js` valida **contra el subset que se despacha**, no contra
el paquete completo — si mirara el paquete, un icono nuevo pasaría la
verificación y aun así no pintaría.

Probado: al agregar un `fa-rocket` inexistente, el verificador dice qué icono
es, en qué archivo, y **sale con código 1**. Va en CI o antes de desplegar.

El barrido de iconos vive en un módulo compartido (`scripts/_iconos_usados.js`)
que consumen el generador y el verificador. Tenerlo duplicado ya falló durante
esta misma sesión: el verificador contaba las *custom properties* del CSS de
Font Awesome (`--fa-bounce-height`) como iconos rotos, y reportaba noventa
fallos falsos.

**Barre también los `.py`**: hay 12 iconos que solo existen en el registro de
módulos del backend (`apps/presupuesto/services/modulos_area.py`) y llegan al
template por interpolación, `class="fa {{ m.icono }}"`. Dos de ellos
—`fa-palette` y `fa-user-graduate`— no aparecen en ningún archivo del frontend:
un barrido que solo mirara `class="…"` los habría dejado fuera del subset, y
serían justo los que nadie nota que faltan.

## 3. Verificación

**199 iconos usados, 0 faltantes.** Todos existen en Font Awesome Free.

## 4. Licencias

Font Awesome Free 7.3.1 se distribuye bajo tres licencias, según la parte:

| Parte | Licencia | Qué obliga |
|---|---|---|
| **Iconos** | **CC BY 4.0** | Atribuir a Font Awesome. Se cumple con la cabecera del `fa-subset.css` generado y con `3rdpartylicenses.txt`, que el build de Angular emite solo |
| **Fuentes** (`.woff2`) | **SIL OFL 1.1** | Permite usar, incrustar y redistribuir. **No** permite vender la fuente por separado, ni usar «Font Awesome» como nombre reservado si se modifica el archivo de fuente |
| **Código** (CSS/JS) | **MIT** | — |

Dos notas que importan si algún día se recorta la fuente:

- El subset de **CSS** que hicimos no toca los archivos de fuente, así que la
  OFL no entra en juego más allá de la redistribución normal.
- Recortar el **`.woff2`** sí produce una fuente modificada. La OFL lo permite,
  pero exige **no conservar el nombre reservado**: el archivo resultante no
  puede seguir llamándose «Font Awesome». Habría que renombrar la familia.

## 5. Lo que falta: la migración a lucide

**No se hace ahora.** 199 iconos en 80 archivos no se migran a mano en medio de
todo lo demás, y el riesgo de cambiar 620 llamadas a la vez no lo justifica
ninguna urgencia.

Para dimensionarla está `docs/propuestas/fa_a_lucide.csv`, que genera:

```bash
npm run iconos:mapeo-lucide
```

| | |
|---|---|
| Iconos que expone `lucide-angular` | 1.705 |
| Iconos FA usados | 199 |
| **Coincidencia exacta de nombre** | **85** — `fa-arrow-left` → `ArrowLeft` |
| Sinónimo conocido, hay que mirarlo | 20 — `fa-times` → `X`, `fa-spinner` → `LoaderCircle` |
| **Sin candidato: a mano** | **94** |

O sea: **casi la mitad son mecánicos y la otra mitad son decisiones de diseño.**
Ese es el tamaño real de la tarea, y es lo que no se sabía antes de medirlo.

El CSV trae por icono el número de archivos afectados y dos ejemplos, ordenado
por uso, para poder atacarlo por impacto y no alfabéticamente.

### El caso raro que hay que resolver primero

`area-panel.component.ts` pinta `class="fa {{ m.icono }}"` con el nombre
viniendo del backend. Migrar eso a lucide **no es sustituir una clase**: hay que
cambiar el contrato de `modulos_area.py`, porque lucide se usa por componente
(`<lucide-icon [name]="…">`) y no por clase CSS. Son 12 iconos, pero tocan
frontend y backend a la vez.

### Una limpieza gratis para cuando se haga

El inventario dejó ver que hay **el mismo icono con dos nombres** por mezclar
épocas de Font Awesome:

| | |
|---|---|
| `fa-exclamation-triangle` (9) vs `fa-triangle-exclamation` (11) | el mismo triángulo |
| `fa-info-circle` (10) vs `fa-circle-info` (8) | la misma «i» |

Unificarlos antes de migrar quita trabajo duplicado.

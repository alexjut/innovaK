# Contraste y accesibilidad

## Por qué hay verificadores

El modo de falla es **silencioso**. Un gris de 2,5:1 no rompe el build, no sale
en ningún log, y en la pantalla del que lo escribió —monitor bueno, luz de
oficina— se ve bien. Lo descubre quien lo usa en un portátil contra una ventana,
y no lo reporta: asume que así es el sistema.

```bash
npm run contraste                      # WCAG 2.1 sobre las 99 hojas
node scripts/verificar_iconos_fa.js    # iconos que no existen
node scripts/verificar_base_href.js    # corre solo dentro de npm run build
```

## Línea base + no-regresión

`scripts/_contraste_base.json` sella las **198 parejas** que ya estaban por
debajo. El script sale en verde hoy y falla **sólo si aparece algo nuevo**. Así
sirve en CI desde el primer día sin tener que saldar antes la deuda histórica.

Eso **no** es deuda nueva: es deuda que antes no se veía.

## Cosas que se aprendieron midiendo

- **Un degradado se mide en su peor extremo.** El subtítulo del hero daba 5,19:1
  en el extremo oscuro —donde uno lo comprueba— y **3,89:1** en el claro.
- **El fondo importa.** Cinco grises daban 4,83:1 sobre blanco, pero la fila
  ABIERTA del explorador cambia de fondo y ahí caían a 4,49:1.
- **Relleno ≠ texto.** Un color calibrado para un punto de semáforo (3:1 contra
  lo adyacente) no sirve como cifra (4,5:1).
- Un `<i class="fa">` sin `aria-hidden` **no** es invisible para un lector: el
  glifo vive en un carácter de uso privado y unos lectores leen basura.

Relacionado: [[Dashboard-360]]

# Territorio

Kennedy: 12 UPZ, 111 barrios, 9 UPL (POT 2022).

## Fuentes verificadas

| Dato | Fuente | Estado |
|---|---|---|
| Estratos, contorno, UPZ | **IDECA** (ArcGIS oficial) | endpoints verificados. El estrato no cambia desde 2019 |
| Colegios | **SED** / IDECA | 48 colegios · 79 sedes · 95.909 alumnos |
| CAI | **SCJ** | 15 CAI. Los móviles no los publica nadie |
| Parques | IDECA | 554 filas, 552 en Kennedy |

> [!warning] Cobertura de barrios: 32 de 111
> Mismatch de códigos con IDECA (deuda M22). El denominador correcto es 111 —
> decir «79 sin geometría» sin el denominador confunde.

## Las direcciones tienen que existir

> **Nunca texto libre.** Autocompletar contra Catastro + pin en el mapa (como
> Uber), y guardar **lat/lon**. Una dirección que no se puede ubicar no sirve
> para planear ni para rendir cuentas.

Todo evento creado sin coordenadas queda en la Alcaldía
(`get_lugar_incidencia_default()`), para que no desaparezca del mapa.

## Estratificación en el mapa

La capa se pintaba **debajo** del basemap por z-index en canvas. El arreglo real
fue usar **SVG**, como los demás filtros. No medir píxeles por consola.

Relacionado: [[Mapa-del-sistema]] · [[Captura-ciudadana]]

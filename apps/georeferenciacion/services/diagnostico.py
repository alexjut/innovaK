"""Contadores de operaciones que pueden devolver vacío SIN lanzar error.

TODO(pendiente 2026-07-30 · ver ESTADO.md §2.4) — este módulo ES el barrido de
fallos silenciosos. Lo que resuelve, en una frase: en este pipeline hay
operaciones cuyo resultado vacío hoy se trata igual que un resultado válido, y
las dos veces que eso mordió nadie se enteró hasta días después.

## Los cuatro desenlaces, y por qué son cuatro y no dos

Un `None` no dice nada por sí solo. Estos cuatro sí, y son excluyentes:

    OK            encontró
    SIN_HIT       buscó y no encontró          ← "no encontré"
    NO_INTENTADO  ni siquiera llegó a buscar   ← "encontré nada"
    ERROR         reventó y alguien se tragó la excepción

`NO_INTENTADO` es el que faltaba y el que importa. Un resumen que dice
"2 sin resolver" cuando en realidad hubo 2 sin hit **y 130 que jamás se
intentaron** no está informando: está tranquilizando. Las dos categorías se ven
idénticas desde afuera —ambas devuelven `None`— y exigen acciones opuestas: una
se arregla corrigiendo el dato, la otra corrigiendo el proceso.

`ERROR` va aparte de `SIN_HIT` por lo mismo. Un `except Exception` que devuelve
`None` convierte una caída de red en "esta dirección no existe", y eso ensucia
el reporte del área con trabajo que no es suyo.

## Cómo se usa

    diag = Diagnostico()
    diag.anotar("url_maps", OK)
    diag.anotar("url_maps", NO_INTENTADO, "sin enlace corto y --sin-red")
    ...
    for linea in diag.lineas():
        self.stdout.write(linea)

La regla de oro: **toda ruta de código que pueda devolver vacío anota**. Si una
rama no anota, vuelve el punto ciego — por eso `sin_anotar()` existe y por eso
hay un test que compara los intentos contra el universo esperado.
"""
from __future__ import annotations

# Los cuatro desenlaces. Cerrados a propósito: si hiciera falta un quinto, es
# una decisión que se toma acá y no un string suelto en el sitio de la llamada.
OK = "ok"
SIN_HIT = "sin_hit"
NO_INTENTADO = "no_intentado"
ERROR = "error"

DESENLACES = (OK, SIN_HIT, NO_INTENTADO, ERROR)

# Cómo se lee cada desenlace en el resumen. El texto importa: lo lee alguien que
# tiene que decidir si el problema es del dato o del proceso.
ETIQUETAS = {
    OK: "resueltos",
    SIN_HIT: "buscados y no encontrados",
    NO_INTENTADO: "NO intentados",
    ERROR: "con error (excepción tragada)",
}


class Diagnostico:
    """Cuenta desenlaces por operación y guarda un ejemplo de cada motivo.

    No decide nada ni interrumpe nada: solo hace visible lo que hoy es mudo.
    Frenar es decisión de quien lo consulta (`exigir_cruces` en el resolver, por
    ejemplo, sí frena).
    """

    # Cuántos motivos distintos se guardan por operación. Suficiente para
    # diagnosticar sin convertir el resumen en un volcado.
    MAX_MOTIVOS = 6

    def __init__(self):
        # {operacion: {desenlace: n}}
        self._conteo: dict[str, dict[str, int]] = {}
        # {operacion: {motivo: n}} — el porqué. Se guarda TAMBIÉN para los OK:
        # hay resultados válidos que igual hay que poder ver ("resolvió, pero la
        # geometría está doblemente codificada en la BD", "ubicada por el pin de
        # Maps y no por Catastro"). Restringirlo a los fallos escondía justo esa
        # clase de aviso — un dato que sirve hoy y está podrido por debajo.
        self._motivos: dict[str, dict[str, int]] = {}

    def anotar(self, operacion: str, desenlace: str, motivo: str = "") -> None:
        if desenlace not in DESENLACES:
            # Un typo en el desenlace haría que el contador mienta en silencio,
            # que es exactamente lo que este módulo existe para evitar.
            raise ValueError(
                f"Desenlace desconocido {desenlace!r}. Los válidos son: "
                f"{', '.join(DESENLACES)}.")
        self._conteo.setdefault(operacion, {}).setdefault(desenlace, 0)
        self._conteo[operacion][desenlace] += 1
        if motivo:
            m = self._motivos.setdefault(operacion, {})
            m[motivo] = m.get(motivo, 0) + 1

    # -- lectura -------------------------------------------------------------
    def total(self, operacion: str, desenlace: str | None = None) -> int:
        conteo = self._conteo.get(operacion, {})
        if desenlace is None:
            return sum(conteo.values())
        return conteo.get(desenlace, 0)

    def operaciones(self) -> list[str]:
        return sorted(self._conteo)

    def mudos(self) -> dict[str, int]:
        """Operaciones con desenlaces que NO son OK, por operación.

        Es el número que hay que mirar primero: son los vacíos que antes se
        confundían con resultados válidos.
        """
        return {op: sum(n for d, n in c.items() if d != OK)
                for op, c in self._conteo.items()
                if any(d != OK for d in c)}

    def sin_anotar(self, operacion: str, esperados: int) -> int:
        """Intentos que debieron anotarse y no se anotaron.

        Un número distinto de 0 significa que hay una rama de código que
        devuelve vacío sin pasar por el contador — o sea, un punto ciego nuevo.
        No es un detalle de contabilidad: es la regresión que este módulo evita.
        """
        return esperados - self.total(operacion)

    # -- salida --------------------------------------------------------------
    def lineas(self, titulo: str = "FALLOS SILENCIOSOS") -> list[str]:
        """El bloque que se imprime al cerrar la corrida."""
        if not self._conteo:
            return [f"--- {titulo} ---", "  (no se registró ninguna operación)"]

        out = [f"--- {titulo} ---"]
        for op in self.operaciones():
            conteo = self._conteo[op]
            total = sum(conteo.values())
            out.append(f"  {op}  ({total} intentos)")
            for desenlace in DESENLACES:
                n = conteo.get(desenlace, 0)
                if not n:
                    continue
                pct = 100 * n / total if total else 0
                out.append(f"      {ETIQUETAS[desenlace]:<32} {n:>5}  ({pct:4.1f} %)")
            for motivo, n in sorted(self._motivos.get(op, {}).items(),
                                    key=lambda kv: -kv[1])[:self.MAX_MOTIVOS]:
                out.append(f"          · {motivo}: {n}")
        return out

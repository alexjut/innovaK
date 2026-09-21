"""Cada `data-tour` que el tour de Kenny señala tiene que existir en algún template.

## Por qué hace falta un test para esto

Los pasos del tour apuntan a un selector CSS escrito a mano en
`tours.data.ts`. Cuando alguien quita o renombra el elemento marcado, el paso
queda señalando la nada — y **nada lo detecta**: no hay error de compilación,
el build pasa, la pantalla se ve bien y el tour solo falla cuando un
funcionario nuevo lo abre.

Pasó dos veces en la misma jornada, las dos en `/app/plan`:

1. Al retirar la sección «El Plan», el marcador `presupuesto-cards` se mudó
   solo a la siguiente sección —va atado a la primera que exista— y el texto
   quedó diciendo «Cuatro secciones… qué se prometió», nombrando una sección
   que acababa de desaparecer.
2. Al partir el hub en Visual y Gestión, el mismo marcador volvió a quedar
   describiendo algo que ya no estaba.

Ninguna de las dos rompía el tour: rompían lo que el tour DICE, que es peor,
porque se ve funcionando.

## Qué comprueba, y qué no

Comprueba que el selector **existe en el código** como atributo `data-tour`.
No comprueba que se esté renderizando en ese momento —eso depende de permisos
y del estado de la pantalla, y exigiría un navegador—, ni que el texto del paso
siga siendo cierto. Lo segundo no lo puede verificar una máquina; por eso el
texto de cada paso se revisa a mano cuando se toca la pantalla que señala.

Es un test de Python sobre archivos de TypeScript a propósito: el proyecto no
tiene suite de Angular corriendo en CI, y este defecto es demasiado silencioso
para dejarlo sin red.
"""
import pathlib
import re
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[3]
FRONTEND = RAIZ / "frontend" / "src" / "app"
TOURS = FRONTEND / "features" / "onboarding" / "tours.data.ts"

#: `selector: '[data-tour="lo-que-sea"]'`
_SELECTOR = re.compile(r"""selector:\s*['"]\[data-tour=["']([^"']+)["']\]['"]""")
#: `data-tour="x"` o `[attr.data-tour]="cond ? 'x' : null"`
_MARCADOR = re.compile(r"""data-tour[^=]{0,12}=\s*["'][^"']*?["']?([a-z0-9-]+)["']?""")
_MARCADOR_SIMPLE = re.compile(r"""data-tour=["']([a-z0-9-]+)["']""")
_MARCADOR_BINDING = re.compile(r"""\[attr\.data-tour\][^>]*?['"]([a-z0-9-]+)['"]""")


def _marcadores_del_codigo() -> set[str]:
    """Todos los `data-tour` que existen en los templates del SPA.

    **Se excluye `tours.data.ts`**, y no es un detalle: sus propios selectores
    tienen la forma `[data-tour="x"]`, así que al escanearlo el archivo se
    encuentra a sí mismo y TODO selector pasa a existir. La primera versión de
    este test se lo comió entero: al romper un selector a propósito para
    comprobar que fallaba, siguió en verde.
    """
    encontrados: set[str] = set()
    for archivo in FRONTEND.rglob("*.ts"):
        if archivo.resolve() == TOURS.resolve():
            continue
        texto = archivo.read_text(encoding="utf-8", errors="ignore")
        if "data-tour" not in texto:
            continue
        encontrados |= set(_MARCADOR_SIMPLE.findall(texto))
        encontrados |= set(_MARCADOR_BINDING.findall(texto))
    for archivo in FRONTEND.rglob("*.html"):
        texto = archivo.read_text(encoding="utf-8", errors="ignore")
        if "data-tour" in texto:
            encontrados |= set(_MARCADOR_SIMPLE.findall(texto))
            encontrados |= set(_MARCADOR_BINDING.findall(texto))
    return encontrados


def _selectores_del_tour() -> list[str]:
    if not TOURS.exists():
        return []
    return _SELECTOR.findall(TOURS.read_text(encoding="utf-8"))


class SelectoresDelTourTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not TOURS.exists():
            raise unittest.SkipTest(f"no está {TOURS}")
        cls.selectores = _selectores_del_tour()
        cls.marcadores = _marcadores_del_codigo()

    def test_el_tour_declara_pasos(self):
        """Si esto falla, el regex dejó de encajar y los demás pasan en falso."""
        self.assertTrue(
            self.selectores,
            "no se encontró ni un `selector: '[data-tour=…]'`: el formato de "
            "tours.data.ts cambió y este test dejó de mirar lo que cree mirar")

    def test_el_codigo_declara_marcadores(self):
        self.assertTrue(
            self.marcadores,
            "no se encontró ni un `data-tour` en los templates: el regex de "
            "marcadores dejó de encajar")

    def test_cada_selector_del_tour_existe_en_algun_template(self):
        huerfanos = [s for s in self.selectores if s not in self.marcadores]
        self.assertFalse(
            huerfanos,
            "el tour de Kenny señala elementos que ya no existen: "
            + ", ".join(sorted(huerfanos))
            + ". Un paso huérfano no rompe el tour —lo deja apuntando a la "
              "nada— y por eso no se nota hasta que alguien lo abre.")

    def test_los_marcadores_del_plan_siguen_ahi(self):
        """Los de `/app/plan`, que ya se rompieron dos veces en un día."""
        for marcador in ("presupuesto-titulo", "presupuesto-cards",
                         "plan-visual-titulo", "plan-visual-arbol"):
            with self.subTest(marcador=marcador):
                self.assertIn(
                    marcador, self.marcadores,
                    f"falta `data-tour=\"{marcador}\"` en los templates")

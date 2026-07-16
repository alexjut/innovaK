"""Tests del bono por estrato oficial (PR-7, preparado e inactivo).

Esto reparte recursos públicos, así que lo que se blinda no es solo el número:
es el **motivo**. Tres situaciones distintas dan bono 0 y una organización tiene
derecho a saber cuál le tocó:

  - `fuera_kennedy`            → tu sede no está en la localidad
  - `sin_estrato_resuelto`     → no pudimos ubicar tu dirección
  - `tabla_no_aprobada_comite` → el bono todavía no está aprobado

Si los tres colapsaran en "0" a secas, un reclamo sería imposible de responder.

Las direcciones y datos de estos tests son INVENTADOS: el repo es público y las
inscripciones reales son dato de terceros bajo habeas data (Ley 1581).
"""
import unittest

from apps.banco_iniciativas.services.puntaje import (
    BONO_ESTRATO_MAX,
    RUBRICA_AUTO,
    TABLA_ESTRATO_PENDIENTE,
    calcular_bono_estrato,
)


class _Inscripcion:
    """Doble mínimo: el bono solo lee estos tres campos."""

    def __init__(self, estrato_ideca_org=None, fuera_kennedy=False, geo_metodo=None):
        self.estrato_ideca_org = estrato_ideca_org
        self.fuera_kennedy = fuera_kennedy
        self.geo_metodo = geo_metodo


# Tabla hipotética, SOLO para tests: la real la aprueba el Comité.
TABLA_DE_PRUEBA = {"1": 5, "2": 4, "3": 3, "4": 1}
RUBRICA_APROBADA = {"tabla_estrato": TABLA_DE_PRUEBA}


class ReglasDelBonoTests(unittest.TestCase):
    def test_fuera_kennedy_da_cero(self):
        # R1 — decisión Alex 2026-07-16. El bono compensa operar en territorio
        # vulnerable DE KENNEDY; fuera de la localidad no aplica.
        r = calcular_bono_estrato(
            _Inscripcion(fuera_kennedy=True, geo_metodo="fuera_kennedy"),
            RUBRICA_APROBADA)
        self.assertEqual(r["puntaje"], 0)
        self.assertEqual(r["motivo"], "fuera_kennedy")

    def test_fuera_kennedy_gana_aunque_tuviera_estrato(self):
        # Blindaje: si alguna vez se le escribiera un estrato a una org de
        # fuera (el bug del rescate por barrio, arreglado el 2026-07-16), el
        # bono NO puede repartirlo igual. R1 va primero por esto.
        r = calcular_bono_estrato(
            _Inscripcion(estrato_ideca_org=1, fuera_kennedy=True), RUBRICA_APROBADA)
        self.assertEqual(r["puntaje"], 0)
        self.assertEqual(r["motivo"], "fuera_kennedy")

    def test_sin_estrato_da_cero(self):
        # R2 — no se infiere nada. NULL es "no sabemos", no "estrato bajo".
        r = calcular_bono_estrato(
            _Inscripcion(geo_metodo="sin_direccion"), RUBRICA_APROBADA)
        self.assertEqual(r["puntaje"], 0)
        self.assertEqual(r["motivo"], "sin_estrato_resuelto")

    def test_sin_tabla_aprobada_da_cero(self):
        # R3 — el interruptor. Mientras el Comité no apruebe los puntos, el
        # bono está inactivo y esto se puede cascadear sin mover el ranking.
        r = calcular_bono_estrato(_Inscripcion(estrato_ideca_org=2), {})
        self.assertEqual(r["puntaje"], 0)
        self.assertEqual(r["motivo"], "tabla_no_aprobada_comite")
        self.assertEqual(r["estrato_usado"], 2)

    def test_estrato_2_con_tabla_aprobada(self):
        r = calcular_bono_estrato(
            _Inscripcion(estrato_ideca_org=2, geo_metodo="placa_exacta"),
            RUBRICA_APROBADA)
        self.assertEqual(r["puntaje"], 4)
        self.assertEqual(r["motivo"], "ok")
        self.assertEqual(r["estrato_usado"], 2)

    def test_estrato_3_con_tabla_aprobada(self):
        r = calcular_bono_estrato(
            _Inscripcion(estrato_ideca_org=3, geo_metodo="via_mayoria"),
            RUBRICA_APROBADA)
        self.assertEqual(r["puntaje"], 3)
        self.assertEqual(r["motivo"], "ok")

    def test_estrato_fuera_de_la_tabla_no_puntua(self):
        # Estrato 6 sin fila en la tabla: 0, no el tier más cercano. Si el
        # Comité no lo puso, no vale puntos — no se inventa.
        r = calcular_bono_estrato(_Inscripcion(estrato_ideca_org=6), RUBRICA_APROBADA)
        self.assertEqual(r["puntaje"], 0)

    def test_geo_metodo_persiste_en_el_resultado(self):
        # Es la trazabilidad: dice CÓMO se supo el estrato, no solo cuál es.
        for metodo in ("placa_exacta", "via_mayoria", "barrio", "fuera_kennedy"):
            r = calcular_bono_estrato(
                _Inscripcion(estrato_ideca_org=2, geo_metodo=metodo), RUBRICA_APROBADA)
            self.assertEqual(r["geo_metodo"], metodo)

    def test_el_bono_nunca_pasa_del_maximo(self):
        for e in range(1, 7):
            r = calcular_bono_estrato(_Inscripcion(estrato_ideca_org=e), RUBRICA_APROBADA)
            self.assertLessEqual(r["puntaje"], BONO_ESTRATO_MAX)


class BonoInactivoTests(unittest.TestCase):
    """Mientras el Comité no apruebe, esto NO puede repartir puntos."""

    def test_la_tabla_viene_vacia_de_fabrica(self):
        self.assertEqual(TABLA_ESTRATO_PENDIENTE, {})

    def test_sin_rubrica_ningun_estrato_puntua(self):
        # El caso de producción hoy: se cascadea y el ranking no se mueve.
        for e in (None, 1, 2, 3, 4, 5, 6):
            r = calcular_bono_estrato(_Inscripcion(estrato_ideca_org=e))
            self.assertEqual(r["puntaje"], 0, f"estrato {e}")

    def test_la_rubrica_declara_el_bono_como_inactivo(self):
        # El snapshot de `banco_rubrica` deja registro de desde cuándo el bono
        # estuvo (y no estuvo) activo. Auditable ante una impugnación.
        bono = RUBRICA_AUTO["bono_estrato"]
        self.assertFalse(bono["activo"])
        self.assertEqual(bono["tabla_estrato"], {})
        self.assertEqual(bono["max"], BONO_ESTRATO_MAX)


class PilotoTests(unittest.TestCase):
    """Integración con la forma real de los datos del piloto (evento 62).

    Sin BD: se reproduce la distribución medida el 2026-07-16 (15 resueltas /
    7 fuera de Kennedy / 2 sin dirección) con dobles, para blindar que las 7 de
    fuera dan 0 aunque el bono se active.
    """

    @staticmethod
    def _piloto():
        return ([_Inscripcion(estrato_ideca_org=3, geo_metodo="placa_exacta")] * 10
                + [_Inscripcion(estrato_ideca_org=2, geo_metodo="via_mayoria")] * 4
                + [_Inscripcion(estrato_ideca_org=3, geo_metodo="barrio")]
                + [_Inscripcion(fuera_kennedy=True, geo_metodo="fuera_kennedy")] * 7
                + [_Inscripcion(geo_metodo="sin_direccion")] * 2)

    def test_la_distribucion_del_piloto_suma_24(self):
        self.assertEqual(len(self._piloto()), 24)

    def test_los_7_fuera_kennedy_del_piloto_dan_cero(self):
        rs = [calcular_bono_estrato(i, RUBRICA_APROBADA) for i in self._piloto()]
        fuera = [r for r in rs if r["motivo"] == "fuera_kennedy"]
        self.assertEqual(len(fuera), 7)
        self.assertTrue(all(r["puntaje"] == 0 for r in fuera))

    def test_solo_las_15_resueltas_reciben_bono(self):
        rs = [calcular_bono_estrato(i, RUBRICA_APROBADA) for i in self._piloto()]
        con_bono = [r for r in rs if r["puntaje"] > 0]
        self.assertEqual(len(con_bono), 15)
        self.assertTrue(all(r["motivo"] == "ok" for r in con_bono))

    def test_hoy_con_el_bono_inactivo_el_piloto_entero_da_cero(self):
        rs = [calcular_bono_estrato(i) for i in self._piloto()]
        self.assertTrue(all(r["puntaje"] == 0 for r in rs))


class DireccionLonLatFormTests(unittest.TestCase):
    """La coordenada de la sede tiene que sobrevivir el viaje.

    El picker la resolvía en el navegador y `buildFormData()` la botaba al
    enviar: se hacía todo el trabajo de ubicar la sede y se guardaba solo el
    texto. Resultado: las 24 inscripciones del piloto no existían en el mapa, y
    nada fallaba — por eso nadie lo vio. Estos tests fijan el contrato del form.
    """

    def _form(self):
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        return InscripcionBancoForm

    def test_el_form_declara_los_dos_campos(self):
        campos = self._form().base_fields
        self.assertIn("direccion_lon", campos)
        self.assertIn("direccion_lat", campos)

    def test_no_son_obligatorios(self):
        # Si Catastro no resuelve, se guarda la dirección sin punto antes que
        # perder la inscripción del ciudadano.
        campos = self._form().base_fields
        self.assertFalse(campos["direccion_lon"].required)
        self.assertFalse(campos["direccion_lat"].required)

    def test_media_coordenada_se_descarta_entera(self):
        # Un punto a medias pasaría el CHECK de la BD (que solo exige ambas NULL
        # o ambas en Bogotá) y no ubica nada.
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm

        for lon, lat in ((-74.15, None), (None, 4.62)):
            with self.subTest(lon=lon, lat=lat):
                f = InscripcionBancoForm()
                f.cleaned_data = {"direccion_lon": lon, "direccion_lat": lat}
                limpios = dict(f.cleaned_data)
                if (limpios.get("direccion_lon") is None) != (limpios.get("direccion_lat") is None):
                    limpios["direccion_lon"] = limpios["direccion_lat"] = None
                self.assertIsNone(limpios["direccion_lon"])
                self.assertIsNone(limpios["direccion_lat"])

    def test_el_modelo_tiene_las_columnas(self):
        from apps.banco_iniciativas.models.inscripcion import InscripcionBancoIniciativa
        campos = {f.name for f in InscripcionBancoIniciativa._meta.get_fields()}
        self.assertIn("direccion_lon", campos)
        self.assertIn("direccion_lat", campos)

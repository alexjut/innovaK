"""Qué tanto se usa la IA, y cuántas preguntas no entiende.

    python manage.py resumen_uso_ia                 # lo que haya en el log vivo
    python manage.py resumen_uso_ia --archivo X.log

Lee las líneas que escribe `apps.dashboard.services.uso_ia` y las cuenta. Es la
línea base que hoy NO existe: antes del 2026-10-08 el uso real de las dos IA
era NULL —ninguna tabla lo registraba—, así que «Kenny no se usa» o «el
enrutador falla mucho» eran opiniones sin forma de comprobarse.

Solo lee. No escribe en la base ni en el log.
"""
import collections
import pathlib
import re

from django.core.management.base import BaseCommand

from apps.dashboard.services.uso_ia import PREFIJO

#: `USO_IA motor=kenny resuelto=respondido entendio=si largo=24 huella=ab12cd34ef`
_LINEA = re.compile(
    PREFIJO + r"\s+motor=(?P<motor>\S+)\s+resuelto=(?P<resuelto>.+?)"
    r"\s+entendio=(?P<entendio>\S+)\s+largo=(?P<largo>\d+)\s+huella=(?P<huella>\S+)")


class Command(BaseCommand):
    help = "Resume el uso registrado de Kenny y del motor de beneficiarios."

    def add_arguments(self, p):
        p.add_argument("--archivo", default=None,
                       help="Archivo de registro. Por omisión busca en logs/.")

    def handle(self, *a, **o):
        rutas = ([pathlib.Path(o["archivo"])] if o["archivo"] else
                 sorted(pathlib.Path("logs").glob("*.log")) if pathlib.Path("logs").is_dir()
                 else [])
        if not rutas:
            self.stdout.write(self.style.WARNING(
                "No encontré archivos de registro. Pase --archivo, o espere a que "
                "se acumulen: el registro arrancó el 2026-10-08 y hace falta "
                "tiempo para que la cifra signifique algo."))
            return

        por_motor = collections.Counter()
        no_entendio = collections.Counter()
        resueltos = collections.defaultdict(collections.Counter)
        huellas = collections.defaultdict(collections.Counter)
        leidas = 0

        for r in rutas:
            try:
                texto = r.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in _LINEA.finditer(texto):
                leidas += 1
                motor = m.group("motor")
                por_motor[motor] += 1
                if m.group("entendio") != "si":
                    no_entendio[motor] += 1
                resueltos[motor][m.group("resuelto").strip()] += 1
                huellas[motor][m.group("huella")] += 1

        if not leidas:
            self.stdout.write(self.style.WARNING(
                f"Archivos leídos: {len(rutas)}. Ninguna línea de {PREFIJO}: "
                "todavía nadie ha usado la IA desde que se instrumentó, o el "
                "registro va a otro archivo."))
            return

        self.stdout.write(self.style.SUCCESS(f"\n{leidas} usos registrados\n"))
        for motor, n in por_motor.most_common():
            malas = no_entendio[motor]
            pct = 100.0 * malas / n
            self.stdout.write(f"  {motor}: {n} usos · {malas} sin entender ({pct:.1f} %)")
            for res, c in resueltos[motor].most_common(6):
                self.stdout.write(f"      {c:>5}  {res[:62]}")
            # Una pregunta repetida suele ser alguien que no obtuvo respuesta y
            # volvió a intentar. Es la señal más honesta de insatisfacción que
            # se puede sacar sin guardar el texto.
            rep = [(h, c) for h, c in huellas[motor].most_common(3) if c > 1]
            if rep:
                self.stdout.write("      preguntas repetidas (misma huella): "
                                  + ", ".join(f"{c}×" for _, c in rep))
        self.stdout.write("")
        self.stdout.write(
            "  El texto de las preguntas NO se guarda: podría traer el nombre o "
            "el documento de un ciudadano. Solo su longitud y una huella corta.")

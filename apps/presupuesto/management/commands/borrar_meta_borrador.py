"""Borra una meta a medio escribir del catálogo, con guardas.

    docker exec innova_k python manage.py borrar_meta_borrador 10
    docker exec innova_k python manage.py borrar_meta_borrador 10 --write --usuario <username>

SECO POR DEFECTO, firmado. No es idempotente al uso —borrar dos veces la misma
meta no tiene sentido—: si ya no está, lo dice y no hace nada.

QUÉ ES UN BORRADOR. Una fila de `metas` que alguien empezó y no terminó: sin
código SEGPLAN, sin indicadores vivos, sin plata en la Matriz y sin alerta. La
que motivó este comando es la 10, «camino seguro las mujeres», que colgaba del
proyecto 2818 y aparecía en el Plan oficial como una tarjeta con la etiqueta de
código vacía y sus cuatro casillas en «Sin dato». Hacía que toda cuenta de
metas de esa pantalla diera uno de más.

LAS GUARDAS SON EL COMANDO. Se niega a borrar si la meta tiene cualquiera de
estas cosas, porque entonces no es un borrador:

- `codigo_meta` — está en el Plan oficial, aunque sea sin cifras.
- un indicador vivo en `presu_indicador_meta_proyecto`.
- cifras en la Matriz para su código.
- una alerta de cumplimiento.

LO QUE SÍ ARRASTRA, y se declara: su fila de `meta_proyecto`, y las filas de la
tabla vieja `presu_indicador` que cuelguen de ella. Esa tabla tiene 3 filas en
toda la base, ningún código Python la lee y las tres son borradores; su vínculo
es NOT NULL, así que bloquea el borrado si no se resuelve. Un borrador de
indicador que solo existía para colgar de un borrador de meta se va con ella.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Borra una meta borrador (sin código, sin indicadores, sin cifras). Seco por defecto."

    def add_arguments(self, parser):
        parser.add_argument("codigo", type=int, help="`metas.codigo` de la meta a borrar")
        parser.add_argument("--write", action="store_true",
                            help="Borra de verdad. Sin esto, solo reporta.")
        parser.add_argument("--usuario", default=None,
                            help="Username de quien lo corre. Obligatorio con --write.")

    def handle(self, *args, **opts):
        codigo = opts["codigo"]
        escribir = opts["write"]
        autor = None
        if escribir:
            from django.contrib.auth import get_user_model
            username = opts.get("usuario")
            if not username:
                raise CommandError("--write exige --usuario: borrar del catálogo "
                                   "sin autor no queda defendible.")
            autor = get_user_model().objects.filter(username=username).first()
            if autor is None:
                raise CommandError(f"No existe el usuario «{username}».")

        with connection.cursor() as cur:
            estado = self._mirar(cur, codigo)
            if estado is None:
                self.stdout.write(self.style.SUCCESS(
                    f"La meta {codigo} no está. Nada que borrar."))
                return
            self._reportar(codigo, estado)
            impedimentos = self._impedimentos(estado)
            if impedimentos:
                raise CommandError(
                    "Esta meta NO es un borrador y no se borra:\n  - "
                    + "\n  - ".join(impedimentos))
            if not escribir:
                self.stdout.write(self.style.WARNING(
                    "\nSECO: no se borró nada. Repite con --write --usuario <u>."))
                return
            with transaction.atomic():
                self._borrar(cur, codigo, estado, autor)
            self.stdout.write(self.style.SUCCESS(f"\nMeta {codigo} borrada."))

    def _mirar(self, cur, codigo) -> dict | None:
        cur.execute("SELECT nombre, codigo_meta FROM metas WHERE codigo = %s", [codigo])
        fila = cur.fetchone()
        if fila is None:
            return None
        nombre, codigo_meta = fila
        cur.execute("SELECT id FROM meta_proyecto WHERE meta_id = %s", [codigo])
        mps = [r[0] for r in cur.fetchall()]
        vivos = viejos = 0
        if mps:
            cur.execute("SELECT COUNT(*) FROM presu_indicador_meta_proyecto "
                        "WHERE meta_proyecto_id = ANY(%s)", [mps])
            vivos = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM presu_indicador WHERE meta_proyecto_id = ANY(%s)", [mps])
            viejos = cur.fetchone()[0]
        cifras = alerta = 0
        if codigo_meta:
            cur.execute("""SELECT COUNT(*), COUNT(alerta) FROM presu_presupuesto_meta_vigencia
                           WHERE codigo_meta = %s""", [str(codigo_meta)])
            cifras, alerta = cur.fetchone()
        return {"nombre": nombre, "codigo_meta": codigo_meta, "meta_proyectos": mps,
                "indicadores_vivos": vivos, "indicadores_viejos": viejos,
                "filas_matriz": cifras, "con_alerta": alerta}

    def _reportar(self, codigo, e):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n[meta {codigo}]"))
        self.stdout.write(f"    nombre              : {e['nombre']}")
        self.stdout.write(f"    código SEGPLAN      : {e['codigo_meta'] or '— ninguno'}")
        self.stdout.write(f"    meta_proyecto       : {e['meta_proyectos'] or '— ninguno'}")
        self.stdout.write(f"    indicadores vivos   : {e['indicadores_vivos']}")
        self.stdout.write(f"    filas en la Matriz  : {e['filas_matriz']} "
                          f"({e['con_alerta']} con alerta)")
        self.stdout.write(f"    se arrastra también : {e['indicadores_viejos']} fila(s) de "
                          f"la tabla vieja `presu_indicador`")

    def _impedimentos(self, e) -> list:
        malas = []
        if e["codigo_meta"]:
            malas.append(f"tiene código SEGPLAN «{e['codigo_meta']}»: está en el Plan oficial")
        if e["indicadores_vivos"]:
            malas.append(f"tiene {e['indicadores_vivos']} indicador(es) vivo(s)")
        if e["filas_matriz"]:
            malas.append(f"tiene {e['filas_matriz']} fila(s) de cifras en la Matriz")
        if e["con_alerta"]:
            malas.append("tiene alerta de cumplimiento cargada")
        return malas

    def _borrar(self, cur, codigo, e, autor):
        from apps.presupuesto.services.auditoria import registrar_cambio

        if e["meta_proyectos"]:
            cur.execute("DELETE FROM presu_indicador WHERE meta_proyecto_id = ANY(%s)",
                        [e["meta_proyectos"]])
            if cur.rowcount:
                self.stdout.write(f"    {cur.rowcount} fila(s) de `presu_indicador` borradas")
            cur.execute("DELETE FROM meta_proyecto WHERE meta_id = %s", [codigo])
            self.stdout.write(f"    {cur.rowcount} fila(s) de `meta_proyecto` borradas")
        cur.execute("DELETE FROM metas WHERE codigo = %s", [codigo])
        registrar_cambio(usuario=autor, entidad="metas", entidad_id=codigo,
                         campo="__borrada__", valor_anterior=e["nombre"], valor_nuevo=None,
                         fuente="borrar_meta_borrador",
                         observacion="meta a medio escribir: sin código, sin indicadores "
                                     "vivos, sin cifras y sin alerta")

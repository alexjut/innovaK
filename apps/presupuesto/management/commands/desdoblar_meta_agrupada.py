"""Desdobla la meta agrupada de posmedia en las dos metas SEGPLAN reales.

    docker exec innova_k python manage.py desdoblar_meta_agrupada
    docker exec innova_k python manage.py desdoblar_meta_agrupada --write --usuario <username>

SECO POR DEFECTO, firmado e IDEMPOTENTE — misma convención que
`importar_matriz_pdl_alk` y `cargar_crp`.

QUÉ ARREGLA. La Matriz reporta 78 metas. Dos de ellas —23771 «acceso» y 23772
«permanencia», las dos del proyecto 2377 de Educación posmedia— NO existen como
fila propia en el catálogo interno: las cubre UNA sola meta agrupada, la 8,
«Impactar 1400 jóvenes… (700 acceso + 700 permanencia)», que lleva los dos
indicadores adentro.

Como todo lo que recorre el catálogo se llavea por el código SEGPLAN y la
agrupada no tiene código, esas dos se caen de cada pantalla que cuenta metas:

    metas del Plan          76 de 78
    metas ejecutadas        21 de 23
    perspectiva «potencial»  5 de 7

Y en la peor dirección: las dos que desaparecen están **Ejecutadas al 100 %**
(175 de 175 cada una, según la hoja Alertas), así que Educación se ve peor de
lo que está. La plata también queda fuera del corte por programa —$52.516,8 M
proyectados, $28.987,3 M apropiados— aunque sí entra por proyecto y por área.

QUÉ HACE, EN ESTE ORDEN (todo en una transacción):

1. Crea las dos `metas` con su `codigo_meta`, copiando del Excel el nombre
   oficial y del hermano 23773 las columnas SEGPLAN que comparten (programa,
   sector, línea, objetivo).
2. Crea sus dos `meta_proyecto` contra el proyecto 2805.
3. MUEVE los dos indicadores vivos a sus metas nuevas. No se recrean: mover
   preserva su id, y con él los avances y las vinculaciones a actividades que
   ya cuelgan de ellos —medido: 2 filas de avance y 2 de actividad—.
4. Borra el `meta_proyecto` de la agrupada y la agrupada.

POR QUÉ EL ORDEN IMPORTA. Los indicadores cuelgan del `meta_proyecto` de la
agrupada; borrarlo antes de moverlos se los llevaría por delante, y con ellos
los avances registrados.

POR QUÉ ESTO NO LO HACE EL IMPORTADOR. `importar_matriz_pdl_alk` se niega a
crear un indicador que ya existe como KPI vivo de una meta agrupada, y con
razón: la primera vez que lo intentó DUPLICÓ los indicadores 51 y 52 de este
mismo proyecto. Desdoblar no es importar: hay que mover lo que ya existe, y eso
es una decisión, no una carga.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

#: La agrupada y sus dos metas reales. Explícito a propósito: un comando que
#: adivina cuál meta desdoblar es un comando que algún día desdobla la que no
#: era.
META_AGRUPADA = 8
PROYECTO_ID = 2805
PROYECTO_CODIGO = 2377
#: El hermano del que se copian las columnas SEGPLAN compartidas.
META_HERMANA = 100036

#: {codigo_meta: (nombre oficial de la Matriz, id del indicador que le
#: corresponde, código del indicador SEGPLAN)}. El emparejamiento sale de los
#: propios nombres de los indicadores, que ya citan su meta.
DESDOBLE = {
    "23771": ("Beneficiar 700 Estudiante(s) En programas de educación posmedia "
              "(niveles de formación técnica, tecnológica y/o profesional)", 30, 52),
    "23772": ("Beneficiar 700 Estudiante(s) con apoyo de sostenimiento para la "
              "permanencia en la educación posmedia", 31, 51),
}

#: Columnas que las dos metas nuevas heredan del hermano: son del proyecto y
#: del programa, no de la meta.
HEREDADAS = ("codprog", "nomprog", "codproy", "linea", "sector",
             "objetivo_estrategico", "sector_id", "programa_id", "anualizacion")


class Command(BaseCommand):
    help = ("Desdobla la meta agrupada de posmedia (8) en las metas SEGPLAN "
            "23771 y 23772. Seco por defecto.")

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe de verdad. Sin esto, solo reporta.")
        parser.add_argument("--usuario", default=None,
                            help="Username de quien lo corre. Obligatorio con --write.")

    def handle(self, *args, **opts):
        escribir = opts["write"]
        autor = None
        if escribir:
            from django.contrib.auth import get_user_model
            username = opts.get("usuario")
            if not username:
                raise CommandError(
                    "--write exige --usuario: un cambio de catálogo sin autor "
                    "no queda defendible.")
            autor = get_user_model().objects.filter(username=username).first()
            if autor is None:
                raise CommandError(f"No existe el usuario «{username}».")

        with connection.cursor() as cur:
            estado = self._leer(cur)
            self._reportar(estado)
            if not escribir:
                self.stdout.write(self.style.WARNING(
                    "\nSECO: no se escribió nada. Repite con --write --usuario <u>."))
                return
            if estado["ya_hecho"]:
                self.stdout.write(self.style.SUCCESS(
                    "Ya estaba desdoblada. Nada que hacer."))
                return
            with transaction.atomic():
                self._aplicar(cur, estado, autor)
            self.stdout.write(self.style.SUCCESS("\nDesdoblada."))

    # ── Lectura ──────────────────────────────────────────────────────
    def _leer(self, cur) -> dict:
        cur.execute("SELECT codigo, nombre FROM metas WHERE codigo = %s", [META_AGRUPADA])
        agrupada = cur.fetchone()
        cur.execute("SELECT codigo_meta FROM metas WHERE codigo_meta = ANY(%s)",
                    [list(DESDOBLE)])
        existentes = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT id FROM meta_proyecto WHERE meta_id = %s", [META_AGRUPADA])
        mp = cur.fetchone()
        indicadores = {}
        if mp:
            cur.execute("""SELECT id, nombre, meta_magnitud, unidad_medida
                           FROM presu_indicador_meta_proyecto
                           WHERE meta_proyecto_id = %s ORDER BY id""", [mp[0]])
            indicadores = {r[0]: r for r in cur.fetchall()}
        return {
            "agrupada": agrupada,
            "meta_proyecto_id": mp[0] if mp else None,
            "indicadores": indicadores,
            "existentes": existentes,
            "ya_hecho": len(existentes) == len(DESDOBLE) and agrupada is None,
        }

    def _reportar(self, e):
        self.stdout.write(self.style.MIGRATE_HEADING("\n[estado actual]"))
        self.stdout.write(f"    meta agrupada        : "
                          f"{e['agrupada'][0] if e['agrupada'] else '— ya no existe'}")
        self.stdout.write(f"    su meta_proyecto     : {e['meta_proyecto_id']}")
        self.stdout.write(f"    indicadores que lleva: {sorted(e['indicadores'])}")
        self.stdout.write(f"    metas SEGPLAN ya creadas: {sorted(e['existentes']) or '—'}")
        self.stdout.write(self.style.MIGRATE_HEADING("\n[lo que se haría]"))
        for cod, (nombre, ind_id, codind) in DESDOBLE.items():
            marca = "ya existe" if cod in e["existentes"] else "crear"
            self.stdout.write(f"    {cod} · {marca:9} · indicador {ind_id} (codind {codind})")
            self.stdout.write(f"           «{nombre[:78]}»")
        if e["agrupada"]:
            self.stdout.write(f"    borrar la agrupada {META_AGRUPADA} y su meta_proyecto "
                              f"{e['meta_proyecto_id']}")

    # ── Escritura ────────────────────────────────────────────────────
    def _aplicar(self, cur, estado, autor):
        from apps.presupuesto.services.auditoria import registrar_cambio

        if estado["agrupada"] is None:
            raise CommandError("No está la meta agrupada: nada que desdoblar.")
        faltan = set(DESDOBLE) - estado["existentes"]
        if not faltan:
            raise CommandError(
                "Las dos metas ya existen pero la agrupada sigue ahí. Revisar a "
                "mano antes de seguir: desdoblar dos veces duplicaría.")

        cur.execute(f"SELECT {', '.join(HEREDADAS)} FROM metas WHERE codigo = %s",
                    [META_HERMANA])
        heredado = dict(zip(HEREDADAS, cur.fetchone()))

        nuevas = {}
        for cod, (nombre, ind_id, codind) in DESDOBLE.items():
            columnas = list(HEREDADAS) + ["nombre", "codigo_meta", "proyecto_codigo",
                                          "codind", "nomind"]
            valores = ([heredado[c] for c in HEREDADAS]
                       + [nombre, cod, PROYECTO_CODIGO, codind, nombre])
            # `codigo` NO se pasa: la columna es GENERATED ALWAYS AS IDENTITY,
            # así que la base la asigna y pasarla a mano es un error duro. (El
            # comentario histórico de CLAUDE.md sobre una «secuencia oculta sin
            # DEFAULT» describe un estado anterior de esta tabla.)
            cur.execute(
                f"INSERT INTO metas ({', '.join(columnas)}) "
                f"VALUES ({', '.join(['%s'] * len(columnas))}) RETURNING codigo",
                valores)
            nuevas[cod] = cur.fetchone()[0]
            self.stdout.write(f"    meta {cod} creada con código interno {nuevas[cod]}")
            registrar_cambio(usuario=autor, entidad="metas", entidad_id=nuevas[cod],
                             campo="codigo_meta", valor_anterior=None, valor_nuevo=cod,
                             fuente="desdoblar_meta_agrupada",
                             observacion=f"desdoble de la meta agrupada {META_AGRUPADA}")

        for cod, codigo_interno in nuevas.items():
            cur.execute("INSERT INTO meta_proyecto (meta_id, proyecto_id) "
                        "VALUES (%s, %s) RETURNING id", [codigo_interno, PROYECTO_ID])
            mp_id = cur.fetchone()[0]
            ind_id = DESDOBLE[cod][1]
            # MOVER, no recrear: el id del indicador se conserva y con él los
            # avances y las vinculaciones a actividades que ya cuelgan de él.
            cur.execute("UPDATE presu_indicador_meta_proyecto SET meta_proyecto_id = %s "
                        "WHERE id = %s", [mp_id, ind_id])
            self.stdout.write(f"    indicador {ind_id} movido a la meta {cod}")
            registrar_cambio(usuario=autor, entidad="presu_indicador_meta_proyecto",
                             entidad_id=ind_id, campo="meta_proyecto_id",
                             valor_anterior=estado["meta_proyecto_id"], valor_nuevo=mp_id,
                             fuente="desdoblar_meta_agrupada",
                             observacion=f"pasa a la meta SEGPLAN {cod}")

        # ── La tabla vieja `presu_indicador`, que también cuelga de acá ──
        #
        # Son 3 filas en toda la base —«becas», «Porcentaje de», «cantidad
        # mujeres»— y NINGÚN código Python la lee: es un remanente. Pero su
        # `meta_proyecto_id` es NOT NULL y con FK, así que bloquea el borrado.
        #
        # Se MUEVE, no se borra ni se deja huérfana: borrar datos que nadie
        # pidió borrar no es de este comando, y la columna no admite vacío.
        # Va a la primera de las dos metas, y se reporta: si el área prefiere
        # otra, moverla es un UPDATE de una línea.
        primera = min(nuevas)
        cur.execute("SELECT id FROM meta_proyecto WHERE meta_id = %s", [nuevas[primera]])
        destino = cur.fetchone()[0]
        cur.execute("SELECT id, nombre FROM presu_indicador WHERE meta_proyecto_id = %s",
                    [estado["meta_proyecto_id"]])
        for ind_id, nombre in cur.fetchall():
            cur.execute("UPDATE presu_indicador SET meta_proyecto_id = %s WHERE id = %s",
                        [destino, ind_id])
            self.stdout.write(self.style.WARNING(
                f"    OJO: la fila vieja `presu_indicador` {ind_id} («{nombre}») "
                f"se movió a la meta {primera}. Ningún código la lee."))
            registrar_cambio(usuario=autor, entidad="presu_indicador", entidad_id=ind_id,
                             campo="meta_proyecto_id",
                             valor_anterior=estado["meta_proyecto_id"], valor_nuevo=destino,
                             fuente="desdoblar_meta_agrupada",
                             observacion="colgaba de la meta agrupada, que se retira")

        cur.execute("SELECT COUNT(*) FROM presu_indicador_meta_proyecto "
                    "WHERE meta_proyecto_id = %s", [estado["meta_proyecto_id"]])
        colgando = cur.fetchone()[0]
        if colgando:
            raise CommandError(
                f"El meta_proyecto de la agrupada todavía tiene {colgando} "
                f"indicadores. Se aborta antes de borrar nada.")

        cur.execute("DELETE FROM meta_proyecto WHERE id = %s", [estado["meta_proyecto_id"]])
        cur.execute("DELETE FROM metas WHERE codigo = %s", [META_AGRUPADA])
        self.stdout.write(f"    agrupada {META_AGRUPADA} retirada")
        registrar_cambio(usuario=autor, entidad="metas", entidad_id=META_AGRUPADA,
                         campo="__borrada__", valor_anterior=estado["agrupada"][1],
                         valor_nuevo=None, fuente="desdoblar_meta_agrupada",
                         observacion="desdoblada en 23771 y 23772")

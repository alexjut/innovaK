"""¿Está encendido el espejo de soportes en OneDrive, y puede escribir?

    docker exec innova_k python manage.py verificar_onedrive

Existe por el mismo motivo que `verificar_kenny`: el espejo es best-effort y
NUNCA lanza excepción —un OneDrive caído no puede tumbar una radicación—, así
que estar apagado no se nota en ninguna pantalla. Llevaba desde agosto apagado y
solo se supo preguntándoselo al código.

Comprueba cinco cosas en orden, y se detiene en la primera que falle porque las
siguientes no tendrían sentido:

    1. que estén las credenciales      (sin red)
    2. que Entra ID dé un token        (distingue 401 de red caída)
    3. que el drive destino resuelva   (por GUID o por correo)
    4. que la carpeta raíz exista      (la crea si falta)
    5. que se pueda ESCRIBIR y BORRAR  (un archivo de prueba, que se borra)

El 5 es el que importa: un token válido sobre un drive que existe no prueba que
la aplicación tenga permiso de escritura, y eso solo se ve escribiendo.

No imprime ninguna credencial, solo su largo.
"""
import requests
from django.core.management.base import BaseCommand

from apps.documentos.services import onedrive_storage as od

#: Nombre del archivo de prueba. Lleva la palabra PRUEBA y se borra al terminar;
#: si alguna vez aparece uno en el OneDrive, es que el borrado falló.
ARCHIVO_PRUEBA = "_PRUEBA_innovaK_borrar.txt"


class Command(BaseCommand):
    help = "Verifica que el espejo de soportes en OneDrive esté operativo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sin-escribir", action="store_true",
            help="Omite el paso 5. Útil si solo se quiere saber si hay token.")

    def handle(self, *args, **opts):
        ok = self.style.SUCCESS
        malo = self.style.ERROR
        aviso = self.style.WARNING

        # ── 1 · credenciales ────────────────────────────────────────────
        self.stdout.write("1 · credenciales")
        claves = ("ONEDRIVE_TENANT_ID", "ONEDRIVE_CLIENT_ID",
                  "ONEDRIVE_CLIENT_SECRET", "ONEDRIVE_DRIVE_ID",
                  "ONEDRIVE_USUARIO", "ONEDRIVE_CARPETA_RAIZ")
        for k in claves:
            v = od._cfg(k)
            self.stdout.write(f"    {k:<26} "
                              + (f"{len(v)} caracteres" if v else "—"))
        if not od.activo():
            self.stdout.write(malo(
                "\n✗ APAGADO. Faltan credenciales.\n\n"
                "  Hacen falta TRES de la app registrada en Entra ID —tenant,\n"
                "  client y secret— más UN destino, que puede ser:\n"
                "    · ONEDRIVE_USUARIO  = el correo cuyo OneDrive recibe los\n"
                "      soportes (lo más fácil: el id del drive se resuelve solo), o\n"
                "    · ONEDRIVE_DRIVE_ID = el GUID del drive, si ya lo tienen.\n\n"
                "  Para ponerlas: bash scripts/poner_credenciales_onedrive.sh\n\n"
                "  Mientras esté apagado NO se pierde nada: los originales siguen\n"
                "  en Mongo cifrado, que es el sistema de registro. Lo que falta es\n"
                "  la copia legible para que el área vea los soportes sin entrar\n"
                "  al aplicativo."))
            return
        self.stdout.write(ok("    ✓ completas"))

        # ── 2 · token ───────────────────────────────────────────────────
        self.stdout.write("\n2 · token de Entra ID")
        od.reiniciar_token()
        token = od._token()
        if not token:
            self.stdout.write(malo(
                "    ✗ no se obtuvo token.\n"
                "      Un 401 aquí es credencial mala o secreto vencido —los de\n"
                "      Entra ID caducan—. Si no hay red, el log dice el error.\n"
                "      Revise el log del contenedor: onedrive_token_*"))
            return
        self.stdout.write(ok(f"    ✓ token obtenido ({len(token)} caracteres)"))

        # ── 3 · drive ───────────────────────────────────────────────────
        self.stdout.write("\n3 · drive destino")
        drive = od.drive_id()
        if not drive:
            self.stdout.write(malo(
                "    ✗ no se resolvió el drive.\n"
                "      Con ONEDRIVE_USUARIO, el correo tiene que existir en el\n"
                "      tenant Y la app necesita permiso Files.ReadWrite.All\n"
                "      (de aplicación, con consentimiento del administrador)."))
            return
        self.stdout.write(ok(f"    ✓ drive {drive[:18]}…"))
        if not od.ping():
            self.stdout.write(malo(
                "    ✗ el drive no responde 200. El id resuelve pero la app no\n"
                "      lo alcanza: falta el consentimiento del administrador."))
            return
        self.stdout.write(ok("    ✓ alcanzable"))

        # ── 4 · carpeta raíz ────────────────────────────────────────────
        self.stdout.write(f"\n4 · carpeta raíz «{od.carpeta_raiz()}»")
        raiz = od.asegurar_carpeta(od.segmentos_raiz())
        if not raiz:
            self.stdout.write(malo(
                "    ✗ no se pudo crear ni encontrar la carpeta raíz.\n"
                "      Suele ser permiso de escritura: ver el paso 3."))
            return
        self.stdout.write(ok("    ✓ existe (se crea sola si falta)"))
        self.stdout.write(
            "    las carpetas por organización se crean al radicar, así:\n"
            f"      {od.carpeta_raiz()}/<vigencia>/<NIT>-<ORGANIZACIÓN>/")

        if opts["sin_escribir"]:
            self.stdout.write(aviso("\n5 · escritura — OMITIDO por --sin-escribir"))
            return

        # ── 5 · escribir y borrar ───────────────────────────────────────
        self.stdout.write("\n5 · escritura")
        item = od.subir_archivo(
            od.segmentos_raiz(), ARCHIVO_PRUEBA,
            b"Prueba de innovaK. Si este archivo sigue aqui, el borrado fallo.\n",
            "text/plain")
        if not item:
            self.stdout.write(malo(
                "    ✗ no se pudo escribir. El token y el drive están bien, así\n"
                "      que es permiso: la app necesita Files.ReadWrite.All de\n"
                "      APLICACIÓN. Con el de delegado no alcanza."))
            return
        self.stdout.write(ok(f"    ✓ escrito: {item.get('name')}"))

        borrado = self._borrar(item.get("id"), drive)
        if borrado:
            self.stdout.write(ok("    ✓ borrado (no quedó basura)"))
        else:
            self.stdout.write(aviso(
                f"    ⚠ se escribió pero NO se pudo borrar. Quedó "
                f"«{ARCHIVO_PRUEBA}» en {od.carpeta_raiz()}: bórrelo a mano."))

        self.stdout.write(ok(
            "\n✓ ENCENDIDO y con permiso de escritura. Al radicar, los soportes "
            "quedan en OneDrive además de Mongo."))

    def _borrar(self, item_id, drive):
        """Borra el archivo de prueba. Sin esto cada corrida deja basura."""
        if not item_id:
            return False
        cabeceras = od._headers()
        if cabeceras is None:
            return False
        try:
            r = requests.delete(
                f"{od.GRAPH_BASE}/drives/{drive}/items/{item_id}",
                headers=cabeceras, timeout=od.TIMEOUT_S)
            return r.status_code in (204, 200)
        except Exception:
            return False

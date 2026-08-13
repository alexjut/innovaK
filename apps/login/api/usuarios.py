"""Crear la cuenta de acceso de una persona ya registrada.

## El hueco que cierra

Se podía crear una **Persona** desde `/app/admin/personas` y asignarle **rol** y
**subgrupo** desde Roles y Accesos… a un usuario que no había forma de crear.
Las únicas vías eran el `/admin` de Django o un comando de consola, o sea: para
dar de alta a alguien había que salirse de la aplicación. Reportado en
producción el 2026-08-13.

## Qué crea, y en qué orden

    Persona (ya existe)  →  Funcionario (el scope: de qué datos ve)
                         →  Usuario (la cuenta, con su rol)

El **Funcionario es lo que le da alcance** al usuario: `usuario.funcionario.
subgrupo_id` es de donde sale qué datos ve. Un usuario sin funcionario es una
cuenta transversal, y eso se pide explícito con `sin_scope`, no se obtiene por
olvidar el campo.

## La contraseña temporal se muestra UNA vez

Se genera fuerte, se devuelve en la respuesta y **no se guarda en ningún lado ni
se escribe en el log**. Quien la crea la entrega por canal seguro y la persona
la cambia en `/perfil`. Guardarla «por si acaso» convertiría la base en un
listado de contraseñas.
"""
from __future__ import annotations

import logging
import re
import secrets
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission

logger = logging.getLogger(__name__)

#: Mismo módulo que gobierna roles: quien puede dar un rol puede dar la cuenta.
_PERMS = [ModuloRequiredPermission("roles")]

#: Sin caracteres ambiguos (l/1/I, O/0): la contraseña se dicta o se copia a
#: mano más veces de las que uno quisiera.
_ALFABETO = (string.ascii_lowercase.replace("l", "").replace("o", "")
             + string.ascii_uppercase.replace("I", "").replace("O", "")
             + "23456789" + "!@#$%*?")


def password_temporal(largo: int = 14) -> str:
    return "".join(secrets.choice(_ALFABETO) for _ in range(largo))


def _slug(texto: str) -> str:
    import unicodedata
    txt = "".join(c for c in unicodedata.normalize("NFKD", texto or "")
                  if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", txt.lower())


def username_sugerido(persona) -> str:
    """`nombre.apellido`, la convención que ya usan las cuentas existentes."""
    base = f"{_slug(persona.nombre1)}.{_slug(persona.apellido1)}".strip(".")
    return base or f"usuario{persona.id}"


def username_libre(base: str) -> str:
    """Agrega un sufijo numérico si el username ya está tomado."""
    User = get_user_model()
    if not User.objects.filter(username=base).exists():
        return base
    for i in range(2, 100):
        candidato = f"{base}{i}"
        if not User.objects.filter(username=candidato).exists():
            return candidato
    return f"{base}{secrets.randbelow(9000) + 1000}"


class UsuarioDePersonaView(APIView):
    """GET propone el username · POST crea la cuenta.

    POST:
        persona_id    (obligatorio)
        username      (opcional, se propone si no viene)
        rol_id        (opcional) grupo que se le asigna
        subgrupo_id   (opcional) alcance; crea el Funcionario si hace falta
        sin_scope     (opcional) cuenta transversal, sin funcionario
    """
    permission_classes = _PERMS

    def get(self, request):
        from apps.login.models import Persona

        persona = Persona.objects.filter(id=request.query_params.get("persona_id") or 0).first()
        if persona is None:
            return Response({"detail": "No se encontró la persona."},
                            status=status.HTTP_404_NOT_FOUND)
        ya = self._usuario_de(persona)
        return Response({
            "persona_id": persona.id,
            "nombre": f"{persona.nombre1} {persona.apellido1}".strip(),
            "username_sugerido": username_libre(username_sugerido(persona)),
            "ya_tiene_usuario": bool(ya),
            "username_existente": ya.username if ya else None,
            "roles": [{"id": g.id, "nombre": g.name} for g in Group.objects.order_by("name")],
        })

    def post(self, request):
        from apps.login.models import Persona
        from apps.login.models.funcionario import Funcionario

        User = get_user_model()
        persona = Persona.objects.filter(id=request.data.get("persona_id") or 0).first()
        if persona is None:
            return Response({"detail": "Elija la persona a la que se le crea la cuenta."},
                            status=status.HTTP_400_BAD_REQUEST)

        ya = self._usuario_de(persona)
        if ya:
            # No se crea una segunda cuenta: dos usuarios para la misma persona
            # es el camino corto a que nadie sepa cuál es el bueno.
            return Response(
                {"detail": f"{persona.nombre1} {persona.apellido1} ya tiene la cuenta "
                           f"«{ya.username}». Si perdió la contraseña, reséteela desde "
                           "esa cuenta en vez de crear otra."},
                status=status.HTTP_400_BAD_REQUEST)

        username = (request.data.get("username") or "").strip().lower()
        if not username:
            username = username_sugerido(persona)
        if not re.fullmatch(r"[a-z0-9._-]{3,30}", username):
            return Response(
                {"detail": "El usuario admite minúsculas, números, punto, guion y guion "
                           "bajo, entre 3 y 30 caracteres."},
                status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"detail": f"El usuario «{username}» ya está tomado."},
                            status=status.HTTP_400_BAD_REQUEST)

        subgrupo_id = request.data.get("subgrupo_id") or None
        sin_scope = bool(request.data.get("sin_scope"))
        if not subgrupo_id and not sin_scope:
            return Response(
                {"detail": "Falta el subgrupo: es lo que define de qué datos ve esta "
                           "persona. Si la cuenta debe ver todo, marque «sin alcance»."},
                status=status.HTTP_400_BAD_REQUEST)

        temp = password_temporal()
        with transaction.atomic():
            funcionario = None
            if not sin_scope:
                funcionario = Funcionario.objects.filter(persona=persona).first()
                if funcionario is None:
                    funcionario = Funcionario.objects.create(
                        persona=persona, subgrupo_id=int(subgrupo_id), activo=True)
                elif str(funcionario.subgrupo_id) != str(subgrupo_id):
                    funcionario.subgrupo_id = int(subgrupo_id)
                    funcionario.save(update_fields=["subgrupo_id"])

            usuario = User.objects.create_user(
                username=username, password=temp,
                first_name=(persona.nombre1 or "").strip(),
                last_name=(persona.apellido1 or "").strip(),
            )
            usuario.es_funcionario = not sin_scope
            usuario.funcionario = funcionario
            usuario.save(update_fields=["es_funcionario", "funcionario"])

            rol_id = request.data.get("rol_id")
            if rol_id:
                grupo = Group.objects.filter(id=int(rol_id)).first()
                if grupo:
                    usuario.groups.add(grupo)

        # El username sí se registra; la contraseña NO — ni acá ni en el log.
        logger.info("Cuenta creada para persona %s: usuario '%s'", persona.id, username)
        return Response({
            "usuario_id": usuario.id,
            "username": usuario.username,
            "password_temporal": temp,
            "aviso": ("Esta contraseña se muestra UNA sola vez y no queda guardada. "
                      "Entréguela por un canal seguro; la persona debe cambiarla en "
                      "su perfil al entrar."),
        }, status=status.HTTP_201_CREATED)

    @staticmethod
    def _usuario_de(persona):
        """La cuenta de esa persona, si ya la tiene.

        Se busca por el funcionario, que es el vínculo real entre persona y
        cuenta — `persona.usuario_id` es otra cosa: auditoría de quién REGISTRÓ
        a esa persona, no de quién es.
        """
        from apps.login.models.funcionario import Funcionario

        User = get_user_model()
        funcionarios = Funcionario.objects.filter(persona=persona).values_list("id", flat=True)
        return User.objects.filter(funcionario_id__in=list(funcionarios)).first()

"""N20: helper para resolver el `funcionario_id` actual desde el request.

Cuando un funcionario logueado levanta una caracterización (wizard interno
en `/dashboard/caracterizacion/<sector>/`), queremos guardar quién la
recolectó para auditoría. En los wizards públicos por QR (sin login) no
hay funcionario; devolvemos None y la columna queda NULL.
"""
from __future__ import annotations

from typing import Optional


def funcionario_actual_o_none(request) -> Optional[int]:
    """Devuelve `funcionario.id` si el usuario logueado es funcionario activo.

    Devuelve None si:
      - El request es anónimo (wizard público).
      - El user no tiene `Persona` vinculada (relación inversa `persona_set`).
      - La persona no tiene Funcionario activo asociado.
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None

    # Persona tiene FK a Usuario (related_name por defecto: persona_set).
    persona = getattr(user, "persona_set", None)
    if persona is None:
        return None
    persona_obj = persona.only("id").first()
    if persona_obj is None:
        return None

    from apps.login.models.funcionario import Funcionario

    funcionario = Funcionario.objects.filter(
        persona_id=persona_obj.id, activo=True
    ).only("id").first()
    return funcionario.id if funcionario else None

from django.db import models

from .candidato import Candidato
from .evento import Evento


class Voto(models.Model):
    evento = models.ForeignKey(
        Evento,
        on_delete=models.PROTECT,
        related_name="votos",
        db_column="event_id",
    )

    # ── Columnas legacy (existen en la BD, ya no se usan en lógica) ──
    candidato_legacy = models.BigIntegerField(
        db_column="candidate_id",
        default=0,
    )
    votante_legacy = models.BigIntegerField(
        db_column="voter_id",
        default=0,
    )

    # ── Columnas nuevas ──
    candidato_identidades = models.ForeignKey(
        Candidato,
        on_delete=models.PROTECT,
        related_name="votos_identidades",
        db_column="candidate_identidades_id",
        null=True,   # permite voto en blanco
        blank=True,
    )

    candidato_derechos = models.ForeignKey(
        Candidato,
        on_delete=models.PROTECT,
        related_name="votos_derechos",
        db_column="candidate_derechos_id",
        null=True,   # permite voto en blanco
        blank=True,
    )

    document_number = models.CharField(max_length=30)
    voter_full_name = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    consent_accepted = models.BooleanField(default=False)
    consent_accepted_at = models.DateTimeField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        db_table = "votaciones_vote"
        indexes = [
            models.Index(fields=["created_at"], name="idx_vote_created"),
            models.Index(fields=["evento", "created_at"], name="idx_vote_event_created"),
            models.Index(fields=["evento", "document_number"], name="idx_vote_event_doc"),
        ]
        # NOTA: la UNIQUE (evento, document_number) se eliminó al introducir
        # voto múltiple administrable por evento (Evento.votos_permitidos).
        # La validación de "no exceder votos permitidos" vive en
        # apps/votaciones/services/voto_service.py::register_vote.
        managed = False

    def __str__(self):
        return (
            f"Voto(evento={self.evento_id}, "
            f"identidades={self.candidato_identidades_id}, "
            f"derechos={self.candidato_derechos_id}, "
            f"document={self.document_number})"
        )

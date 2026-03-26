from django.db import models

from .candidate import Candidate
from .event import Event


class Vote(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="votes",
        db_column="event_id",
    )

    # ── Columnas legacy (existen en la BD, ya no se usan en lógica) ──
    candidate_legacy = models.BigIntegerField(
        db_column="candidate_id",
        default=0,
    )
    voter_legacy = models.BigIntegerField(
        db_column="voter_id",
        default=0,
    )

    # ── Columnas nuevas ──
    candidate_identidades = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        related_name="votes_identidades",
        db_column="candidate_identidades_id",
        null=True,   # permite voto en blanco
        blank=True,
    )

    candidate_derechos = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        related_name="votes_derechos",
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
            models.Index(fields=["event", "created_at"], name="idx_vote_event_created"),
            models.Index(fields=["event", "document_number"], name="idx_vote_event_doc"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "document_number"],
                name="uniq_vote_per_event_document",
            ),
        ]
        managed = False

    def __str__(self):
        return (
            f"Vote(event={self.event_id}, "
            f"identidades={self.candidate_identidades_id}, "
            f"derechos={self.candidate_derechos_id}, "
            f"document={self.document_number})"
        )
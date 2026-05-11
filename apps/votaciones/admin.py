from django.contrib import admin

from .models import Evento, Candidato, Voto, Votante


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "starts_at", "ends_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "evento", "genre", "code", "is_active")
    list_filter = ("is_active", "evento", "genre")
    search_fields = ("name", "code", "genre")
    ordering = ("evento", "id")


@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "evento",
        "candidato_identidades",
        "candidato_derechos",
        "document_number",
        "voter_full_name",
        "created_at",
    )
    list_filter = ("evento", "created_at", "consent_accepted")
    search_fields = ("document_number", "voter_full_name")
    ordering = ("-created_at",)


@admin.register(Votante)
class VotanteAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "email", "phone", "created_at")
    search_fields = ("first_name", "last_name", "email", "phone")
    ordering = ("-created_at",)

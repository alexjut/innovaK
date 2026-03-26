from django.contrib import admin

from .models import Event, Candidate, Vote, Voter


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "starts_at", "ends_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "event", "genre", "code", "is_active")
    list_filter = ("is_active", "event", "genre")
    search_fields = ("name", "code", "genre")
    ordering = ("event", "id")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event",
        "candidate_identidades",
        "candidate_derechos",
        "document_number",
        "voter_full_name",
        "created_at",
    )
    list_filter = ("event", "created_at", "consent_accepted")
    search_fields = ("document_number", "voter_full_name")
    ordering = ("-created_at",)


@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "email", "phone", "created_at")
    search_fields = ("first_name", "last_name", "email", "phone")
    ordering = ("-created_at",)
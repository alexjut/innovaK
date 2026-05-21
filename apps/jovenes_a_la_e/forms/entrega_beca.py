"""Formulario público de Entrega de Beca (Jóvenes a la E).

Captura por QR desde el celular del estudiante. SIN autenticación.

Política de Persona (idéntica a caracterización N12, opción A):
  - Si la cédula ya existe → reusa Persona sin tocar nombre/apellido.
  - Si no existe → crea Persona + PersonaDocumento mínimos.

Tras guardar la entrega:
  - Crea/asegura Beneficiario tipo PERSONA (idempotente).
  - Crea EntregaBeca con `metas_codigos` derivado de los flags de
    cumplimiento (23771 si acceso, 23772 si permanencia, ambos si las dos).
  - Asocia elementos entregados vía tabla puente.

NO se sincroniza automáticamente al `AvanceIndicador` desde aquí — eso
queda a cargo del organizador al validar la entrega (PR-3).
"""
from typing import Optional

from django import forms
from django.db import transaction

from apps.banco_iniciativas.models import Upl
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona
from apps.georeferenciacion.models import Barrio
from apps.jovenes_a_la_e.models import (
    EntregaBeca, EntregaBecaElemento, ElementoDotacion,
)
from apps.login.models.persona_documento import TipoDocumento
from apps.login.services.beneficiario_helpers import asegurar_beneficiario_persona


def _solo_doc_persona_natural():
    """Tipos de documento válidos para una persona natural (excluye NIT codigo=5)."""
    return TipoDocumento.objects.exclude(codigo=5).order_by("codigo")


class EntregaBecaForm(forms.Form):
    """Form público — patrón Banco simplificado para becas."""

    # ── Identificación del estudiante ───────────────────────────
    tipo_doc = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.none(),
        label="Tipo de documento",
        required=True,
    )
    numero_documento = forms.CharField(
        label="Número de documento",
        max_length=40,
        widget=forms.TextInput(attrs={
            "inputmode": "numeric", "autocomplete": "off",
            "placeholder": "Ej. 1023456789",
        }),
    )
    nombre1 = forms.CharField(label="Primer nombre", max_length=80)
    nombre2 = forms.CharField(label="Segundo nombre", max_length=80, required=False)
    apellido1 = forms.CharField(label="Primer apellido", max_length=80)
    apellido2 = forms.CharField(label="Segundo apellido", max_length=80, required=False)

    telefono = forms.CharField(label="Teléfono", max_length=40, required=False,
                               widget=forms.TextInput(attrs={"inputmode": "tel"}))
    correo = forms.EmailField(label="Correo electrónico", required=False)

    # ── Ubicación ───────────────────────────────────────────────
    direccion = forms.CharField(label="Dirección de residencia", required=False,
                                widget=forms.TextInput(attrs={"placeholder": "Ej. Cl 38 # 80-21"}))
    upl = forms.ModelChoiceField(
        queryset=Upl.objects.none(),
        label="UPL",
        required=False,
        empty_label="— Seleccione UPL —",
    )
    barrio = forms.ModelChoiceField(
        queryset=Barrio.objects.none(),
        label="Barrio",
        required=False,
        empty_label="— Seleccione barrio —",
    )

    # ── Cumplimiento de metas (23771 / 23772) ───────────────────
    cumplimiento_acceso = forms.BooleanField(
        label="ACCESO — Está iniciando estudios posmedia este periodo (meta 23771)",
        required=False,
    )
    cumplimiento_permanencia = forms.BooleanField(
        label="PERMANENCIA — Recibe apoyo de sostenimiento para continuar (meta 23772)",
        required=False,
    )

    # ── Datos académicos ────────────────────────────────────────
    nivel_formacion = forms.ChoiceField(
        label="Nivel de formación",
        choices=[("", "— Seleccione —")] + EntregaBeca.NIVEL_CHOICES,
        required=False,
    )
    institucion = forms.CharField(label="Institución educativa", max_length=200, required=False)
    programa_academico = forms.CharField(label="Programa académico", max_length=200, required=False)
    periodo_academico = forms.CharField(
        label="Período académico",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej. 2026-1"}),
    )

    # ── Elementos entregados ────────────────────────────────────
    elementos = forms.ModelMultipleChoiceField(
        queryset=ElementoDotacion.objects.none(),
        label="Elementos / apoyos entregados",
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    # ── Firma ───────────────────────────────────────────────────
    firma_imagen = forms.ImageField(
        label="Firma del beneficiario",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/*",
            "capture": "environment",
        }),
    )
    firma_url = forms.URLField(
        label="O URL de la firma (alternativa)",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_doc"].queryset = _solo_doc_persona_natural()
        self.fields["elementos"].queryset = (
            ElementoDotacion.objects.filter(activo=True).order_by("orden", "nombre")
        )
        self.fields["upl"].queryset = Upl.objects.filter(activo=True).order_by("orden", "nombre")
        self.fields["barrio"].queryset = Barrio.objects.all().order_by("nombre")

    # ── Validaciones ────────────────────────────────────────────
    def clean_numero_documento(self):
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if not v.isdigit():
            raise forms.ValidationError("El documento debe contener solo dígitos.")
        if len(v) < 5:
            raise forms.ValidationError("Documento demasiado corto.")
        return v

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get("cumplimiento_acceso") or cleaned.get("cumplimiento_permanencia")):
            raise forms.ValidationError(
                "Debe marcar al menos uno de los dos: ACCESO o PERMANENCIA."
            )
        # Firma obligatoria (consentimiento). Cualquiera de los dos vale.
        if not (cleaned.get("firma_imagen") or cleaned.get("firma_url")):
            raise forms.ValidationError(
                "Adjunte una imagen de la firma o ingrese una URL."
            )
        return cleaned

    # ── Guardado ────────────────────────────────────────────────
    @transaction.atomic
    def save(self, *, evento_id: int) -> EntregaBeca:
        d = self.cleaned_data

        # 1. Resolver Persona (opción A: si existe, no se sobrescribe).
        persona, _creada = obtener_o_crear_persona(
            tipo_documento_codigo=d["tipo_doc"].codigo,
            numero_documento=d["numero_documento"],
            nombre1=d["nombre1"],
            apellido1=d["apellido1"],
            nombre2=d.get("nombre2") or None,
            apellido2=d.get("apellido2") or None,
        )

        # 2. Asegurar Beneficiario tipo PERSONA (idempotente).
        asegurar_beneficiario_persona(
            persona,
            correo=d.get("correo") or None,
            telefono=d.get("telefono") or None,
            direccion=d.get("direccion") or None,
        )

        # 3. Calcular metas_codigos a partir de los flags.
        metas: list[str] = []
        if d.get("cumplimiento_acceso"):       metas.append("23771")
        if d.get("cumplimiento_permanencia"):  metas.append("23772")

        # 4. Resolver firma — URL externa o subida (la subida se cifra a
        #    Mongo después del create, ver paso 6).
        firma_url = d.get("firma_url") or None

        # 5. Crear EntregaBeca.
        entrega = EntregaBeca.objects.create(
            evento_id=evento_id,
            persona=persona,
            tipo_doc_codigo=d["tipo_doc"].codigo,
            numero_documento=d["numero_documento"],
            nombre1=d["nombre1"],
            nombre2=d.get("nombre2") or None,
            apellido1=d["apellido1"],
            apellido2=d.get("apellido2") or None,
            telefono=d.get("telefono") or None,
            correo=d.get("correo") or None,
            direccion=d.get("direccion") or None,
            upl_codigo=(d["upl"].codigo if d.get("upl") else None),
            barrio_codigo=(d["barrio"].codigo if d.get("barrio") else None),
            cumplimiento_acceso=bool(d.get("cumplimiento_acceso")),
            cumplimiento_permanencia=bool(d.get("cumplimiento_permanencia")),
            nivel_formacion=d.get("nivel_formacion") or None,
            institucion=d.get("institucion") or None,
            programa_academico=d.get("programa_academico") or None,
            periodo_academico=d.get("periodo_academico") or None,
            metas_codigos=",".join(metas) or None,
            firma_imagen_url=firma_url,
            estado="enviada",
        )

        # 6. Subir firma cifrada a MongoDB (si vino archivo).
        firma_archivo = d.get("firma_imagen")
        if firma_archivo:
            from apps.documentos.services import mongo_storage
            firma_archivo.seek(0)
            blob = firma_archivo.read()
            try:
                entrega.firma_mongo_id = mongo_storage.guardar(
                    plaintext=blob,
                    mime=getattr(firma_archivo, "content_type", None) or "image/png",
                    owner={
                        "tipo": "jovenes_beca",
                        "entrega_id": entrega.id,
                        "campo": "firma",
                    },
                )
                entrega.save(update_fields=["firma_mongo_id"])
            except Exception:  # noqa: BLE001
                # Si Mongo está caído: no rompe la entrega; queda solo
                # la URL si la había. Se loguea silenciosamente.
                import logging
                logging.getLogger(__name__).exception(
                    "Fallo subiendo firma a Mongo para EntregaBeca #%s", entrega.id,
                )

        # 7. Asociar elementos entregados.
        for elem in d.get("elementos") or []:
            EntregaBecaElemento.objects.create(
                entrega=entrega, elemento=elem, cantidad=1,
            )

        return entrega

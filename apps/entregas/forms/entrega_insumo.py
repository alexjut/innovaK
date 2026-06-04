"""Formulario público de Entrega de Insumos / Utensilios (tipo ENTREGA).

Captura por QR desde el celular del beneficiario. SIN autenticación.

Espeja `apps.jovenes_a_la_e.forms.EntregaBecaForm` pero sin lo
académico/cumplimiento de metas. La diferencia central es el manejo de
insumos CON CANTIDAD: el POST trae dos listas paralelas
`implementos[]` (códigos del catálogo) y `cantidades[]` (enteros). No se
usa `ModelMultipleChoiceField` porque ese widget no soporta cantidad por
ítem. Las listas se parean y validan en `clean()`.

Política de Persona (idéntica a caracterización N12, opción A):
  - Si la cédula ya existe → reusa Persona sin tocar nombre/apellido.
  - Si no existe → crea Persona + PersonaDocumento mínimos.

Tras guardar la entrega:
  - Crea/asegura Beneficiario tipo PERSONA (idempotente).
  - Crea EntregaInsumo.
  - Asocia cada (implemento, cantidad) vía la tabla puente.

La firma es OBLIGATORIA (consentimiento). Se cifra a MongoDB tras el
create (pipeline reusado del Banco/Jóvenes). Si Mongo está caído, la
entrega no se rompe.
"""
from django import forms
from django.db import transaction

from apps.banco_iniciativas.models import Implemento, Upl
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona
from apps.entregas.models import EntregaInsumo, EntregaInsumoElemento
from apps.georeferenciacion.models import Barrio
from apps.login.models.persona_documento import TipoDocumento
from apps.login.services.beneficiario_helpers import asegurar_beneficiario_persona


def _solo_doc_persona_natural():
    """Tipos de documento válidos para una persona natural (excluye NIT codigo=5)."""
    return TipoDocumento.objects.exclude(codigo=5).order_by("codigo")


class EntregaInsumoForm(forms.Form):
    """Form público — captura de beneficiario de entrega de insumos."""

    # ── Identificación del beneficiario ─────────────────────────
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

    # ── Firma (obligatoria) ─────────────────────────────────────
    firma_imagen = forms.ImageField(
        label="Firma del beneficiario",
        required=True,
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
        self.fields["upl"].queryset = Upl.objects.filter(activo=True).order_by("orden", "nombre")
        self.fields["barrio"].queryset = Barrio.objects.all().order_by("nombre")
        # Insumos parseados en clean(): lista de (Implemento, cantidad).
        self._insumos: list[tuple[Implemento, int]] = []

    # ── Validaciones ────────────────────────────────────────────
    def clean_numero_documento(self):
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if not v.isdigit():
            raise forms.ValidationError("El documento debe contener solo dígitos.")
        if len(v) < 5:
            raise forms.ValidationError("Documento demasiado corto.")
        return v

    def _parsear_insumos(self):
        """Parea las listas paralelas implementos[] y cantidades[] del POST.

        - Lee `implementos[]` (alias `implementos`) y `cantidades[]`
          (alias `cantidades`) desde el `data` crudo (no son fields).
        - Empareja por índice: el i-ésimo código va con la i-ésima
          cantidad. Si faltan cantidades, default 1.
        - Valida que cada código exista y esté activo; cantidad >= 1.
        - Deduplica códigos repetidos sumando cantidades.

        Devuelve lista de (Implemento, cantidad). Lanza ValidationError
        ante código inválido o cantidad no numérica.
        """
        data = self.data
        getlist = getattr(data, "getlist", None)
        if getlist is None:
            return []

        codigos = data.getlist("implementos[]") or data.getlist("implementos")
        cantidades = data.getlist("cantidades[]") or data.getlist("cantidades")

        if not codigos:
            return []

        # Cargar catálogo válido una sola vez.
        validos = {
            i.codigo: i
            for i in Implemento.objects.filter(activo=True)
        }

        acumulado: dict[int, int] = {}
        for idx, raw_cod in enumerate(codigos):
            raw_cod = (raw_cod or "").strip()
            if not raw_cod:
                continue
            try:
                cod = int(raw_cod)
            except (TypeError, ValueError):
                raise forms.ValidationError(
                    f"Código de insumo inválido: «{raw_cod}»."
                )
            if cod not in validos:
                raise forms.ValidationError(
                    f"El insumo con código {cod} no existe o no está activo."
                )
            raw_cant = cantidades[idx] if idx < len(cantidades) else "1"
            raw_cant = (raw_cant or "1").strip() or "1"
            try:
                cant = int(raw_cant)
            except (TypeError, ValueError):
                raise forms.ValidationError(
                    f"Cantidad inválida para el insumo {cod}: «{raw_cant}»."
                )
            if cant < 1:
                raise forms.ValidationError(
                    f"La cantidad del insumo {cod} debe ser al menos 1."
                )
            acumulado[cod] = acumulado.get(cod, 0) + cant

        return [(validos[cod], cant) for cod, cant in acumulado.items()]

    def clean(self):
        cleaned = super().clean()
        # Firma obligatoria (consentimiento). Cualquiera de los dos vale.
        if not (cleaned.get("firma_imagen") or cleaned.get("firma_url")):
            raise forms.ValidationError(
                "Adjunte una imagen de la firma o ingrese una URL."
            )
        self._insumos = self._parsear_insumos()
        if not self._insumos:
            raise forms.ValidationError(
                "Debe seleccionar al menos un insumo entregado con su cantidad."
            )
        return cleaned

    # ── Guardado ────────────────────────────────────────────────
    @transaction.atomic
    def save(self, *, evento_id: int) -> EntregaInsumo:
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

        # 3. Resolver firma — URL externa o subida (la subida se cifra a
        #    Mongo después del create, ver paso 5).
        firma_url = d.get("firma_url") or None

        # 4. Crear EntregaInsumo.
        entrega = EntregaInsumo.objects.create(
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
            firma_imagen_url=firma_url,
            estado="enviada",
        )

        # 5. Subir firma cifrada a MongoDB (si vino archivo).
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
                        "tipo": "entrega_insumo",
                        "entrega_id": entrega.id,
                        "campo": "firma",
                    },
                )
                entrega.save(update_fields=["firma_mongo_id"])
            except Exception:  # noqa: BLE001
                import logging
                logging.getLogger(__name__).exception(
                    "Fallo subiendo firma a Mongo para EntregaInsumo #%s", entrega.id,
                )

        # 6. Asociar insumos entregados con su cantidad.
        for implemento, cantidad in self._insumos:
            EntregaInsumoElemento.objects.create(
                entrega=entrega, implemento=implemento, cantidad=cantidad,
            )

        return entrega

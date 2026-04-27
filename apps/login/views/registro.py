# apps/login/views/registro.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.login.forms import UsuarioRegistroForm, PersonaForm, EventoPersonaForm
from django.utils.timezone import now
from apps.login.decorators import group_required
from apps.login.models.persona import Persona, Participante
from apps.login.forms import InscripcionForm
from apps.login.models.inscripcion import Inscripcion
from apps.kactivo.models.kasistencia import Evento
import logging
from django.db import transaction, connection


logger = logging.getLogger(__name__)

@login_required
@group_required('Admin', 'Coordinador')
def crear_persona(request):
    if request.method == 'POST':
        form = PersonaForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    persona = form.save(commit=False)
                    # S5: id auto-asignado por nextval('persona_id_seq')
                    persona.created_at = now()
                    persona.usuario_editor = str(request.user)
                    persona.save()

                messages.success(request, "✅ Persona registrada exitosamente.")
                return redirect('login:crear_participante', persona_id=persona.id)

            except Exception as e:
                logger.error(f"❌ Error al guardar persona: {e}", exc_info=True)
                messages.error(request, "⚠️ No se pudo guardar la persona. Verifica los datos.")
        else:
            logger.warning(f"Errores en formulario: {form.errors}")
            messages.warning(request, "⚠️ Revisa los campos del formulario.")
    else:
        form = PersonaForm()

    return render(request, 'login/crear_persona.html', {'form': form})


@login_required
@group_required('Admin', 'Coordinador')
def crear_participante(request, persona_id):
    persona = get_object_or_404(Persona, id=persona_id)

    # Si ya existe, redirigimos (para evitar duplicados)
    participante_existente = Participante.objects.filter(persona=persona).first()
    if participante_existente:
        messages.warning(request, f"La persona {persona} ya está registrada como participante.")
        return redirect('detalle_participante', participante_id=participante_existente.id)

    if request.method == 'POST':
        participante = Participante.objects.create(persona=persona)
        messages.success(request, f"✅ {persona} se registró como participante correctamente.")
        return redirect('detalle_participante', participante_id=participante.id)

    return render(request, 'login/crear_participante.html', {'persona': persona})

@login_required
@group_required('Admin', 'Coordinador')
def inscribir_participante(request, participante_id):
    participante = get_object_or_404(Participante, id=participante_id)

    if request.method == 'POST':
        form = InscripcionForm(request.POST)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.participante = participante
            inscripcion.save()
            messages.success(request, f"✅ {participante.persona} se inscribió correctamente.")
            return redirect('detalle_participante', participante_id=participante.id)
    else:
        form = InscripcionForm()

    return render(request, 'login/inscribir_participante.html', {
        'form': form,
        'participante': participante
    })





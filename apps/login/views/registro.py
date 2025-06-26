# apps/login/views/registro.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.login.forms import UsuarioRegistroForm, PersonaForm
from django.utils.timezone import now
from apps.login.decorators import group_required


@login_required
@group_required('Admin', 'Coordinador')
def crear_persona(request):
    form = PersonaForm(request.POST or None)
    
    if request.method == 'POST':
        if form.is_valid():
            persona = form.save(commit=False)
            persona.created_at = now()
            persona.usuario_editor = str(request.user)
            persona.save()
            return redirect('crear_participante', persona_id=persona.id)
        else:
            print(form.errors)
   
    return render(request, 'login/crear_persona.html', {'form': form})
   
   

@login_required
def registrar_usuario_view(request):
    if not request.user.groups.filter(name='Admin').exists():
        messages.warning(request, "Tu usuario no tiene acceso a esta vista.")
        return redirect('login:dashboard')

    if request.method == 'POST':
        form = UsuarioRegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = True
            user.save()

            grupo_asignado = form.cleaned_data['grupo']
            user.groups.add(grupo_asignado)

            messages.success(request, "Usuario creado y asignado al grupo correctamente.")
            return redirect('login:dashboard')
    else:
        form = UsuarioRegistroForm()

    return render(request, 'login/registrar_usuario.html', {'form': form})

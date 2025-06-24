# apps/login/views/registro.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.login.forms import UsuarioRegistroForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group



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

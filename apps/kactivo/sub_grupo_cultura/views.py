from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from apps.login.models.funcionario import Subgrupo, Dependencia  # M1: ya no duplicados en kactivo
from .forms import SubgrupoCulturaForm, CULTURA_NOMBRE

def _qs_cultura():
    return Subgrupo.objects.filter(dependencia__nombre__iexact=CULTURA_NOMBRE)

def lista(request):
    q = request.GET.get("q", "").strip()
    qs = _qs_cultura()
    if q:
        qs = qs.filter(Q(nombre__icontains=q))
    # Para mostrar cabecera de dependencia
    dep = Dependencia.objects.filter(nombre__iexact=CULTURA_NOMBRE).first()
    return render(request, "sub_grupo_cultura/lista.html", {"subgrupos": qs, "dep": dep, "q": q})

def crear(request):
    form = SubgrupoCulturaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("sub_grupo_cultura:lista")
    return render(request, "sub_grupo_cultura/formulario.html", {"form": form, "modo": "crear"})

def editar(request, pk: int):
    obj = get_object_or_404(_qs_cultura(), pk=pk)
    form = SubgrupoCulturaForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("sub_grupo_cultura:lista")
    return render(request, "sub_grupo_cultura/formulario.html", {"form": form, "modo": "editar", "obj": obj})

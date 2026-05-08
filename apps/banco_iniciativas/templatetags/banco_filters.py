"""Filtros de template del módulo Banco de Iniciativas.

`group_by_categoria` agrupa los checkboxes del field `escenarios_actuales`
por la columna `escenario.categoria_pot`. Devuelve una lista de grupos
con label, descripción y los checkboxes que pertenecen al grupo.

Uso en template:
    {% load banco_filters %}
    {% with grupos=form.escenarios_actuales|group_by_categoria %}
      {% for grupo in grupos %}
        <h3>{{ grupo.label }}</h3>
        <p>{{ grupo.descripcion }}</p>
        {% for box in grupo.checkboxes %}{{ box.tag }}{% endfor %}
      {% endfor %}
    {% endwith %}
"""
from django import template

from apps.banco_iniciativas.models import Escenario

register = template.Library()


# Orden de presentación + descripción humana de cada categoría POT 2022.
GRUPOS_META = [
    (
        "red_estructurante",
        "Red Estructurante (parques metropolitanos y zonales, > 1 ha)",
        "Coliseo, polideportivo, pista de atletismo, piscina, patinódromo.",
    ),
    (
        "red_proximidad",
        "Red de Proximidad (parques vecinales / de bolsillo, < 1 ha)",
        "Cancha múltiple, cancha de fútbol, gimnasio, escenario NTD.",
    ),
    (
        "otros_dotacionales",
        "Otros espacios dotacionales",
        "Salones comunales, plazoletas, humedales, senderos, zonas verdes.",
    ),
    (
        None,  # NULL → bloque "Sin categoría"
        "Otros espacios",
        None,
    ),
]


@register.filter(name="group_by_categoria")
def group_by_categoria(bound_field):
    """Agrupa los checkboxes del bound_field por escenario.categoria_pot.

    `bound_field` es `form['escenarios_actuales']` (un BoundField de un
    ModelMultipleChoiceField). Iteramos sus checkboxes y mapeamos cada
    uno a su `categoria_pot` consultando `Escenario` por código.
    """
    # Construir mapa codigo → categoria_pot del catálogo (1 query).
    escenarios = list(
        Escenario.objects.filter(activo=True).values("codigo", "categoria_pot")
    )
    cat_por_codigo = {e["codigo"]: e["categoria_pot"] for e in escenarios}

    # Reagrupar checkboxes.
    buckets = {meta[0]: [] for meta in GRUPOS_META}
    for box in bound_field:
        # box.data["value"] es ModelChoiceIteratorValue; str() devuelve el código.
        raw = box.data.get("value")
        try:
            codigo = int(str(raw))
        except (TypeError, ValueError):
            codigo = None
        cat = cat_por_codigo.get(codigo)
        # Si la categoría no está en GRUPOS_META, va al bucket "None".
        if cat not in buckets:
            cat = None
        buckets[cat].append(box)

    grupos = []
    for cat, label, descripcion in GRUPOS_META:
        boxes = buckets.get(cat, [])
        if not boxes:
            continue
        grupos.append({
            "categoria": cat,
            "label": label,
            "descripcion": descripcion,
            "checkboxes": boxes,
        })
    return grupos

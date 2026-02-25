from django import template

register = template.Library()

@register.filter
def mayusculas(valor):
    return valor.upper()

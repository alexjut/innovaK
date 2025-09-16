# apps/login/templatetags/roles.py
from django import template

register = template.Library()

@register.filter
def has_group(user, group_names):
    """Uso: {% if request.user|has_group:'Admin,Lider' %} ... {% endif %}"""
    if not getattr(user, "is_authenticated", False):
        return False
    wanted = {g.strip() for g in group_names.split(',') if g.strip()}
    user_groups = set(user.groups.values_list('name', flat=True))
    return bool(wanted & user_groups)
# apps/login/decorators.py
from django.contrib.auth.decorators import user_passes_test

def group_required(*group_names):
    def in_groups(u):
        return u.is_authenticated and bool(u.groups.filter(name__in=group_names))
    return user_passes_test(in_groups)
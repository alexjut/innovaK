from django.urls import path
from .views import ai_query_view

urlpatterns = [
    path('consulta-inteligente/', ai_query_view, name="consulta_ai")
]
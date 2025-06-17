from django.urls import path
from .views.home import home_view

app_name = 'login'

urlpatterns = [
    path('', home_view, name='dashboard'),  # la ruta principal
]
from django.urls import path
from .views.home import home_view
from .views.login import login_view
from .views.registro import registrar_usuario_view


app_name = 'login'

urlpatterns = [
    path('', home_view, name='dashboard'),  # la ruta principal
    path("login/", login_view, name="login"),
    path('registrar/', registrar_usuario_view, name='registrar_usuario'),
]
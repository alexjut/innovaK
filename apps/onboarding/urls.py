from django.urls import path

from .api.views import OnboardingCompletarView, OnboardingEstadoView

app_name = "onboarding"

urlpatterns = [
    path("estado/", OnboardingEstadoView.as_view(), name="estado"),
    path("completado/", OnboardingCompletarView.as_view(), name="completado"),
]

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.onboarding.models import OnboardingProgreso

from .serializers import CompletarTourSerializer


class OnboardingEstadoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        completados = list(
            OnboardingProgreso.objects
            .filter(usuario=request.user, completado=True)
            .values_list("tour_id", flat=True)
        )
        return Response({"completados": completados})


class OnboardingCompletarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = CompletarTourSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tour_id = ser.validated_data["tour_id"]
        OnboardingProgreso.objects.update_or_create(
            usuario=request.user,
            tour_id=tour_id,
            defaults={"completado": True},
        )
        return Response(
            {"tour_id": tour_id, "completado": True},
            status=status.HTTP_200_OK,
        )

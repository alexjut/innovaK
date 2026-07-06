from rest_framework import serializers


class CompletarTourSerializer(serializers.Serializer):
    tour_id = serializers.CharField(max_length=64)

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status

class HealthCheckViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)

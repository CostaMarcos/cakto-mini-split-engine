from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.api.serializers import RequestTransactionSerializer, PaymentResponseSerializer
from app.services.payment_process import PaymentProcessor


class HealthCheckViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)

class CheckoutQuoteView(APIView):
    def post(self, request):
        serializer = RequestTransactionSerializer(data=request.data)
        if serializer.is_valid():
            processor = PaymentProcessor()
            result = processor.execute(serializer.validated_data)

            response_serializer = PaymentResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

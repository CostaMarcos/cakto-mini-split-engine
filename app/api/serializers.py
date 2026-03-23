from rest_framework import serializers

class SplitSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(max_length=255)
    role = serializers.CharField(max_length=50)
    percent = serializers.IntegerField(min_value=0, max_value=100)

class RequestTransactionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='BRL')
    payment_method = serializers.ChoiceField(choices=['card', 'pix'])
    installments = serializers.IntegerField(min_value=0, max_value=12, required=False)
    splits = SplitSerializer(many=True)

    def validate_splits(self, value):
        if len(value) > 5:
            raise serializers.ValidationError("Uma transação pode ter no máximo 5 splits.")

        total_percent = sum(split['percent'] for split in value)

        if total_percent != 100:
            raise serializers.ValidationError("A soma das porcentagens dos splits deve ser exatamente 100.")
        return value

class ReceivableSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(max_length=255)
    role = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class OutboxEventSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=100)
    status = serializers.CharField(max_length=50)

class PaymentResponseSerializer(serializers.Serializer):
    payment_id = serializers.CharField(max_length=255, required=False)
    status = serializers.CharField(max_length=50, required=False)
    gross_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    platform_fee_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    receivables = ReceivableSerializer(many=True)
    outbox_event = OutboxEventSerializer(required=False)

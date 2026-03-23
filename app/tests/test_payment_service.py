from django.test import TestCase
from decimal import Decimal
from app.models import Payment, LedgerEntry, OutboxEvent
from app.services.payment_service import PaymentService

class PaymentServiceTestCase(TestCase):
    def setUp(self):
        self.service = PaymentService()
        self.valid_data = {
            "amount": Decimal("100.00"),
            "currency": "BRL",
            "payment_method": "card",
            "installments": 1,
            "splits": [
                {"recipient_id": "producer_1", "role": "producer", "percent": 60},
                {"recipient_id": "affiliate_1", "role": "affiliate", "percent": 40},
            ]
        }
        self.idempotency_key = "test-key-123"

    def test_execute_success(self):
        result = self.service.execute(self.valid_data, self.idempotency_key)

        # Verify response structure
        self.assertIn("payment_id", result)
        self.assertEqual(result["status"], "captured")
        self.assertEqual(result["gross_amount"], Decimal("100.00"))
        self.assertEqual(result["platform_fee_amount"], Decimal("3.99"))
        self.assertEqual(result["net_amount"], Decimal("96.01"))
        self.assertEqual(len(result["receivables"]), 2)
        self.assertEqual(result["outbox_event"]["type"], "payment_captured")
        self.assertEqual(result["outbox_event"]["status"], "published")

        # Verify DB records
        payment = Payment.objects.get(idempotency_key=self.idempotency_key)
        self.assertEqual(payment.gross_amount, Decimal("100.00"))
        self.assertEqual(payment.ledger_entries.count(), 2)
        
        self.assertTrue(OutboxEvent.objects.filter(payload__payment_id=str(payment.id)).exists())

    def test_execute_idempotency(self):
        # First execution
        result1 = self.service.execute(self.valid_data, self.idempotency_key)
        payment_id1 = result1["payment_id"]

        # Second execution with same key
        result2 = self.service.execute(self.valid_data, self.idempotency_key)
        payment_id2 = result2["payment_id"]

        self.assertEqual(payment_id1, payment_id2)
        self.assertEqual(Payment.objects.filter(idempotency_key=self.idempotency_key).count(), 1)

    def test_execute_with_different_splits(self):
        data = {
            "amount": Decimal("200.00"),
            "currency": "BRL",
            "payment_method": "pix",
            "splits": [
                {"recipient_id": "only_one", "role": "producer", "percent": 100},
            ]
        }
        result = self.service.execute(data, "another-key")

        self.assertEqual(result["gross_amount"], Decimal("200.00"))
        self.assertEqual(result["platform_fee_amount"], Decimal("0.00"))
        self.assertEqual(result["net_amount"], Decimal("200.00"))
        self.assertEqual(len(result["receivables"]), 1)
        self.assertEqual(result["receivables"][0]["recipient_id"], "only_one")

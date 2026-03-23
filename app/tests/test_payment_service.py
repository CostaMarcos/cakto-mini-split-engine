from django.test import TestCase
from decimal import Decimal
from unittest.mock import patch
from app.models import Payment, LedgerEntry, OutboxEvent
from app.services.payment_service import PaymentService

class PaymentServiceTestCase(TestCase):
    def setUp(self):
        self.service = PaymentService()
        self.valid_data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 1,
            "splits": [
                {"recipient_id": "producer_1", "role": "producer", "percent": 60},
                {"recipient_id": "affiliate_1", "role": "affiliate", "percent": 40},
            ]
        }
        self.idempotency_key = "test-key-123"

    @patch('django.db.transaction.on_commit', lambda f: f())
    @patch('app.tasks.process_payment_task.delay')
    def test_execute_async_success(self, mock_task):
        result = self.service.execute(self.valid_data, self.idempotency_key)

        # Verify response structure (should be processing/pending)
        self.assertEqual(result["payment_id"], "pending")
        self.assertEqual(result["status"], "processing")
        self.assertEqual(result["gross_amount"], 100.00)
        self.assertEqual(result["platform_fee_amount"], 3.99)
        self.assertEqual(result["net_amount"], 96.01)
        self.assertEqual(len(result["receivables"]), 2)
        
        # Verify OutboxEvent creation
        self.assertEqual(result["outbox_event"]["type"], "payment_requested")
        self.assertEqual(result["outbox_event"]["status"], "pending")

        # Verify DB records (Payment should NOT be created yet)
        self.assertFalse(Payment.objects.filter(idempotency_key=self.idempotency_key).exists())
        self.assertTrue(OutboxEvent.objects.filter(status='pending').exists())
        
        # Task should be dispatched
        mock_task.assert_called_once()

    @patch('django.db.transaction.on_commit', lambda f: f())
    @patch('app.tasks.process_payment_task.delay')
    def test_execute_idempotency_before_processing(self, mock_task):
        # Two calls with same key
        self.service.execute(self.valid_data, self.idempotency_key)
        self.service.execute(self.valid_data, self.idempotency_key)

        # Should only create 1 OutboxEvent and dispatch 1 task
        self.assertEqual(OutboxEvent.objects.filter(type="payment_requested").count(), 1)
        self.assertEqual(mock_task.call_count, 1)

    @patch('django.db.transaction.on_commit', lambda f: f())
    @patch('app.tasks.process_payment_task.delay')
    def test_execute_idempotency_after_processing(self, mock_task):
        # Simulate payment already exists
        Payment.objects.create(
            status='captured',
            gross_amount=Decimal("100.00"),
            platform_fee_amount=Decimal("3.99"),
            net_amount=Decimal("96.01"),
            payment_method="card",
            installments=1,
            idempotency_key=self.idempotency_key
        )

        result = self.service.execute(self.valid_data, self.idempotency_key)

        # Should return existing payment info
        self.assertNotEqual(result["payment_id"], "pending")
        self.assertEqual(result["status"], "captured")
        self.assertEqual(mock_task.call_count, 0)

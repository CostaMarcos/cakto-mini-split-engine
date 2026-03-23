from django.test import TestCase
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app.models import Payment, LedgerEntry, OutboxEvent
from app.tasks import process_payment_task

class TaskTestCase(TestCase):
    def setUp(self):
        self.valid_payload = {
            "transaction_data": {
                "amount": 100.0,
                "currency": "BRL",
                "payment_method": "card",
                "installments": 1,
                "splits": [
                    {"recipient_id": "producer_1", "role": "producer", "percent": 60},
                    {"recipient_id": "affiliate_1", "role": "affiliate", "percent": 40},
                ]
            },
            "idempotency_key": "test-key-task-123",
            "calculated_results": {
                "gross_amount": 100.0,
                "platform_fee_amount": 3.99,
                "net_amount": 96.01,
                "receivables": [
                    {"recipient_id": "producer_1", "role": "producer", "amount": 57.61},
                    {"recipient_id": "affiliate_1", "role": "affiliate", "amount": 38.40},
                ]
            }
        }
        self.event = OutboxEvent.objects.create(
            type="payment_requested",
            payload=self.valid_payload,
            status="pending"
        )

    @patch('app.tasks.process_payment_task.retry')
    def test_process_payment_task_success(self, mock_retry):
        result = process_payment_task(self.event.id)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["event_id"], self.event.id)

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, "published")
        self.assertIn("payment_id", self.event.payload)
        self.assertEqual(self.event.payload["processed_status"], "captured")

        payment = Payment.objects.get(idempotency_key="test-key-task-123")
        self.assertEqual(payment.gross_amount, Decimal("100.00"))
        self.assertEqual(payment.platform_fee_amount, Decimal("3.99"))
        self.assertEqual(payment.net_amount, Decimal("96.01"))

        self.assertEqual(payment.ledger_entries.count(), 2)
        ledger_producer = payment.ledger_entries.get(role="producer")
        self.assertEqual(ledger_producer.amount, Decimal("57.61"))

    def test_process_payment_task_already_processed_event(self):
        self.event.status = "published"
        self.event.save()

        result = process_payment_task(self.event.id)
        self.assertIsNone(result)
        self.assertEqual(Payment.objects.count(), 0)

    def test_process_payment_task_idempotency_payment_exists(self):
        Payment.objects.create(
            status='captured',
            gross_amount=Decimal("100.00"),
            platform_fee_amount=Decimal("3.99"),
            net_amount=Decimal("96.01"),
            payment_method="card",
            installments=1,
            idempotency_key="test-key-task-123"
        )

        process_payment_task(self.event.id)

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, "published")
        # Should not create another payment
        self.assertEqual(Payment.objects.count(), 1)

    @patch('app.tasks.process_payment_task.retry')
    def test_process_payment_task_failure_and_retry(self, mock_retry):
        with patch('app.models.Payment.objects.create', side_effect=Exception("Database error")):
            mock_retry.side_effect = Exception("Retry called")
            
            with self.assertRaises(Exception) as cm:
                process_payment_task(self.event.id)
            
            self.assertEqual(str(cm.exception), "Retry called")
            
            self.event.refresh_from_db()
            self.assertEqual(self.event.status, "failed")
            mock_retry.assert_called_once()

    @patch('app.tasks.process_payment_task.retry')
    def test_process_payment_task_recalculate_if_no_results(self, mock_retry):
        payload = self.valid_payload.copy()
        del payload["calculated_results"]
        self.event.payload = payload
        self.event.save()

        process_payment_task(self.event.id)

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, "published")
        
        payment = Payment.objects.get(idempotency_key="test-key-task-123")
        self.assertEqual(payment.gross_amount, Decimal("100.00"))
        self.assertEqual(payment.platform_fee_amount, Decimal("3.99"))

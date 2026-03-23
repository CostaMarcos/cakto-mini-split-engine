from decimal import Decimal
from django.db import transaction
from app.models import Payment, OutboxEvent
from app.services.payment_process import TransactionData, PaymentProcessor
from app.tasks import process_payment_task
from typing import Dict, Any

class PaymentService:
    def __init__(self):
        self.processor = PaymentProcessor()

    def execute(self, data: TransactionData, idempotency_key: str) -> Dict[str, Any]:

        payment_cache = self.payment_cache(idempotency_key)

        if payment_cache:
            return payment_cache

        outbox_event_exists = self.outbox_event_cache(idempotency_key)

        if outbox_event_exists is not None:
            return {
                "payment_id": "pending",
                "status": "processing",
                "gross_amount": None,
                "platform_fee_amount": None,
                "net_amount": None,
                "receivables": [],
                "outbox_event": {
                    "type": outbox_event_exists.type,
                    "status": outbox_event_exists.status
                }
            }

        with transaction.atomic():
            results = self.processor.execute(data)

            payload = {
                "transaction_data": data,
                "idempotency_key": idempotency_key,
                "calculated_results": results
            }

            outbox_event = OutboxEvent.objects.create(
                type="payment_requested",
                payload=payload,
                status="pending",
                idempotency_key=idempotency_key
            )

            transaction.on_commit(
                lambda: process_payment_task.delay(outbox_event.id)
            )

            return {
                "payment_id": "pending",
                "status": "processing",
                "gross_amount": results["gross_amount"],
                "platform_fee_amount": results["platform_fee_amount"],
                "net_amount": results["net_amount"],
                "receivables": results["receivables"],
                "outbox_event": {
                    "type": outbox_event.type,
                    "status": outbox_event.status
                }
            }

    def payment_cache(self, idempotency_key: str) -> dict | None:
        existing_payment = Payment.objects.filter(idempotency_key=idempotency_key).first()

        if existing_payment:
            return self._format_response(existing_payment)

        return None

    def outbox_event_cache(self, idempotency_key: str) -> dict | None:
        return OutboxEvent.objects.filter(idempotency_key=idempotency_key).first()

    def _format_response(self, payment: Payment) -> Dict[str, Any]:
        receivables = []
        for ledger in payment.ledger_entries.all():
            receivables.append({
                "recipient_id": ledger.recipient_id,
                "role": ledger.role,
                "amount": ledger.amount
            })

        outbox_event = OutboxEvent.objects.filter(idempotency_key=payment.idempotency_key).first()

        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "gross_amount": payment.gross_amount,
            "platform_fee_amount": payment.platform_fee_amount,
            "net_amount": payment.net_amount,
            "receivables": receivables,
            "outbox_event": {
                "type": outbox_event.type if outbox_event else "payment_captured",
                "status": outbox_event.status if outbox_event else "pending"
            }
        }

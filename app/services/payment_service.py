from django.db import transaction
from app.models import Payment, LedgerEntry, OutboxEvent
from app.services.payment_process import PaymentProcessor, TransactionData
from typing import Dict, Any

class PaymentService:
    def __init__(self):
        self.processor = PaymentProcessor()

    def execute(self, data: TransactionData, idempotency_key: str) -> Dict[str, Any]:
        existing_payment = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing_payment:
            return self._format_response(existing_payment)

        with transaction.atomic():
            results = self.processor.execute(data)

            payment = Payment.objects.create(
                status='captured',
                gross_amount=results["gross_amount"],
                platform_fee_amount=results["platform_fee_amount"],
                net_amount=results["net_amount"],
                payment_method=data["payment_method"],
                installments=data.get("installments", 1),
                idempotency_key=idempotency_key
            )

            for rec in results["receivables"]:
                LedgerEntry.objects.create(
                    payment=payment,
                    recipient_id=rec["recipient_id"],
                    role=rec["role"],
                    amount=rec["amount"]
                )

            outbox_event = OutboxEvent.objects.create(
                type="payment_captured",
                payload={
                    "payment_id": str(payment.id),
                    "status": payment.status,
                    "gross_amount": float(payment.gross_amount),
                    "platform_fee_amount": float(payment.platform_fee_amount),
                    "net_amount": float(payment.net_amount),
                },
                status="published"
            )

            return self._format_response(payment, outbox_event)

    def _format_response(self, payment: Payment, outbox_event: OutboxEvent = None) -> Dict[str, Any]:
        if outbox_event is None:
            outbox_event = OutboxEvent.objects.filter(type="payment_captured").order_by("-created_at").first()

        receivables = []
        for ledger in payment.ledger_entries.all():
            receivables.append({
                "recipient_id": ledger.recipient_id,
                "role": ledger.role,
                "amount": ledger.amount
            })

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

from decimal import Decimal
from celery import shared_task
from django.db import transaction
from app.models import Payment, LedgerEntry, OutboxEvent
from app.services.payment_process import PaymentProcessor
import logging

logger = logging.getLogger(__name__)

@shared_task(name='app.tasks.process_payment_task', bind=True, max_retries=3)
def process_payment_task(self, event_id):
    try:
        outbox_event = OutboxEvent.objects.get(id=event_id)
        
        if outbox_event.status != 'pending':
            logger.info(f"Event {event_id} already in status {outbox_event.status}. Skipping.")
            return

        payload = outbox_event.payload
        transaction_data = payload.get("transaction_data")
        idempotency_key = payload.get("idempotency_key")
        calculated_results = payload.get("calculated_results")

        with transaction.atomic():
            if Payment.objects.filter(idempotency_key=idempotency_key).exists():
                outbox_event.status = 'published'
                outbox_event.save()
                return

            if not calculated_results:
                processor = PaymentProcessor()
                working_data = transaction_data.copy()
                working_data["amount"] = Decimal(str(working_data["amount"]))
                results = processor.execute(working_data)
            else:
                results = {
                    "gross_amount": calculated_results["gross_amount"],
                    "platform_fee_amount":calculated_results["platform_fee_amount"],
                    "net_amount": calculated_results["net_amount"],
                    "receivables": [
                        {
                            "recipient_id": rec["recipient_id"],
                            "role": rec["role"],
                            "amount": rec["amount"]
                        } for rec in calculated_results["receivables"]
                    ]
                }

            payment = Payment.objects.create(
                status='captured',
                gross_amount=results["gross_amount"],
                platform_fee_amount=results["platform_fee_amount"],
                net_amount=results["net_amount"],
                payment_method=transaction_data["payment_method"],
                installments=transaction_data.get("installments", 1),
                idempotency_key=idempotency_key
            )

            for rec in results["receivables"]:
                LedgerEntry.objects.create(
                    payment=payment,
                    recipient_id=rec["recipient_id"],
                    role=rec["role"],
                    amount=rec["amount"]
                )

            outbox_event.status = 'published'
            new_payload = outbox_event.payload.copy()
            new_payload.update({
                "payment_id": str(payment.id),
                "processed_status": payment.status
            })
            outbox_event.payload = new_payload
            outbox_event.save()

            print(f"Payment {payment.id} processed successfully for event {event_id}")

    except OutboxEvent.DoesNotExist:
        logger.error(f"OutboxEvent {event_id} not found.")
    except Exception as exc:
        logger.error(f"Error processing payment for event {event_id}: {exc}")
        try:
            with transaction.atomic():
                event = OutboxEvent.objects.get(id=event_id)
                event.status = 'failed'
                event.save()
        except Exception as e:
            logger.error(f"Could not update status to failed for event {event_id}: {e}")
            
        raise self.retry(exc=exc, countdown=60)

    return {"status": "completed", "event_id": event_id}

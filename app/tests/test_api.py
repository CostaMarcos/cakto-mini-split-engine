from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
from unittest.mock import patch
from app.models import Payment

class CheckoutQuoteAPITestCase(APITestCase):
    def test_post_checkout_quote_success(self):
        url = reverse('checkout-quote')
        data = {
            "amount": "297.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 3,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 70 },
                { "recipient_id": "affiliate_9", "role": "affiliate", "percent": 30 }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["gross_amount"], "297.00")
        self.assertIn("platform_fee_amount", response.data)
        self.assertIn("receivables", response.data)
        self.assertEqual(len(response.data["receivables"]), 2)

    def test_post_checkout_quote_invalid_splits(self):
        url = reverse('checkout-quote')
        # Sum of percent is not 100
        data = {
            "amount": "297.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 3,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 50 },
                { "recipient_id": "affiliate_9", "role": "affiliate", "percent": 30 }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("splits", response.data)
        self.assertEqual(response.data["splits"][0], "A soma das porcentagens dos splits deve ser exatamente 100.")

    def test_post_checkout_quote_max_splits(self):
        url = reverse('checkout-quote')
        # 6 splits should fail
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 1,
            "splits": [
                { "recipient_id": "r1", "role": "p", "percent": 10 },
                { "recipient_id": "r2", "role": "p", "percent": 10 },
                { "recipient_id": "r3", "role": "p", "percent": 10 },
                { "recipient_id": "r4", "role": "p", "percent": 10 },
                { "recipient_id": "r5", "role": "p", "percent": 10 },
                { "recipient_id": "r6", "role": "p", "percent": 50 }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("splits", response.data)
        self.assertEqual(response.data["splits"][0], "Uma transação pode ter no máximo 5 splits.")

    def test_post_checkout_quote_decimal_splits(self):
        url = reverse('checkout-quote')
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 3,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 33.33 },
                { "recipient_id": "affiliate_2", "role": "affiliate", "percent": 33.33 },
                { "recipient_id": "affiliate_3", "role": "affiliate", "percent": 33.34 }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 100 - (4.99 + (3-1)*2) = 100 - 8.99 = 91.01 net amount
        self.assertEqual(Decimal(response.data["platform_fee_amount"]) + Decimal(response.data["net_amount"]), Decimal(data.get("amount")))
        total_sum_split = sum(Decimal(receivable["amount"]) for receivable in response.data["receivables"])
        self.assertEqual(total_sum_split, Decimal(response.data["net_amount"]))
        self.assertEqual(len(response.data["receivables"]), 3)

    def test_post_checkout_quote_twelve_installment_decimal_splits(self):
        url = reverse('checkout-quote')
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 12,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 30 },
                { "recipient_id": "affiliate_2", "role": "affiliate", "percent": 30 },
                { "recipient_id": "affiliate_3", "role": "affiliate", "percent": 13.33 },
                { "recipient_id": "affiliate_4", "role": "affiliate", "percent": 13.33 },
                { "recipient_id": "affiliate_5", "role": "affiliate", "percent": 13.34 }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        # 100 - (4.99 + (12-1)*2) = 100 - 26.99 = 73.01 net amount
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["platform_fee_amount"]) + Decimal(response.data["net_amount"]), Decimal(data.get("amount")))
        total_sum_split = sum(Decimal(receivable["amount"]) for receivable in response.data["receivables"])
        self.assertEqual(total_sum_split, Decimal(response.data["net_amount"]))
        self.assertEqual(len(response.data["receivables"]), 5)

    def test_post_checkout_quote_pix_with_installments_fail(self):
        url = reverse('checkout-quote')
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "pix",
            "installments": 2,
            "splits": [
                { "recipient_id": "r1", "role": "p", "percent": 100 }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("installments", response.data)
        self.assertEqual(response.data["installments"][0], "Transações via PIX não podem ter parcelas.")

    def test_post_checkout_quote_pix_decimal_splits(self):
        url = reverse('checkout-quote')
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "pix",
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 30 },
                { "recipient_id": "affiliate_2", "role": "affiliate", "percent": 30 },
                { "recipient_id": "affiliate_3", "role": "affiliate", "percent": 13.33 },
                { "recipient_id": "affiliate_4", "role": "affiliate", "percent": 13.33 },
                { "recipient_id": "affiliate_5", "role": "affiliate", "percent": 13.34 }
            ]
        }
        
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["platform_fee_amount"]) + Decimal(response.data["net_amount"]), Decimal(data.get("amount")))
        total_sum_split = sum(Decimal(receivable["amount"]) for receivable in response.data["receivables"])
        self.assertEqual(total_sum_split, Decimal(response.data["net_amount"]))
        self.assertEqual(len(response.data["receivables"]), 5)

class PaymentAPITestCase(APITestCase):
    @patch('django.db.transaction.on_commit', lambda f: f())
    @patch('app.tasks.process_payment_task.delay')
    def test_post_payment_async_success(self, mock_task):
        url = reverse('payment-create')
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 1,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 100 }
            ]
        }
        headers = {'HTTP_IDEMPOTENCY_KEY': 'test-payment-123'}

        response = self.client.post(url, data, format='json', **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["gross_amount"], "100.00")
        self.assertEqual(response.data["payment_id"], "pending")
        self.assertEqual(response.data["status"], "processing")
        self.assertIn("outbox_event", response.data)
        self.assertEqual(response.data["outbox_event"]["status"], "pending")
        
        # Verify task dispatched
        mock_task.assert_called_once()

    def test_post_payment_missing_idempotency_key(self):
        url = reverse('payment-create')
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 1,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 100 }
            ]
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Idempotency-Key header é obrigatório.")

    @patch('django.db.transaction.on_commit', lambda f: f())
    @patch('app.tasks.process_payment_task.delay')
    def test_post_payment_idempotency(self, mock_task):
        url = reverse('payment-create')
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 1,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 100 }
            ]
        }
        key = "same-key-123"
        headers = {'HTTP_IDEMPOTENCY_KEY': key}

        # First request
        response1 = self.client.post(url, data, format='json', **headers)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response1.data["payment_id"], "pending")

        # Second request with same key (still pending)
        response2 = self.client.post(url, data, format='json', **headers)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.data["payment_id"], "pending")

        self.assertEqual(mock_task.call_count, 1)

    @patch('django.db.transaction.on_commit', lambda f: f())
    @patch('app.tasks.process_payment_task.delay')
    def test_post_payment_idempotency_after_captured(self, mock_task):
        # Manually create a captured payment
        Payment.objects.create(
            status='captured',
            gross_amount=Decimal("100.00"),
            platform_fee_amount=Decimal("3.99"),
            net_amount=Decimal("96.01"),
            payment_method="card",
            installments=1,
            idempotency_key="captured-key"
        )
        
        url = reverse('payment-create')
        data = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 1,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 100 }
            ]
        }
        headers = {'HTTP_IDEMPOTENCY_KEY': "captured-key"}

        response = self.client.post(url, data, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "captured")
        self.assertNotEqual(response.data["payment_id"], "pending")
        self.assertEqual(mock_task.call_count, 0)

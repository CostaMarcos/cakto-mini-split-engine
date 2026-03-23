from django.test import TestCase
from decimal import Decimal
from app.services.payment_process import PaymentProcessor, TransactionData

class PaymentProcessorTestCase(TestCase):
    def setUp(self):
        self.processor = PaymentProcessor()

    def test_calculate_platform_fee_pix(self):
        # PIX should have 0 fee
        fee = self.processor._calculate_platform_fee(Decimal("100.00"), "pix", 1)
        self.assertEqual(fee, Decimal("0.00"))

    def test_calculate_platform_fee_card_1_installment(self):
        # 3.99% fee for 1 installment
        fee = self.processor._calculate_platform_fee(Decimal("100.00"), "card", 1)
        self.assertEqual(fee, Decimal("3.99"))

    def test_calculate_platform_fee_card_3_installments(self):
        # 4.99% + (3-1)*2% = 4.99% + 4% = 8.99%
        fee = self.processor._calculate_platform_fee(Decimal("100.00"), "card", 3)
        self.assertEqual(fee, Decimal("8.99"))

    def test_execute_with_multiple_splits(self):
        data: TransactionData = {
            "amount": Decimal("100.00"),
            "currency": "BRL",
            "payment_method": "card",
            "installments": 1,
            "splits": [
                {"recipient_id": "r1", "role": "p1", "percent": 60},
                {"recipient_id": "r2", "role": "p2", "percent": 40},
            ]
        }
        
        result = self.processor.execute(data)
        
        # 100 - 3.99 = 96.01 net
        # 96.01 * 0.6 = 57.606 -> 57.61
        # 96.01 - 57.61 = 38.40
        
        self.assertEqual(result["gross_amount"], Decimal("100.00"))
        self.assertEqual(result["platform_fee_amount"], Decimal("3.99"))
        self.assertEqual(result["net_amount"], Decimal("96.01"))
        self.assertEqual(result["receivables"][0]["amount"], Decimal("57.61"))
        self.assertEqual(result["receivables"][1]["amount"], Decimal("38.40"))

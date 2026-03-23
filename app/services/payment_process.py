from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, TypedDict

class SplitData(TypedDict):
    recipient_id: str
    role: str
    percent: int

class TransactionData(TypedDict):
    amount: Decimal
    currency: str
    payment_method: str
    installments: int
    splits: List[SplitData]

class PaymentProcessor:
    def __init__(self):
        self.PRECISION = Decimal("0.01")

    def _calculate_platform_fee(self, gross_amount: Decimal, method: str, installments: int) -> Decimal:
        if method.lower() == "pix":
            return Decimal("0.00")

        if installments <= 1:
            fee_percent = Decimal("3.99")
        else:
            fee_percent = Decimal("4.99") + (Decimal(installments) - 1) * Decimal("2.00")

        fee_amount = (gross_amount * (fee_percent / 100)).quantize(self.PRECISION, rounding=ROUND_HALF_UP)
        return fee_amount

    def execute(self, data: TransactionData) -> Dict[str, Any]:
        gross_amount = data["amount"]
        installments = data.get("installments", 1) 
        method = data["payment_method"]
        splits = data["splits"]

        fee_amount = self._calculate_platform_fee(gross_amount, method, installments)
        net_amount = gross_amount - fee_amount

        receivables = []
        accumulated_split = Decimal("0.00")

        for i, split in enumerate(splits):
            percent = Decimal(str(split["percent"]))

            if i == len(splits) - 1:
                recipient_amount = net_amount - accumulated_split
            else:
                recipient_amount = (net_amount * (percent / 100)).quantize(self.PRECISION, rounding=ROUND_HALF_UP)
                accumulated_split += recipient_amount
            
            receivables.append({
                "recipient_id": split["recipient_id"],
                "role": split["role"],
                "amount": recipient_amount
            })

        return {
            "gross_amount": gross_amount,
            "platform_fee_amount": fee_amount,
            "net_amount": net_amount,
            "receivables": receivables,
        }

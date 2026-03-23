from django.db import models

class Payment(models.Model):
    STATUS_CHOICES = [
        ('captured', 'captured'),
        ('pending', 'pending'),
        ('failed', 'failed'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('pix', 'pix'),
        ('card', 'card')
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='captured')
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    installments = models.IntegerField(default=1)
    idempotency_key = models.CharField(unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.status}"


class LedgerEntry(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='ledger_entries')
    recipient_id = models.CharField(max_length=100)
    role = models.CharField(max_length=50) # 'producer', 'affiliate'
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Ledger entries"


class OutboxEvent(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('published', 'Published'),
    ]

    type = models.CharField(max_length=100, default='payment_captured')
    payload = models.JSONField() # Requer PostgreSQL (ou Django 3.0+)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(unique=True, editable=False, null=True, blank=True)

    def __str__(self):
        return f"{self.type} - {self.status}"

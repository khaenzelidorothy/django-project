from django.db import models
from users.models import User
from orders.models import Order

class Payment(models.Model):
    STATUS_CHOICES = (
        ('held', 'Held'),
        ('released', 'Released'),
        ('refunded', 'Refunded'),
    )
    order_id = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    artisan_id = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'artisan'}, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='held')
    paid_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    held_by_platform = models.BooleanField(default=True)
    mpesa_receipt_number = models.CharField(max_length=50, null=True, blank=True)
    buyer_phone = models.CharField(max_length=15, default="UNKNOWN")
    artisan_phone = models.CharField(max_length=15, default="UNKNOWN")
    result_description = models.CharField(max_length=255, null=True, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)
    refunded_reason = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'Payment {self.transaction_code} - Status: {self.status}'
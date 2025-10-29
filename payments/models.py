from django.db import models
from Marketplace.models import Shop
import uuid


class Order(models.Model):
    """
    Order created from session/cart prior to payment.
    items: list of {"product_id": str, "name": str, "price": int, "quantity": int}
    status: pending -> paid -> failed/refunded
    payment_intent_id: Stripe PaymentIntent id once created/confirmed
    """
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_amount = models.PositiveIntegerField(default=0)
    items = models.JSONField(default=list)  # store cart snapshot
    metadata = models.JSONField(default=dict, blank=True)
    # payment_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"

class MethodPaid(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(Shop, related_name="qrcodes", on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    nom = models.CharField(max_length=255, null=True, blank=True)
    pathimg = models.ImageField(upload_to="QrCodes/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now_add=True)
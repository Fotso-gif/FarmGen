from django.db import models
import uuid

class Product(models.Model):
    """
    Simple product model for inventory management.
    product_id: external/product SKU identifier (string)
    """
    product_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    price_cents = models.PositiveIntegerField(default=0)
    stock = models.IntegerField(default=0)  # available quantity

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.product_id})"

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
    total_amount_cents = models.PositiveIntegerField(default=0)
    items = models.JSONField(default=list)  # store cart snapshot
    metadata = models.JSONField(default=dict, blank=True)
    payment_intent_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"

from django.db import models
from account.models import User
from Marketplace.models import Shop
import uuid

class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_WAITING_PAYMENT = 'waiting_payment'
    STATUS_PAYMENT_VERIFIED = 'payment_verified'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_PAID, 'Payé'),
        (STATUS_FAILED, 'Échec'),
        (STATUS_REFUNDED, 'Remboursé'),
        (STATUS_WAITING_PAYMENT, 'En attente de paiement'),
        (STATUS_PAYMENT_VERIFIED, 'Paiement vérifié'),
    ]

    PAYMENT_METHODS = [
        ('whatsapp', 'WhatsApp'),
        ('om', 'Orange Money'),
        ('momo', 'MTN Mobile Money'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_amount = models.PositiveIntegerField(default=0)
    tax_amount = models.PositiveIntegerField(default=0)
    final_amount = models.PositiveIntegerField(default=0)
    
    # Informations client
    customer_first_name = models.CharField(max_length=100)
    customer_last_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    
    # Méthode de paiement
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_phone = models.CharField(max_length=20, blank=True, null=True)  # Numéro pour paiement
    
    # Preuve de paiement
    payment_proof = models.ImageField(upload_to="payment_proofs/%Y/%m/%d/", blank=True, null=True)
    payment_verified = models.BooleanField(default=False)
    payment_verified_at = models.DateTimeField(blank=True, null=True)
    
    # Données du panier
    cart_items = models.JSONField(default=list)
    shop_id = models.IntegerField()  # ID de la boutique
    
    # Métadonnées
    metadata = models.JSONField(default=dict, blank=True)
    
    # QR Code et USSD (pour OM et MOMO)
    qr_code_data = models.TextField(blank=True, null=True)
    ussd_code = models.CharField(max_length=50, blank=True, null=True)
    whatsapp_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"

    @property
    def full_name(self):
        return f"{self.customer_first_name} {self.customer_last_name}"

class PaymentVerification(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='verifications')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Verification for {self.order.id}"

class MethodPaid(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(Shop, related_name="qrcodes", on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    nom = models.CharField(max_length=255, null=True, blank=True)
    pathimg = models.ImageField(upload_to="QrCodes/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now_add=True)
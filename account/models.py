# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.crypto import get_random_string
import uuid

class User(AbstractUser):
    ACCOUNT_TYPES = (
        ('seller', 'Agriculteur/Vendeur'),
        ('client', 'Client/Utilisateur'),
    )
    
    REGIONS_CAMEROUN = (
        ('adamaoua', 'Adamaoua'),
        ('centre', 'Centre'),
        ('est', 'Est'),
        ('extreme-nord', 'Extrême-Nord'),
        ('littoral', 'Littoral'),
        ('nord', 'Nord'),
        ('nord-ouest', 'Nord-Ouest'),
        ('ouest', 'Ouest'),
        ('sud', 'Sud'),
        ('sud-ouest', 'Sud-Ouest'),
    )
    
    # Champs communs à tous les utilisateurs
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES)
    phone = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=20, choices=REGIONS_CAMEROUN)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    
    # Champs de suivi
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_account_type_display()})"
    
    @property
    def is_seller(self):
        return self.account_type == 'seller'
    
    @property
    def is_client(self):
        return self.account_type == 'client'

class SellerProfile(models.Model):
    SPECIALTIES = (
        ('legumes', 'Légumes'),
        ('fruits', 'Fruits'),
        ('cereales', 'Céréales'),
        ('tubercules', 'Tubercules'),
        ('elevage', 'Élevage'),
        ('produits_laitiers', 'Produits Laitiers'),
        ('volailles', 'Volailles'),
        ('apiculture', 'Apiculture'),
        ('autres', 'Autres'),
    )
    
    CERTIFICATION_TYPES = (
        ('bio', 'Agriculture Biologique'),
        ('local', 'Produit Local'),
        ('qualite', 'Certification Qualité'),
        ('aucune', 'Aucune Certification'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    farm_name = models.CharField(max_length=255)
    farm_description = models.TextField(blank=True)
    specialty = models.CharField(max_length=20, choices=SPECIALTIES, default='autres')
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, help_text="Superficie en hectares")  # en hectares
    production_capacity = models.CharField(max_length=255, blank=True, help_text="Capacité de production mensuelle/annuelle")
    certification = models.CharField(max_length=20, choices=CERTIFICATION_TYPES, default='aucune')
    certification_details = models.TextField(blank=True)
    
    # Options de livraison
    delivery_options = models.JSONField(default=dict, blank=True)
    delivery_radius = models.IntegerField(default=50, help_text="Rayon de livraison en km")
    
    # Statistiques du vendeur
    total_sales = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_reviews = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Boutique: {self.farm_name} - {self.user.get_full_name()}"
    
    class Meta:
        verbose_name = "Profil Vendeur"
        verbose_name_plural = "Profils Vendeurs"

class ClientProfile(models.Model):
    PREFERENCE_CATEGORIES = (
        ('legumes', 'Légumes'),
        ('fruits', 'Fruits'),
        ('cereales', 'Céréales'),
        ('tubercules', 'Tubercules'),
        ('viande', 'Viande'),
        ('produits_laitiers', 'Produits Laitiers'),
        ('volailles', 'Volailles'),
        ('miel', 'Miel'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    
    # Préférences d'achat
    preferences = models.JSONField(default=dict, blank=True)
    favorite_categories = models.JSONField(default=list, blank=True)
    
    # Adresses de livraison multiples
    delivery_addresses = models.JSONField(default=list, blank=True)
    
    # Paramètres de notification
    newsletter_subscribed = models.BooleanField(default=True)
    price_alerts = models.BooleanField(default=False)
    
    # Historique et préférences
    favorite_sellers = models.ManyToManyField('SellerProfile', blank=True, related_name='favorited_by')
    recently_viewed_products = models.JSONField(default=list, blank=True)
    
    # Informations de fidélité
    loyalty_points = models.IntegerField(default=0)
    membership_level = models.CharField(max_length=20, default='standard', choices=(
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('vip', 'VIP'),
    ))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profil Client: {self.user.get_full_name()}"
    
    class Meta:
        verbose_name = "Profil Client"
        verbose_name_plural = "Profils Clients"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Reset token for {self.user.email}"
    
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at
    
    @classmethod
    def generate_token(cls, user):
        # Supprimer les anciens tokens
        cls.objects.filter(user=user).delete()
        
        # Créer un nouveau token
        token = get_random_string(50)
        expires_at = timezone.now() + timezone.timedelta(hours=24)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
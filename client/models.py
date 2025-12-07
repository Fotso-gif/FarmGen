from django.db import models
from django.utils import timezone
from account.models import User
from django.core.validators import EmailValidator

class NewsletterSubscriber(models.Model):
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
        ('unsubscribed', 'Désabonné'),
    ]
    
    email = models.EmailField(
        unique=True,
        verbose_name="Adresse email",
        validators=[EmailValidator()]
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Utilisateur",
        related_name='newsletter_subscriptions'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Statut"
    )
    subscribed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'inscription"
    )
    unsubscribed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de désabonnement"
    )
    source = models.CharField(
        max_length=100,
        default='blog',
        verbose_name="Source d'inscription",
        help_text="Page où l'utilisateur s'est inscrit"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )
    confirmation_token = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Token de confirmation"
    )
    is_confirmed = models.BooleanField(
        default=False,
        verbose_name="Email confirmé"
    )
    last_email_sent = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernier email envoyé"
    )
    preferences = models.JSONField(
        default=dict,
        verbose_name="Préférences",
        help_text="Préférences de l'utilisateur"
    )
    
    class Meta:
        verbose_name = "Abonné à la newsletter"
        verbose_name_plural = "Abonnés à la newsletter"
        ordering = ['-subscribed_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['subscribed_at']),
        ]
    
    def __str__(self):
        return self.email
    
    def unsubscribe(self):
        """Désabonner l'utilisateur"""
        self.status = 'unsubscribed'
        self.unsubscribed_at = timezone.now()
        self.save()
    
    def resubscribe(self):
        """Réabonner l'utilisateur"""
        self.status = 'active'
        self.unsubscribed_at = None
        self.save()
    
    @property
    def is_active(self):
        return self.status == 'active' and self.is_confirmed
from django.db import models
from account.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from Blog.models import Article
import uuid

class Comment(models.Model):
    """Modèle pour les commentaires sur les articles"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('spam', 'Spam'),
    ]
    
    TYPE_CHOICES = [
        ('article', 'Commentaire Article'),
        ('testimonial', 'Commentaire Témoignage'),
    ]
    
    # Informations de base
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Utilisateur"
    )
    
    # Contenu lié
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comments',
        verbose_name="Article"
    )
    testimonial = models.ForeignKey(
        'Testimonial',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comments',
        verbose_name="Témoignage"
    )
    
    # Contenu du commentaire
    content = models.TextField(
        verbose_name="Contenu",
        max_length=2000
    )
    
    # Métadonnées
    comment_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='article',
        verbose_name="Type de commentaire"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Relations
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name="Commentaire parent"
    )
    
    # Métadonnées techniques
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name="User Agent"
    )
    
    # Dates
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'approbation"
    )
    
    # Modération
    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_comments',
        verbose_name="Modéré par"
    )
    moderation_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="Raison de la modération"
    )
    
    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['article', 'status']),
        ]
    
    def __str__(self):
        return f"Commentaire de {self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        # Si le commentaire est approuvé, mettre à jour la date d'approbation
        if self.status == 'approved' and not self.approved_at:
            self.approved_at = timezone.now()
        
        # Déterminer le type automatiquement
        if self.article:
            self.comment_type = 'article'
        elif self.testimonial:
            self.comment_type = 'testimonial'
        
        super().save(*args, **kwargs)
    
    @property
    def is_reply(self):
        return self.parent is not None
    
    @property
    def likes_count(self):
        return self.likes.filter(is_active=True).count()
    
    @property
    def replies_count(self):
        return self.replies.filter(status='approved').count()
    
    def approve(self, moderator=None):
        """Approuver le commentaire"""
        self.status = 'approved'
        self.moderated_by = moderator
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, moderator=None, reason=""):
        """Rejeter le commentaire"""
        self.status = 'rejected'
        self.moderated_by = moderator
        self.moderation_reason = reason
        self.save()


class Testimonial(models.Model):
    """Modèle pour les témoignages clients"""
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('published', 'Publié'),
        ('archived', 'Archivé'),
    ]
    
    CATEGORY_CHOICES = [
        ('customer', 'Client'),
        ('partner', 'Partenaire'),
        ('farmer', 'Agriculteur'),
        ('expert', 'Expert'),
        ('general', 'Général'),
    ]
    
    # Informations de base
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        verbose_name="Utilisateur"
    )
    
    # Contenu du témoignage
    title = models.CharField(
        max_length=200,
        verbose_name="Titre du témoignage"
    )
    content = models.TextField(
        verbose_name="Contenu du témoignage",
        max_length=1000
    )
    
    # Informations supplémentaires
    author_name = models.CharField(
        max_length=100,
        verbose_name="Nom de l'auteur"
    )
    author_role = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Rôle/Profession"
    )
    author_company = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Entreprise/Organisation"
    )
    author_location = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Localisation"
    )
    
    # Catégorie et statut
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='customer',
        verbose_name="Catégorie"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Évaluation
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5,
        verbose_name="Note (1-5)"
    )
    
    # Images
    author_photo = models.ImageField(
        upload_to='testimonials/authors/',
        null=True,
        blank=True,
        verbose_name="Photo de l'auteur"
    )
    featured_image = models.ImageField(
        upload_to='testimonials/featured/',
        null=True,
        blank=True,
        verbose_name="Image mise en avant"
    )
    
    # Métadonnées
    is_featured = models.BooleanField(
        default=False,
        verbose_name="Mis en avant"
    )
    allow_display = models.BooleanField(
        default=True,
        verbose_name="Autoriser l'affichage public"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Vérifié par l'équipe"
    )
    
    # Dates
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification"
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de publication"
    )
    
    # SEO
    meta_title = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Meta titre"
    )
    meta_description = models.TextField(
        null=True,
        blank=True,
        verbose_name="Meta description"
    )
    
    class Meta:
        verbose_name = "Témoignage"
        verbose_name_plural = "Témoignages"
        ordering = ['-is_featured', '-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['rating']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['published_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.author_name}"
    
    def save(self, *args, **kwargs):
        # Si publié, mettre à jour la date de publication
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        # Si l'utilisateur est connecté, utiliser ses informations
        if self.user and not self.author_name:
            self.author_name = self.user.get_full_name() or self.user.username
        
        super().save(*args, **kwargs)
    
    @property
    def is_published(self):
        return self.status == 'published' and self.allow_display
    
    @property
    def author_display_name(self):
        """Retourne le nom d'affichage de l'auteur"""
        if self.author_role and self.author_company:
            return f"{self.author_name}, {self.author_role} chez {self.author_company}"
        elif self.author_role:
            return f"{self.author_name}, {self.author_role}"
        elif self.author_company:
            return f"{self.author_name} de {self.author_company}"
        return self.author_name
    
    def publish(self):
        """Publier le témoignage"""
        self.status = 'published'
        self.published_at = timezone.now()
        self.save()
    
    def get_absolute_url(self):
        return f"/testimonials/{self.id}/"


class CommentLike(models.Model):
    """Modèle pour les likes sur les commentaires"""
    
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name="Commentaire"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comment_likes',
        verbose_name="Utilisateur"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Like de commentaire"
        verbose_name_plural = "Likes de commentaires"
        unique_together = ['comment', 'user']
        indexes = [
            models.Index(fields=['comment', 'user']),
        ]
    
    def __str__(self):
        return f"Like de {self.user.username} sur commentaire {self.comment.id}"


class CommentReport(models.Model):
    """Modèle pour les signalements de commentaires"""
    
    REASON_CHOICES = [
        ('spam', 'Spam ou publicité'),
        ('offensive', 'Contenu offensant'),
        ('inappropriate', 'Contenu inapproprié'),
        ('fake', 'Information fausse'),
        ('other', 'Autre'),
    ]
    
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name="Commentaire signalé"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comment_reports',
        verbose_name="Utilisateur signalant"
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        verbose_name="Raison du signalement"
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="Description supplémentaire"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )
    is_resolved = models.BooleanField(
        default=False,
        verbose_name="Signalement traité"
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports',
        verbose_name="Résolu par"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de résolution"
    )
    resolution_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Notes de résolution"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Signalement de commentaire"
        verbose_name_plural = "Signalements de commentaires"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['comment', 'is_resolved']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Signalement de {self.user or 'Anonyme'} sur commentaire {self.comment.id}"
    
    def resolve(self, moderator, notes=""):
        """Marquer le signalement comme résolu"""
        self.is_resolved = True
        self.resolved_by = moderator
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save()
from django.db import models

class Article(models.Model):
    TYPE_CHOICES = [
        ('article', 'Article (texte)'),
        ('affiche', 'Affiche (image)'),
        ('podcast', 'Podcast (vidéo)'),
    ]

    # 🔹 Référence vers la boutique
    shop = models.ForeignKey(
        'Marketplace.Shop',       # référence au modèle Shop d'une autre app
        on_delete=models.CASCADE, # si la boutique est supprimée → supprime ses articles
        related_name='articles',  # permet de faire shop.articles.all()
        null=True,                # facultatif au début pour migration
        blank=True,
        help_text="Boutique qui a publié cet article"
    )

    titre = models.CharField(max_length=200)
    type_contenu = models.CharField(max_length=20, choices=TYPE_CHOICES, default='article')
    contenu = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    date_publication = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titre} ({self.shop})"

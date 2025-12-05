from django.db import models
from django.utils import timezone
from account.models import User

class Shop(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, related_name="shop", on_delete=models.PROTECT)
    title = models.CharField(max_length=120, unique=True)
    localisation = models.CharField(max_length=120)
    type_shop = models.CharField(max_length=120)
    note = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    couverture = models.ImageField(upload_to="shop/%Y/%m/%d/")
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    def __str__(self): return self.title


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    shop = models.ForeignKey(
        'Marketplace.Shop',            
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Référencement optionnel vers la boutique (nullable pour migration)"
    )
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    def __str__(self): return self.name

class Product(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)
    LOW_STOCK_THRESHOLD = 5
    class Meta: ordering = ["-updated_at", "name"]
    def is_expired(self): return self.expiry_date and self.expiry_date < timezone.localdate()
    def stock_value(self): return self.price * self.quantity
    def is_low_stock(self): return self.quantity < self.LOW_STOCK_THRESHOLD
    def __str__(self): return f"{self.name} ({self.quantity})"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/%Y/%m/%d/")
    alt_text = models.CharField(max_length=255, blank=True)
    def __str__(self): return f"Image for {self.product.name}"

class Favorite(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, related_name="favorites", on_delete=models.CASCADE)
    shop = models.ForeignKey(
    Shop,
    related_name="favorited_by",
    on_delete=models.CASCADE,
    null=True,
    blank=True
)
    product = models.ForeignKey(
    Product,
    related_name="fav_product",
    on_delete=models.CASCADE,
    null=True,
    blank=True
)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'shop')  # Un utilisateur ne peut favoriser qu'une fois une boutique
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.user.username} - {self.shop.title}"

class ProductLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

class ProductView(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    query = models.CharField(max_length=255)
    filters = models.JSONField(default=dict)
    searched_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    RATING_CHOICES = [
        (1, '★'),
        (2, '★★'),
        (3, '★★★'),
        (4, '★★★★'),
        (5, '★★★★★'),
    ]
    
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Un utilisateur ne peut commenter qu'une fois par boutique/produit
        unique_together = [
            ('user', 'shop'),
            ('user', 'product')
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Avis de {self.user.username} - Note: {self.rating}"
    
class FAQ(models.Model):
    """FAQ par boutique"""
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='faqs')
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
class ChatHistory(models.Model):
    """Historique des conversations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    thread_id = models.CharField(max_length=100)
    message = models.TextField()
    response = models.TextField()
    shop_name = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
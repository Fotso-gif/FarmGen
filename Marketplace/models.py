from django.db import models
from django.utils import timezone
from account.models import User

class shop(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, related_name="shop", on_delete=models.PROTECT)
    title = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    couverture = models.ImageField(upload_to="shop/%Y/%m/%d/")
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    def __str__(self): return self.name


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    shop = models.ForeignKey(shop, related_name="category", on_delete=models.PROTECT)
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

from django.contrib import admin
from .models import Product, Order

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'name', 'price_cents', 'stock', 'updated_at')
    search_fields = ('product_id', 'name')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'total_amount_cents', 'payment_intent_id', 'created_at')
    readonly_fields = ('created_at',)
    search_fields = ('id', 'payment_intent_id')
    list_filter = ('status',)

from django.urls import path
from . import views

urlpatterns = [
     # === PANIER (AJAX / SESSIONS) ===
    path('cart/add/<int:product_id>/', views.add_to_cart_view, name='add-to-cart'),
    path('cart/remove/<int:product_id>/', views.remove_cart_view, name='remove-from-cart'),
    path('cart/update/<int:product_id>/', views.update_cart_view, name='update-cart'),
    path('cart/clear/', views.clear_cart_view, name='clear-cart'),
    path('cart/summary/', views.cart_summary_view, name='cart-summary'),
]

from django.urls import path
from . import views

urlpatterns = [
     # === PANIER (AJAX / SESSIONS) ===
    
    # Ajouter un produit au panier
    path('add/<int:product_id>/', views.add_to_cart, name='add-to-cart'),
    
    # Supprimer un produit du panier
    path('remove/<int:product_id>/', views.remove_from_cart, name='remove-from-cart'),
    
    # Mettre à jour la quantité d'un produit
    path('update/<int:product_id>/', views.update_cart, name='update-cart'),
    
    # Vider complètement le panier
    path('clear/', views.clear_cart, name='clear-cart'),
    
    # Récupérer le résumé du panier (AJAX)
    path('summary/', views.cart_summary_view, name='cart-summary'),

]

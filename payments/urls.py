from django.urls import path
from . import views
from django.conf import settings
from django.http import JsonResponse

urlpatterns = [
    # Page UI
    path('panier/', views.cart_page, name='cart-page'),
    path('checkout/', views.checkout_page, name='checkout-page'),

]

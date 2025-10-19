from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_to_cart, name='cart-add'),
    path('summary/', views.cart_summary, name='cart-summary'),
]

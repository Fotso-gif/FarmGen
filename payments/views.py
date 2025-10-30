import json
import logging
from cart.views import  get_cart_data
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.shortcuts import render, redirect

from .models import Order  # new import

logger = logging.getLogger(__name__)

# Session-cart helpers
def _get_cart(session):
    return session.get('cart', {})

def _save_cart(session, cart):
    session['cart'] = cart
    session.modified = True

#Pages Cart/Checkout
def cart_page(request):
    cart, cart_count, cart_total = get_cart_data(request.session)
    
    # Calcul des taxes (10% comme indiqué dans votre template)
    tax = cart_total * 0.10
    total_with_tax = cart_total + tax
    
    context = {
        'cart': cart,
        'cart_count': cart_count,
        'cart_total': cart_total,
        'tax': tax,
        'total_with_tax': total_with_tax,
    }
    return render(request, 'payments/cart.html', context)

def checkout_page(request):
    """Page de checkout - à implémenter selon vos besoins"""
    cart, cart_count, cart_total = get_cart_data(request.session)
    
    if cart_count == 0:
        return redirect('cart-page')
    
    tax = cart_total * 0.10
    total_with_tax = cart_total + tax
    
    context = {
        'cart': cart,
        'cart_count': cart_count,
        'cart_total': cart_total,
        'tax': tax,
        'total_with_tax': total_with_tax,
    }
    return render(request, 'payments/checkout.html', context)

import json
import logging
from cart.utils.cart_utils import get_cart, cart_count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.shortcuts import render

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
    cart = get_cart(request.session)
    total = sum(float(item['amount']) for item in cart.values())
    context = {
        'cart': cart,
        'total': total,
        'cart_count': cart_count(request.session),
    }
    return render(request, 'payments/cart.html',context)

def checkout_page(request):
    cart = get_cart(request.session)
    total = sum(float(item['amount']) for item in cart.values())
    context = {
        'cart': cart,
        'total': total,
        'cart_count': cart_count(request.session),
    }
    return render(request, 'payments/checkout.html',context)


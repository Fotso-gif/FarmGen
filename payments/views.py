import json
import logging
from django.http import JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView

from .serializers import CartItemSerializer, CheckoutSerializer
from . import services
from .models import Order  # new import

logger = logging.getLogger(__name__)

# Session-cart helpers
def _get_cart(session):
    return session.get('cart', {})

def _save_cart(session, cart):
    session['cart'] = cart
    session.modified = True

# new helper: compute totals
def _cart_summary(cart):
    total = 0
    item_count = 0
    for item in cart.values():
        qty = int(item.get('quantity', 0))
        price = int(item.get('price', 0))
        total += price * qty
        item_count += qty
    return {'total_cents': total, 'item_count': item_count}

class CartAPIView(APIView):
    """
    GET: list cart with totals
    POST: add/update item (accepts JSON or form-encoded)
    DELETE: remove item (expects product_id in body)
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        cart = _get_cart(request.session)
        summary = _cart_summary(cart)
        return Response({'cart': cart, **summary})

    def post(self, request):
        # Accept form-encoded from HTMX or JSON
        data = request.data.copy()
        # ensure quantity default
        if 'quantity' not in data or data.get('quantity') in (None, ''):
            data['quantity'] = 1
        serializer = CartItemSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = _get_cart(request.session)
        pid = data['product_id']
        existing_qty = cart.get(pid, {}).get('quantity', 0)
        cart[pid] = {
            'name': data['name'],
            'price': data['price'],
            'quantity': existing_qty + data['quantity'],
        }
        _save_cart(request.session, cart)
        summary = _cart_summary(cart)
        return Response({'cart': cart, **summary}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        pid = request.data.get('product_id')
        cart = _get_cart(request.session)
        if pid and pid in cart:
            del cart[pid]
            _save_cart(request.session, cart)
            summary = _cart_summary(cart)
            return Response({'cart': cart, **summary})
        return Response({'detail': 'product_id not found'}, status=status.HTTP_400_BAD_REQUEST)

class CheckoutAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        amount = data.get('amount')
        if amount is None:
            cart = _get_cart(request.session)
            total = 0
            for item in cart.values():
                total += int(item['price']) * int(item['quantity'])
            amount = total

        if amount <= 0:
            return Response({'detail': 'amount must be > 0'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create an Order record first (snapshot of cart)
            metadata = {'source': 'cart'}
            order = services.create_order_from_session(request.session, metadata=metadata)
            # include order id in payment metadata so webhook can relate
            pi_metadata = {'order_id': str(order.id)}
            intent = services.create_stripe_payment_intent(amount_cents=amount, currency=data.get('currency', 'usd'), metadata=pi_metadata)
            # Save payment_intent_id on order for easier lookup
            order.payment_intent_id = intent.id
            order.save()
            return Response({'client_secret': intent.client_secret, 'payment_intent': intent.id, 'order_id': str(order.id)})
        except Exception as e:
            logger.exception("Error creating payment intent or order")
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StripePublishableKeyAPIView(APIView):
    """
    Expose the Stripe publishable key for the frontend.
    """
    permission_classes = (AllowAny,)
    def get(self, request):
        return Response({'publishableKey': settings.STRIPE_PUBLISHABLE_KEY or ''})

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookAPIView(APIView):
    """
    Receives Stripe webhooks. Verifies signature using STRIPE_WEBHOOK_SECRET.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        try:
            event = services.verify_stripe_event(payload, sig_header)
        except Exception as e:
            logger.warning("Stripe webhook signature verification failed: %s", e)
            return HttpResponse(status=400)

        event_type = event.get('type') if isinstance(event, dict) else getattr(event, 'type', None)
        data_object = None
        if isinstance(event, dict):
            data_object = event.get('data', {}).get('object', {})
        else:
            data_object = getattr(event, 'data', {}).get('object', None)

        if event_type == 'payment_intent.succeeded':
            payment_intent_id = data_object.get('id') if isinstance(data_object, dict) else getattr(data_object, 'id', None)
            metadata = data_object.get('metadata', {}) if isinstance(data_object, dict) else getattr(data_object, 'metadata', {})
            order_id = metadata.get('order_id')
            try:
                services.fulfill_order(order_id=order_id, payment_intent_id=payment_intent_id, event=event)
                logger.info("Payment succeeded for intent %s, order %s", payment_intent_id, order_id)
            except Exception as e:
                logger.exception("Error fulfilling order %s: %s", order_id, e)
                return HttpResponse(status=500)
            return HttpResponse(status=200)

        # handle other event types as needed
        return HttpResponse(status=200)

class CartPageView(TemplateView):
    """
    Renders the client-side cart page (template/cart.html).
    """
    template_name = "cart.html"

class CheckoutPageView(TemplateView):
    """
    Renders the checkout page (template/checkout.html).
    Injecte la clé publishable Stripe dans le contexte pour le JS.
    """
    template_name = "checkout.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stripe_publishable_key'] = settings.STRIPE_PUBLISHABLE_KEY or ''
        return ctx

import json
import logging
import requests
import stripe
from django.conf import settings
from django.db import transaction

from .models import Order, Product

logger = logging.getLogger(__name__)

# Initialize Stripe with secret key from settings
stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_payment_intent(amount_cents, currency='usd', metadata=None):
    """
    Create a Stripe PaymentIntent (amount in cents).
    Uses automatic payment methods to allow card wallets, etc.
    """
    metadata = metadata or {}
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        metadata=metadata,
        automatic_payment_methods={'enabled': True},
    )
    return intent

def verify_stripe_event(payload, sig_header):
    """
    Verify Stripe webhook event. Raises stripe.error.SignatureVerificationError on failure.
    Returns the event object (dict or Stripe Event object).
    """
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    if webhook_secret:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=webhook_secret)
    else:
        # insecure fallback: attempt to parse JSON (NOT recommended in production)
        event = json.loads(payload)
    return event

# --- Order & inventory helpers ---

def create_order_from_session(session, metadata=None):
    """
    Create an Order instance from the session 'cart' snapshot.
    Returns Order instance.
    """
    cart = session.get('cart', {})
    items = []
    total = 0
    for pid, item in cart.items():
        qty = int(item.get('quantity', 0))
        price = int(item.get('price', 0))
        items.append({
            'product_id': pid,
            'name': item.get('name'),
            'price': price,
            'quantity': qty
        })
        total += price * qty
    order = Order.objects.create(
        total_amount_cents=total,
        items=items,
        metadata=metadata or {}
    )
    # Optionally clear session cart or keep it until fulfillment
    # session.pop('cart', None); session.modified = True
    return order

def fulfill_order(order_id=None, payment_intent_id=None, event=None):
    """
    Mark order as paid and decrement product stock.
    If stock insufficient, mark order as failed and raise.
    """
    try:
        if order_id:
            order = Order.objects.get(pk=order_id)
        elif payment_intent_id:
            order = Order.objects.filter(payment_intent_id=payment_intent_id).first()
            if not order:
                raise Order.DoesNotExist("Order not found for payment_intent")
        else:
            raise ValueError("order_id or payment_intent_id required to fulfill order")
    except Order.DoesNotExist:
        logger.warning("Order not found: order_id=%s payment_intent=%s", order_id, payment_intent_id)
        return None

    if order.status == Order.STATUS_PAID:
        logger.info("Order already paid: %s", order.id)
        return order

    # Use DB transaction to decrement stock safely
    with transaction.atomic():
        # Check and decrement stock for each item
        for it in order.items:
            pid = it.get('product_id')
            qty = int(it.get('quantity', 0))
            product = Product.objects.select_for_update().filter(product_id=pid).first()
            if not product:
                logger.warning("Product not found while fulfilling order %s: %s", order.id, pid)
                # Decide policy: fail order or continue. Here we fail.
                order.status = Order.STATUS_FAILED
                order.save()
                raise ValueError(f"Product not found: {pid}")
            if product.stock < qty:
                logger.warning("Insufficient stock for product %s (need %s, have %s)", pid, qty, product.stock)
                order.status = Order.STATUS_FAILED
                order.save()
                raise ValueError(f"Insufficient stock for product {pid}")
            product.stock -= qty
            product.save()
        # All stock decremented successfully, mark order paid
        order.status = Order.STATUS_PAID
        if payment_intent_id:
            order.payment_intent_id = payment_intent_id
        order.save()

    # Here you can send confirmations, reduce reserved inventory elsewhere, notify user, etc.
    logger.info("Order fulfilled: %s", order.id)
    return order

# --- Mobile Money integrations (examples) ---

def _mtn_get_oauth_token(provider_cfg):
    """
    MTN example OAuth client credentials flow.
    provider_cfg must include CLIENT_ID, CLIENT_SECRET, BASE_URL
    """
    token_url = provider_cfg.get('BASE_URL', '').rstrip('/') + '/oauth/token'
    client_id = provider_cfg.get('CLIENT_ID')
    client_secret = provider_cfg.get('CLIENT_SECRET')
    if not (token_url and client_id and client_secret):
        raise ValueError("MTN config incomplete")
    resp = requests.post(token_url, data={'grant_type': 'client_credentials'}, auth=(client_id, client_secret), timeout=10)
    resp.raise_for_status()
    return resp.json().get('access_token')

def mtn_initiate_collection(amount_cents, msisdn, external_id, provider_cfg=None):
    """
    Initiate an MTN collection/charge request.
    - amount_cents: integer
    - msisdn: phone number in international format
    - external_id: client-side reference id
    """
    cfg = provider_cfg or settings.MOMO.get('MTN', {})
    base = cfg.get('BASE_URL')
    if not base:
        raise ValueError("MTN BASE_URL missing")
    token = _mtn_get_oauth_token(cfg)
    url = base.rstrip('/') + '/collection/v1_0/requesttopay'  # example path
    headers = {
        'Authorization': f'Bearer {token}',
        'Ocp-Apim-Subscription-Key': cfg.get('API_KEY', ''),
        'X-Reference-Id': external_id,
        'Content-Type': 'application/json'
    }
    body = {
        "amount": str(amount_cents / 100.0),
        "currency": "EUR",  # adapt to your currency or provider expectations
        "externalId": external_id,
        "payer": {"partyIdType": "MSISDN", "partyId": msisdn},
        "payerMessage": "Payment request",
        "payeeNote": "Payment for order"
    }
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()

def orange_initiate_payment(amount_cents, msisdn, provider_cfg=None):
    """
    Orange Money example (illustrative). Replace with actual Orange API paths and auth.
    """
    cfg = provider_cfg or settings.MOMO.get('ORANGE', {})
    base = cfg.get('BASE_URL')
    if not base:
        raise ValueError("ORANGE BASE_URL missing")
    # Many Orange APIs also require OAuth token exchange; implement similarly to MTN
    token = cfg.get('API_KEY')  # or perform token exchange
    url = base.rstrip('/') + '/payment/v1/charge'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    body = {
        "amount": str(amount_cents / 100.0),
        "currency": "EUR",
        "msisdn": msisdn,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()

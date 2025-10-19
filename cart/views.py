from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
from . import cart as cart_utils

import json

@csrf_exempt
@require_POST
def add_to_cart(request):
    """
    Expects JSON: { product_id, name, price (cents), quantity }
    If product_id exists in project Product model, we prefer its name/price.
    Returns { success: true, total_cents, total_display, item_count }.
    """
    try:
        data = json.loads(request.body.decode() or '{}')
    except Exception:
        data = {}
    product_id = data.get('product_id')
    name = data.get('name') or 'Produit'
    price = data.get('price')  # expected in cents
    quantity = data.get('quantity', 1) or 1

    # Try to resolve product info from existing Product model (Marketplace or shop)
    product_model = None
    Product = None
    try:
        # prefer Marketplace.Product if present
        Product = apps.get_model('Marketplace', 'Product')
    except Exception:
        try:
            Product = apps.get_model('shop', 'Product')
        except Exception:
            Product = None
    if Product and product_id:
        try:
            prod = Product.objects.filter(pk=product_id).first()
            if prod:
                name = getattr(prod, 'name', name)
                # try to get price in cents from DecimalField price
                price = int(getattr(prod, 'price', 0) * 100)
        except Exception:
            pass

    # Fallback price required
    if price is None:
        return JsonResponse({'success': False, 'error': 'price required'}, status=400)

    cart = cart_utils.add_item(request.session, product_id or name, name, int(price), int(quantity))
    summary = cart_utils.cart_summary(cart)
    total_cents = summary['total_cents']
    total_display = f"{total_cents/100:.2f} €"
    return JsonResponse({'success': True, 'total_cents': total_cents, 'total_display': total_display, 'item_count': summary['item_count']})

@require_GET
def cart_summary(request):
    cart = cart_utils.get_cart(request.session)
    summary = cart_utils.cart_summary(cart)
    return JsonResponse({'cart': cart, **summary})

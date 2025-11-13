from decimal import Decimal
from django.shortcuts import get_object_or_404
from Marketplace.models import Product, ProductImage

def get_cart(session):
    return session.get('cart', {})

def save_cart(session, cart):
    session['cart'] = cart
    session.modified = True

def add_to_cart(request, product_id, quantity=1):
    cart = get_cart(request.session)
    product = get_object_or_404(Product, id=product_id)
    image = product.images.first().image.url if product.images.exists() else ''
    key = str(product.id)
    price = Decimal(product.price)
    
    if key in cart:
        cart[key]['quantity'] += quantity
        cart[key]['amount'] = str(Decimal(cart[key]['quantity']) * price)
    else:
        cart[key] = {
            'shop_id': product.category.shop.id if hasattr(product.category, 'shop') else None,
            'name': product.name,
            'image': image,
            'description': product.description[:100],
            'slug': product.name.replace(" ", "-").lower(),
            'price': str(price),
            'quantity': quantity,
            'amount': str(price * quantity)
        }
    
    save_cart(request.session, cart)
    return cart

def remove_from_cart(request, product_id):
    cart = get_cart(request.session)
    key = str(product_id)
    if key in cart:
        del cart[key]
        save_cart(request.session, cart)
    return cart

def update_cart(request, product_id, quantity):
    cart = get_cart(request.session)
    key = str(product_id)
    if key in cart:
        price = Decimal(cart[key]['price'])
        cart[key]['quantity'] = int(quantity)
        cart[key]['amount'] = str(price * int(quantity))
        save_cart(request.session, cart)
    return cart

def clear_cart(request):
    request.session['cart'] = {}
    request.session.modified = True

def cart_count(session):
    cart = get_cart(session)
    return sum(item['quantity'] for item in cart.values())

"""
Session-based cart helpers.
Store cart in session as dict: { product_id: {name, price, quantity} }
price is in cents (int).
"""
from django.utils.functional import cached_property

CART_SESSION_KEY = 'cart'

def get_cart(session):
    return session.get(CART_SESSION_KEY, {})

def save_cart(session, cart):
    session[CART_SESSION_KEY] = cart
    session.modified = True

def add_item(session, product_id, name, price_cents, quantity=1):
    cart = get_cart(session)
    pid = str(product_id)
    existing = cart.get(pid)
    if existing:
        existing_qty = int(existing.get('quantity', 0))
        cart[pid]['quantity'] = existing_qty + int(quantity)
    else:
        cart[pid] = {'name': name, 'price': int(price_cents), 'quantity': int(quantity)}
    save_cart(session, cart)
    return cart

def remove_item(session, product_id):
    cart = get_cart(session)
    pid = str(product_id)
    if pid in cart:
        del cart[pid]
        save_cart(session, cart)
    return cart

def clear_cart(session):
    if CART_SESSION_KEY in session:
        del session[CART_SESSION_KEY]
        session.modified = True

def cart_summary(cart):
    total = 0
    count = 0
    for it in cart.values():
        qty = int(it.get('quantity', 0))
        price = int(it.get('price', 0))
        total += price * qty
        count += qty
    return {'total_cents': total, 'item_count': count}

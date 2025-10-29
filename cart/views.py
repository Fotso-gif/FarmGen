from django.http import JsonResponse
from .utils.cart_utils import add_to_cart, remove_from_cart, update_cart, clear_cart, cart_count

def add_to_cart_view(request, product_id):
    quantity = int(request.POST.get('quantity', 1))
    cart = add_to_cart(request, product_id, quantity)
    return JsonResponse({'cart_count': cart_count(request.session), 'cart': cart})

def remove_cart_view(request, product_id):
    cart = remove_from_cart(request, product_id)
    return JsonResponse({'cart_count': cart_count(request.session), 'cart': cart})

def update_cart_view(request, product_id):
    quantity = int(request.POST.get('quantity', 1))
    cart = update_cart(request, product_id, quantity)
    return JsonResponse({'cart_count': cart_count(request.session), 'cart': cart})

def clear_cart_view(request):
    clear_cart(request)
    return JsonResponse({'cart_count': 0, 'cart': {}})

def cart_summary_view(request):
    cart = request.session.get('cart', {})
    return JsonResponse({'cart': cart, 'cart_count': cart_count(request.session)})

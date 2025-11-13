from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from Marketplace.models import Product
import json

def get_cart_data(session):
    """Helper function to get cart data with count and total"""
    cart = session.get('cart', {})
    cart_count = sum(item['quantity'] for item in cart.values())
    cart_total = sum(item['price'] * item['quantity'] for item in cart.values())
    return cart, cart_count, cart_total

@require_http_methods(["POST"])
def add_to_cart(request, product_id):
    try:
        cart = request.session.get('cart', {})
        product_id_str = str(product_id)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            return JsonResponse({'error': 'La quantité doit être positive'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        
        if product_id_str in cart:
            cart[product_id_str]['quantity'] += quantity
        else:
            cart[product_id_str] = {
                'name': product.name,
                'shop_id': product.category.shop.id,
                'slug': f'{product.name}-farm-{product.id}',
                'price': float(product.price),
                'quantity': quantity,
                'image': product.images.first().image.url if product.images.exists() else '',
                'description': getattr(product, 'description', '')[:100]  # Truncate long descriptions
            }
        
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_data, cart_count, cart_total = get_cart_data(request.session)
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'cart_total': cart_total,
            'cart': cart_data
        })
        
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Quantité invalide'}, status=400)
    except Exception as e:
        import traceback
        print("❌ ERREUR PANIER :", traceback.format_exc())
        return JsonResponse({'error': f'Erreur lors de l\'ajout au panier : {str(e)}'}, status=500)
@require_http_methods(["POST"])
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        request.session.modified = True
    
    cart_data, cart_count, cart_total = get_cart_data(request.session)
    
    return JsonResponse({
        'success': True,
        'cart_count': cart_count,
        'cart_total': cart_total,
        'cart': cart_data
    })

@require_http_methods(["POST"])
def update_cart(request, product_id):
    try:
        cart = request.session.get('cart', {})
        product_id_str = str(product_id)
        quantity = int(request.POST.get('quantity', 1))
        
        if product_id_str in cart:
            if quantity <= 0:
                del cart[product_id_str]
            else:
                cart[product_id_str]['quantity'] = quantity
            
            request.session['cart'] = cart
            request.session.modified = True
        
        cart_data, cart_count, cart_total = get_cart_data(request.session)
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'cart_total': cart_total,
            'cart': cart_data
        })
        
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Quantité invalide'}, status=400)

@require_http_methods(["POST"])
def clear_cart(request):
    request.session['cart'] = {}
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'cart_count': 0,
        'cart_total': 0,
        'cart': {}
    })

@require_http_methods(["GET"])
def cart_summary_view(request):
    cart_data, cart_count, cart_total = get_cart_data(request.session)
    
    return JsonResponse({
        'cart': cart_data,
        'cart_count': cart_count,
        'cart_total': cart_total
    })
import json
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Shop, Product, Favorite, Category, ProductImage

# Create your views here.


    
def shop(request, shop_id):
    shop = Shop.objects.get(id = shop_id)
    produits = Product.objects.filter(category__shop=shop)
    return render(request, 'marketplace/e_shop.html', {'produits': produits, 'shop': shop})    

@login_required
@require_POST
@csrf_exempt
def toggle_favorite(request, shop_id):
    try:
        shop = Shop.objects.get(id=shop_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            shop=shop
        )
        
        if not created:
            # Si déjà favori, on supprime
            favorite.delete()
            return JsonResponse({
                'status': 'removed',
                'message': 'Boutique retirée des favoris',
                'is_favorite': False
            })
        
        return JsonResponse({
            'status': 'added',
            'message': 'Boutique ajoutée aux favoris',
            'is_favorite': True
        })
        
    except Shop.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Boutique non trouvée'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_favorites_status(request):
    """Récupère le statut favori des boutiques pour l'utilisateur connecté"""
    favorite_shop_ids = Favorite.objects.filter(
        user=request.user
    ).values_list('shop_id', flat=True)
    
    return JsonResponse({
        'favorites': list(favorite_shop_ids)
})

@login_required
def shop_dashboard(request):
    """Tableau de bord de la boutique"""
    shop = get_object_or_404(Shop, user=request.user)
    
    # Statistiques
    total_products = Product.objects.filter(category__shop=shop).count()
    total_orders =  0 # À adapter selon votre modèle Order
    total_views = 0  # À implémenter avec un modèle de vue
    low_stock_products = Product.objects.filter(category__shop=shop, quantity__lte=5).count()
    
    # Données pour les tableaux
    # products = Product.objects.filter(category__shop=shop).select_related('category').prefetch_related('images')
    #categories = Category.objects.filter(shop=shop).annotate(product_count=Count('products'))
    
    # Analytics
    # popular_products = products.order_by('-views_count')[:5]  # À adapter
    #category_stats = categories
    
    context = {
        'shop': shop,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_views': total_views,
        'low_stock_products': low_stock_products,
        # 'products': products,
        # 'categories': categories,
        # 'popular_products': popular_products,
        # 'category_stats': category_stats,
    }
    
    return render(request, 'marketplace/index.html', context)

@login_required
@csrf_exempt
def create_update_product(request):
    """Créer ou mettre à jour un produit"""
    if request.method == 'POST':
        shop = get_object_or_404(Shop, user=request.user)
        product_id = request.POST.get('product_id')
        
        try:
            if product_id:
                # Mise à jour
                product = get_object_or_404(Product, id=product_id, category__shop=shop)
            else:
                # Création
                product = Product()
            
            product.name = request.POST.get('name')
            product.category = get_object_or_404(Category, id=request.POST.get('category'), shop=shop)
            product.price = request.POST.get('price')
            product.quantity = request.POST.get('quantity')
            product.description = request.POST.get('description')
            product.save()
            
            # Gestion des images
            images = request.FILES.getlist('images')
            for image in images:
                ProductImage.objects.create(product=product, image=image)
            
            return JsonResponse({'success': True, 'message': 'Produit enregistré avec succès'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@login_required
@csrf_exempt
def create_update_category(request):
    """Créer ou mettre à jour une catégorie"""
    if request.method == 'POST':
        shop = get_object_or_404(Shop, user=request.user)
        category_id = request.POST.get('category_id')
        
        try:
            if category_id:
                # Mise à jour
                category = get_object_or_404(Category, id=category_id, shop=shop)
            else:
                # Création
                category = Category(shop=shop)
            
            category.name = request.POST.get('name')
            category.description = request.POST.get('description')
            category.save()
            
            return JsonResponse({'success': True, 'message': 'Catégorie enregistrée avec succès'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@login_required
def get_product(request, product_id):
    """Récupérer un produit pour édition"""
    shop = get_object_or_404(Shop, user=request.user)
    product = get_object_or_404(Product, id=product_id, category__shop=shop)
    
    return JsonResponse({
        'id': product.id,
        'name': product.name,
        'category_id': product.category.id,
        'price': float(product.price),
        'quantity': product.quantity,
        'description': product.description,
    })

@login_required
def get_category(request, category_id):
    """Récupérer une catégorie pour édition"""
    shop = get_object_or_404(Shop, user=request.user)
    category = get_object_or_404(Category, id=category_id, shop=shop)
    
    return JsonResponse({
        'id': category.id,
        'name': category.name,
        'description': category.description,
    })

@login_required
@csrf_exempt
def delete_product(request, product_id):
    """Supprimer un produit"""
    if request.method == 'POST':
        shop = get_object_or_404(Shop, user=request.user)
        product = get_object_or_404(Product, id=product_id, category__shop=shop)
        product.delete()
        
        return JsonResponse({'success': True, 'message': 'Produit supprimé avec succès'})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@login_required
@csrf_exempt
def delete_category(request, category_id):
    """Supprimer une catégorie"""
    if request.method == 'POST':
        shop = get_object_or_404(Shop, user=request.user)
        category = get_object_or_404(Category, id=category_id, shop=shop)
        
        # Vérifier s'il y a des produits dans cette catégorie
        if category.products.exists():
            return JsonResponse({
                'success': False, 
                'message': 'Impossible de supprimer une catégorie contenant des produits'
            })
        
        category.delete()
        return JsonResponse({'success': True, 'message': 'Catégorie supprimée avec succès'})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@login_required
@csrf_exempt
def duplicate_product(request, product_id):
    """Dupliquer un produit"""
    if request.method == 'POST':
        shop = get_object_or_404(Shop, user=request.user)
        original_product = get_object_or_404(Product, id=product_id, category__shop=shop)
        
        try:
            # Créer une copie du produit
            new_product = Product.objects.create(
                name=f"{original_product.name} (Copie)",
                category=original_product.category,
                price=original_product.price,
                quantity=original_product.quantity,
                description=original_product.description,
            )
            
            # Copier les images
            for image in original_product.images.all():
                ProductImage.objects.create(product=new_product, image=image.image)
            
            return JsonResponse({'success': True, 'message': 'Produit dupliqué avec succès'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@login_required
def update_shop(request):
    """Mettre à jour les informations de la boutique"""
    if request.method == 'POST':
        shop = get_object_or_404(Shop, user=request.user)
        
        try:
            shop.title = request.POST.get('title')
            shop.description = request.POST.get('description')
            shop.localisation = request.POST.get('localisation')
            shop.type_shop = request.POST.get('type_shop')
            
            # Gestion de l'image de couverture
            if 'couverture' in request.FILES:
                shop.couverture = request.FILES['couverture']
            
            shop.save()
            
            return JsonResponse({'success': True, 'message': 'Boutique mise à jour avec succès'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})  

@login_required
def order_history(request):
    """Historique des commandes avec filtres par rôle"""
    # Récupérer les filtres depuis l'URL
    # status_filter = request.GET.getlist('status')
    # payment_filter = request.GET.get('payment')
    # date_from = request.GET.get('date_from')
    # date_to = request.GET.get('date_to')
    
    # Base queryset selon le rôle
    if request.user.is_superuser:
        # Admin: voir toutes les commandes
        # orders = Order.objects.all().select_related('user', 'shop').prefetch_related('items__product')
        orders = None
        all_shops = Shop.objects.all()
        # customers = User.objects.filter(orders__isnull=False).distinct()
        
    elif hasattr(request.user, 'shop'):
        # Vendeur: voir les commandes de sa boutique
        shop = request.user.shop
        # orders = Order.objects.filter(shop=shop).select_related('user').prefetch_related('items__product')
        # customers = User.objects.filter(orders__shop=shop).distinct()
        orders=None
        all_shops = None
        
    else:
        # Client: voir ses propres commandes
        # orders = Order.objects.filter(user=request.user).select_related('shop').prefetch_related('items__product')
        orders = None
        customers = None
        all_shops = None
    
    # Appliquer les filtres
    # if status_filter:
    #     orders = orders.filter(status__in=status_filter) or None
    
    # if payment_filter:
    #     orders = orders.filter(payment_status=payment_filter) or None
    
    # if date_from:
    #     orders = orders.filter(created_at__date__gte=date_from) or None
    
    # if date_to:
    #     orders = orders.filter(created_at__date__lte=date_to) or None
    
    # Statistiques
    # total_orders = orders.count() or None
    # pending_orders = orders.filter(status='pending').count() or None
    # delivered_orders = orders.filter(status='delivered').count() or None
    # cancelled_orders = orders.filter(status='cancelled').count() or None
    
    # Pagination
    # paginator = Paginator(orders, 10)
    # page_number = request.GET.get('page')
    # page_orders = paginator.get_page(page_number)
    
    context = {
         'orders': None,
        'total_orders': None,
        'pending_orders': None,
        'delivered_orders': None,
        'cancelled_orders': None,
        'all_shops': all_shops,
        # 'customers': None,
    }
    
    return render(request, 'marketplace/historiqueCommande.html', context)

@login_required
def update_order_status(request, order_id):
    """Mettre à jour le statut d'une commande"""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        
        # Vérifier les permissions
        if not (request.user.is_superuser or 
                (hasattr(request.user, 'shop') and order.shop == request.user.shop) or
                (order.user == request.user and request.POST.get('status') == 'cancelled')):
            return JsonResponse({'success': False, 'message': 'Permission denied'})
        
        new_status = request.POST.get('status')
        if new_status in dict(Order.ORDER_STATUS):
            order.status = new_status
            order.save()
            return JsonResponse({'success': True, 'message': 'Statut mis à jour'})
        
        return JsonResponse({'success': False, 'message': 'Statut invalide'})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@login_required
def export_orders(request, format):
    """Exporter les commandes en CSV ou PDF"""
    # Implémentation de l'export selon le format
    # CSV: utiliser csv module
    # PDF: utiliser reportlab ou weasyprint
    pass
"""from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Category, Product, ProductImage
from .serializers import CategorySerializer, ProductSerializer, ProductCreateUpdateSerializer, ProductImageSerializer
from .filters import ProductFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from django.db.models import Sum, F
from django.utils import timezone

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "id"

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.prefetch_related("images").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "quantity", "expiry_date"]
    def get_serializer_class(self):
        if self.action in ["create","update","partial_update"]: return ProductCreateUpdateSerializer
        return ProductSerializer
    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        threshold = int(request.query_params.get("threshold", Product.LOW_STOCK_THRESHOLD))
        items = Product.objects.filter(quantity__lt=threshold)
        serializer = ProductSerializer(items, many=True, context={"request": request})
        return Response(serializer.data)
    @action(detail=False, methods=["get"])
    def expired(self, request):
        today = timezone.localdate()
        items = Product.objects.filter(expiry_date__lt=today)
        serializer = ProductSerializer(items, many=True, context={"request": request})
        return Response(serializer.data)
    @action(detail=False, methods=["get"])
    def report(self, request):
        total_products = Product.objects.count()
        total_value = Product.objects.aggregate(total_value=Sum(F("price") * F("quantity")))["total_value"] or 0
        most_expensive = Product.objects.order_by("-price").first()
        cheapest = Product.objects.order_by("price").first()
        def serialize_simple(p): return {"id": p.id, "name": p.name, "price": str(p.price), "quantity": p.quantity} if p else None
        return Response({"total_products": total_products,"total_stock_value": str(total_value),"most_expensive": serialize_simple(most_expensive),"cheapest": serialize_simple(cheapest)})
class ProductImageViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = ProductImage.objects.select_related("product").all()
    serializer_class = ProductImageSerializer
"""
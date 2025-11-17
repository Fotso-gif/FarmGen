import json
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from account.models import User
from .models import Shop, Product, Favorite, Category, ProductImage
from payments.models import Order, MethodPaid
# Create your views here.
from django.utils import timezone
from datetime import datetime, timedelta


    
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
    try:
        shop = Shop.objects.get(user=request.user)
        
        # Statistiques
        total_products = Product.objects.filter(category__shop=shop).count()
        total_orders = 0  # À adapter selon votre modèle Order
        total_views = 0   # À implémenter avec un modèle de vue
        low_stock_products = Product.objects.filter(
            category__shop=shop, 
            quantity__lte=5
        ).count()
        
        # Données pour les tableaux
        products = Product.objects.filter(
            category__shop=shop
        ).select_related('category').prefetch_related('images')
        
        categories = Category.objects.filter(shop=shop).annotate(
            product_count=Count('products')
        )
        
        context = {
            'shop': shop,
            'total_products': total_products,
            'total_orders': total_orders,
            'total_views': total_views,
            'low_stock_products': low_stock_products,
            'products': products,
            'categories': categories,
        }
        
    except Shop.DoesNotExist:
        # Aucune boutique trouvée pour cet utilisateur
        context = {
            'shop': None
        }
    
    return render(request, 'marketplace/index.html', context)

@login_required
def create_shop(request):
    """Création d'une nouvelle boutique"""
    if request.method == 'POST':
        try:
            # Vérifier si l'utilisateur a déjà une boutique
            if Shop.objects.filter(user=request.user).exists():
                messages.error(request, "Vous avez déjà une boutique.")
                return redirect('marketplace_list')
            
            shop = Shop.objects.create(
                user=request.user,
                title=request.POST['title'],
                localisation=request.POST['localisation'],
                type_shop=request.POST['type_shop'],
                description=request.POST.get('description', ''),
                note=0.0  # Note par défaut
            )
            
            # Gérer l'image de couverture
            if 'couverture' in request.FILES:
                shop.couverture = request.FILES['couverture']
                shop.save()
            
            # Générer le slug automatiquement
            shop.slug = slugify(shop.title)
            shop.save()
            
            messages.success(request, "Boutique créée avec succès!")
            return redirect('marketplace_list')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    return redirect('marketplace_list')

@login_required
def update_shop(request):
    """Mise à jour des informations de la boutique"""
    if request.method == 'POST':
        try:
            shop = get_object_or_404(Shop, user=request.user)
            
            shop.title = request.POST['title']
            shop.localisation = request.POST['localisation']
            shop.type_shop = request.POST.get('type_shop', '')
            shop.description = request.POST.get('description', '')
            
            # Gérer l'image de couverture
            if 'couverture' in request.FILES:
                shop.couverture = request.FILES['couverture']
            
            shop.save()
            
            messages.success(request, "Boutique mise à jour avec succès!")
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return redirect('marketplace_list')

@login_required
def create_category(request):
    """Création d'une nouvelle catégorie"""
    if request.method == 'POST':
        try:
            shop = get_object_or_404(Shop, user=request.user)
            
            category = Category.objects.create(
                shop=shop,
                name=request.POST['name'],
                description=request.POST.get('description', '')
            )
            
            # Générer le slug automatiquement
            from django.utils.text import slugify
            category.slug = slugify(category.name)
            category.save()
            
            messages.success(request, "Catégorie créée avec succès!")
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    return redirect('marketplace_list')

@login_required
def create_product(request):
    """Création d'un nouveau produit"""
    if request.method == 'POST':
        try:
            shop = get_object_or_404(Shop, user=request.user)
            category = get_object_or_404(Category, id=request.POST['category'], shop=shop)
            
            product = Product.objects.create(
                name=request.POST['name'],
                category=category,
                price=request.POST['price'],
                quantity=request.POST['quantity'],
                description=request.POST.get('description', ''),
                expiry_date=request.POST.get('expiry_date') or None
            )
            
            # Gérer les images
            for image_file in request.FILES.getlist('images'):
                ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    alt_text=product.name
                )
            
            messages.success(request, "Produit créé avec succès!")
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    return redirect('marketplace_list')

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
    """Affiche l'historique des commandes avec filtres selon le rôle utilisateur."""

    # 🔹 Récupération des filtres
    status_filter = request.GET.getlist('status')
    payment_filter = request.GET.get('payment')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    shop_filter = request.GET.get('shop')
    customer_filter = request.GET.get('customer')

    # 🔹 Base queryset selon le rôle
    if request.user.is_superuser:
        orders = Order.objects.all().order_by('-created_at')
        all_shops = Shop.objects.all()
        customers = User.objects.filter(
            Q(orders__isnull=False) |
            Q(first_name__isnull=False)
        ).distinct()

    elif hasattr(request.user, 'shop'):
        # Vendeur → uniquement commandes de sa boutique
        shop = request.user.shop
        orders = Order.objects.filter(shop_id=shop.id).order_by('-created_at')
        all_shops = None
        customers = User.objects.filter(
            Q(orders__shop_id=shop.id) |
            Q(first_name__isnull=False)
        ).distinct()

    else:
        # Client → ses commandes seulement
        orders = Order.objects.filter(
            Q(customer_email=request.user.email) |
            Q(customer_phone=request.user.phone)
        ).order_by('-created_at')
        all_shops = None
        customers = None

    # 🔹 Application des filtres dynamiques
    if status_filter:
        orders = orders.filter(status__in=status_filter)

    if payment_filter:
        if payment_filter == 'paid':
            orders = orders.filter(status__in=[
                Order.STATUS_PAID, Order.STATUS_PAYMENT_VERIFIED
            ])
        elif payment_filter == 'pending':
            orders = orders.filter(status__in=[
                Order.STATUS_PENDING, Order.STATUS_WAITING_PAYMENT
            ])
        elif payment_filter == 'failed':
            orders = orders.filter(status__in=[
                Order.STATUS_FAILED, Order.STATUS_REFUNDED
            ])

    # 🔹 Filtres par dates
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            orders = orders.filter(created_at__lte=date_to_obj)
        except ValueError:
            pass

    # 🔹 Filtre boutique (admin uniquement)
    if shop_filter and request.user.is_superuser:
        orders = orders.filter(shop_id=shop_filter)

    # 🔹 Filtre client (admin uniquement)
    if customer_filter and request.user.is_superuser:
        orders = orders.filter(
            Q(customer_email__icontains=customer_filter) |
            Q(customer_first_name__icontains=customer_filter) |
            Q(customer_last_name__icontains=customer_filter)
        )

    # 🔹 Statistiques globales
    if request.user.is_superuser:
        base_orders = Order.objects.all()
    elif hasattr(request.user, 'shop'):
        base_orders = Order.objects.filter(shop_id=request.user.shop.id)
    else:
        base_orders = Order.objects.filter(
            Q(customer_email=request.user.email) |
            Q(customer_phone=request.user.phone)
        )

    total_orders = base_orders.count()
    pending_orders = base_orders.filter(
        status__in=[Order.STATUS_PENDING, Order.STATUS_WAITING_PAYMENT]
    ).count()
    delivered_orders = base_orders.filter(
        status__in=[Order.STATUS_PAID, Order.STATUS_PAYMENT_VERIFIED]
    ).count()
    cancelled_orders = base_orders.filter(
        status__in=[Order.STATUS_FAILED, Order.STATUS_REFUNDED]
    ).count()

    # 🔹 Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_orders = paginator.get_page(page_number)

    # 🔹 Formatage des données
    orders_data = []
    for order in page_orders:
        total_items = sum(
            item.get('quantity', 0) for item in (order.cart_items or [])
        )

        shop_info = None
        if request.user.is_superuser:
            shop_info = Shop.objects.filter(id=order.shop_id).first()

        orders_data.append({
            'id': order.id,
            'order_number': str(order.id)[:8].upper(),
            'created_at': order.created_at,
            'status': order.status,
            'payment_status': 'paid' if order.status in [
                Order.STATUS_PAID, Order.STATUS_PAYMENT_VERIFIED
            ] else 'pending',
            'total_amount': order.final_amount,
            'customer_name': f"{order.customer_first_name} {order.customer_last_name}",
            'customer_email': order.customer_email,
            'customer_phone': order.customer_phone,
            'payment_method': order.payment_method,
            'cart_items': order.cart_items,
            'shop': shop_info,
            'total_items': total_items
        })

    # 🔹 Contexte final
    context = {
        'orders': orders_data,
        'page_orders': page_orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'all_shops': all_shops,
        'customers': customers,
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



@csrf_exempt
def payment_methods_list(request):
    if request.method == 'GET':
        try:
            shop = Shop.objects.get(user=request.user)
            methods = MethodPaid.objects.filter(shop=shop)
            
            data = []
            for method in methods:
                data.append({
                    'id': str(method.id),
                    'payment_method': method.payment_method,
                    'nom': method.nom,
                    'number': method.number,
                    'status': method.status,
                    'created_at': method.created_at.isoformat(),
                    'pathimg': method.pathimg.url if method.pathimg else None
                })
            
            return JsonResponse(data, safe=False)
            
        except Shop.DoesNotExist:
            return JsonResponse([], safe=False)

@csrf_exempt
def create_payment_method(request):
    if request.method == 'POST':
        try:
            shop = Shop.objects.get(user=request.user)
            
            payment_method = MethodPaid.objects.create(
                shop=shop,
                payment_method=request.POST['payment_method'],
                nom=request.POST.get('nom'),
                number=request.POST['number'],
                status=request.POST.get('status', 'false') == 'true'
            )
            
            if 'pathimg' in request.FILES:
                payment_method.pathimg = request.FILES['pathimg']
                payment_method.save()
            
            return JsonResponse({'success': True, 'method_id': str(payment_method.id)})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
def deactivate_payment_method(request, method_id):
    if request.method == 'POST':
        try:
            method = MethodPaid.objects.get(id=method_id, shop__user=request.user)
            method.status = False
            method.save()
            
            return JsonResponse({'success': True})
            
        except MethodPaid.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Méthode non trouvée'})
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
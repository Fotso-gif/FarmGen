import json
from django.http import JsonResponse
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from account.models import User
from .models import Shop, Product, Favorite, Category, ProductImage, ProductLike, ProductView, SearchHistory
from payments.models import Order, MethodPaid
# Create your views here.
from django.utils import timezone
from datetime import datetime, timedelta
   
def shop(request, shop_id):
    shop = Shop.objects.get(id = shop_id)
    produits = Product.objects.filter(category__shop=shop)
    return render(request, 'marketplace/e_shop.html', {'produits': produits, 'shop': shop})    


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

def api_shops(request):
    """
    API pour récupérer les boutiques avec filtres et pagination
    """
    try:
        # Récupération des paramètres
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 12))
        search = request.GET.get('search', '')
        shop_type = request.GET.get('type', '')
        location = request.GET.get('location', '')
        min_rating = request.GET.get('min_rating', '')
        sort_by = request.GET.get('sort', 'popular')

        # Construction de la queryset de base
        shops = Shop.objects.select_related('user').prefetch_related('favorited_by').all()

        # Application des filtres
        if search:
            shops = shops.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(type_shop__icontains=search)
            )

        if shop_type:
            shops = shops.filter(type_shop=shop_type)

        if location:
            shops = shops.filter(localisation__icontains=location)

        if min_rating:
            shops = shops.filter(note__gte=float(min_rating))

        # Application du tri
        if sort_by == 'rating':
            shops = shops.order_by('-note')
        elif sort_by == 'name':
            shops = shops.order_by('title')
        elif sort_by == 'new':
            shops = shops.order_by('-id')
        else:  # popular par défaut
            shops = shops.annotate(favorite_count=Count('favorited_by')).order_by('-favorite_count', '-note')

        # Pagination
        paginator = Paginator(shops, per_page)
        shops_page = paginator.get_page(page)

        # Préparation des données pour la réponse
        shops_data = []
        for shop in shops_page:
            shop_data = {
                'id': shop.id,
                'title': shop.title,
                'localisation': shop.localisation,
                'type_shop': shop.type_shop,
                'note': float(shop.note) if shop.note else 0.0,
                'description': shop.description,
                'couverture': shop.couverture.url if shop.couverture else None,
                'user': {
                    'username': shop.user.username,
                    'profile_picture': shop.user.profile_picture.url if hasattr(shop.user, 'profile_picture') and shop.user.profile_picture else None,
                },
                'favorite_count': shop.favorited_by.count(),
                'is_favorited': False,
            }

            # Vérifier si l'utilisateur connecté a favorisé cette boutique
            if request.user.is_authenticated:
                shop_data['is_favorited'] = Favorite.objects.filter(
                    user=request.user, 
                    shop=shop
                ).exists()

            shops_data.append(shop_data)

        response_data = {
            'shops': shops_data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_shops': paginator.count,
                'has_next': shops_page.has_next(),
                'has_previous': shops_page.has_previous(),
            },
            'filters': {
                'available_types': list(Shop.objects.values_list('type_shop', flat=True).distinct()),
                'available_locations': list(Shop.objects.values_list('localisation', flat=True).distinct()),
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def toggle_favorite(request, shop_id):
    """
    API pour ajouter/retirer une boutique des favoris
    """
    try:
        shop = Shop.objects.get(id=shop_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            shop=shop
        )

        if not created:
            # Si déjà existant, on le supprime (toggle)
            favorite.delete()
            return JsonResponse({
                'status': 'removed',
                'message': 'Boutique retirée des favoris',
                'favorite_count': shop.favorited_by.count()
            })

        return JsonResponse({
            'status': 'added',
            'message': 'Boutique ajoutée aux favoris',
            'favorite_count': shop.favorited_by.count()
        })

    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Boutique non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def favorites_status(request):
    """
    API pour récupérer le statut des favoris de l'utilisateur
    """
    try:
        favorite_shop_ids = Favorite.objects.filter(
            user=request.user
        ).values_list('shop_id', flat=True)
        
        return JsonResponse({
            'favorites': list(favorite_shop_ids)
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def save_search_history(request):
    """
    API pour sauvegarder l'historique de recherche
    """
    try:
        data = json.loads(request.body)
        search_history = SearchHistory.objects.create(
            user=request.user,
            query=data.get('query', ''),
            filters=data.get('filters', {})
        )
        
        return JsonResponse({
            'status': 'success',
            'search_id': search_history.id
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def marketplace_filters(request):
    """
    API pour récupérer les filtres disponibles
    """
    try:
        filters = {
            'types': list(Shop.objects.values_list('type_shop', flat=True)
                        .distinct()
                        .order_by('type_shop')),
            'locations': list(Shop.objects.values_list('localisation', flat=True)
                            .distinct()
                            .order_by('localisation')),
            'rating_ranges': [
                {'min': 4, 'label': '4 étoiles et plus'},
                {'min': 3, 'label': '3 étoiles et plus'},
            ]
        }
        
        return JsonResponse(filters)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
#Boutique
def shop_products_api(request, shop_id):
    """
    API pour récupérer les produits d'une boutique avec filtres
    """
    try:
        shop = Shop.objects.get(id=shop_id)
        
        # Paramètres de pagination et filtres
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 12))
        search = request.GET.get('search', '')
        categories = request.GET.getlist('categories[]')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sort_by = request.GET.get('sort_by', 'popular')
        
        # Base queryset
        products = Product.objects.filter(
            category__shop=shop
        ).select_related('category').prefetch_related('images')
        
        # Appliquer les filtres
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        if categories:
            products = products.filter(category_id__in=categories)
        
        if min_price:
            products = products.filter(price__gte=float(min_price))
        
        if max_price:
            products = products.filter(price__lte=float(max_price))
        
        # Appliquer le tri
        if sort_by == 'price-low':
            products = products.order_by('price')
        elif sort_by == 'price-high':
            products = products.order_by('-price')
        elif sort_by == 'new':
            products = products.order_by('-created_at')
        elif sort_by == 'likes':
            products = products.annotate(like_count=Count('productlike')).order_by('-like_count')
        else:  # popular par défaut
            products = products.annotate(
                like_count=Count('productlike'),
                view_count=Count('productview')
            ).order_by('-view_count', '-like_count')
        
        # Pagination
        paginator = Paginator(products, per_page)
        products_page = paginator.get_page(page)
        
        # Préparer les données de réponse
        products_data = []
        for product in products_page:
            product_data = {
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'price': float(product.price),
                'quantity': product.quantity,
                'created_at': product.created_at.isoformat(),
                'category': {
                    'id': product.category.id,
                    'name': product.category.name
                } if product.category else None,
                'images': [
                    {
                        'image': image.image.url,
                        'alt_text': image.alt_text
                    } for image in product.images.all()
                ],
                'likes_count': product.productlike_set.count(),
                'views_count': product.productview_set.count(),
                'rating': 4.8  # À calculer selon votre logique
            }
            products_data.append(product_data)
        
        return JsonResponse({
            'products': products_data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_products': paginator.count,
                'has_next': products_page.has_next(),
                'has_previous': products_page.has_previous(),
            }
        })
        
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Boutique non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def shop_categories_api(request, shop_id):
    """
    API pour récupérer les catégories d'une boutique
    """
    try:
        categories = Category.objects.filter(shop_id=shop_id).values('id', 'name')
        return JsonResponse({
            'categories': list(categories)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def toggle_product_like(request, product_id):
    """
    API pour liker/unliker un produit
    """
    try:
        product = Product.objects.get(id=product_id)
        like, created = ProductLike.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            like.delete()
            return JsonResponse({
                'status': 'unliked',
                'likes_count': product.productlike_set.count()
            })
        
        return JsonResponse({
            'status': 'liked',
            'likes_count': product.productlike_set.count()
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Produit non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def track_product_view(request, product_id):
    """
    API pour tracker les vues de produits
    """
    try:
        product = Product.objects.get(id=product_id)
        ip_address = get_client_ip(request)
        
        ProductView.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address
        )
        
        return JsonResponse({'status': 'view_tracked'})
        
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Produit non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
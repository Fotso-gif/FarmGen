# account/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages

import json
from .models import User, SellerProfile, ClientProfile, PasswordResetToken, EmailVerificationToken
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from Marketplace.models import Shop, Product, Category, ProductImage, ProductView, ProductLike, SearchHistory, Review
from payments.models import Order as OrderModel, MethodPaid

from django.core.mail import send_mail
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from FarmGen import settings
import uuid

from django.core.serializers import serialize

@csrf_exempt
@require_http_methods(["POST"])
def register_api(request):
    try:
        data = request.POST
        
        # Validation des champs requis
        required_fields = ['first_name', 'last_name', 'email', 'phone', 
                         'address', 'city', 'region', 'password', 'account_type']
        
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'error': f'Le champ {field} est requis',
                    'errors': {field: ['Ce champ est obligatoire']}
                }, status=400)
        
        # Vérification si l'email existe déjà
        if User.objects.filter(email=data['email']).exists():
            return JsonResponse({
                'error': 'Cet email est déjà utilisé',
                'errors': {'email': ['Un compte avec cet email existe déjà']}
            }, status=400)
        
        # Vérification si le téléphone existe déjà
        if User.objects.filter(phone=data['phone']).exists():
            return JsonResponse({
                'error': 'Ce numéro de téléphone est déjà utilisé',
                'errors': {'phone': ['Un compte avec ce numéro de téléphone existe déjà']}
            }, status=400)
        
        # Vérification de la correspondance des mots de passe
        if data['password'] != data.get('password_confirmation', ''):
            return JsonResponse({
                'error': 'Les mots de passe ne correspondent pas',
                'errors': {'password_confirmation': ['Les mots de passe ne correspondent pas']}
            }, status=400)
        
        # Création de l'utilisateur
        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            username=data['email'],  # Utilisation de l'email comme username
            phone=data['phone'],
            address=data['address'],
            city=data['city'],
            region=data['region'],
            account_type=data['account_type']
        )
        user.set_password(data['password'])
        user.save()
        
        # Création du profil spécifique
        if data['account_type'] == 'seller':
            seller_profile = SellerProfile(
                user=user,
                farm_name=data.get('farm_name', ''),
                specialty=data.get('specialty', 'autres'),
                farm_size=data.get('farm_size', 0) or 0,
                production_capacity=data.get('production_capacity', ''),
                certification=data.get('certification', 'aucune'),
                certification_details=data.get('certification_details', ''),
                delivery_radius=data.get('delivery_radius', 50) or 50
            )
            seller_profile.save()
        else:
            client_profile = ClientProfile(
                user=user,
                newsletter_subscribed=data.get('newsletter_subscribed', 'true') == 'true',
                price_alerts=data.get('price_alerts', 'false') == 'true'
            )
            client_profile.save()
        
         # Génération du token de vérification
        verification_token = EmailVerificationToken.generate_token(user)
        verification_url = f"{settings.FRONTEND_URL}/account/verify-email/{verification_token.token}/"
        
        # Envoi de l'email de vérification
        send_verification_email(user, verification_url)
        
        # Envoi de l'email de bienvenue
        send_welcome_email(user)
        
        # Connexion automatique
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'message': 'Votre compte a été créé avec succès ! Un email de vérification vous a été envoyé.',
            'redirect_url': '/account/verification-sent/'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Une erreur est survenue lors de la création du compte',
            'message': str(e)
        }, status=500)
    
    # Vérification d'email
def verify_email_view(request, token):
    try:
        verification_token = EmailVerificationToken.objects.get(token=token)
        
        if not verification_token.is_valid():
            return render(request, 'account/verify-email-invalid.html')
        
        # Marquer l'email comme vérifié
        user = verification_token.user
        user.is_verified = True
        user.save()
        
        # Marquer le token comme utilisé
        verification_token.is_used = True
        verification_token.save()
        
        # Connexion automatique si pas déjà connecté
        if not request.user.is_authenticated:
            login(request, user)
        
        return render(request, 'account/verify-email-success.html', {
            'user': user
        })
        
    except EmailVerificationToken.DoesNotExist:
        return render(request, 'account/verify-email-invalid.html')

# Renvoyer l'email de vérification
@csrf_exempt
@require_http_methods(["POST"])
def resend_verification_email_api(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({
                'error': 'L\'adresse email est requise'
            }, status=400)
        
        try:
            user = User.objects.get(email=email, is_active=True)
            
            if user.is_verified:
                return JsonResponse({
                    'error': 'Cet email est déjà vérifié'
                }, status=400)
            
            # Générer un nouveau token
            verification_token = EmailVerificationToken.generate_token(user)
            verification_url = f"{settings.FRONTEND_URL}/account/verify-email/{verification_token.token}/"
            
            # Renvoyer l'email
            send_verification_email(user, verification_url)
            
            return JsonResponse({
                'success': True,
                'message': 'Un nouvel email de vérification vous a été envoyé.'
            })
            
        except User.DoesNotExist:
            # Ne pas révéler si l'email existe ou non
            return JsonResponse({
                'success': True,
                'message': 'Si votre email existe dans notre système, vous recevrez un lien de vérification.'
            })
            
    except Exception as e:
        return JsonResponse({
            'error': 'Une erreur est survenue',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def login_api(request):
    try:
        # Vérifier le content-type pour gérer FormData et JSON
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            # Pour FormData
            data = {
                'email': request.POST.get('email'),
                'password': request.POST.get('password')
            }
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return JsonResponse({
                'error': 'Email et mot de passe requis'
            }, status=400)
        
        # Authentification
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Connexion réussie',
                    'redirect_url': reverse('dashboard')  # Correction ici
                })
            else:
                return JsonResponse({
                    'error': 'Ce compte est désactivé'
                }, status=400)
        else:
            return JsonResponse({
                'error': 'Email ou mot de passe incorrect'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Données invalides',
            'message': 'Le format des données est incorrect'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': 'Une erreur est survenue lors de la connexion',
            'message': str(e)
        }, status=500)
        
def logout_view(request):
    logout(request)
    return redirect('login_view')

@login_required
def dashboard(request):
    if not request.user.is_seller:
        # Statistiques principales
        total_orders = OrderModel.objects.filter(user=request.user).count()
        
        # Boutiques favorites
        favorite_shops = Shop.objects.filter(
            favorited_by__user=request.user
        ).distinct()
        favorite_shops_count = favorite_shops.count()
        
        # Produits suivis (likés ou dans les favoris)
        products_tracked = Product.objects.filter(
            Q(fav_product__user=request.user) | 
            Q(productlike__user=request.user)
        ).distinct().count()
        
        # Avis publiés
        total_reviews = Review.objects.filter(user=request.user).count()
        
        # Commandes récentes (30 derniers jours)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_orders = OrderModel.objects.filter(
            user=request.user,
            created_at__gte=thirty_days_ago
        ).order_by('-created_at')[:10]

        
        # Boutiques favorites avec plus d'informations
        favorite_shops_detailed = favorite_shops.annotate(
            product_count=Count('category__products', distinct=True),
            avg_rating=Avg('reviews__rating', distinct=True)
        )[:6]

        
        # Produits récemment consultés (7 derniers jours)
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        # D'abord, récupérer les IDs des produits consultés
        viewed_product_ids = ProductView.objects.filter(
            user=request.user,
            viewed_at__gte=seven_days_ago
        ).values_list('product_id', flat=True).distinct()[:12]
        
        # Ensuite, récupérer les produits avec leurs images
        recent_products = Product.objects.filter(id__in=viewed_product_ids
        ).select_related('category__shop').prefetch_related('images')[:8]
        
        # Si pas assez de produits consultés, ajouter des suggestions
        if recent_products.count() < 4:
            # Produits les plus populaires des boutiques favorites
            suggested_products = Product.objects.filter(
            category__shop__in=favorite_shops
            ).order_by('?')[:8]

            
            # Combiner les listes
            product_ids = list(recent_products.values_list('id', flat=True))
            for product in suggested_products:
                if product.id not in product_ids and len(product_ids) < 8:
                    product_ids.append(product.id)
            
            recent_products = Product.objects.filter(id__in=product_ids).select_related('category__shop').prefetch_related('images')
        
        # Produits likés par l'utilisateur (pour suggestions alternatives)
        liked_products = Product.objects.filter(
            productlike__user=request.user
        ).select_related('category__shop').prefetch_related('images')[:4]
        
        # Historique de recherche récent
        recent_searches = SearchHistory.objects.filter(
            user=request.user
        ).order_by('-searched_at')[:5]
        
        # Commandes en cours (non livrées)
        pending_orders = OrderModel.objects.filter(
            user=request.user
        ).exclude(
            status__in=['delivered', 'cancelled']
        ).count()
        
        # Contexte enrichi
        context = {
            # Statistiques
            'total_orders': total_orders,
            'favorite_shops_count': favorite_shops_count,
            'products_tracked': products_tracked,
            'total_reviews': total_reviews,
            
            # Commandes
            'recent_orders': recent_orders,
            'pending_orders': pending_orders,
            
            # Boutiques
            'favorite_shops': favorite_shops_detailed,
            
            # Produits
            'recent_products': recent_products,
            'liked_products': liked_products,
            
            # Historique
            'recent_searches': recent_searches,
            
            # Informations utilisateur
            'user': request.user,
            
            # Dates pour référence
            'thirty_days_ago': thirty_days_ago,
            'seven_days_ago': seven_days_ago,
        }
        
        return render(request, 'account/client/dashboard.html', context)
    
    try:
        shop = Shop.objects.get(user=request.user)
        
        # Calcul des dates pour les statistiques du mois
        today = timezone.now()
        first_day_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Statistiques des ventes du mois
        monthly_sales = OrderModel.objects.filter(
            shop_id=shop.id,
            status__in=['paid', 'payment_verified'],
            created_at__gte=first_day_month
        ).aggregate(
            total_sales=Sum('final_amount'),
            total_orders=Count('id')
        )
        
        # Produits de la boutique
        total_products = Product.objects.filter(category__shop=shop).count()
        
        # Produits récents (6 derniers) avec images
        recent_products = Product.objects.filter(
            category__shop=shop
        ).select_related('category').prefetch_related('images').order_by('-created_at')[:6]
        
        # Commandes en attente avec détails
        pending_orders = OrderModel.objects.filter(
            shop_id=shop.id,
            status__in=['pending', 'waiting_payment']
        ).order_by('-created_at')[:5]
        
        # Note moyenne de la boutique
        average_rating = shop.note
        
        # Méthodes de paiement configurées
        payment_methods = MethodPaid.objects.filter(shop=shop, status=True)
        
        # Catégories pour le formulaire
        categories = Category.objects.filter(shop=shop)
        
        # Toutes les commandes pour le modal
        all_orders = OrderModel.objects.filter(
            shop_id=shop.id
        ).order_by('-created_at')[:50]
        
        # Tous les produits pour le modal
        all_products = Product.objects.filter(
            category__shop=shop
        ).select_related('category').prefetch_related('images').order_by('-created_at')
        
        # Statistiques détaillées
        orders_by_status = OrderModel.objects.filter(
            shop_id=shop.id
        ).values('status').annotate(
            count=Count('id'),
            total=Sum('final_amount')
        )
        
        # Produits les plus vendus (basé sur les commandes)
        # Note: Cette requête nécessite une relation OrderItem dans vos modèles
        # Pour l'instant, on utilise une approximation
        top_products = Product.objects.filter(
            category__shop=shop,
            quantity__gt=0
        ).order_by('?')[:5]  # À remplacer par une vraie logique de calcul
        
        context = {
            'shop': shop,
            'total_sales': monthly_sales['total_sales'] or 0,
            'total_orders': monthly_sales['total_orders'] or 0,
            'total_products': total_products,
            'average_rating': average_rating,
            'recent_products': recent_products,
            'pending_orders': pending_orders,
            'payment_methods': payment_methods,
            'categories': categories,
            'all_orders': all_orders,
            'all_products': all_products,
            'orders_by_status': orders_by_status,
            'top_products': top_products,
        }
        
        return render(request, 'account/seller/dashboard.html', context)
        
    except Shop.DoesNotExist:
        return redirect('marketplace_list')

# API pour récupérer les données produit
def get_product_data(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        data = {
            'id': product.id,
            'name': product.name,
            'category': product.category.id,
            'price': float(product.price),
            'quantity': product.quantity,
            'expiry_date': product.expiry_date.isoformat() if product.expiry_date else None,
            'description': product.description,
            'images': [
                {
                    'image': image.image.url,
                    'alt_text': image.alt_text
                } for image in product.images.all()
            ]
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Produit non trouvé'}, status=404)

# API pour créer un produit
def create_product(request):
    if request.method == 'POST':
        try:
            # Récupération de la boutique de l'utilisateur
            shop = Shop.objects.get(user=request.user)
            
            # Création du produit
            product = Product.objects.create(
                name=request.POST['name'],
                category_id=request.POST['category'],
                price=request.POST['price'],
                quantity=request.POST['quantity'],
                description=request.POST.get('description', ''),
                expiry_date=request.POST.get('expiry_date') or None
            )
            
            # Gestion des images
            for file in request.FILES.getlist('images'):
                ProductImage.objects.create(
                    product=product,
                    image=file,
                    alt_text=product.name
                )
            
            return JsonResponse({'success': True, 'product_id': product.id})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

# API pour récupérer les données de commande
def get_order_data(request, order_id):
    try:
        order = OrderModel.objects.get(id=order_id)
        data = {
            'id': str(order.id),
            'customer_first_name': order.customer_first_name,
            'customer_last_name': order.customer_last_name,
            'customer_email': order.customer_email,
            'customer_phone': order.customer_phone,
            'payment_method': order.get_payment_method_display(),
            'status': order.status,
            'status_display': order.get_status_display(),
            'final_amount': order.final_amount,
            'cart_items': order.cart_items
        }
        return JsonResponse(data)
    except OrderModel.DoesNotExist:
        return JsonResponse({'error': 'Commande non trouvée'}, status=404)
            
@login_required
@require_http_methods(["GET"])
def api_product_detail(request, product_id):
    try:
        product = Product.objects.get(
            id=product_id,
            category__shop__user=request.user
        )
        
        images = []
        for img in product.images.all():
            images.append({
                'id': img.id,
                'image': request.build_absolute_uri(img.image.url) if img.image else '',
                'alt_text': img.alt_text
            })
        
        data = {
            'id': product.id,
            'name': product.name,
            'category': product.category.id,
            'price': str(product.price),
            'quantity': product.quantity,
            'expiry_date': product.expiry_date.strftime('%Y-%m-%d') if product.expiry_date else None,
            'description': product.description,
            'images': images,
            'created_at': product.created_at.strftime('%Y-%m-%d'),
            'is_low_stock': product.is_low_stock(),
            'stock_value': str(product.stock_value()),
        }
        
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Produit non trouvé'}, status=404)


@login_required
@require_http_methods(["GET"])
def api_order_detail(request, order_id):
    try:
        order = OrderModel.objects.get(
            id=order_id,
            shop_id=Shop.objects.get(user=request.user).id
        )
        
        # Analyser les items du panier
        cart_items = []
        if order.cart_items:
            try:
                cart_items = json.loads(order.cart_items) if isinstance(order.cart_items, str) else order.cart_items
            except:
                cart_items = order.cart_items if isinstance(order.cart_items, list) else []
        
        data = {
            'id': str(order.id),
            'customer_first_name': order.customer_first_name,
            'customer_last_name': order.customer_last_name,
            'customer_email': order.customer_email,
            'customer_phone': order.customer_phone,
            'payment_method': order.get_payment_method_display(),
            'payment_method_code': order.payment_method,
            'status': order.status,
            'status_display': order.get_status_display(),
            'final_amount': order.final_amount,
            'total_amount': order.total_amount,
            'tax_amount': order.tax_amount,
            'created_at': order.created_at.strftime('%d/%m/%Y %H:%M'),
            'payment_verified': order.payment_verified,
            'cart_items': cart_items,
        }
        
        return JsonResponse(data)
    except OrderModel.DoesNotExist:
        return JsonResponse({'error': 'Commande non trouvée'}, status=404)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_order_update(request, order_id):
    try:
        shop = Shop.objects.get(user=request.user)
        order = OrderModel.objects.get(id=order_id, shop_id=shop.id)
        
        new_status = request.POST.get('status')
        if new_status in dict(OrderModel.STATUS_CHOICES):
            order.status = new_status
            order.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Statut mis à jour avec succès'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Statut invalide'
            }, status=400)
    except OrderModel.DoesNotExist:
        return JsonResponse({'error': 'Commande non trouvée'}, status=404)

@login_required
@require_http_methods(["GET"])
def api_statistics(request):
    try:
        shop = Shop.objects.get(user=request.user)
        
        # Statistiques mensuelles
        today = timezone.now()
        first_day_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Ventes par jour du mois
        daily_sales = OrderModel.objects.filter(
            shop_id=shop.id,
            status__in=['paid', 'payment_verified'],
            created_at__gte=first_day_month
        ).extra({
            'day': "DATE(created_at)"
        }).values('day').annotate(
            total=Sum('final_amount'),
            count=Count('id')
        ).order_by('day')
        
        # Produits par catégorie
        products_by_category = Product.objects.filter(
            category__shop=shop
        ).values('category__name').annotate(
            count=Count('id'),
            total_value=Sum(F('price') * F('quantity'))
        )
        
        # Commandes par statut
        orders_by_status = OrderModel.objects.filter(
            shop_id=shop.id
        ).values('status').annotate(
            count=Count('id'),
            total=Sum('final_amount')
        )
        
        data = {
            'daily_sales': list(daily_sales),
            'products_by_category': list(products_by_category),
            'orders_by_status': list(orders_by_status),
            'total_products': Product.objects.filter(category__shop=shop).count(),
            'low_stock_products': Product.objects.filter(
                category__shop=shop,
                quantity__lt=Product.LOW_STOCK_THRESHOLD
            ).count(),
        }
        
        return JsonResponse(data)
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Boutique non trouvée'}, status=404)

@login_required
@require_http_methods(["GET"])
def api_shop_detail(request, shop_id):
    """Récupère les détails d'une boutique pour l'édition"""
    try:
        # Vérifier que l'utilisateur est propriétaire de la boutique
        shop = Shop.objects.get(id=shop_id, user=request.user)
        
        # Récupérer les méthodes de paiement
        payment_methods = MethodPaid.objects.filter(shop=shop, status=True)
        payment_methods_data = []
        for method in payment_methods:
            payment_methods_data.append({
                'id': str(method.id),
                'payment_method': method.payment_method,
                'payment_method_display': method.get_payment_method_display(),
                'nom': method.nom,
                'number': method.number,
                'pathimg': request.build_absolute_uri(method.pathimg.url) if method.pathimg else None,
                'status': method.status,
                'created_at': method.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Récupérer les statistiques
        today = timezone.now()
        first_day_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_stats = OrderModel.objects.filter(
            shop_id=shop.id,
            status__in=['paid', 'payment_verified'],
            created_at__gte=first_day_month
        ).aggregate(
            total_sales=Sum('final_amount'),
            total_orders=Count('id')
        )
        
        # Produits par catégorie
        categories_with_stats = Category.objects.filter(shop=shop).annotate(
            product_count=Count('products'),
            low_stock_count=Count('products', filter=models.Q(products__quantity__lt=Product.LOW_STOCK_THRESHOLD)),
            total_value=Sum(F('products__price') * F('products__quantity'))
        )
        
        categories_data = []
        for cat in categories_with_stats:
            categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'product_count': cat.product_count,
                'low_stock_count': cat.low_stock_count,
                'total_value': str(cat.total_value) if cat.total_value else '0.00'
            })
        
        # Commandes récentes (7 derniers jours)
        seven_days_ago = today - timedelta(days=7)
        recent_orders = OrderModel.objects.filter(
            shop_id=shop.id,
            created_at__gte=seven_days_ago
        ).order_by('-created_at')[:10]
        
        recent_orders_data = []
        for order in recent_orders:
            recent_orders_data.append({
                'id': str(order.id),
                'customer_name': f"{order.customer_first_name} {order.customer_last_name}",
                'amount': order.final_amount,
                'status': order.status,
                'status_display': order.get_status_display(),
                'payment_method': order.get_payment_method_display(),
                'created_at': order.created_at.strftime('%d/%m/%Y %H:%M')
            })
        
        # Produits en faible stock
        low_stock_products = Product.objects.filter(
            category__shop=shop,
            quantity__lt=Product.LOW_STOCK_THRESHOLD
        ).select_related('category').prefetch_related('images')[:10]
        
        low_stock_data = []
        for product in low_stock_products:
            low_stock_data.append({
                'id': product.id,
                'name': product.name,
                'category': product.category.name,
                'quantity': product.quantity,
                'price': str(product.price),
                'image': request.build_absolute_uri(product.images.first().image.url) if product.images.first() else None
            })
        
        # Données de la boutique
        data = {
            'shop': {
                'id': shop.id,
                'title': shop.title,
                'localisation': shop.localisation,
                'type_shop': shop.type_shop,
                'note': str(shop.note),
                'description': shop.description,
                'couverture': request.build_absolute_uri(shop.couverture.url) if shop.couverture else None,
                'slug': shop.slug,
                'created_at': shop.created_at.strftime('%Y-%m-%d') if hasattr(shop, 'created_at') else None,
                'total_products': Product.objects.filter(category__shop=shop).count(),
                'total_orders': OrderModel.objects.filter(shop_id=shop.id).count(),
                'total_sales': monthly_stats['total_sales'] or 0,
                'avg_rating': str(shop.note),
            },
            'payment_methods': payment_methods_data,
            'categories': categories_data,
            'statistics': {
                'monthly_sales': monthly_stats['total_sales'] or 0,
                'monthly_orders': monthly_stats['total_orders'] or 0,
                'total_customers': OrderModel.objects.filter(shop_id=shop.id).values('customer_email').distinct().count(),
                'avg_order_value': OrderModel.objects.filter(
                    shop_id=shop.id,
                    status__in=['paid', 'payment_verified']
                ).aggregate(avg=Avg('final_amount'))['avg'] or 0,
            },
            'recent_orders': recent_orders_data,
            'low_stock_products': low_stock_data,
            'performance': {
                'orders_today': OrderModel.objects.filter(
                    shop_id=shop.id,
                    created_at__date=today.date()
                ).count(),
                'sales_today': OrderModel.objects.filter(
                    shop_id=shop.id,
                    status__in=['paid', 'payment_verified'],
                    created_at__date=today.date()
                ).aggregate(total=Sum('final_amount'))['total'] or 0,
                'conversion_rate': calculate_conversion_rate(shop.id),  # Fonction à implémenter
            }
        }
        
        return JsonResponse(data)
        
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Boutique non trouvée ou accès non autorisé'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_product_update(request, product_id):
    """Met à jour un produit existant"""
    try:
        # Vérifier que l'utilisateur est propriétaire du produit
        product = Product.objects.get(
            id=product_id,
            category__shop__user=request.user
        )
        
        shop = Shop.objects.get(user=request.user)
        
        # Récupérer les données du formulaire
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        quantity = request.POST.get('quantity')
        expiry_date = request.POST.get('expiry_date')
        description = request.POST.get('description', '')
        
        # Validation des données
        if not all([name, category_id, price, quantity]):
            return JsonResponse({
                'success': False,
                'error': 'Tous les champs obligatoires doivent être remplis'
            }, status=400)
        
        try:
            # Vérifier que la catégorie appartient à la boutique
            category = Category.objects.get(id=category_id, shop=shop)
            
            # Mettre à jour le produit
            product.name = name.strip()
            product.category = category
            product.price = float(price)
            product.quantity = int(quantity)
            
            if expiry_date:
                product.expiry_date = expiry_date
            else:
                product.expiry_date = None
                
            product.description = description.strip()
            product.save()
            
            # Gérer les nouvelles images
            new_images = request.FILES.getlist('images')
            if new_images:
                for image_file in new_images:
                    ProductImage.objects.create(
                        product=product,
                        image=image_file,
                        alt_text=f"{product.name} - image"
                    )
            
            # Gérer les images à supprimer (si envoyées via un champ hidden)
            images_to_delete = request.POST.get('deleted_images', '')
            if images_to_delete:
                deleted_ids = [int(id_str) for id_str in images_to_delete.split(',') if id_str.isdigit()]
                if deleted_ids:
                    ProductImage.objects.filter(
                        id__in=deleted_ids,
                        product=product
                    ).delete()
            
            # Préparer les données de réponse
            updated_product = {
                'id': product.id,
                'name': product.name,
                'category': product.category.name,
                'price': str(product.price),
                'quantity': product.quantity,
                'expiry_date': product.expiry_date.strftime('%Y-%m-%d') if product.expiry_date else None,
                'description': product.description,
                'is_low_stock': product.is_low_stock(),
                'stock_value': str(product.stock_value()),
                'images': []
            }
            
            # Ajouter les URLs des images
            for img in product.images.all():
                updated_product['images'].append({
                    'id': img.id,
                    'url': request.build_absolute_uri(img.image.url) if img.image else '',
                    'alt_text': img.alt_text
                })
            
            return JsonResponse({
                'success': True,
                'message': 'Produit mis à jour avec succès',
                'product': updated_product
            })
            
        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Catégorie invalide'
            }, status=400)
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Données invalides: {str(e)}'
            }, status=400)
            
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Produit non trouvé ou accès non autorisé'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la mise à jour: {str(e)}'
        }, status=500)

# Fonction utilitaire pour calculer le taux de conversion (optionnelle)
def calculate_conversion_rate(shop_id):
    """Calcule le taux de conversion de la boutique"""
    try:
        # Compter les vues de produits (approximation)
        total_views = ProductView.objects.filter(
            product__category__shop_id=shop_id
        ).count()
        
        # Compter les commandes payées
        total_orders = OrderModel.objects.filter(
            shop_id=shop_id,
            status__in=['paid', 'payment_verified']
        ).count()
        
        if total_views > 0:
            conversion_rate = (total_orders / total_views) * 100
            return round(conversion_rate, 2)
        return 0.0
        
    except:
        return 0.0


# Version alternative avec gestion plus avancée des images
@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_product_update_advanced(request, product_id):
    """Version avancée avec gestion des images et validation améliorée"""
    try:
        product = Product.objects.get(
            id=product_id,
            category__shop__user=request.user
        )
        
        # Récupérer les données JSON si envoyées
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            name = data.get('name')
            category_id = data.get('category')
            price = data.get('price')
            quantity = data.get('quantity')
            expiry_date = data.get('expiry_date')
            description = data.get('description', '')
            deleted_images = data.get('deleted_images', [])
        else:
            # Données du formulaire multipart
            name = request.POST.get('name')
            category_id = request.POST.get('category')
            price = request.POST.get('price')
            quantity = request.POST.get('quantity')
            expiry_date = request.POST.get('expiry_date')
            description = request.POST.get('description', '')
            deleted_images = request.POST.getlist('deleted_images')
        
        # Validation
        errors = []
        
        if not name or len(name.strip()) < 2:
            errors.append("Le nom du produit doit contenir au moins 2 caractères")
        
        if not category_id:
            errors.append("La catégorie est obligatoire")
        
        if not price or float(price) <= 0:
            errors.append("Le prix doit être supérieur à 0")
        
        if quantity is None or int(quantity) < 0:
            errors.append("La quantité ne peut pas être négative")
        
        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        
        # Mise à jour
        product.name = name.strip()
        
        # Vérifier la catégorie
        try:
            category = Category.objects.get(id=category_id, shop__user=request.user)
            product.category = category
        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Catégorie invalide'
            }, status=400)
        
        product.price = float(price)
        product.quantity = int(quantity)
        
        if expiry_date:
            try:
                product.expiry_date = expiry_date
            except:
                product.expiry_date = None
        else:
            product.expiry_date = None
            
        product.description = description.strip()
        product.save()
        
        # Gestion des images à supprimer
        if deleted_images:
            try:
                # Convertir en liste d'entiers
                deleted_ids = [int(img_id) for img_id in deleted_images if str(img_id).isdigit()]
                if deleted_ids:
                    ProductImage.objects.filter(
                        id__in=deleted_ids,
                        product=product
                    ).delete()
            except Exception as e:
                print(f"Erreur suppression images: {e}")
        
        # Ajouter de nouvelles images (formulaire multipart seulement)
        if request.FILES:
            for image_file in request.FILES.getlist('images'):
                if image_file.size > 5 * 1024 * 1024:  # 5MB max
                    continue  # Ignorer les fichiers trop gros
                
                ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    alt_text=f"{product.name}"
                )
        
        # Préparer la réponse
        response_data = {
            'success': True,
            'message': 'Produit mis à jour avec succès',
            'product': {
                'id': product.id,
                'name': product.name,
                'category': product.category.name,
                'category_id': product.category.id,
                'price': str(product.price),
                'quantity': product.quantity,
                'expiry_date': product.expiry_date.strftime('%Y-%m-%d') if product.expiry_date else None,
                'description': product.description,
                'is_low_stock': product.is_low_stock(),
                'stock_value': str(product.stock_value()),
                'updated_at': product.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        return JsonResponse(response_data)
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Produit non trouvé'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }, status=500)


# Fonction pour obtenir les catégories d'une boutique
@login_required
@require_http_methods(["GET"])
def api_shop_categories(request, shop_id):
    """Récupère les catégories d'une boutique"""
    try:
        shop = Shop.objects.get(id=shop_id, user=request.user)
        categories = Category.objects.filter(shop=shop).annotate(
            product_count=Count('products')
        )
        
        categories_data = []
        for category in categories:
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'product_count': category.product_count,
                'created_at': category.created_at.strftime('%Y-%m-%d') if hasattr(category, 'created_at') else None
            })
        
        return JsonResponse({
            'success': True,
            'categories': categories_data
        })
        
    except Shop.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Boutique non trouvée'
        }, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def forgot_password_api(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({
                'error': 'L\'adresse email est requise'
            }, status=400)
        
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Ne pas révéler si l'email existe ou non
            return JsonResponse({
                'success': True,
                'message': 'Si votre email existe dans notre système, vous recevrez un lien de réinitialisation.'
            })
        
        # Générer le token
        reset_token = PasswordResetToken.generate_token(user)
        
        # Construire l'URL de réinitialisation
        reset_url = f"{settings.FRONTEND_URL}/account/reset-password-confirm/{reset_token.token}/"
        
        # Préparer l'email
        subject = 'Réinitialisation de votre mot de passe FarmGen'
        html_message = render_to_string('account/email/reset-password.html', {
            'user': user,
            'reset_url': reset_url,
            'expires_hours': 24
        })
        plain_message = strip_tags(html_message)
        
        # Envoyer l'email
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Si votre email existe dans notre système, vous recevrez un lien de réinitialisation.'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Une erreur est survenue',
            'message': str(e)
        }, status=500)

@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_product_image_delete(request, image_id):
    try:
        image = ProductImage.objects.get(
            id=image_id,
            product__category__shop__user=request.user
        )
        image.delete()
        return JsonResponse({'success': True})
    except ProductImage.DoesNotExist:
        return JsonResponse({'error': 'Image non trouvée'}, status=404)
    
def reset_password_email_sent_view(request):
    return render(request, 'client/auth/reset-password-email.html')

def reset_password_confirm_view(request, token):
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        if not reset_token.is_valid():
            return render(request, 'client/auth/reset-password-invalid.html')
        
        return render(request, 'client/auth/reset-password.html', {'token': token})
        
    except PasswordResetToken.DoesNotExist:
        return render(request, 'client/auth/reset-password-invalid.html')

@csrf_exempt
@require_http_methods(["POST"])
def reset_password_confirm_api(request, token):
    try:
        data = json.loads(request.body)
        password = data.get('password')
        password_confirmation = data.get('password_confirmation')
        
        if not password or not password_confirmation:
            return JsonResponse({
                'error': 'Tous les champs sont requis'
            }, status=400)
        
        if password != password_confirmation:
            return JsonResponse({
                'error': 'Les mots de passe ne correspondent pas'
            }, status=400)
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            if not reset_token.is_valid():
                return JsonResponse({
                    'error': 'Ce lien de réinitialisation est invalide ou a expiré'
                }, status=400)
            
            # Mettre à jour le mot de passe
            user = reset_token.user
            user.set_password(password)
            user.save()
            
            # Marquer le token comme utilisé
            reset_token.is_used = True
            reset_token.save()
            
            # Envoyer un email de confirmation
            subject = 'Votre mot de passe a été modifié'
            html_message = render_to_string('account/email/password_changed.html', {
                'user': user
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Votre mot de passe a été modifié avec succès. Vous pouvez maintenant vous connecter.'
            })
            
        except PasswordResetToken.DoesNotExist:
            return JsonResponse({
                'error': 'Ce lien de réinitialisation est invalide'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'error': 'Une erreur est survenue',
            'message': str(e)
        }, status=500)
    
def send_verification_email(user, verification_url):
    subject = 'Vérification de votre email - FarmGen'
    html_message = render_to_string('account/email/verify_email.html', {
        'user': user,
        'verification_url': verification_url,
        'expires_hours': 24
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_welcome_email(user):
    subject = 'Bienvenue sur FarmGen !'
    html_message = render_to_string('account/email/welcome.html', {
        'user': user,
        'login_url': f"{settings.FRONTEND_URL}/login/"
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )
# Vérification d'email
def verification_sent_view(request):
    return render(request, 'account/verification-sent.html')

@login_required
def profile(request):
    """Page de profil utilisateur"""
    user = request.user
    shop = user.shop.first()
    orders_count = OrderModel.objects.filter(shop_id=shop.id).count()
    if(user.account_type == "seller"):
        products_count = Product.objects.filter(category__shop=shop).count()
        revenue_today = OrderModel.objects.filter(
            shop_id=shop.id,
            status__in=['paid', 'payment_verified'],
            created_at__date=timezone.now().date()
        ).aggregate(total=Sum('final_amount'))['total'] or 0
    else:
        products_count = 0
        revenue_today = 0
    
    if request.method == 'POST':
        # Mettre à jour les informations du profil
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.address = request.POST.get('address', user.address)
        user.city = request.POST.get('city', user.city)
        user.region = request.POST.get('region', user.region)
        
        # Gérer l'upload de l'image de profil
        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']
        
        user.save()
        messages.success(request, "Profil mis à jour avec succès")
        return redirect('profile')
    
    context = {
        'user': user,
        'products_count':products_count,
        'revenue_today': revenue_today,
        'orders_count':orders_count
    }
    return render(request, 'account/profile.html', context)

@login_required
def update_password(request):
    """Mettre à jour le mot de passe"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, "Mot de passe actuel incorrect")
        elif new_password != confirm_password:
            messages.error(request, "Les nouveaux mots de passe ne correspondent pas")
        elif len(new_password) < 8:
            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères")
        else:
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, "Mot de passe mis à jour avec succès")
            # Reconnecter l'utilisateur
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
    
    return redirect('profile')
def update_avatar(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Méthode invalide."}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "Utilisateur non connecté."}, status=401)

    if "profile_image" not in request.FILES:
        return JsonResponse({"success": False, "message": "Aucun fichier reçu."}, status=400)

    try:
        image = request.FILES["profile_image"]
        user = request.user
        user.profile_picture = image
        user.save()

        return JsonResponse({
            "success": True,
            "message": "Avatar mis à jour avec succès.",
            "image_url": user.profile_picture.url
        })

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)
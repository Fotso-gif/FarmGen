# account/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import User, SellerProfile, ClientProfile, PasswordResetToken, EmailVerificationToken
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta
from Marketplace.models import Shop, Product, Category, ProductImage
from payments.models import Order as OrderModel, MethodPaid

from django.core.mail import send_mail
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from FarmGen import settings
import uuid


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
        return render(request, 'account/client/dashboard.html')
    
    try:
        # Récupération de la boutique de l'utilisateur
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
        
        # Produits récents (6 derniers)
        recent_products = Product.objects.filter(category__shop=shop).order_by('-created_at')[:6]
        
        # Commandes en attente
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
        }
        
        return render(request, 'account/seller/dashboard.html', context)
        
    except Shop.DoesNotExist:
        # Rediriger vers la création de boutique si aucune trouvée
        return redirect('shop_create')

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
    }
    return render(request, 'account\profile.html', context)

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
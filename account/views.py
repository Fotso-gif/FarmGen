# account/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import User, SellerProfile, ClientProfile


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
        
        # Connexion automatique
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'message': 'Votre compte a été créé avec succès!',
            'redirect_url': '/dashboard/'  # À adapter selon vos URLs
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Une erreur est survenue lors de la création du compte',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_api(request):
    try:
        data = json.loads(request.body)
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return JsonResponse({
                'error': 'Email et mot de passe requis'
            }, status=400)
        
        # Authentification
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Connexion réussie',
                    'redirect_url': "{% url 'dashboard' %}"  # À adapter selon vos URLs
                })
            else:
                return JsonResponse({
                    'error': 'Ce compte est désactivé'
                }, status=400)
        else:
            return JsonResponse({
                'error': 'Email ou mot de passe incorrect'
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
def dashboard_view(request):
    # Redirection selon le type de compte
    if request.user.is_seller:
        return render(request, 'account/seller/dashboard.html')
    else:
        return render(request, 'account/client/dashboard.html')
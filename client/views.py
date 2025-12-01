from django.shortcuts import render
from Marketplace.models import Shop, SearchHistory
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

# Create your views here.
def index(request):
    shops = Shop.objects.all()[:4]
    return render(request, 'client/index.html',{'shops':shops})

def login(request):
    return render(request, 'client/auth/login.html')

def register(request):
    return render(request, 'client/auth/register.html')

def forgot_password(request):
    return render(request, 'client/auth/forgot-password.html')

# views.py (suite)
@login_required
def marketplace(request):
    """
    Vue principale pour la page marketplace
    """
    context = {
        'page_title': 'Marketplace FarmGen',
        'meta_description': 'Découvrez les meilleurs produits agricoles directement des producteurs locaux',
    }
    return render(request, 'client/marketplace.html', context)


def search_shops(request):
    """
    Vue pour la recherche avancée
    """
    query = request.GET.get('q', '')
    shop_type = request.GET.get('type', '')
    location = request.GET.get('location', '')
    min_rating = request.GET.get('min_rating', '')
    
    shops = Shop.objects.all()
    
    if query:
        shops = shops.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(type_shop__icontains=query)
        )
    
    if shop_type:
        shops = shops.filter(type_shop=shop_type)
    
    if location:
        shops = shops.filter(localisation__icontains=location)
    
    if min_rating:
        shops = shops.filter(note__gte=float(min_rating))
    
    # Sauvegarder la recherche si l'utilisateur est connecté
    if request.user.is_authenticated and (query or shop_type or location):
        SearchHistory.objects.create(
            user=request.user,
            query=query,
            filters={
                'type': shop_type,
                'location': location,
                'min_rating': min_rating
            }
        )
    
    context = {
        'shops': shops,
        'search_query': query,
        'filters': {
            'type': shop_type,
            'location': location,
            'min_rating': min_rating,
        },
        'page_title': f'Résultats de recherche - FarmGen',
    }
    return render(request, 'client/marketplace.html', context)

def blog(request):
    return render(request, 'client/blog.html')

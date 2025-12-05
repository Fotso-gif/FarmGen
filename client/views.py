import json
from Marketplace.models import Shop, SearchHistory
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.core.paginator import Paginator
from Blog.models import Article
from Marketplace.models import Shop,  Favorite  # Si dans une autre app
from django.http import JsonResponse
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
    # Récupérer tous les articles avec leurs boutiques
    articles_list = Article.objects.select_related('shop').all().order_by('-date_publication')
    
    # Filtrer par boutique si spécifié
    shop_id = request.GET.get('shop')
    if shop_id:
        articles_list = articles_list.filter(shop_id=shop_id)
    
    # Filtrer par type de contenu
    content_type = request.GET.get('type')
    if content_type:
        articles_list = articles_list.filter(type_contenu=content_type)
    
    #Decompte des articles
    count_articles = Article.objects.filter(type_contenu='article').count()
    count_affiches = Article.objects.filter(type_contenu='affiche').count()
    count_podcasts = Article.objects.filter(type_contenu='podcast').count()

    # Filtrer par tag (recherche dans le contenu)
    tag = request.GET.get('tag')
    if tag:
        articles_list = articles_list.filter(
            Q(titre__icontains=tag) | 
            Q(contenu__icontains=tag)
        )
    
    # Pagination
    paginator = Paginator(articles_list, 6)  # 6 articles par page
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)
    
    # Boutiques avec des articles (pour les filtres)
    shops_with_articles = Shop.objects.filter(articles__isnull=False).distinct()
    
    # Catégories populaires (basé sur les tags dans le titre/contenu)
    popular_tags = Article.objects.values_list('type_contenu', flat=True).distinct()
    
    # Articles récents pour la sidebar
    recent_articles = Article.objects.select_related('shop').order_by('-date_publication')[:5]
    
    # Boutiques les plus populaires (basé sur les favoris)
    popular_shops = Shop.objects.annotate(
        favorite_count=Count('favorited_by')
    ).order_by('-favorite_count')[:5]
    
    # Pour les utilisateurs connectés, vérifier les favoris
    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = Favorite.objects.filter(user=request.user).values_list('shop_id', flat=True)
    
    context = {
        'articles': articles,
        'shops': shops_with_articles,
        'popular_tags': popular_tags,
        'recent_articles': recent_articles,
        'popular_shops': popular_shops,
        'user_favorites': list(user_favorites),
        'total_articles': articles_list.count(),
        'current_shop_filter': shop_id,
        'current_type_filter': content_type,
        'current_tag_filter': tag,
        
        'count_articles': count_articles,
        'count_affiches': count_affiches,
        'count_podcasts': count_podcasts,
    }
    
    return render(request, 'client/blog.html', context)


def article_detail(request, article_id):
    """Page de détail d'un article"""
    article = get_object_or_404(Article.objects.select_related('shop'), id=article_id)
    
    # Articles similaires (même boutique ou même type)
    similar_articles = Article.objects.filter(
        Q(shop=article.shop) | Q(type_contenu=article.type_contenu)
    ).exclude(id=article.id).order_by('-date_publication')[:3]
    
    # Boutique de l'article
    shop = article.shop
    
    # Compter les favoris de la boutique
    favorite_count = Favorite.objects.filter(shop=shop).count()
    #Listing des articles
    count_articles = shop.articles.filter(type_contenu='article').count()
    count_affiches = shop.articles.filter(type_contenu='affiche').count()
    count_podcasts = shop.articles.filter(type_contenu='podcast').count()
    # Vérifier si l'utilisateur connecté a favorisé cette boutique
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(
            user=request.user, 
            shop=shop
        ).exists()
    
    context = {
        'article': article,
        'shop': shop,
        'similar_articles': similar_articles,
        'favorite_count': favorite_count,
        'is_favorited': is_favorited,
        'article_type_display': dict(Article.TYPE_CHOICES).get(article.type_contenu, 'Article'),
        'count_articles': count_articles,
        'count_affiches': count_affiches,
        'count_podcasts': count_podcasts,
    }
    
    return render(request, 'blog/article_detail.html', context)



def get_articles_by_shop(request, shop_id):
    """Récupère les articles d'une boutique spécifique (pour AJAX)"""
    articles = Article.objects.filter(shop_id=shop_id).order_by('-date_publication')
    
    articles_data = []
    for article in articles:
        articles_data.append({
            'id': article.id,
            'titre': article.titre,
            'type_contenu': article.type_contenu,
            'type_display': dict(Article.TYPE_CHOICES).get(article.type_contenu),
            'contenu_preview': article.contenu[:200] + '...' if article.contenu and len(article.contenu) > 200 else (article.contenu or ''),
            'image_url': article.image.url if article.image else None,
            'date_publication': article.date_publication.strftime('%d %B %Y'),
            'shop_title': article.shop.title if article.shop else 'FarmGen',
            'shop_id': article.shop.id if article.shop else None,
        })
    
    return JsonResponse({'articles': articles_data})
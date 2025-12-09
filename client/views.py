
import hashlib
import uuid
import json
from datetime import timedelta
import logging
from django.db import models
from .models import NewsletterSubscriber
from .forms import NewsletterSubscriptionForm
from Marketplace.models import Shop, SearchHistory
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.core.paginator import Paginator
from Blog.models import Article
from Marketplace.models import Shop,  Favorite  # Si dans une autre app
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

logger = logging.getLogger(__name__)

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

class NewsletterSubscribeView(View):
    """Vue pour gérer l'inscription à la newsletter via AJAX"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Gérer l'inscription à la newsletter"""
        response_data = {
            'success': False,
            'error': None,
            'message': None,
            'requires_confirmation': False
        }
        
        try:
            # Vérifier si c'est une requête AJAX
            if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data['error'] = 'Requête invalide'
                return JsonResponse(response_data, status=400)
            
            # Récupérer les données du formulaire
            data = request.POST.copy()
            
            # Ajouter l'adresse IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            data['ip_address'] = ip
            
            # Ajouter la source (page d'où vient l'inscription)
            data['source'] = request.GET.get('source', 'blog')
            
            # Créer le formulaire
            form = NewsletterSubscriptionForm(data)
            
            if form.is_valid():
                email = form.cleaned_data['email']
                
                # Vérifier si l'utilisateur existe déjà
                subscriber, created = NewsletterSubscriber.objects.get_or_create(
                    email=email,
                    defaults={
                        'ip_address': data.get('ip_address'),
                        'source': data.get('source'),
                        'user': request.user if request.user.is_authenticated else None,
                    }
                )
                
                if not created:
                    # Si l'utilisateur existe déjà
                    if subscriber.status == 'unsubscribed':
                        # Réabonner l'utilisateur
                        subscriber.resubscribe()
                        subscriber.ip_address = data.get('ip_address')
                        subscriber.source = data.get('source')
                        subscriber.user = request.user if request.user.is_authenticated else subscriber.user
                        subscriber.save()
                        
                        response_data.update({
                            'success': True,
                            'message': 'Bienvenue de nouveau ! Votre réinscription a été prise en compte.',
                            'requires_confirmation': not subscriber.is_confirmed
                        })
                    elif subscriber.is_active:
                        response_data.update({
                            'success': False,
                            'error': 'Vous êtes déjà inscrit à notre newsletter.'
                        })
                    else:
                        # Si l'email n'est pas confirmé
                        response_data.update({
                            'success': True,
                            'message': 'Un email de confirmation a déjà été envoyé. Veuillez vérifier votre boîte de réception.',
                            'requires_confirmation': True
                        })
                else:
                    # Nouvel inscrit
                    # Générer un token de confirmation
                    token = hashlib.sha256(f"{email}{uuid.uuid4()}".encode()).hexdigest()
                    subscriber.confirmation_token = token
                    
                    # Envoyer un email de confirmation
                    if self.send_confirmation_email(subscriber):
                        subscriber.save()
                        response_data.update({
                            'success': True,
                            'message': 'Un email de confirmation a été envoyé. Veuillez vérifier votre boîte de réception.',
                            'requires_confirmation': True
                        })
                    else:
                        response_data['error'] = "Erreur lors de l'envoi de l'email de confirmation"
                
            else:
                # Erreurs de formulaire
                errors = form.errors.as_json()
                error_dict = json.loads(errors)
                if 'email' in error_dict:
                    response_data['error'] = error_dict['email'][0]['message']
                else:
                    response_data['error'] = 'Veuillez vérifier les informations saisies.'
        
        except Exception as e:
            logger.error(f"Erreur lors de l'inscription à la newsletter: {str(e)}")
            response_data['error'] = 'Une erreur technique est survenue. Veuillez réessayer plus tard.'
        
        return JsonResponse(response_data)
    
    def send_confirmation_email(self, subscriber):
        """Envoyer un email de confirmation"""
        try:
            # Construire l'URL de confirmation
            confirmation_url = f"{settings.SITE_URL}/newsletter/confirm/{subscriber.confirmation_token}/"
            
            # Préparer le contenu de l'email
            context = {
                'subscriber': subscriber,
                'confirmation_url': confirmation_url,
                'site_name': settings.SITE_NAME,
                'current_year': timezone.now().year,
            }
            
            # Rendre le template HTML
            html_message = render_to_string('emails/newsletter_confirmation.html', context)
            plain_message = strip_tags(html_message)
            
            # Envoyer l'email
            send_mail(
                subject=f'Confirmez votre inscription à la newsletter {settings.SITE_NAME}',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[subscriber.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Email de confirmation envoyé à {subscriber.email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de confirmation: {str(e)}")
            return False


class NewsletterConfirmView(View):
    """Vue pour confirmer l'inscription à la newsletter"""
    
    def get(self, request, token, *args, **kwargs):
        """Confirmer l'inscription via token"""
        try:
            subscriber = NewsletterSubscriber.objects.get(
                confirmation_token=token,
                is_confirmed=False
            )
            
            # Confirmer l'abonnement
            subscriber.is_confirmed = True
            subscriber.status = 'active'
            subscriber.confirmation_token = ''  # Invalider le token
            subscriber.save()
            
            # Envoyer un email de bienvenue
            self.send_welcome_email(subscriber)
            
            context = {
                'success': True,
                'subscriber': subscriber,
                'message': 'Votre inscription a été confirmée avec succès !'
            }
            
        except NewsletterSubscriber.DoesNotExist:
            context = {
                'success': False,
                'message': 'Token invalide ou déjà utilisé.'
            }
        except Exception as e:
            logger.error(f"Erreur lors de la confirmation: {str(e)}")
            context = {
                'success': False,
                'message': 'Une erreur est survenue.'
            }
        
        return render(request, 'newsletter/confirmation.html', context)
    
    def send_welcome_email(self, subscriber):
        """Envoyer un email de bienvenue"""
        try:
            context = {
                'subscriber': subscriber,
                'site_name': settings.SITE_NAME,
                'unsubscribe_url': f"{settings.SITE_URL}/newsletter/unsubscribe/{subscriber.confirmation_token}/",
                'current_year': timezone.now().year,
            }
            
            html_message = render_to_string('emails/newsletter_welcome.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f'Bienvenue dans la newsletter {settings.SITE_NAME} !',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[subscriber.email],
                html_message=html_message,
                fail_silently=True,
            )
            
            # Mettre à jour la date du dernier email
            subscriber.last_email_sent = timezone.now()
            subscriber.save(update_fields=['last_email_sent'])
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de bienvenue: {str(e)}")


# Vue pour la désinscription
class NewsletterUnsubscribeView(View):
    """Vue pour gérer la désinscription"""
    
    def get(self, request, token, *args, **kwargs):
        """Page de désinscription"""
        try:
            subscriber = NewsletterSubscriber.objects.get(
                confirmation_token=token,
                status='active'
            )
            context = {'subscriber': subscriber}
            
        except NewsletterSubscriber.DoesNotExist:
            context = {'error': 'Abonné non trouvé'}
        
        return render(request, 'newsletter/unsubscribe.html', context)
    
    def post(self, request, token, *args, **kwargs):
        """Traiter la désinscription"""
        try:
            subscriber = NewsletterSubscriber.objects.get(
                confirmation_token=token,
                status='active'
            )
            
            # Désabonner
            subscriber.unsubscribe()
            
            context = {
                'success': True,
                'message': 'Vous avez été désabonné avec succès.'
            }
            
        except NewsletterSubscriber.DoesNotExist:
            context = {
                'success': False,
                'message': 'Abonné non trouvé.'
            }
        
        return render(request, 'newsletter/unsubscribe_result.html', context)


# Vue pour les statistiques (admin)
@method_decorator(login_required, name='dispatch')
class NewsletterStatsView(View):
    """Vue pour afficher les statistiques de la newsletter"""
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden()
        
        # Statistiques
        total_subscribers = NewsletterSubscriber.objects.count()
        active_subscribers = NewsletterSubscriber.objects.filter(
            status='active', 
            is_confirmed=True
        ).count()
        new_today = NewsletterSubscriber.objects.filter(
            subscribed_at__date=timezone.now().date()
        ).count()
        
        # Graphique d'inscriptions par jour (7 derniers jours)
        seven_days_ago = timezone.now() - timedelta(days=7)
        subscriptions_by_day = NewsletterSubscriber.objects.filter(
            subscribed_at__gte=seven_days_ago
        ).extra({
            'date': "DATE(subscribed_at)"
        }).values('date').annotate(
            count=models.Count('id')
        ).order_by('date')
        
        context = {
            'total_subscribers': total_subscribers,
            'active_subscribers': active_subscribers,
            'new_today': new_today,
            'subscriptions_by_day': list(subscriptions_by_day),
        }
        
        return render(request, 'admin/newsletter_stats.html', context)
import json
import os
import base64
from datetime import timedelta, datetime
from decimal import Decimal
from django.core.files.base import ContentFile
from .models import Article
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.conf import settings

from Marketplace.models import Shop
from account.models import User  # Si nécessaire

def liste_articles(request):
    articles = Article.objects.all().order_by('-date_publication')
    return render(request, 'blog/liste_articles.html', {'articles': articles})


@login_required
def seller_blog(request):
    """Dashboard seller pour la gestion du blog de la boutique"""
    
    # Vérifier que l'utilisateur est un vendeur avec une boutique
    if not hasattr(request.user, 'shop'):
        messages.error(request, "Vous devez être un vendeur pour accéder à cette page")
        return redirect('dashboard')
    
    try:
        shop = request.user.shop.first()
        if not shop:
            messages.error(request, "Vous devez avoir une boutique pour accéder à cette page")
            return redirect('dashboard')
    except AttributeError:
        messages.error(request, "Vous devez avoir une boutique pour accéder à cette page")
        return redirect('dashboard')
    
    # Récupérer tous les paramètres de filtrage
    content_type = request.GET.get('type', '')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-date_publication')
    page_number = request.GET.get('page', 1)
    
    # Récupérer les articles de la boutique
    articles = Article.objects.filter(shop=shop)
    
    # Appliquer les filtres
    if content_type:
        articles = articles.filter(type_contenu=content_type)
    
    if search_query:
        articles = articles.filter(
            Q(titre__icontains=search_query) |
            Q(contenu__icontains=search_query)
        )
    
    # Trier
    if sort_by == 'titre':
        articles = articles.order_by('titre')
    elif sort_by == '-titre':
        articles = articles.order_by('-titre')
    elif sort_by == 'date_publication':
        articles = articles.order_by('date_publication')
    else:  # '-date_publication' par défaut
        articles = articles.order_by('-date_publication')
    
    # Calculer les statistiques
    total_articles = articles.count()
    
    # Statistiques par type
    articles_by_type = [
        {'type_contenu': 'article', 'count': articles.filter(type_contenu='article').count()},
        {'type_contenu': 'affiche', 'count': articles.filter(type_contenu='affiche').count()},
        {'type_contenu': 'podcast', 'count': articles.filter(type_contenu='podcast').count()},
    ]
    
    # Articles récents (7 derniers jours)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_articles = articles.filter(
        date_publication__gte=seven_days_ago
    ).count()
    
    # Pagination
    paginator = Paginator(articles, 12)
    try:
        page_articles = paginator.page(page_number)
    except:
        page_articles = paginator.page(1)
    
    # Préparer les données pour le template
    articles_data = []
    for article in page_articles:
        articles_data.append({
            'id': article.id,
            'titre': article.titre,
            'type_contenu': article.type_contenu,
            'excerpt': article.contenu[:150] + "..." if article.contenu and len(article.contenu) > 150 else article.contenu or "",
            'image_url': article.image.url if article.image else None,
            'video_url': article.video.url if article.video else None,
            'date_formatted': article.date_publication.strftime("%d/%m/%Y"),
        })
    
    context = {
        'shop': shop,
        'articles': articles_data,
        'page_articles': page_articles,
        'total_articles': total_articles,
        'recent_articles': recent_articles,
        'articles_by_type': articles_by_type,
        'current_type': content_type,
        'search_query': search_query,
        'sort_by': sort_by,
        'type_choices': Article.TYPE_CHOICES,
    }
    
    # Si requête AJAX, retourner JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'articles': articles_data,
            'pagination': {
                'current_page': page_articles.number,
                'total_pages': paginator.num_pages,
                'has_previous': page_articles.has_previous(),
                'has_next': page_articles.has_next(),
            },
            'stats': {
                'total': total_articles,
                'recent': recent_articles,
                'by_type': articles_by_type,
            }
        })
    
    return render(request, 'blog/blogAdmin.html', context)

@login_required
def create_article(request):
    """Créer un nouvel article"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Méthode non autorisée'
        }, status=405)
    
    # Vérifier que l'utilisateur est un vendeur
    if not hasattr(request.user, 'shop'):
        return JsonResponse({
            'success': False,
            'error': 'Vous devez être un vendeur pour créer un article'
        }, status=403)
    
    shop = request.user.shop.first()
    if not shop:
        return JsonResponse({
            'success': False,
            'error': 'Boutique non trouvée'
        }, status=404)
    
    try:
        data = request.POST
        files = request.FILES
        
        # Valider les données requises
        titre = data.get('titre', '').strip()
        type_contenu = data.get('type_contenu', 'article')
        
        if not titre:
            return JsonResponse({
                'success': False,
                'error': 'Le titre est requis'
            }, status=400)
        
        # Vérifier les fichiers requis selon le type
        if type_contenu == 'affiche' and 'image' not in files:
            return JsonResponse({
                'success': False,
                'error': 'Une image est requise pour une affiche'
            }, status=400)
        
        if type_contenu == 'podcast' and 'video' not in files:
            return JsonResponse({
                'success': False,
                'error': 'Un fichier vidéo/audio est requis pour un podcast'
            }, status=400)
        
        # Créer l'article
        article = Article.objects.create(
            shop=shop,
            titre=titre,
            type_contenu=type_contenu,
            contenu=data.get('contenu', ''),
            date_publication=timezone.now()
        )
        
        # Gérer l'image si fournie
        if 'image' in files:
            image_file = files['image']
            allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_image_types:
                article.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Type de fichier image non supporté'
                }, status=400)
            
            if image_file.size > 10 * 1024 * 1024:
                article.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'L\'image est trop volumineuse (max 10MB)'
                }, status=400)
            
            article.image = image_file
        
        # Gérer la vidéo si fournie
        if 'video' in files:
            video_file = files['video']
            allowed_video_types = [
                'video/mp4', 'video/avi', 'video/mov', 'video/webm',
                'audio/mpeg', 'audio/wav', 'audio/ogg'
            ]
            if video_file.content_type not in allowed_video_types:
                article.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Type de fichier vidéo/audio non supporté'
                }, status=400)
            
            if video_file.size > 100 * 1024 * 1024:
                article.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Le fichier vidéo/audio est trop volumineux (max 100MB)'
                }, status=400)
            
            article.video = video_file
        
        article.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Article publié avec succès!',
            'article': {
                'id': article.id,
                'titre': article.titre,
                'type_contenu': article.type_contenu,
            }
        })
        
    except Exception as e:
        print(f"Erreur lors de la création d'article: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la création: {str(e)}'
        }, status=500)

@login_required
def edit_article(request, article_id):
    """Éditer un article existant"""
    try:
        article = get_object_or_404(Article, id=article_id)
        
        # Vérifier que l'article appartient à la boutique du vendeur
        if not hasattr(request.user, 'shop') or article.shop != request.user.shop.first():
            return JsonResponse({
                'success': False,
                'error': 'Vous n\'avez pas accès à cet article'
            }, status=403)
        
        if request.method == 'GET':
            # Retourner les données de l'article
            return JsonResponse({
                'success': True,
                'article': {
                    'id': article.id,
                    'titre': article.titre,
                    'type_contenu': article.type_contenu,
                    'contenu': article.contenu or '',
                    'image_url': article.image.url if article.image else None,
                    'video_url': article.video.url if article.video else None,
                }
            })
        
        elif request.method == 'POST':
            try:
                data = request.POST
                files = request.FILES
                
                # Valider les données
                titre = data.get('titre', article.titre).strip()
                if not titre:
                    raise ValueError("Le titre est requis")
                
                # Mettre à jour l'article
                article.titre = titre
                article.type_contenu = data.get('type_contenu', article.type_contenu)
                article.contenu = data.get('contenu', article.contenu)
                
                # Gérer l'image si fournie
                if 'image' in files:
                    image_file = files['image']
                    
                    # Valider le type de fichier image
                    allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                    if image_file.content_type not in allowed_image_types:
                        return JsonResponse({
                            'success': False,
                            'error': 'Type de fichier image non supporté'
                        }, status=400)
                    
                    # Valider la taille
                    if image_file.size > 10 * 1024 * 1024:
                        return JsonResponse({
                            'success': False,
                            'error': 'L\'image est trop volumineuse (max 10MB)'
                        }, status=400)
                    
                    # Supprimer l'ancienne image si elle existe
                    if article.image:
                        try:
                            if default_storage.exists(article.image.name):
                                default_storage.delete(article.image.name)
                        except:
                            pass
                    
                    article.image = image_file
                
                # Gérer la vidéo si fournie
                if 'video' in files:
                    video_file = files['video']
                    
                    # Valider le type de fichier
                    allowed_video_types = [
                        'video/mp4', 'video/avi', 'video/mov', 'video/webm',
                        'audio/mpeg', 'audio/wav', 'audio/ogg'
                    ]
                    if video_file.content_type not in allowed_video_types:
                        return JsonResponse({
                            'success': False,
                            'error': 'Type de fichier vidéo/audio non supporté'
                        }, status=400)
                    
                    # Valider la taille
                    if video_file.size > 100 * 1024 * 1024:
                        return JsonResponse({
                            'success': False,
                            'error': 'Le fichier vidéo/audio est trop volumineux (max 100MB)'
                        }, status=400)
                    
                    # Supprimer l'ancienne vidéo si elle existe
                    if article.video:
                        try:
                            if default_storage.exists(article.video.name):
                                default_storage.delete(article.video.name)
                        except:
                            pass
                    
                    article.video = video_file
                
                article.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Article mis à jour avec succès!',
                    'article': {
                        'id': article.id,
                        'titre': article.titre,
                        'type_contenu': article.type_contenu,
                        'contenu': article.contenu,
                        'image_url': article.image.url if article.image else None,
                        'video_url': article.video.url if article.video else None,
                    }
                })
                
            except ValueError as ve:
                return JsonResponse({
                    'success': False,
                    'error': str(ve)
                }, status=400)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f"Erreur lors de la mise à jour: {str(e)}"
                }, status=500)
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Méthode non autorisée'
            }, status=405)
            
    except Article.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Article non trouvé'
        }, status=404)

@login_required
def delete_article(request, article_id):
    """Supprimer un article"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Méthode non autorisée'
        }, status=405)
    
    try:
        article = get_object_or_404(Article, id=article_id)
        
        # Vérifier les permissions
        if not hasattr(request.user, 'shop') or article.shop != request.user.shop.first():
            return JsonResponse({
                'success': False,
                'error': 'Vous n\'avez pas la permission de supprimer cet article'
            }, status=403)
        
        # Sauvegarder les infos pour le message
        article_title = article.titre
        
        # Supprimer les fichiers associés
        if article.image:
            try:
                if default_storage.exists(article.image.name):
                    default_storage.delete(article.image.name)
            except Exception as e:
                print(f"Erreur lors de la suppression de l'image: {e}")
        
        if article.video:
            try:
                if default_storage.exists(article.video.name):
                    default_storage.delete(article.video.name)
            except Exception as e:
                print(f"Erreur lors de la suppression de la vidéo: {e}")
        
        # Supprimer l'article
        article.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Article "{article_title}" supprimé avec succès!',
            'article_id': article_id
        })
        
    except Article.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Article non trouvé'
        }, status=404)
    
    except Exception as e:
        print(f"Erreur lors de la suppression d'article: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la suppression: {str(e)}'
        }, status=500)


@login_required
def article_preview(request):
    """Prévisualiser un article - version simplifiée"""
    if request.method == 'POST':
        # Stocker les données en session pour la prévisualisation
        try:
            data = request.POST
            files = request.FILES
            
            preview_data = {
                'titre': data.get('titre', 'Sans titre'),
                'type_contenu': data.get('type_contenu', 'article'),
                'contenu': data.get('contenu', ''),
                'date_formatted': timezone.now().strftime("%d/%m/%Y"),
            }
            
            # Gérer l'image si fournie
            if 'image' in files:
                image_file = files['image']
                # Convertir en base64 pour la prévisualisation
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
                preview_data['image_data'] = {
                    'content_type': image_file.content_type,
                    'data': image_data
                }
                image_file.seek(0)
            
            # Gérer la vidéo si fournie
            if 'video' in files:
                video_file = files['video']
                video_data = base64.b64encode(video_file.read()).decode('utf-8')
                preview_data['video_data'] = {
                    'content_type': video_file.content_type,
                    'data': video_data
                }
                video_file.seek(0)
            
            request.session['preview_data'] = preview_data
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Erreur lors de la prévisualisation: {e}")
            return JsonResponse({
                'success': False,
                'error': f"Erreur lors de la prévisualisation: {str(e)}"
            }, status=500)
    
    # Pour GET, afficher la prévisualisation
    context = {}
    
    # Vérifier si un ID d'article est fourni dans l'URL
    article_id = request.GET.get('id')
    if article_id:
        try:
            article = get_object_or_404(Article, id=article_id)
            
            # Vérifier les permissions
            if hasattr(request.user, 'shop') and article.shop == request.user.shop.first():
                context['article'] = {
                    'id': article.id,
                    'titre': article.titre,
                    'type_contenu': article.type_contenu,
                    'contenu': article.contenu,
                    'image_url': article.image.url if article.image else None,
                    'video_url': article.video.url if article.video else None,
                    'date_formatted': article.date_publication.strftime("%d/%m/%Y"),
                    'shop': article.shop,
                }
                context['is_preview'] = False
        except Article.DoesNotExist:
            pass
    
    # Si pas d'article spécifique, vérifier les données de session
    if 'preview_data' in request.session and not context.get('article'):
        context['preview_data'] = request.session['preview_data']
        context['is_preview'] = True
        
        # Nettoyer les données de session après utilisation
        if not request.GET.get('keep_session'):
            del request.session['preview_data']
    
    # Si aucune donnée n'est disponible
    if not context:
        return render(request, 'blog/article_preview.html', {
            'error': 'Aucune donnée disponible pour la prévisualisation'
        })
    
    return render(request, 'blog/article_preview.html', context)
    # Fonctions utilitaires supplémentaires

def get_article_stats(articles):
    """Calculer des statistiques avancées sur les articles"""
    stats = {
        'total_words': 0,
        'avg_word_count': 0,
        'longest_article': None,
        'shortest_article': None,
        'publishing_frequency': 0,
    }
    
    if articles.exists():
        # Compter les mots totaux
        word_counts = []
        for article in articles:
            if article.contenu:
                word_count = len(article.contenu.split())
                word_counts.append(word_count)
                stats['total_words'] += word_count
                
                # Trouver le plus long article
                if not stats['longest_article'] or word_count > stats['longest_article']['word_count']:
                    stats['longest_article'] = {
                        'id': article.id,
                        'titre': article.titre,
                        'word_count': word_count
                    }
                
                # Trouver le plus court article
                if not stats['shortest_article'] or word_count < stats['shortest_article']['word_count']:
                    stats['shortest_article'] = {
                        'id': article.id,
                        'titre': article.titre,
                        'word_count': word_count
                    }
        
        # Calculer la moyenne
        if word_counts:
            stats['avg_word_count'] = sum(word_counts) / len(word_counts)
        
        # Calculer la fréquence de publication
        if articles.count() > 1:
            dates = articles.order_by('date_publication')
            first_date = dates.first().date_publication
            last_date = dates.last().date_publication
            
            if first_date != last_date:
                days_diff = (last_date - first_date).days
                stats['publishing_frequency'] = articles.count() / max(1, days_diff) * 30  # Articles par mois
    
    return stats


def validate_article_data(data, files):
    """Valider les données d'un article"""
    errors = []
    
    # Validation du titre
    titre = data.get('titre', '').strip()
    if not titre:
        errors.append("Le titre est requis")
    elif len(titre) > 200:
        errors.append("Le titre ne doit pas dépasser 200 caractères")
    
    # Validation du type de contenu
    type_contenu = data.get('type_contenu', 'article')
    if type_contenu not in ['article', 'affiche', 'podcast']:
        errors.append("Type de contenu invalide")
    
    # Validation des fichiers selon le type
    if type_contenu == 'affiche' and 'image' not in files:
        errors.append("Une image est requise pour une affiche")
    
    if type_contenu == 'podcast' and 'video' not in files:
        errors.append("Un fichier vidéo/audio est requis pour un podcast")
    
    # Validation de la taille des fichiers
    if 'image' in files:
        image_file = files['image']
        if image_file.size > 10 * 1024 * 1024:  # 10MB
            errors.append("L'image est trop volumineuse (max 10MB)")
    
    if 'video' in files:
        video_file = files['video']
        if video_file.size > 100 * 1024 * 1024:  # 100MB
            errors.append("Le fichier vidéo/audio est trop volumineux (max 100MB)")
    
    return errors


# Décorateur pour gérer les exceptions
def handle_article_exceptions(view_func):
    """Décorateur pour gérer les exceptions dans les vues d'articles"""
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Article.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Article non trouvé'
                }, status=404)
            
            messages.error(request, "Article non trouvé")
            return redirect('seller_blog')
        except PermissionError:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Permission refusée'
                }, status=403)
            
            messages.error(request, "Permission refusée")
            return redirect('seller_blog')
        except Exception as e:
            print(f"Erreur inattendue: {e}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Une erreur est survenue'
                }, status=500)
            
            messages.error(request, "Une erreur est survenue")
            return redirect('seller_blog')
    
    return wrapper


# Exporter les fonctions décorées
seller_blog = handle_article_exceptions(seller_blog)
create_article = handle_article_exceptions(create_article)
edit_article = handle_article_exceptions(edit_article)
delete_article = handle_article_exceptions(delete_article)
article_preview = handle_article_exceptions(article_preview)
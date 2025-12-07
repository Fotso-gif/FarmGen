from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from account.models import User
from django.urls import reverse
import json
import logging

from Blog.models import Article
from .models import Comment, Testimonial, CommentLike, CommentReport
from .forms import CommentForm, ReplyForm, TestimonialForm, TestimonialCommentForm, CommentReportForm

def contact_page(request):
    return render(request, 'contacts/contact.html')

logger = logging.getLogger(__name__)


# ============ COMMENTAIRES ============

class GetCommentsView(View):
    """Récupérer les commentaires pour un article"""
    
    def get(self, request, *args, **kwargs):
        """Récupérer les commentaires"""
        try:
            article_id = request.GET.get('article_id')
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 10))
            
            # Vérifier l'article
            article = get_object_or_404(Article, id=article_id)
            
            # Filtrer les commentaires approuvés
            comments = Comment.objects.filter(
                article=article,
                status='approved',
                parent__isnull=True  # Seulement les commentaires parents
            ).select_related('user').prefetch_related('replies').order_by('-created_at')
            
            # Pagination
            paginator = Paginator(comments, limit)
            page_obj = paginator.get_page(page)
            
            # Préparer les données
            comments_data = []
            for comment in page_obj:
                # Récupérer les réponses approuvées
                replies = comment.replies.filter(status='approved').select_related('user')[:5]
                
                comment_data = {
                    'id': str(comment.id),
                    'user': {
                        'id': comment.user.id,
                        'username': comment.user.username,
                        'full_name': comment.user.get_full_name() or comment.user.username,
                        'avatar_url': comment.user.profile.avatar.url if hasattr(comment.user, 'profile') and comment.user.profile.avatar else '/static/images/default-avatar.png',
                    },
                    'content': comment.content,
                    'created_at': comment.created_at.strftime('%d/%m/%Y à %H:%M'),
                    'likes_count': comment.likes_count,
                    'replies_count': comment.replies_count,
                    'user_has_liked': comment.likes.filter(user=request.user, is_active=True).exists() if request.user.is_authenticated else False,
                    'replies': []
                }
                
                # Ajouter les réponses
                for reply in replies:
                    reply_data = {
                        'id': str(reply.id),
                        'user': {
                            'id': reply.user.id,
                            'username': reply.user.username,
                            'full_name': reply.user.get_full_name() or reply.user.username,
                            'avatar_url': reply.user.profile.avatar.url if hasattr(reply.user, 'profile') and reply.user.profile.avatar else '/static/images/default-avatar.png',
                        },
                        'content': reply.content,
                        'created_at': reply.created_at.strftime('%d/%m/%Y à %H:%M'),
                    }
                    comment_data['replies'].append(reply_data)
                
                comments_data.append(comment_data)
            
            response_data = {
                'success': True,
                'comments': comments_data,
                'total_comments': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': page,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des commentaires: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class CreateCommentView(View):
    """Créer un commentaire"""
    
    def post(self, request, *args, **kwargs):
        """Créer un commentaire"""
        try:
            data = json.loads(request.body)
            article_id = data.get('article_id')
            content = data.get('content')
            parent_id = data.get('parent_id')
            
            # Valider les données
            if not article_id or not content:
                return JsonResponse({'success': False, 'error': 'Données manquantes'}, status=400)
            
            # Vérifier l'article
            article = get_object_or_404(Article, id=article_id)
            
            # Créer le commentaire
            comment = Comment(
                user=request.user,
                article=article,
                content=content,
                status='approved' if request.user.is_superuser else 'pending'
            )
            
            # Si c'est une réponse
            if parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id, article=article)
                comment.parent = parent_comment
            
            # Enregistrer l'IP et user agent
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                comment.ip_address = x_forwarded_for.split(',')[0]
            else:
                comment.ip_address = request.META.get('REMOTE_ADDR')
            
            comment.user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            comment.save()
            
            # Si c'est un commentaire admin, envoyer une notification
            if not request.user.is_superuser:
                self.send_comment_notification(comment, article)
            
            # Préparer la réponse
            comment_data = {
                'id': str(comment.id),
                'user': {
                    'username': request.user.username,
                    'full_name': request.user.get_full_name() or request.user.username,
                    'avatar_url': request.user.profile.avatar.url if hasattr(request.user, 'profile') and request.user.profile.avatar else '/static/images/default-avatar.png',
                },
                'content': comment.content,
                'created_at': comment.created_at.strftime('%d/%m/%Y à %H:%M'),
                'status': comment.status,
                'is_reply': bool(parent_id),
                'parent_id': parent_id
            }
            
            return JsonResponse({
                'success': True,
                'comment': comment_data,
                'message': 'Votre commentaire a été soumis avec succès.' + 
                          (' Il est en attente de modération.' if comment.status == 'pending' else '')
            })
                
        except Exception as e:
            logger.error(f"Erreur lors de la création du commentaire: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)
    
    def send_comment_notification(self, comment, article, request):
        """Envoyer une notification pour un nouveau commentaire"""
        try:
            # Liste des administrateurs
            admins = User.objects.filter(is_staff=True)
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if admin_emails:
                subject = f'Nouveau commentaire sur l\'article: {article.titre}'
                
                context = {
                    'comment': comment,
                    'article': article,
                    'user': comment.user,
                    'admin_url': request.build_absolute_uri('/admin/')
                }
                
                message = render_to_string('emails/comment_notification.txt', context)
                html_message = render_to_string('emails/comment_notification.html', context)
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    html_message=html_message,
                    fail_silently=True,
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class LikeCommentView(View):
    """Like/Dislike un commentaire"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            comment_id = data.get('comment_id')
            
            comment = get_object_or_404(Comment, id=comment_id, status='approved')
            
            # Vérifier si l'utilisateur a déjà liké
            like, created = CommentLike.objects.get_or_create(
                comment=comment,
                user=request.user,
                defaults={'is_active': True}
            )
            
            if not created:
                # Toggle like/dislike
                like.is_active = not like.is_active
                like.save()
            
            return JsonResponse({
                'success': True,
                'likes_count': comment.likes_count,
                'is_liked': like.is_active if not created else True
            })
            
        except Exception as e:
            logger.error(f"Erreur lors du like du commentaire: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ReportCommentView(View):
    """Signaler un commentaire"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            comment_id = data.get('comment_id')
            reason = data.get('reason')
            description = data.get('description', '')
            
            comment = get_object_or_404(Comment, id=comment_id)
            
            # Créer le signalement
            report = CommentReport(
                comment=comment,
                reason=reason,
                description=description
            )
            
            if request.user.is_authenticated:
                report.user = request.user
            
            # Enregistrer l'IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                report.ip_address = x_forwarded_for.split(',')[0]
            else:
                report.ip_address = request.META.get('REMOTE_ADDR')
            
            report.save()
            
            # Marquer le commentaire comme suspect si nécessaire
            if comment.status == 'approved':
                comment.status = 'pending'
                comment.save()
            
            # Envoyer une notification aux admins
            self.send_report_notification(report, comment)
            
            return JsonResponse({
                'success': True,
                'message': 'Votre signalement a été envoyé. Merci !'
            })
                
        except Exception as e:
            logger.error(f"Erreur lors du signalement: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)
    
    def send_report_notification(self, report, comment, request):
        """Envoyer une notification pour un signalement"""
        try:
            admins = User.objects.filter(is_staff=True)
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if admin_emails:
                subject = f'Signalement de commentaire sur l\'article: {comment.article.titre}'
                
                context = {
                    'report': report,
                    'comment': comment,
                    'user': report.user,
                    'admin_url': request.build_absolute_uri('/admin/')
                }
                
                message = render_to_string('emails/comment_report_notification.txt', context)
                html_message = render_to_string('emails/comment_report_notification.html', context)
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    html_message=html_message,
                    fail_silently=True,
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification de signalement: {str(e)}")


# ============ TÉMOIGNAGES ============

class TestimonialListView(View):
    """Liste des témoignages"""
    
    def get(self, request, *args, **kwargs):
        # Récupérer les témoignages publiés et approuvés
        testimonials = Testimonial.objects.filter(
            status='published',
            allow_display=True
        ).order_by('-is_featured', '-published_at')
        
        # Filtrer par catégorie si spécifiée
        category = request.GET.get('category')
        if category:
            testimonials = testimonials.filter(category=category)
        
        # Pagination
        paginator = Paginator(testimonials, 12)
        page = request.GET.get('page', 1)
        page_obj = paginator.get_page(page)
        
        context = {
            'testimonials': page_obj,
            'categories': Testimonial.CATEGORY_CHOICES,
            'current_category': category,
        }
        
        return render(request, 'testimonials/list.html', context)


class TestimonialDetailView(View):
    """Détail d'un témoignage"""
    
    def get(self, request, testimonial_id, *args, **kwargs):
        testimonial = get_object_or_404(Testimonial, id=testimonial_id, status='published')
        
        # Récupérer les commentaires approuvés
        comments = testimonial.comments.filter(status='approved').select_related('user')
        
        context = {
            'testimonial': testimonial,
            'comments': comments,
        }
        
        return render(request, 'testimonials/detail.html', context)


class TestimonialCreateView(View):
    """Créer un témoignage"""
    
    def get(self, request, *args, **kwargs):
        form = TestimonialForm()
        context = {'form': form}
        return render(request, 'testimonials/create.html', context)
    
    def post(self, request, *args, **kwargs):
        form = TestimonialForm(request.POST, request.FILES)
        
        if form.is_valid():
            testimonial = form.save(commit=False)
            
            # Associer l'utilisateur s'il est connecté
            if request.user.is_authenticated:
                testimonial.user = request.user
            
            # Statut initial
            testimonial.status = 'pending'
            
            testimonial.save()
            
            # Envoyer une notification aux admins
            self.send_testimonial_notification(testimonial)
            
            # Envoyer un email de confirmation à l'utilisateur
            if request.user.is_authenticated and request.user.email:
                self.send_confirmation_email(testimonial, request.user)
            
            messages.success(
                request,
                'Merci pour votre témoignage ! Il sera examiné par notre équipe avant publication.'
            )
            
            return render(request, 'testimonials/thank_you.html')
        
        context = {'form': form}
        return render(request, 'testimonials/create.html', context)
    
    def send_testimonial_notification(self, testimonial, request):
        """Envoyer une notification pour un nouveau témoignage"""
        try:
            admins = User.objects.filter(is_staff=True)
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if admin_emails:
                subject = f'Nouveau témoignage soumis: {testimonial.title}'
                
                context = {
                    'testimonial': testimonial,
                    'admin_url': request.build_absolute_uri('/admin/')
                }
                
                message = render_to_string('emails/testimonial_notification.txt', context)
                html_message = render_to_string('emails/testimonial_notification.html', context)
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    html_message=html_message,
                    fail_silently=True,
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")
    
    def send_confirmation_email(self, testimonial, user, request):
        """Envoyer un email de confirmation"""
        try:
            subject = 'Confirmation de votre témoignage - FarmGen'
            
            context = {
                'testimonial': testimonial,
                'user': user,
                'site_url': request.build_absolute_uri('/')
            }
            
            message = render_to_string('emails/testimonial_confirmation.txt', context)
            html_message = render_to_string('emails/testimonial_confirmation.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de confirmation: {str(e)}")


class TestimonialAPIView(View):
    """API pour récupérer les témoignages pour la page contact"""
    
    def get(self, request, *args, **kwargs):
        try:
            limit = int(request.GET.get('limit', 6))
            
            # Récupérer les témoignages mis en avant
            testimonials = Testimonial.objects.filter(
                status='published',
                allow_display=True,
                is_featured=True
            ).order_by('-published_at')[:limit]
            
            # Préparer les données
            testimonials_data = []
            for testimonial in testimonials:
                # Générer une initiale pour le logo si pas de photo
                if testimonial.author_photo:
                    logo_html = f'<img src="{testimonial.author_photo.url}" alt="{testimonial.author_name}" class="testimonial-photo">'
                else:
                    initial = testimonial.author_name[0].upper()
                    logo_html = f'<div class="testimonial-initial">{initial}</div>'
                
                testimonial_data = {
                    'id': str(testimonial.id),
                    'logo_html': logo_html,
                    'author_name': testimonial.author_name,
                    'author_role': testimonial.author_role,
                    'content': testimonial.content,
                    'rating': testimonial.rating,
                    'is_verified': testimonial.is_verified,
                }
                testimonials_data.append(testimonial_data)
            
            return JsonResponse({
                'success': True,
                'testimonials': testimonials_data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des témoignages: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class TestimonialCommentView(View):
    """Ajouter un commentaire à un témoignage"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            testimonial_id = data.get('testimonial_id')
            content = data.get('content')
            
            if not testimonial_id or not content:
                return JsonResponse({'success': False, 'error': 'Données manquantes'}, status=400)
            
            testimonial = get_object_or_404(Testimonial, id=testimonial_id, status='published')
            
            # Créer le commentaire
            comment = Comment(
                user=request.user,
                testimonial=testimonial,
                content=content,
                status='approved' if request.user.is_superuser else 'pending'
            )
            
            # Enregistrer l'IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                comment.ip_address = x_forwarded_for.split(',')[0]
            else:
                comment.ip_address = request.META.get('REMOTE_ADDR')
            
            comment.user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            comment.save()
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': str(comment.id),
                    'user': {
                        'username': request.user.username,
                        'full_name': request.user.get_full_name() or request.user.username,
                    },
                    'content': comment.content,
                    'created_at': comment.created_at.strftime('%d/%m/%Y à %H:%M'),
                    'status': comment.status,
                }
            })
                
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du commentaire au témoignage: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)


# ============ VUES ADMIN ============

@method_decorator(login_required, name='dispatch')
class AdminCommentsView(View):
    """Interface d'administration des commentaires"""
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('home')
        
        status = request.GET.get('status', 'pending')
        search = request.GET.get('search', '')
        
        # Filtrer les commentaires
        comments = Comment.objects.all().select_related('user', 'article')
        
        if status != 'all':
            comments = comments.filter(status=status)
        
        if search:
            comments = comments.filter(
                Q(content__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        comments = comments.order_by('-created_at')
        
        # Pagination
        paginator = Paginator(comments, 20)
        page = request.GET.get('page', 1)
        page_obj = paginator.get_page(page)
        
        context = {
            'comments': page_obj,
            'status_choices': Comment.STATUS_CHOICES,
            'current_status': status,
            'search_query': search,
        }
        
        return render(request, 'admin/comments.html', context)


@method_decorator(login_required, name='dispatch')
class AdminTestimonialsView(View):
    """Interface d'administration des témoignages"""
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('home')
        
        status = request.GET.get('status', 'pending')
        search = request.GET.get('search', '')
        
        # Filtrer les témoignages
        testimonials = Testimonial.objects.all().select_related('user')
        
        if status != 'all':
            testimonials = testimonials.filter(status=status)
        
        if search:
            testimonials = testimonials.filter(
                Q(title__icontains=search) |
                Q(author_name__icontains=search) |
                Q(content__icontains=search)
            )
        
        testimonials = testimonials.order_by('-created_at')
        
        # Pagination
        paginator = Paginator(testimonials, 20)
        page = request.GET.get('page', 1)
        page_obj = paginator.get_page(page)
        
        context = {
            'testimonials': page_obj,
            'status_choices': Testimonial.STATUS_CHOICES,
            'current_status': status,
            'search_query': search,
        }
        
        return render(request, 'admin/testimonials.html', context)


@method_decorator(login_required, name='dispatch')
class ApproveCommentView(View):
    """Approuver un commentaire"""
    
    def post(self, request, comment_id, *args, **kwargs):
        if not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
        
        try:
            comment = get_object_or_404(Comment, id=comment_id)
            comment.approve(request.user)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Erreur lors de l'approbation du commentaire: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)


@method_decorator(login_required, name='dispatch')
class RejectCommentView(View):
    """Rejeter un commentaire"""
    
    def post(self, request, comment_id, *args, **kwargs):
        if not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
        
        try:
            comment = get_object_or_404(Comment, id=comment_id)
            reason = request.POST.get('reason', '')
            comment.reject(request.user, reason)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Erreur lors du rejet du commentaire: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)


@method_decorator(login_required, name='dispatch')
class PublishTestimonialView(View):
    """Publier un témoignage"""
    
    def post(self, request, testimonial_id, *args, **kwargs):
        if not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
        
        try:
            testimonial = get_object_or_404(Testimonial, id=testimonial_id)
            testimonial.status = 'published'
            testimonial.published_at = timezone.now()
            testimonial.save()
            
            # Envoyer un email de notification à l'auteur
            if testimonial.user and testimonial.user.email:
                self.send_publication_email(testimonial)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Erreur lors de la publication du témoignage: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Erreur serveur'}, status=500)
    
    def send_publication_email(self, testimonial, request):
        """Envoyer un email de notification de publication"""
        try:
            subject = f'Votre témoignage a été publié - FarmGen'
            
            context = {
                'testimonial': testimonial,
                'user': testimonial.user,
                'site_url': request.build_absolute_uri('/'),
                'testimonial_url': request.build_absolute_uri(f'/testimonials/{testimonial.id}/')
            }
            
            message = render_to_string('emails/testimonial_published.txt', context)
            html_message = render_to_string('emails/testimonial_published.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[testimonial.user.email],
                html_message=html_message,
                fail_silently=True,
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de publication: {str(e)}")
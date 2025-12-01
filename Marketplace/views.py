import io
import qrcode
import base64
from decimal import Decimal
import json

from django.views.static import serve
from django.conf import settings
from django.http import JsonResponse, HttpResponse, FileResponse
from django.db.models import Q, Avg, Count, Sum
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from account.models import User
from .models import Shop, Product, Favorite, Category, ProductImage, ProductLike, ProductView, SearchHistory
from payments.models import Order, MethodPaid, PaymentVerification
# Create your views here.
from django.utils import timezone
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from xhtml2pdf import pisa





   
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
def order_listing(request):
    # Filtres de période
    period = request.GET.get('period', 'monthly')  # daily, weekly, monthly, yearly, custom
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_filter = request.GET.getlist('status')
    payment_method_filter = request.GET.get('payment_method')
    
    # Déterminer les dates en fonction de la période
    today = timezone.now().date()
    
    if period == 'daily':
        date_filter = today
        date_label = "Aujourd'hui"
    elif period == 'weekly':
        date_filter = today - timedelta(days=7)
        date_label = "Cette semaine"
    elif period == 'monthly':
        date_filter = today.replace(day=1)
        date_label = "Ce mois"
    elif period == 'yearly':
        date_filter = today.replace(month=1, day=1)
        date_label = "Cette année"
    elif period == 'custom' and start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            date_filter = (start_date_obj, end_date_obj)
            date_label = f"Du {start_date} au {end_date}"
        except ValueError:
            date_filter = None
            date_label = "Période personnalisée"
    else:
        date_filter = today.replace(day=1)  # Par défaut: mois courant
        date_label = "Ce mois"
    
    # Base queryset selon le rôle utilisateur
    if request.user.is_superuser:
        orders = Order.objects.all()
    elif hasattr(request.user, 'shop'):
        # Vendeur: commandes de sa boutique seulement
        shop = request.user.shop
        orders = Order.objects.filter(shop_id=shop.id)
    else:
        # Client: ses commandes seulement
        orders = Order.objects.filter(user=request.user)
    
    # Appliquer le filtre de période
    if date_filter:
        if isinstance(date_filter, tuple):
            # Période personnalisée
            start_date_obj, end_date_obj = date_filter
            orders = orders.filter(
                created_at__date__gte=start_date_obj,
                created_at__date__lte=end_date_obj
            )
        else:
            orders = orders.filter(created_at__date__gte=date_filter)
    
    # Appliquer les filtres de statut
    if status_filter:
        orders = orders.filter(status__in=status_filter)
    
    # Appliquer le filtre de méthode de paiement
    if payment_method_filter:
        orders = orders.filter(payment_method=payment_method_filter)
    
    # Trier par date de création (plus récent en premier)
    orders = orders.order_by('-created_at')
    
    # Statistiques globales
    total_orders_count = orders.count()
    total_amount = orders.aggregate(Sum('final_amount'))['final_amount__sum'] or 0
    total_tax = orders.aggregate(Sum('tax_amount'))['tax_amount__sum'] or 0
    
    # Statistiques par statut
    status_stats = orders.values('status').annotate(
        count=Count('id'),
        amount=Sum('final_amount')
    ).order_by('status')
    
    # Statistiques par méthode de paiement
    payment_stats = orders.values('payment_method').annotate(
        count=Count('id'),
        amount=Sum('final_amount')
    ).order_by('payment_method')
    
    # Statistiques quotidiennes (pour le graphique)
    daily_stats = orders.extra(
        {'date': "DATE(created_at)"}
    ).values('date').annotate(
        count=Count('id'),
        amount=Sum('final_amount')
    ).order_by('date')[:30]  # 30 derniers jours
    
    # Top produits (depuis les cart_items)
    product_stats = {}
    for order in orders:
        for item in order.cart_items:
            product_name = item.get('name', 'Produit inconnu')
            quantity = item.get('quantity', 0)
            price = item.get('price', 0)
            
            if product_name not in product_stats:
                product_stats[product_name] = {
                    'quantity': 0,
                    'revenue': 0
                }
            
            product_stats[product_name]['quantity'] += quantity
            product_stats[product_name]['revenue'] += quantity * price
    
    # Convertir en liste triée par revenue
    top_products = sorted(
        [{'name': k, **v} for k, v in product_stats.items()],
        key=lambda x: x['revenue'],
        reverse=True
    )[:10]
    
    # Pour les vendeurs/admins: statistiques par client
    if request.user.is_seller or hasattr(request.user, 'shop'):
        customer_stats = orders.values(
            'customer_email', 'customer_first_name', 'customer_last_name'
        ).annotate(
            order_count=Count('id'),
            total_spent=Sum('final_amount'),
            avg_order=Avg('final_amount')
        ).order_by('-total_spent')[:10]
    else:
        customer_stats = None
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page', 1)
    page_orders = paginator.get_page(page_number)
    
    # Formater les données pour le template
    formatted_orders = []
    for order in page_orders:
        # Récupérer les informations de la boutique si admin
        shop_info = None
        if request.user.is_superuser:
            try:
                shop = Shop.objects.get(id=order.shop_id)
                shop_info = {
                    'id': shop.id,
                    'title': shop.title,
                    'logo': shop.couverture.url if shop.couverture else None
                }
            except Shop.DoesNotExist:
                shop_info = None
        
        # Calculer le nombre total d'articles
        total_items = sum(item.get('quantity', 0) for item in order.cart_items)
        
        formatted_orders.append({
            'id': order.id,
            'order_number': str(order.id)[:8].upper(),
            'created_at': order.created_at,
            'updated_at': order.updated_at,
            'status': order.status,
            'status_display': order.get_status_display(),
            'total_amount': order.total_amount,
            'tax_amount': order.tax_amount,
            'final_amount': order.final_amount,
            'customer': {
                'full_name': order.full_name,
                'email': order.customer_email,
                'phone': order.customer_phone
            },
            'payment_method': order.payment_method,
            'payment_method_display': order.get_payment_method_display(),
            'payment_verified': order.payment_verified,
            'payment_verified_at': order.payment_verified_at,
            'cart_items': order.cart_items,
            'shop': shop_info,
            'total_items': total_items,
            'has_payment_proof': bool(order.payment_proof)
        })
    
    # Contexte
    context = {
        # Données principales
        'orders': formatted_orders,
        'page_orders': page_orders,
        'period': period,
        'date_label': date_label,
        'start_date': start_date,
        'end_date': end_date,
        
        # Statistiques
        'total_orders_count': total_orders_count,
        'total_amount': total_amount,
        'total_tax': total_tax,
        'status_stats': status_stats,
        'payment_stats': payment_stats,
        'daily_stats': json.dumps(list(daily_stats), default=str),
        'top_products': top_products,
        'customer_stats': customer_stats,
        
        # Filtres disponibles
        'status_choices': Order.STATUS_CHOICES,
        'payment_method_choices': Order.PAYMENT_METHODS,
        
        # Utilisateur
        'is_admin': request.user.is_superuser,
        'is_seller': hasattr(request.user, 'shop'),
        'user': request.user,
    }
    
    # Si requête AJAX, retourner JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'orders': formatted_orders,
            'stats': {
                'total_orders': total_orders_count,
                'total_amount': total_amount,
                'total_tax': total_tax,
                'daily_stats': list(daily_stats)
            },
            'pagination': {
                'has_next': page_orders.has_next(),
                'has_previous': page_orders.has_previous(),
                'current_page': page_orders.number,
                'total_pages': page_orders.paginator.num_pages,
                'total_count': page_orders.paginator.count
            }
        })
    
    return render(request, 'marketplace/listingCommand.html', context)


@login_required
def download_invoice(request, order_id):
    """Télécharger une facture PDF"""
    try:
        # Vérifier les permissions
        if request.user.is_superuser:
            order = Order.objects.get(id=order_id)
        elif hasattr(request.user, 'shop'):
            # Vendeur: vérifier que la commande appartient à sa boutique
            shop = request.user.shop
            order = Order.objects.get(id=order_id, shop_id=shop.id)
        else:
            # Client: vérifier que c'est sa commande
            order = Order.objects.get(id=order_id, user=request.user)
        
        # Récupérer les informations de la boutique
        try:
            shop = Shop.objects.get(id=order.shop_id)
        except Shop.DoesNotExist:
            shop = None
        
        # Calculer les totaux des articles
        items_total = sum(
            float(item.get('price', 0)) * int(item.get('quantity', 0))
            for item in order.cart_items
        )
        
        # Calculer la TVA (18% par défaut)
        vat_rate = 0.18
        vat_amount = items_total * Decimal(vat_rate)
        
        # Générer QR code pour la facture
        qr_data = f"""
Facture N°: {str(order.id)[:8].upper()}
Client: {order.full_name}
Date: {order.created_at.strftime('%d/%m/%Y')}
Montant HT: {items_total:.2f} FCFA
TVA ({vat_rate*100}%): {vat_amount:.2f} FCFA
Montant TTC: {order.final_amount:.2f} FCFA
        """.strip()
        
        qr_img = qrcode.make(qr_data)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
        
        # Contexte pour le template PDF
        context = {
            'order': order,
            'shop': shop,
            'items_total': items_total,
            'vat_rate': vat_rate * 100,
            'vat_amount': vat_amount,
            'qr_code': qr_base64,
            'today': timezone.now().strftime("%d/%m/%Y"),
            'generated_at': timezone.now().strftime("%d/%m/%Y %H:%M"),
        }
        
        # Rendre le template HTML
        html_string = render_to_string('marketplace/invoice_template.html', context)
        
        # Créer le PDF
        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            html_string,
            dest=pdf_file,
            encoding='UTF-8'
        )
        
        if pisa_status.err:
            return HttpResponse('Erreur lors de la génération du PDF', status=500)
        
        # Retourner le PDF
        pdf_file.seek(0)
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture_{order.id}.pdf"'
        
        return response
        
    except Order.DoesNotExist:
        return HttpResponse('Commande non trouvée', status=404)
    except PermissionError:
        return HttpResponse('Non autorisé', status=403)
    except Exception as e:
        print(f"Erreur génération PDF: {e}")
        return HttpResponse('Erreur interne', status=500)


@login_required
def update_order_status(request, order_id):
    """API pour mettre à jour le statut d'une commande"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    try:
        # Vérifier les permissions
        if not (request.user.is_superuser or hasattr(request.user, 'shop')):
            return JsonResponse({'error': 'Non autorisé'}, status=403)
        
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in dict(Order.STATUS_CHOICES):
            return JsonResponse({'error': 'Statut invalide'}, status=400)
        
        # Récupérer la commande
        if request.user.is_superuser:
            order = Order.objects.get(id=order_id)
        else:
            shop = request.user.shop
            order = Order.objects.get(id=order_id, shop_id=shop.id)
        
        # Mettre à jour le statut
        old_status = order.status
        order.status = new_status
        
        # Si le statut est payment_verified, marquer comme vérifié
        if new_status == Order.STATUS_PAYMENT_VERIFIED:
            order.payment_verified = True
            order.payment_verified_at = timezone.now()
        
        order.save()
        
        # Créer une entrée de vérification si nécessaire
        if new_status == Order.STATUS_PAYMENT_VERIFIED:
            PaymentVerification.objects.create(
                order=order,
                verified_by=request.user,
                is_approved=True,
                notes=f"Statut changé de {old_status} à {new_status}"
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Statut mis à jour de {old_status} à {new_status}',
            'order': {
                'id': str(order.id),
                'status': order.status,
                'status_display': order.get_status_display(),
                'payment_verified': order.payment_verified,
                'updated_at': order.updated_at.isoformat()
            }
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Commande non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def export_orders(request, format_type):
    """Exporter les commandes en CSV ou JSON"""
    # Appliquer les mêmes filtres que order_listing
    # ... (code similaire à order_listing pour filtrer)
    
    if format_type == 'csv':
        # Générer CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="commandes.csv"'
        
        # Écrire le CSV
        writer = csv.writer(response)
        writer.writerow([
            'N° Commande', 'Date', 'Client', 'Email', 'Téléphone',
            'Statut', 'Méthode Paiement', 'Montant HT', 'TVA', 'Montant TTC',
            'Boutique', 'Articles'
        ])
        
        for order in orders:
            items_str = ', '.join([
                f"{item.get('name')} (x{item.get('quantity')})"
                for item in order.cart_items[:3]
            ])
            if len(order.cart_items) > 3:
                items_str += f'... (+{len(order.cart_items) - 3})'
            
            writer.writerow([
                str(order.id)[:8].upper(),
                order.created_at.strftime('%d/%m/%Y'),
                order.full_name,
                order.customer_email,
                order.customer_phone,
                order.get_status_display(),
                order.get_payment_method_display(),
                order.total_amount,
                order.tax_amount,
                order.final_amount,
                order.shop_id,
                items_str
            ])
        
        return response
    
    elif format_type == 'json':
        # Générer JSON
        data = []
        for order in orders:
            data.append({
                'id': str(order.id),
                'order_number': str(order.id)[:8].upper(),
                'created_at': order.created_at.isoformat(),
                'customer': order.full_name,
                'email': order.customer_email,
                'phone': order.customer_phone,
                'status': order.status,
                'status_display': order.get_status_display(),
                'payment_method': order.payment_method,
                'payment_method_display': order.get_payment_method_display(),
                'total_amount': order.total_amount,
                'tax_amount': order.tax_amount,
                'final_amount': order.final_amount,
                'shop_id': order.shop_id,
                'cart_items': order.cart_items
            })
        
        return JsonResponse(data, safe=False)
    
    return HttpResponse('Format non supporté', status=400)

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
    


@login_required
def order_details(request, order_id):
    """Afficher les détails complets d'une commande"""
    try:
        # Vérifier les permissions selon le rôle
        if request.user.is_superuser:
            # Admin: peut voir toutes les commandes
            order = get_object_or_404(Order, id=order_id)
        elif hasattr(request.user, 'shop'):
            # Vendeur: seulement les commandes de sa boutique
            shop = request.user.shop
            order = get_object_or_404(Order, id=order_id, shop_id=shop.id)
        else:
            # Client: seulement ses propres commandes
            order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Récupérer les informations de la boutique depuis votre modèle Shop
        shop_info = None
        try:
            shop = Shop.objects.get(id=order.shop_id)
            shop_info = {
                'id': shop.id,
                'title': shop.title,
                'description': shop.description,
                'localisation': shop.localisation,
                'type_shop': shop.type_shop,
                'note': float(shop.note) if shop.note else None,
                'logo_url': shop.couverture.url if shop.couverture else None,
                'phone': shop.user.phone if hasattr(shop.user, 'phone') else None,
                'email': shop.user.email
            }
        except Shop.DoesNotExist:
            shop_info = None
        
        # Récupérer l'historique des vérifications de paiement
        verifications = PaymentVerification.objects.filter(order=order).order_by('-verified_at')
        verification_history = []
        for verification in verifications:
            verified_by_name = "Système"
            if verification.verified_by:
                if verification.verified_by.first_name and verification.verified_by.last_name:
                    verified_by_name = f"{verification.verified_by.first_name} {verification.verified_by.last_name}"
                else:
                    verified_by_name = verification.verified_by.username
            
            verification_history.append({
                'verified_by': verified_by_name,
                'verified_at': verification.verified_at,
                'is_approved': verification.is_approved,
                'notes': verification.notes
            })
        
        # Calculer les totaux détaillés
        cart_items = order.cart_items or []
        items_total_ht = Decimal('0')
        for item in cart_items:
            try:
                price = Decimal(str(item.get('price', 0)))
                quantity = int(item.get('quantity', 0))
                items_total_ht += price * quantity
            except (ValueError, TypeError):
                continue
        
        # Calculer la TVA (18% par défaut)
        vat_rate = Decimal('0.18')
        calculated_vat = items_total_ht * vat_rate
        items_total_ttc = items_total_ht + calculated_vat
        
        # Calculer le nombre total d'articles et d'articles uniques
        total_items = sum(int(item.get('quantity', 0)) for item in cart_items)
        unique_items = len(cart_items)
        
        # Formater les données de la commande
        order_data = {
            'id': str(order.id),
            'order_number': str(order.id)[:8].upper(),
            'created_at': order.created_at,
            'updated_at': order.updated_at,
            'status': order.status,
            'status_display': order.get_status_display(),
            
            # Totaux financiers
            'total_amount': order.total_amount,
            'tax_amount': order.tax_amount,
            'final_amount': order.final_amount,
            'items_total_ht': float(items_total_ht),
            'calculated_vat': float(calculated_vat),
            'items_total_ttc': float(items_total_ttc),
            
            # Informations client
            'customer': {
                'first_name': order.customer_first_name,
                'last_name': order.customer_last_name,
                'full_name': order.full_name,
                'email': order.customer_email,
                'phone': order.customer_phone,
                'user_id': order.user.id if order.user else None,
                'username': order.user.username if order.user else None
            },
            
            # Informations de paiement
            'payment_method': order.payment_method,
            'payment_method_display': order.get_payment_method_display(),
            'payment_phone': order.payment_phone,
            'payment_verified': order.payment_verified,
            'payment_verified_at': order.payment_verified_at,
            
            # Preuve de paiement
            'has_payment_proof': bool(order.payment_proof),
            'payment_proof_url': order.payment_proof.url if order.payment_proof else None,
            
            # Données du panier
            'cart_items': cart_items,
            'total_items': total_items,
            'unique_items': unique_items,
            
            # Informations boutique
            'shop': shop_info,
            'shop_id': order.shop_id,
            
            # Métadonnées
            'metadata': order.metadata or {},
            
            # Codes de paiement
            'qr_code_data': order.qr_code_data,
            'ussd_code': order.ussd_code,
            'whatsapp_link': order.whatsapp_link,
            
            # Historique
            'verification_history': verification_history,
            
            # Statut calculé
            'is_paid': order.status in ['paid', 'payment_verified'],
            'is_pending': order.status in ['pending', 'waiting_payment'],
            'is_failed': order.status in ['failed', 'refunded'],
            
            # Délais
            'days_since_creation': (timezone.now() - order.created_at).days,
            'is_overdue': (timezone.now() - order.created_at).days > 7 and order.status in ['pending', 'waiting_payment']
        }
        
        # Si requête AJAX, retourner JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Convertir les dates en format ISO pour JSON
            from django.core.serializers.json import DjangoJSONEncoder
            import json
            
            class CustomJSONEncoder(DjangoJSONEncoder):
                def default(self, obj):
                    if isinstance(obj, Decimal):
                        return float(obj)
                    if hasattr(obj, 'isoformat'):
                        return obj.isoformat()
                    return super().default(obj)
            
            response_data = {
                'success': True,
                'order': order_data,
                'permissions': {
                    'can_verify_payment': request.user.is_superuser or hasattr(request.user, 'shop'),
                    'can_update_status': request.user.is_superuser or hasattr(request.user, 'shop'),
                    'can_view_payment_proof': True,
                    'can_download_invoice': True
                }
            }
            
            return JsonResponse(response_data, encoder=CustomJSONEncoder)
        
        # Sinon, rendre le template HTML
        context = {
            'order': order_data,
            'page_title': f'Commande #{order_data["order_number"]}',
            'is_admin': request.user.is_superuser,
            'is_seller': hasattr(request.user, 'shop'),
            'user': request.user,
            'status_choices': Order.STATUS_CHOICES,
            'payment_method_choices': Order.PAYMENT_METHODS,
        }
        
        return render(request, 'marketplace/order_details.html', context)
        
    except Order.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Commande non trouvée'
            }, status=404)
        return render(request, '404.html', status=404)
    
    except Exception as e:
        print(f"Erreur dans order_details: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        return render(request, '500.html', {'error': str(e)}, status=500)
    


@login_required
def payment_proof(request, order_id):
    """Afficher ou télécharger la preuve de paiement d'une commande"""
    try:
        # Vérifier les permissions selon le rôle
        if request.user.is_superuser:
            # Admin: peut voir toutes les preuves
            order = get_object_or_404(Order, id=order_id)
        elif hasattr(request.user, 'shop'):
            # Vendeur: seulement les commandes de sa boutique
            shop = request.user.shop
            order = get_object_or_404(Order, id=order_id, shop_id=shop.id)
        else:
            # Client: seulement ses propres preuves
            order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Vérifier si une preuve de paiement existe
        if not order.payment_proof:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Aucune preuve de paiement disponible pour cette commande'
                }, status=404)
            
            # Afficher un message d'erreur dans le template
            context = {
                'order': order,
                'error': 'Aucune preuve de paiement disponible',
                'order_number': str(order.id)[:8].upper(),
                'order_full_name': order.full_name,
                'order_final_amount': order.final_amount
            }
            return render(request, 'marketplace/payment_proof.html', context, status=404)
        
        # Déterminer l'action (view ou download)
        action = request.GET.get('action', 'view')
        
        # Si c'est une requête AJAX pour des infos sur la preuve
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            verified_by_name = "Système"
            if order.payment_verified_at and order.user:
                if order.user.first_name and order.user.last_name:
                    verified_by_name = f"{order.user.first_name} {order.user.last_name}"
                else:
                    verified_by_name = order.user.username
            
            response_data = {
                'success': True,
                'payment_proof': {
                    'url': order.payment_proof.url,
                    'filename': os.path.basename(order.payment_proof.name),
                    'size': order.payment_proof.size if hasattr(order.payment_proof, 'size') else None,
                    'uploaded_at': order.payment_verified_at.isoformat() if order.payment_verified_at else order.updated_at.isoformat(),
                    'verified': order.payment_verified,
                    'verified_at': order.payment_verified_at.isoformat() if order.payment_verified_at else None,
                    'verified_by': verified_by_name
                },
                'order': {
                    'id': str(order.id),
                    'order_number': str(order.id)[:8].upper(),
                    'status': order.status,
                    'status_display': order.get_status_display(),
                    'final_amount': order.final_amount,
                    'payment_method': order.get_payment_method_display(),
                    'customer_name': order.full_name
                }
            }
            return JsonResponse(response_data)
        
        # Formater les informations de la preuve
        proof_info = {
            'url': order.payment_proof.url,
            'filename': os.path.basename(order.payment_proof.name),
            'size': format_file_size(order.payment_proof.size) if hasattr(order.payment_proof, 'size') else 'Inconnu',
            'uploaded_at': order.payment_verified_at or order.updated_at,
            'verified': order.payment_verified,
            'verified_by': None,
            'verified_at': order.payment_verified_at
        }
        
        # Déterminer qui a vérifié
        if order.payment_verified_at and order.user:
            if order.user.first_name and order.user.last_name:
                proof_info['verified_by'] = f"{order.user.first_name} {order.user.last_name}"
            else:
                proof_info['verified_by'] = order.user.username
        
        # Pour le téléchargement direct
        if action == 'download':
            # Créer une réponse de fichier avec le bon Content-Type
            file_path = order.payment_proof.path
            
            # Vérifier si le fichier existe physiquement
            if not os.path.exists(file_path):
                # Essayer de le récupérer depuis le storage
                try:
                    from django.core.files.storage import default_storage
                    if default_storage.exists(order.payment_proof.name):
                        # Servir depuis le storage
                        response = HttpResponse(
                            default_storage.open(order.payment_proof.name).read(),
                            content_type='application/octet-stream'
                        )
                    else:
                        raise FileNotFoundError("Fichier non trouvé dans le storage")
                except Exception as e:
                    print(f"Erreur lors du téléchargement: {e}")
                    return HttpResponse("Fichier non trouvé", status=404)
            else:
                # Servir le fichier local
                try:
                    response = FileResponse(
                        open(file_path, 'rb'),
                        content_type='application/octet-stream'
                    )
                except FileNotFoundError:
                    return HttpResponse("Fichier non trouvé", status=404)
            
            # Définir le nom du fichier pour le téléchargement
            filename = f"preuve_paiement_{str(order.id)[:8]}_{os.path.basename(file_path)}"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        # Pour la visualisation dans le navigateur
        elif action == 'view':
            # Utiliser la vue serve de Django pour servir le fichier
            file_path = order.payment_proof.path
            
            if not os.path.exists(file_path):
                # Essayer depuis le storage
                try:
                    from django.core.files.storage import default_storage
                    if default_storage.exists(order.payment_proof.name):
                        file_obj = default_storage.open(order.payment_proof.name)
                        content = file_obj.read()
                        file_obj.close()
                        
                        # Déterminer le content-type
                        import mimetypes
                        content_type, _ = mimetypes.guess_type(order.payment_proof.name)
                        if not content_type:
                            content_type = 'application/octet-stream'
                        
                        response = HttpResponse(content, content_type=content_type)
                        response['Content-Disposition'] = f'inline; filename="{os.path.basename(order.payment_proof.name)}"'
                        return response
                except Exception as e:
                    print(f"Erreur lors de la visualisation: {e}")
                    pass
            
            # Servir le fichier local avec le bon content-type
            try:
                return serve(request, order.payment_proof.name, document_root=settings.MEDIA_ROOT)
            except Exception as e:
                return HttpResponse(f"Erreur lors du chargement du fichier: {str(e)}", status=500)
        
        # Sinon, afficher la page de visualisation complète
        else:
            # Informations sur les formats supportés
            supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'webp']
            file_extension = proof_info['filename'].split('.')[-1].lower() if '.' in proof_info['filename'] else ''
            is_image = file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']
            is_pdf = file_extension == 'pdf'
            
            context = {
                'order': {
                    'id': order.id,
                    'order_number': str(order.id)[:8].upper(),
                    'full_name': order.full_name,
                    'final_amount': order.final_amount,
                    'status': order.status,
                    'payment_verified': order.payment_verified,
                    'payment_method': order.get_payment_method_display(),
                },
                'proof': proof_info,
                'order_number': str(order.id)[:8].upper(),
                'is_admin': request.user.is_superuser,
                'is_seller': hasattr(request.user, 'shop'),
                'is_image': is_image,
                'is_pdf': is_pdf,
                'file_extension': file_extension,
                'supported_formats': supported_formats,
                'can_download': True,
                'can_verify': (request.user.is_superuser or hasattr(request.user, 'shop')) and not order.payment_verified,
                'page_title': f'Preuve de paiement - Commande #{str(order.id)[:8].upper()}'
            }
            
            return render(request, 'payments/payment_proof.html', context)
            
    except Order.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Commande non trouvée'
            }, status=404)
        return render(request, '404.html', status=404)
    
    except Exception as e:
        print(f"Erreur dans payment_proof: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        
        context = {
            'error': str(e),
            'error_message': 'Une erreur est survenue lors du chargement de la preuve de paiement'
        }
        return render(request, '500.html', context, status=500)


def format_file_size(size_bytes):
    """Formater la taille du fichier en unités lisibles"""
    if size_bytes is None:
        return "Inconnu"
    
    try:
        size_bytes = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    except (ValueError, TypeError):
        return "Inconnu"
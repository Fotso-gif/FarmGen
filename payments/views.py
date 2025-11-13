import os
import qrcode
import base64
from io import BytesIO
import json
import logging
from django.utils import timezone
from cart.views import  get_cart_data
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from .models import Order, MethodPaid, PaymentVerification
from django.core.files.storage import default_storage
from .utils import image_processor  # Assure-toi que le chemin est bon

logger = logging.getLogger(__name__)

# Session-cart helpers
def _get_cart(session):
    return session.get('cart', {})

def _save_cart(session, cart):
    session['cart'] = cart
    session.modified = True

#Pages Cart/Checkout
def cart_page(request):
    cart, cart_count, cart_total = get_cart_data(request.session)
    
    # Calcul des taxes (10% comme indiqué dans votre template)
    tax = cart_total * 0.10
    total_with_tax = cart_total + tax
    
    context = {
        'cart': cart,
        'cart_count': cart_count,
        'cart_total': cart_total,
        'tax': tax,
        'total_with_tax': total_with_tax,
    }
    return render(request, 'payments/cart.html', context)

def checkout_page(request):
    """Page de checkout principale"""
    cart, cart_count, cart_total = get_cart_data(request.session)
    
    if cart_count == 0:
        return redirect('cart-page')
    
    # Calcul des taxes (10%)
    tax = cart_total * 0.10
    total_with_tax = cart_total + tax
    
    # Récupérer la première boutique du panier (vous pouvez adapter selon votre logique)
    shop_id = None
    if cart:
        first_item = next(iter(cart.values()))
        shop_id = first_item.get('shop_id')  # Assurez-vous que shop_id est stocké dans le panier
    
    # Récupérer les méthodes de paiement de la boutique
    payment_methods = MethodPaid.objects.filter(shop_id=shop_id, status=True) if shop_id else MethodPaid.objects.none()
    
    context = {
        'cart': cart,
        'cart_count': cart_count,
        'cart_total': cart_total,
        'tax': tax,
        'total_with_tax': total_with_tax,
        'payment_methods': payment_methods,
        'shop_id': shop_id,
    }
    return render(request, 'payments/checkout.html', context)

@require_http_methods(["POST"])
def process_checkout(request, payment_method):
    """Traiter la commande et générer les infos de paiement"""
    try:
        cart, cart_count, cart_total = get_cart_data(request.session)
        
        if cart_count == 0:
            return JsonResponse({'success': False, 'message': 'Votre panier est vide'})
        
        # Récupérer les données du formulaire
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        payment_phone = request.POST.get('payment_phone')
        
        # Validation des données
        if not all([first_name, last_name, email, phone]):
            return JsonResponse({'success': False, 'message': 'Veuillez remplir tous les champs obligatoires'})
        
        if payment_method in ['om', 'momo', 'whatsapp'] and not payment_phone:
            return JsonResponse({'success': False, 'message': f'Veuillez entrer votre numéro {payment_method.upper()}'})
        
        # Calcul des montants
        tax = cart_total * 0.10
        final_amount = cart_total + tax
        
        # Récupérer la boutique (premier item du panier)
        shop_id = None
        if cart:
            first_item = next(iter(cart.values()))
            shop_id = first_item.get('shop_id')
        
        # Créer la commande
        order = Order.objects.create(
            user = request.user,
            total_amount=cart_total,
            tax_amount=tax,
            final_amount=final_amount,
            customer_first_name=first_name,
            customer_last_name=last_name,
            customer_email=email,
            customer_phone=phone,
            payment_method=payment_method,
            payment_phone=payment_phone,
            cart_items=list(cart.values()),
            shop_id=shop_id,
            status=Order.STATUS_WAITING_PAYMENT
        )
        
        response_data = {
            'success': True,
            'order_id': str(order.id),
            'message': 'Commande créée avec succès'
        }
        
        # Générer les infos de paiement selon la méthode
        if payment_method == 'whatsapp':
            whatsapp_link = generate_whatsapp_link(order, payment_phone)
            order.whatsapp_link = whatsapp_link
            order.save()
            response_data['whatsapp_link'] = whatsapp_link
            
        elif payment_method in ['om', 'momo']:
            qr_code_base64, ussd_code = generate_payment_qr(order, payment_method)
            order.qr_code_data = qr_code_base64
            order.ussd_code = ussd_code
            order.save()
            response_data['qrcode'] = qr_code_base64
            response_data['ussd_code'] = ussd_code
            response_data['paiementMethod'] = payment_method
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erreur lors du traitement: {str(e)}'})

def generate_whatsapp_link(order, phone_number):
    """Générer le lien WhatsApp pour le paiement"""
    message = f"Bonjour, je souhaite payer ma commande {order.id} d'un montant de {order.final_amount} FCFA."
    whatsapp_url = f"https://wa.me/message/RBJXVFN6B5LHG1?text={message}"
    return whatsapp_url

def generate_payment_qr(order, method):
    """Générer QR code et code USSD pour OM/MOMO"""
    # Données pour le QR code (à adapter selon votre API de paiement)
    payment_data = {
        'order_id': str(order.id),
        'amount': order.final_amount,
        'method': method,
        'currency': 'XAF'
    }
    
    # Générer QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(payment_data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Générer code USSD (exemple)
    if method == 'om':
        ussd_code = f"#150*1*1*674907032*{order.final_amount}#"
    else:  # momo
        ussd_code = f"*126*1*658094842*{order.final_amount}#"
    
    return qr_code_base64, ussd_code

@require_http_methods(["POST"])
@csrf_exempt
def upload_payment_proof(request, order_id):
    """Uploader et vérifier la preuve de paiement (avec OCR automatique)"""
    try:
        order = get_object_or_404(Order, id=order_id)

        if 'payment_proof' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'Aucun fichier fourni'})

        payment_proof = request.FILES['payment_proof']

        # Vérifications du fichier
        if payment_proof.size > 5 * 1024 * 1024:  # 5MB max
            return JsonResponse({'success': False, 'message': 'Fichier trop volumineux (max 5MB)'})

        if not payment_proof.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'message': 'Format de fichier non supporté'})

        # Sauvegarder le fichier temporairement pour OCR
        file_name = f"payment_proof_{order_id}_{payment_proof.name}"
        file_path = default_storage.save(f'payment_proofs/{file_name}', payment_proof)

        full_file_path = default_storage.path(file_path)

        # === ÉTAPE OCR ===
        extracted_data = image_processor(full_file_path)

        if "erreur" in extracted_data:
            # Nettoyer le fichier temporaire si besoin
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            return JsonResponse({
                'success': False,
                'message': f'Erreur OCR: {extracted_data["erreur"]}'
            })

        # Sauvegarder le fichier dans la commande même si OCR échoue partiellement
        order.payment_proof = file_path
        order.save()

        # === VÉRIFICATION AUTOMATIQUE ===
        auto_verified = False
        verification_message = "Preuve uploadée. En attente de vérification manuelle."

        # Vérifier le montant
        extracted_amount = extracted_data.get("montant")
        expected_amount = float(order.final_amount)

        if extracted_amount is None:
            verification_message = "Montant non détecté dans l'image."
        elif abs(extracted_amount - expected_amount) > 1:  # Tolérance de 1 XAF
            verification_message = f"Montant incorrect. Attendu : {expected_amount} XAF, trouvé : {extracted_amount} XAF."
        else:
            # Vérifier le destinataire (nom et numéro)
            extracted_nom = extracted_data.get("destinataire")
            extracted_numero = extracted_data.get("numero_destinataire")

            if not extracted_nom or not extracted_numero:
                verification_message = "Nom ou numéro du destinataire non détecté."
            else:
                # Rechercher dans MethodPaid lié au shop de la commande
                # Supposons que l'Order a un champ `shop` (sinon adapte selon ton modèle)
                try:
                    shop = order.shop  # ← Assure-toi que ton modèle Order a un champ `shop`
                except AttributeError:
                    verification_message = "La commande n'est pas liée à un shop."
                else:
                    method_paid_qs = MethodPaid.objects.filter(
                        shop=shop,
                        nom__iexact=extracted_nom.strip(),
                        numero=extracted_numero,
                        status=True  # Optionnel : ne vérifier que les comptes actifs
                    )

                    if method_paid_qs.exists():
                        # ✅ TOUT CORRESPOND → VÉRIFICATION AUTOMATIQUE
                        auto_verified = True
                        order.payment_verified = True
                        order.payment_verified_at = timezone.now()
                        order.status = Order.STATUS_PAID
                        order.save()

                        PaymentVerification.objects.create(
                            order=order,
                            verified_by=None,  # ou un utilisateur système si tu veux
                            is_approved=True,
                            notes=f"Paiement vérifié automatiquement via OCR. Données extraites : {extracted_data}"
                        )

                        # Vider le panier
                        request.session['cart'] = {}
                        request.session.modified = True

                        verification_message = "Paiement vérifié automatiquement avec succès !"
                    else:
                        verification_message = f"Aucun compte de paiement trouvé pour le nom '{extracted_nom}' et le numéro '{extracted_numero}'."

        return JsonResponse({
            'success': True,
            'verified': auto_verified,
            'message': verification_message,
            'data': {
                'montant': extracted_amount,
                'destinataire': extracted_data.get("destinataire"),
                'numero_destinataire': extracted_data.get("numero_destinataire"),
                'date_heure': extracted_data.get("date_heure"),
                'transaction_id': extracted_data.get("transaction_id"),
                'solde': extracted_data.get("solde"),
                'texte_complet': extracted_data.get("texte_complet")[:200] + "..." if extracted_data.get("texte_complet") else ""
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erreur lors de l\'upload: {str(e)}'})
    
@require_http_methods(["POST"])
def verify_payment_manual(request, order_id):
    """Vérification manuelle du paiement par l'admin"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        if not order.payment_proof:
            return JsonResponse({'success': False, 'message': 'Aucune preuve de paiement fournie'})
        
        # Marquer comme vérifié et payé
        order.payment_verified = True
        order.payment_verified_at = timezone.now()
        order.status = Order.STATUS_PAID
        order.save()
        
        # Créer un enregistrement de vérification
        PaymentVerification.objects.create(
            order=order,
            verified_by=request.user if request.user.is_authenticated else None,
            is_approved=True,
            notes="Paiement vérifié manuellement"
        )
        
        # Vider le panier après paiement confirmé
        request.session['cart'] = {}
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': 'Paiement vérifié et confirmé avec succès!',
            'order_id': str(order.id)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erreur lors de la vérification: {str(e)}'})

@require_http_methods(["GET"])
def order_status(request, order_id):
    """Vérifier le statut d'une commande"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        return JsonResponse({
            'success': True,
            'status': order.status,
            'payment_verified': order.payment_verified,
            'final_amount': order.final_amount
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
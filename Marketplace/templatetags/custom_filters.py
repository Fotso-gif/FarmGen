# ton_app/templatetags/custom_filters.py
from django import template
from django.utils.formats import number_format
import re

register = template.Library()
@register.filter
def sum_items(cart_items):
    """Calcule le nombre total d'articles dans le panier."""
    if not cart_items:
        return 0
    return sum(item.get('quantity', 0) for item in cart_items)

@register.filter
def multiply(value, arg):
    """Multiplie la valeur par l'argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def payment_method_icon(method):
    """Retourne l'icône correspondant à la méthode de paiement."""
    icons = {
        'whatsapp': 'whatsapp',
        'om': 'mobile-alt',
        'momo': 'money-bill-wave',
    }
    return icons.get(method, 'credit-card')

@register.filter
def divide(value, arg):
    """Diviser deux valeurs"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def subtract(value, arg):
    """Soustraire deux valeurs"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def format_currency(value):
    """Formater un montant en devise"""
    try:
        return f"{float(value):,.0f} FCFA".replace(',', ' ')
    except (ValueError, TypeError):
        return f"0 FCFA"
    
@register.filter
def intcomma(value):
    """Formate un nombre avec des séparateurs de milliers."""
    if value is None:
        return ''
    
    try:
        value = int(value)
        # Format français: 1 000 000 au lieu de 1,000,000
        formatted = number_format(value, force_grouping=True)
        return formatted.replace(',', ' ')
    except (ValueError, TypeError):
        return value

@register.filter
def naturaltime(value):
    """Affiche le temps en format naturel (ex: "il y a 2 heures")."""
    if not value:
        return ''
    
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    now = timezone.now()
    diff = now - value
    
    if diff < timedelta(minutes=1):
        return "à l'instant"
    elif diff < timedelta(minutes=2):
        return "il y a 1 minute"
    elif diff < timedelta(hours=1):
        return f"il y a {diff.seconds // 60} minutes"
    elif diff < timedelta(hours=2):
        return "il y a 1 heure"
    elif diff < timedelta(days=1):
        return f"il y a {diff.seconds // 3600} heures"
    elif diff < timedelta(days=2):
        return "hier"
    elif diff < timedelta(days=7):
        return f"il y a {diff.days} jours"
    elif diff < timedelta(days=30):
        weeks = diff.days // 7
        return f"il y a {weeks} semaine{'s' if weeks > 1 else ''}"
    elif diff < timedelta(days=365):
        months = diff.days // 30
        return f"il y a {months} mois"
    else:
        years = diff.days // 365
        return f"il y a {years} an{'s' if years > 1 else ''}"

@register.filter
def naturalday(value, arg=None):
    """Affiche la date en format naturel (ex: "aujourd'hui", "demain")."""
    if not value:
        return ''
    
    from django.utils import timezone
    from datetime import date, timedelta
    
    try:
        tzinfo = timezone.get_current_timezone()
        value = timezone.localtime(value, tzinfo)
        today = timezone.localtime(timezone.now(), tzinfo).date()
        value_date = value.date()
        
        delta = value_date - today
        
        if delta.days == 0:
            return "aujourd'hui"
        elif delta.days == 1:
            return "demain"
        elif delta.days == -1:
            return "hier"
        else:
            # Retourne le format par défaut
            return value.strftime('%d/%m/%Y')
    except:
        return value

@register.filter
def apnumber(value):
    """Convertit un nombre en texte (ex: 1 → "un")."""
    numbers = {
        0: 'zéro', 1: 'un', 2: 'deux', 3: 'trois', 4: 'quatre',
        5: 'cinq', 6: 'six', 7: 'sept', 8: 'huit', 9: 'neuf',
        10: 'dix'
    }
    return numbers.get(value, str(value))

@register.filter
def ordinal(value):
    """Ajoute le suffixe ordinal (ex: 1 → "1er")."""
    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            return value
    
    if value == 1:
        return f"{value}er"
    else:
        return f"{value}ème"

@register.filter
def filesizeformat(bytes_value):
    """Formate la taille d'un fichier."""
    try:
        bytes_value = float(bytes_value)
    except (TypeError, ValueError):
        return "0 octets"
    
    if bytes_value < 1024:
        return f"{int(bytes_value)} octets"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} Ko"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.1f} Mo"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.1f} Go"

@register.filter
def truncatechars(value, arg):
    """Tronque une chaîne après un certain nombre de caractères."""
    try:
        length = int(arg)
    except ValueError:
        return value
    
    if len(value) > length:
        return value[:length-3] + '...'
    return value

@register.filter
def truncatewords(value, arg):
    """Tronque une chaîne après un certain nombre de mots."""
    try:
        word_count = int(arg)
    except ValueError:
        return value
    
    words = value.split()
    if len(words) > word_count:
        return ' '.join(words[:word_count]) + '...'
    return value

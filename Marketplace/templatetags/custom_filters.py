# ton_app/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplie deux valeurs numériques."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
# marketplace/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplier deux valeurs"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

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
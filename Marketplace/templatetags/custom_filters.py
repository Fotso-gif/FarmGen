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

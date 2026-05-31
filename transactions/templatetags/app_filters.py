from django import template
import re

register = template.Library()

@register.filter
def intspace(value):
    try:
        val = int(float(value))
        s = f"{val:,}"
        return s.replace(",", " ")
    except (ValueError, TypeError):
        return str(value)

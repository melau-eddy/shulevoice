# base/templatetags/math_filters.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    """Subtract the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def divisibleby(value, arg):
    """Check if value is divisible by argument"""
    try:
        return int(value) % int(arg) == 0
    except (ValueError, TypeError):
        return False
from django import template
import random

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divisibleby(value, arg):
    """Divide the value by the argument and return the result"""
    try:
        arg = float(arg)
        if arg == 0:
            return 0
        return float(value) / arg
    except (ValueError, TypeError):
        return 0

@register.filter
def get_range(value):
    """Return a range of numbers from 0 to value-1"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def get_item(value, arg):
    """Get an item from a list or dictionary"""
    try:
        if isinstance(value, list):
            return value[int(arg)]
        elif isinstance(value, dict):
            return value.get(arg)
        return None
    except (IndexError, KeyError, ValueError, TypeError):
        return None

@register.filter
def get_chart_color(index):
    """Return a color based on the index for chart elements"""
    colors = [
        'rgba(255, 99, 132, 0.8)',   # Red
        'rgba(54, 162, 235, 0.8)',   # Blue
        'rgba(255, 206, 86, 0.8)',   # Yellow
        'rgba(75, 192, 192, 0.8)',   # Green
        'rgba(153, 102, 255, 0.8)',  # Purple
        'rgba(255, 159, 64, 0.8)',   # Orange
        'rgba(199, 199, 199, 0.8)',  # Gray
        'rgba(83, 102, 255, 0.8)',   # Indigo
        'rgba(255, 99, 255, 0.8)',   # Pink
        'rgba(99, 255, 132, 0.8)',   # Light Green
    ]

    try:
        idx = int(index) % len(colors)
        return colors[idx]
    except (ValueError, TypeError):
        # Return a random color if there's an error
        return random.choice(colors)

@register.filter
def sum_list(value):
    """Return the sum of a list of numbers"""
    try:
        if isinstance(value, list):
            return sum(float(item) for item in value if item is not None)
        return 0
    except (ValueError, TypeError):
        return 0

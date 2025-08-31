from django import template

register = template.Library()

@register.filter(name='split')
def split_filter(value, delimiter):
    """
    Split a string by a delimiter and return a list.
    Usage: {{ value|split:"," }}
    """
    if value:
        return value.split(delimiter)
    return []

@register.filter(name='get_item')
def get_item(list_or_dict, index):
    """
    Get an item from a list or dictionary by index/key.
    Usage: {{ my_list|get_item:index }} or {{ my_dict|get_item:key }}
    """
    try:
        if isinstance(list_or_dict, dict):
            return list_or_dict.get(index)
        elif isinstance(list_or_dict, (list, tuple)) and 0 <= index < len(list_or_dict):
            return list_or_dict[index]
        return None
    except (IndexError, KeyError, TypeError):
        return None

@register.filter(name='multiply')
def multiply(value, arg):
    """
    Multiply the value by the argument.
    Usage: {{ value|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='divisibleby')
def divisibleby(value, arg):
    """
    Return value divided by arg.
    Usage: {{ value|divisibleby:2 }}
    """
    try:
        arg = float(arg)
        if arg == 0:
            return 0
        return float(value) / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

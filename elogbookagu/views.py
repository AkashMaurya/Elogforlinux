from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
import json


def _safe_render_without_request(template_name: str, status_code: int) -> HttpResponse:
    """Render a template to string without passing the request object.

    This avoids running request-based context processors (which may assume
    request.user exists) while rendering error pages.
    """
    try:
        content = render_to_string(template_name, {})
        return HttpResponse(content, status=status_code)
    except Exception:
        # Fallback to a minimal plain-text response if template rendering fails
        return HttpResponse(f"Error {status_code}", content_type="text/plain", status=status_code)


def custom_400(request, exception):
    return _safe_render_without_request('400.html', 400)


def custom_403(request, exception):
    return _safe_render_without_request('403.html', 403)


def custom_404(request, exception):
    return _safe_render_without_request('404.html', 404)


def custom_500(request):
    return _safe_render_without_request('500.html', 500)


@require_http_methods(["POST"])
def set_theme(request):
    try:
        data = json.loads(request.body)
        theme = data.get('theme')
        if theme in ['light', 'dark']:
            request.session['theme'] = theme
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Invalid theme'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

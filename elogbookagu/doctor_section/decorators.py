from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from functools import wraps

def doctor_required(view_func):
    """
    Decorator for views that checks that the user is a doctor,
    redirecting to the login page if necessary.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect(reverse('accounts:login'))
        
        # Check if the user has a doctor profile
        if not hasattr(request.user, 'doctor_profile'):
            messages.error(request, "You must be a doctor to access this page.")
            return redirect(reverse('accounts:login'))
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

def user_data(request):
    """
    Context processor to add user data to all templates.
    """
    context = {}
    
    # Add user data to context if user is authenticated
    if request.user.is_authenticated:
        # Add user object
        context['user'] = request.user
        
        # Add session variables if they don't exist
        if 'first_name' not in request.session:
            request.session['first_name'] = request.user.first_name
        if 'last_name' not in request.session:
            request.session['last_name'] = request.user.last_name
        if 'username' not in request.session:
            request.session['username'] = request.user.username
        if 'email' not in request.session:
            request.session['email'] = request.user.email
        if 'role' not in request.session:
            request.session['role'] = getattr(request.user, 'role', 'user')
            
        # Add session variables to context
        context['username'] = request.session.get('username', '')
        context['first_name'] = request.session.get('first_name', '')
        context['last_name'] = request.session.get('last_name', '')
        context['email'] = request.session.get('email', '')
        context['role'] = request.session.get('role', '')
        
        # Add other useful variables
        context['full_name'] = f"{context['first_name']} {context['last_name']}".strip()
        
    return context

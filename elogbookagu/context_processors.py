def user_data(request):
    """Context processor to add user data to all templates.

    This is defensive: during exception handling or some middleware paths the
    `request` object may not have a `user` attribute. Guard against missing or
    unauthenticated users to avoid raising while rendering templates.
    """
    context = {}

    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return context

    # Add user object
    context['user'] = user

    # Populate session values safely and keep `role` in-sync with the DB.
    # We intentionally write the session fields so that admin changes to the
    # user's role are reflected on the next request instead of being masked
    # by stale session values created at login time.
    session = getattr(request, 'session', {})
    if isinstance(session, dict) or hasattr(session, 'get'):
        # Always update session values from the authoritative user object.
        try:
            session['first_name'] = getattr(user, 'first_name', '')
            session['last_name'] = getattr(user, 'last_name', '')
            session['username'] = getattr(user, 'username', '')
            session['email'] = getattr(user, 'email', '')
            session['role'] = getattr(user, 'role', '')
        except Exception:
            # Be defensive - don't fail template rendering if session isn't writable
            pass

        context['username'] = session.get('username', '')
        context['first_name'] = session.get('first_name', '')
        context['last_name'] = session.get('last_name', '')
        context['email'] = session.get('email', '')
        context['role'] = session.get('role', '')

        context['full_name'] = f"{context['first_name']} {context['last_name']}".strip()

    return context

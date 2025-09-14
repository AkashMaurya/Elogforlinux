from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('sso_debug')


class SSOStateRestoreMiddleware(MiddlewareMixin):
    """Restore allauth's stashed state from DB when the session is missing.

    This middleware runs early and checks the Microsoft callback path. If the
    expected `socialaccount_states` is not present in `request.session` but
    the callback contains a `state` query parameter, we try to load a saved
    `SSOState` (if any) and place it in the session so allauth can continue
    the login flow.
    """

    CALLBACK_PATH = '/accounts/microsoft/login/callback/'

    def process_request(self, request):
        try:
            if request.path.startswith(self.CALLBACK_PATH):
                logger.debug('SSOStateRestoreMiddleware: callback path hit=%s session_keys=%s', request.path, list(request.session.keys()) if hasattr(request, 'session') else None)
                qs_state = request.GET.get('state')
                # If session already has socialaccount_states, nothing to do
                session_keys = list(request.session.keys()) if hasattr(request, 'session') else []
                if qs_state and 'socialaccount_states' not in session_keys:
                    # Lazy import to avoid circular imports at startup
                    from accounts.models import SSOState

                    try:
                        s = SSOState.objects.filter(state_id=qs_state).first()
                        if s:
                            # Restore minimal payload into session under the key
                            # expected by allauth's statekit.
                            request.session['socialaccount_states'] = {qs_state: s.payload}
                            request.session.save()
                            logger.debug('Restored SSOState state_id=%s into session', qs_state)
                    except Exception:
                        logger.exception('Error while restoring SSOState for state=%s', qs_state)
        except Exception:
            logger.exception('Unexpected error in SSOStateRestoreMiddleware')

        return None

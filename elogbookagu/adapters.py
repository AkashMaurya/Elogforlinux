import logging
from typing import List

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp


logger = logging.getLogger(__name__)


class SafeSocialAccountAdapter(DefaultSocialAccountAdapter):
    """A defensive adapter that tolerates multiple SocialApp rows.

    In some deployments duplicate SocialApp entries (or a mixture of DB and
    settings-backed entries) can exist for the same provider which causes
    allauth's default `get_app` to raise MultipleObjectsReturned. Prefer to
    pick a sane default (a single non-hidden app, or first app) and log a
    warning instead of raising an exception that results in a 500.
    """

    def get_app(self, request, provider, client_id=None):
        """Return a SocialApp instance for the provider.

        If multiple apps exist, prefer a single visible app. If ambiguity
        remains, pick the first and log a warning. This prevents
        MultipleObjectsReturned from bubbling up into a 500 for end users.
        """
        apps: List[SocialApp] = self.list_apps(request, provider=provider, client_id=client_id)

        if len(apps) > 1:
            # Visible apps are those not explicitly marked hidden in their settings
            visible_apps = [a for a in apps if not (getattr(a, "settings", {}) or {}).get("hidden")]
            if len(visible_apps) == 1:
                apps = visible_apps
            elif len(visible_apps) > 1:
                logger.warning(
                    "Multiple SocialApp entries found for provider '%s' — using the first visible app.",
                    provider,
                )
                apps = visible_apps
            else:
                logger.warning(
                    "Multiple SocialApp entries found for provider '%s' and none marked visible — using the first app.",
                    provider,
                )

        if len(apps) == 0:
            # Preserve existing behavior when no app is available
            raise SocialApp.DoesNotExist()

        # Return the chosen app (first element)
        return apps[0]

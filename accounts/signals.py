import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def ensure_role_profile(sender, instance, created, **kwargs):
    """Ensure that when a CustomUser is created or their role changes, the
    corresponding profile model exists (Student/Doctor/Staff). Also ensure
    student records get unique student_id when created via SSO or admin.
    """
    try:
        role = getattr(instance, 'role', None)
        if created:
            # Only create a profile if the role is explicitly set to a profile type.
            # New SSO-created users default to 'pending' and should not get a
            # Student record until an admin assigns the 'student' role.
            if role == 'student':
                from .models import Student

                if not hasattr(instance, 'student'):
                    Student.objects.create(user=instance, student_id=f"S{int(timezone.now().timestamp())}{instance.pk}")
                    logger.info("Created Student profile for new user %s", instance.email)
            elif role == 'doctor':
                from .models import Doctor

                if not hasattr(instance, 'doctor_profile'):
                    Doctor.objects.create(user=instance)
                    logger.info("Created Doctor profile for new user %s", instance.email)
            elif role == 'staff':
                from .models import Staff

                if not hasattr(instance, 'staff_profile'):
                    Staff.objects.create(user=instance)
                    logger.info("Created Staff profile for new user %s", instance.email)
        else:
            # If role changed, ensure new profile exists. We can't easily detect
            # the old role here without additional state, but admins call save()
            # when editing; ensure the matching profile exists now.
            if role == 'student':
                from .models import Student

                Student.objects.get_or_create(user=instance, defaults={'student_id': f"S{int(timezone.now().timestamp())}{instance.pk}"})
            elif role == 'doctor':
                from .models import Doctor

                Doctor.objects.get_or_create(user=instance)
            elif role == 'staff':
                from .models import Staff

                Staff.objects.get_or_create(user=instance)
    except Exception:
        logger.exception("Error ensuring role profile for user %s", getattr(instance, 'email', 'unknown'))


@receiver(pre_save, sender=CustomUser)
def ensure_admin_role_for_superuser(sender, instance, **kwargs):
    """Keep behavior where superusers are always admin role before save."""
    try:
        # Capture previous role (if any) so post_save can detect changes.
        if instance.pk:
            try:
                old = CustomUser.objects.filter(pk=instance.pk).values_list('role', flat=True).first()
                setattr(instance, '_old_role', old)
            except Exception:
                setattr(instance, '_old_role', None)

        if instance.is_superuser:
            instance.role = 'admin'
    except Exception:
        logger.exception('Error setting admin role for superuser %s', getattr(instance, 'email', None))


def invalidate_user_sessions(user):
    """Delete all DB sessions associated with `user` (force logout).

    This is a best-effort approach which iterates active sessions and removes
    any whose decoded session data references the user's id under
    `_auth_user_id`.
    """
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone

        now = timezone.now()
        sessions = Session.objects.filter(expire_date__gte=now)
        deleted = 0
        for sess in sessions:
            try:
                data = sess.get_decoded()
                if str(data.get('_auth_user_id')) == str(user.pk):
                    sess.delete()
                    deleted += 1
            except Exception:
                # Ignore malformed session data
                continue
        logger.info('Invalidated %d sessions for user %s', deleted, getattr(user, 'email', user.pk))
    except Exception:
        logger.exception('Error invalidating sessions for user %s', getattr(user, 'email', user.pk))


@receiver(post_save, sender=CustomUser)
def invalidate_sessions_on_role_change(sender, instance, created, **kwargs):
    """Invalidate sessions when a user's role changes (but not on create).

    This helps make admin role changes take effect immediately (users will
    need to re-login and the new role will be loaded from the DB).
    """
    try:
        if created:
            return

        old_role = getattr(instance, '_old_role', None)
        new_role = getattr(instance, 'role', None)
        if old_role is None:
            # If we didn't capture the old role, try to read from DB
            try:
                old_role = CustomUser.objects.filter(pk=instance.pk).values_list('role', flat=True).first()
            except Exception:
                old_role = None

        if old_role != new_role:
            # Invalidate any active sessions for this user
            invalidate_user_sessions(instance)
    except Exception:
        logger.exception('Error in invalidate_sessions_on_role_change for %s', getattr(instance, 'email', instance.pk))


@receiver(post_save, sender=CustomUser)
def ensure_role_persisted(sender, instance, created, **kwargs):
    """Defensive: ensure the `role` column in the DB matches the instance.

    Some admin/form flows or third-party hooks may not persist `role` due
    to custom save logic. Use a direct `update()` to guarantee the value
    is written without re-triggering model save() semantics.
    """
    try:
        db_role = CustomUser.objects.filter(pk=instance.pk).values_list('role', flat=True).first()
        if db_role != getattr(instance, 'role', None):
            CustomUser.objects.filter(pk=instance.pk).update(role=getattr(instance, 'role', None))
            logger.info('Enforced role persistence for user %s: %s', getattr(instance, 'email', instance.pk), getattr(instance, 'role', None))
    except Exception:
        logger.exception('Error enforcing role persistence for user %s', getattr(instance, 'email', instance.pk))

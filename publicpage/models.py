
from django.db import models
from django.utils import timezone


class PageVisit(models.Model):
    """Track page visits for statistics"""
    page_name = models.CharField(max_length=100, help_text="Name of the page visited")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, help_text="Browser user agent")
    visited_at = models.DateTimeField(default=timezone.now)
    is_unique = models.BooleanField(default=True, help_text="Whether this is a unique visit from this IP")

    class Meta:
        ordering = ['-visited_at']
        verbose_name = "Page Visit"
        verbose_name_plural = "Page Visits"

    def __str__(self):
        return f"{self.page_name} - {self.visited_at.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def record_visit(cls, page_name, request):
        """Record a page visit"""
        ip_address = cls.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Check if this IP visited this page in the last hour (to determine uniqueness)
        recent_visit = cls.objects.filter(
            page_name=page_name,
            ip_address=ip_address,
            visited_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).exists()

        # Create the visit record
        visit = cls.objects.create(
            page_name=page_name,
            ip_address=ip_address,
            user_agent=user_agent,
            is_unique=not recent_visit
        )

        return visit

    @staticmethod
    def get_client_ip(request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

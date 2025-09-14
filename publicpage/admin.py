from django.contrib import admin
from .models import PageVisit


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ('page_name', 'ip_address', 'is_unique', 'visited_at')
    list_filter = ('page_name', 'is_unique', 'visited_at')
    search_fields = ('page_name', 'ip_address')
    readonly_fields = ('visited_at',)
    date_hierarchy = 'visited_at'

    def has_add_permission(self, request):
        return False  # Don't allow manual addition

    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing
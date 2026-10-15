"""
Espace mairie « gratuit » : l'admin Django. Chaque agent ne voit que les signalements des services de ses groupes.
"""

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import CaptureSession, Category, Report, Service, StatusChange, Zone


class StatusChangeInline(admin.TabularInline):
    model = StatusChange
    extra = 0
    readonly_fields = ["from_status", "to_status", "agent", "note", "at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Report)
class ReportAdmin(GISModelAdmin):
    list_display = ["tracking_code", "category", "status", "support_count", "channel", "created_at"]
    list_filter = ["status", "category", "channel"]
    search_fields = ["tracking_code", "description"]
    inlines = [StatusChangeInline]
    # Données calculées par le serveur : consultables, jamais modifiables à la main
    readonly_fields = [
        "tracking_code", "channel", "photo_sha256", "ai_verdict", "reject_reason", "distance_m",
        "reporter_accuracy_m", "reporter_ref", "duplicate_of", "created_at", "updated_at", "resolved_at",
    ]  # fmt: skip

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("category")
        if request.user.is_superuser:
            return queryset
        return queryset.filter(category__services__group__in=request.user.groups.all()).distinct()

    def get_exclude(self, request, obj=None):
        # La position du citoyen est privée : réservée aux administrateurs
        return None if request.user.is_superuser else ["reporter_location"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["label", "slug", "needs_moderation"]
    filter_horizontal = ["services"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "group"]


@admin.register(Zone)
class ZoneAdmin(GISModelAdmin):
    list_display = ["name"]


@admin.register(CaptureSession)
class CaptureSessionAdmin(admin.ModelAdmin):
    list_display = ["token", "channel", "created_at", "expires_at", "used_at"]
    readonly_fields = ["token", "channel", "reporter_ref", "created_at", "expires_at", "used_at"]

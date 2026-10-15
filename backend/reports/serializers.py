"""
Serializers de l'API. Règle de confidentialité : le public ne voit JAMAIS `reporter_location`, `reporter_ref`,
`ai_verdict` ni `distance_m`. Ne les ajouter dans aucun serializer public ou agent.
"""

from rest_framework import serializers

from .models import Category, Report, StatusChange


# --- Entrées ----------------------------------------------------------------------------------------------
class ReportCreateSerializer(serializers.Serializer):
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), help_text="Slug de la catégorie, ex. depot_sauvage"
    )
    description = serializers.CharField(max_length=280, required=False, allow_blank=True, default="")
    # FileField (et non ImageField) : la vérification n° 2 (PHOTO_INVALID) décide si la photo est valable
    photo = serializers.FileField(help_text="Photo prise sur place (JPEG, PNG ou WebP, 8 Mo max)")
    point_lat = serializers.FloatField(min_value=-90, max_value=90, help_text="Latitude du point du problème")
    point_lng = serializers.FloatField(min_value=-180, max_value=180, help_text="Longitude du point du problème")
    device_lat = serializers.FloatField(min_value=-90, max_value=90, help_text="Latitude du téléphone")
    device_lng = serializers.FloatField(min_value=-180, max_value=180, help_text="Longitude du téléphone")
    device_accuracy_m = serializers.FloatField(min_value=0, help_text="Précision GPS du téléphone, en mètres")
    capture_token = serializers.CharField(required=False, allow_blank=True, default="")


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


AGENT_STATUS_CHOICES = [Report.Status.IN_PROGRESS.value, Report.Status.RESOLVED.value]


class AgentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AGENT_STATUS_CHOICES)
    note = serializers.CharField(max_length=280, required=False, allow_blank=True, default="")


class AfterPhotoSerializer(serializers.Serializer):
    photo = serializers.FileField()
    note = serializers.CharField(max_length=280, required=False, allow_blank=True, default="")


# --- Sorties ----------------------------------------------------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    services = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = Category
        fields = ["slug", "label", "services", "needs_moderation"]


class ReportCreatedSerializer(serializers.Serializer):
    """Réponse de POST /reports (documentation du contrat)."""

    tracking_code = serializers.CharField()
    status = serializers.CharField()
    duplicate = serializers.BooleanField()
    support_count = serializers.IntegerField()
    message = serializers.CharField()


class StatusChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusChange
        fields = ["from_status", "to_status", "note", "at"]  # volontairement sans le nom de l'agent


class ReportDetailSerializer(serializers.ModelSerializer):
    """Suivi citoyen : détail public d'un signalement."""

    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    category_label = serializers.CharField(source="category.label", read_only=True)
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    photo_after_url = serializers.SerializerMethodField()
    history = StatusChangeSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = [
            "tracking_code", "category", "category_label", "status", "description", "lat", "lng",
            "photo_url", "photo_after_url", "support_count",
            "created_at", "updated_at", "resolved_at", "history",
        ]  # fmt: skip

    def get_lat(self, obj) -> float:
        return obj.location.y

    def get_lng(self, obj) -> float:
        return obj.location.x

    def get_photo_url(self, obj) -> str:
        return obj.photo.url if obj.photo else ""

    def get_photo_after_url(self, obj) -> str | None:
        return obj.photo_after.url if obj.photo_after else None


class AgentReportSerializer(ReportDetailSerializer):
    """Vue de l'agent : le détail public + ce dont la mairie a besoin pour traiter (verdict IA, canal)."""

    class Meta(ReportDetailSerializer.Meta):
        fields = ReportDetailSerializer.Meta.fields + ["channel", "ai_verdict"]


# --- GeoJSON (carte) --------------------------------------------------------------------------------------
def report_to_feature(report):
    """Une entité GeoJSON publique. ATTENTION : [longitude, latitude]."""
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [report.location.x, report.location.y]},
        "properties": {
            "tracking_code": report.tracking_code,
            "category": report.category.slug,
            "status": report.status,
            "support_count": report.support_count,
            "photo_url": report.photo.url if report.photo else "",
            "created_at": report.created_at,
        },
    }

"""
Modèles de Cotonou Signale (voir docs/data-model.md).

ATTENTION : seule l'équipe 4 modifie ce fichier et crée des migrations. Les autres équipes demandent un champ.
Un signalement porte DEUX positions : `location` (le point du problème, publique) et `reporter_location`
(où se trouvait le citoyen, privée : jamais renvoyée par l'API).
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.gis.db import models
from django.utils import timezone

from config.errors import ApiError

# Alphabet sans caractères ambigus (pas de 0/O, 1/I/L) pour les codes de suivi lus à voix haute ou recopiés
TRACKING_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


class Service(models.Model):
    """Un service de la mairie (créés par la migration 0002)."""

    name = models.CharField("nom", max_length=80, unique=True)
    group = models.OneToOneField(
        Group, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="groupe d'agents"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    slug = models.SlugField(unique=True)
    label = models.CharField("libellé", max_length=80)
    services = models.ManyToManyField(Service, blank=True, verbose_name="services")
    needs_moderation = models.BooleanField("passe par la modération", default=False)

    class Meta:
        ordering = ["id"]
        verbose_name = "catégorie"

    def __str__(self):
        return self.label


class Zone(models.Model):
    """Polygone de la zone couverte (Cotonou). Chargé avec `python manage.py load_zone`."""

    name = models.CharField(max_length=80, unique=True)
    polygon = models.MultiPolygonField(srid=4326)

    def __str__(self):
        return self.name


class Report(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En cours de vérification"
        REJECTED = "rejected", "Rejeté"
        MODERATION = "moderation", "En modération"
        PUBLISHED = "published", "Publié"
        IN_PROGRESS = "in_progress", "Pris en charge"
        RESOLVED = "resolved", "Résolu"

    # Statuts visibles sur la carte publique
    PUBLIC_STATUSES = (Status.PUBLISHED, Status.IN_PROGRESS, Status.RESOLVED)

    class Channel(models.TextChoices):
        WEB = "web", "Web"
        WHATSAPP = "whatsapp", "WhatsApp"

    tracking_code = models.CharField(max_length=12, unique=True)  # ex. CS-7K3F9Q
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="catégorie")
    description = models.CharField(max_length=280, blank=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.WEB)

    # Position PUBLIQUE : le point du problème (ajusté sur la carte)
    location = models.PointField(geography=True, srid=4326)
    # Position PRIVÉE : où se trouvait le citoyen. Jamais exposée par l'API.
    reporter_location = models.PointField(geography=True, srid=4326)
    reporter_accuracy_m = models.FloatField()
    distance_m = models.FloatField()  # distance entre les deux, calculée par le serveur

    photo = models.ImageField(upload_to="reports/%Y/%m/")
    photo_sha256 = models.CharField(max_length=64, db_index=True)
    photo_after = models.ImageField(upload_to="reports/after/%Y/%m/", null=True, blank=True)

    ai_verdict = models.JSONField(default=dict, blank=True)  # jamais exposé au public
    reject_reason = models.CharField(max_length=40, blank=True)
    duplicate_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates"
    )
    support_count = models.PositiveIntegerField(default=1)  # le compteur « +1 »

    reporter_ref = models.CharField(max_length=64, blank=True)  # HMAC du numéro WhatsApp, jamais le numéro
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "signalement"

    def __str__(self):
        return f"{self.tracking_code} · {self.category.label}"

    @classmethod
    def generate_tracking_code(cls):
        while True:
            code = "CS-" + "".join(secrets.choice(TRACKING_ALPHABET) for _ in range(6))
            if not cls.objects.filter(tracking_code=code).exists():
                return code


class StatusChange(models.Model):
    """Historique des changements de statut (visible dans le suivi citoyen, sans le nom de l'agent)."""

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.CharField(max_length=280, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["at", "id"]


class CaptureSession(models.Model):
    """Lien de capture à usage unique (web et WhatsApp), valable `CAPTURE_TOKEN_TTL_MIN` minutes."""

    token = models.CharField(max_length=64, unique=True)
    channel = models.CharField(max_length=10, choices=Report.Channel.choices, default=Report.Channel.WEB)
    reporter_ref = models.CharField(max_length=64, blank=True)
    phone_number = models.CharField(
        "numéro WhatsApp (temporaire)",
        max_length=20,
        blank=True,
        default="",
        help_text="Stocké temporairement pour envoyer la confirmation WhatsApp, effacé après usage.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def create_for(cls, channel=Report.Channel.WEB, reporter_ref="", phone_number=""):
        return cls.objects.create(
            token=secrets.token_urlsafe(24),
            channel=channel,
            reporter_ref=reporter_ref,
            phone_number=phone_number,
            expires_at=timezone.now() + timedelta(minutes=settings.CAPTURE_TOKEN_TTL_MIN),
        )

    def assert_usable(self):
        """Lève TOKEN_USED ou TOKEN_EXPIRED si le lien ne peut plus servir."""
        if self.used_at is not None:
            raise ApiError("TOKEN_USED")
        if self.expires_at <= timezone.now():
            raise ApiError("TOKEN_EXPIRED")

    @property
    def capture_url(self):
        return f"{settings.FRONT_URL.rstrip('/')}/capture/{self.token}"

    # P2 : AuditLog(actor, action, target_type, target_id, payload, at)

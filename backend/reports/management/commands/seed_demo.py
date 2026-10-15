"""
Données de DÉMONSTRATION : comptes agents et signalements FICTIFS (photos générées). Idempotent.

    docker compose exec web python manage.py seed_demo

Refuse de s'exécuter si DJANGO_DEBUG est faux (les mots de passe de démonstration sont connus de tous).
"""

import hashlib
import io

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image, ImageDraw

from reports.geo import make_point
from reports.models import Category, Report, Service, StatusChange

DEMO_PREFIX = "[démo]"

# nom d'utilisateur → service
AGENTS = {
    "agent.dechets": "Collecte des déchets",
    "agent.assainissement": "Assainissement",
    "agent.techniques": "Services techniques",
    "agent.eclairage": "Éclairage public",
    "agent.police": "Police municipale",
}

# (catégorie, lat, lng, description, statut, +1)  — lieux FICTIFS, approximatifs, à l'intérieur de Cotonou
DEMO_REPORTS = [
    ("depot_sauvage", 6.3667, 2.4390, "Dépôt d'ordures devant le marché", "published", 4),
    ("caniveau_bouche", 6.3590, 2.3830, "Caniveau bouché après la pluie", "published", 2),
    ("eau_stagnante", 6.3560, 2.4420, "Eau stagnante sur la chaussée", "in_progress", 3),
    ("chaussee_degradee", 6.3640, 2.3980, "Nid-de-poule profond", "published", 1),
    ("eclairage_panne", 6.3760, 2.4040, "Lampadaire éteint depuis une semaine", "published", 2),
    ("brulage_dechets", 6.3600, 2.4290, "Brûlage de déchets en bord de rue", "published", 1),
    ("regard_dalle", 6.3420, 2.3600, "Dalle de caniveau cassée", "resolved", 2),
    ("vehicule_abandonne", 6.3610, 2.4150, "Épave sur le trottoir", "published", 1),
]

COLORS = ["#2f6f4f", "#8a5a2b", "#2b5d8a", "#7a2f6f", "#6f6f2f"]


def fake_photo(text, index, suffix=""):
    """Image de substitution (aucune vraie photo, aucune donnée personnelle)."""
    image = Image.new("RGB", (640, 480), COLORS[index % len(COLORS)])
    draw = ImageDraw.Draw(image)
    draw.text((24, 24), f"PHOTO FICTIVE · {text}{suffix}", fill="white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Crée les comptes agents de démonstration et quelques signalements fictifs (idempotent)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo est réservé au développement (DJANGO_DEBUG=true).")
        self.create_accounts()
        self.create_reports()

    def create_accounts(self):
        User = get_user_model()
        admin, created = User.objects.get_or_create(
            username="admin", defaults={"is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password(settings.DEMO_ADMIN_PASSWORD)
            admin.save()

        permissions = Permission.objects.filter(
            content_type__app_label="reports", codename__in=["view_report", "change_report"]
        )
        for username, service_name in AGENTS.items():
            service = Service.objects.get(name=service_name)
            service.group.permissions.set(permissions)
            agent, created = User.objects.get_or_create(username=username, defaults={"is_staff": True})
            if created:
                agent.set_password(settings.DEMO_AGENT_PASSWORD)
                agent.save()
            agent.groups.add(service.group)
        self.stdout.write(
            f"Comptes : admin / {settings.DEMO_ADMIN_PASSWORD}  ·  agents ({', '.join(AGENTS)}) / "
            f"{settings.DEMO_AGENT_PASSWORD}"
        )

    def create_reports(self):
        if Report.objects.filter(description__startswith=DEMO_PREFIX).exists():
            self.stdout.write("Signalements de démonstration déjà présents.")
            return
        for index, (slug, lat, lng, text, status, support) in enumerate(DEMO_REPORTS):
            category = Category.objects.get(slug=slug)
            content = fake_photo(category.label, index)
            report = Report(
                tracking_code=Report.generate_tracking_code(),
                category=category,
                description=f"{DEMO_PREFIX} {text}",
                status=status,
                location=make_point(lat, lng),
                reporter_location=make_point(lat + 0.0001, lng),
                reporter_accuracy_m=10,
                distance_m=11,
                photo_sha256=hashlib.sha256(content).hexdigest(),
                support_count=support,
            )
            report.photo.save(f"demo-{index}.jpg", ContentFile(content), save=False)
            if status == "resolved":
                after = fake_photo(category.label, index + 1, " (APRÈS)")
                report.photo_after.save(f"demo-{index}-apres.jpg", ContentFile(after), save=False)
                report.resolved_at = timezone.now()
            report.save()
            StatusChange.objects.create(report=report, from_status="", to_status="published", note="Signalement reçu")
            if status in ("in_progress", "resolved"):
                StatusChange.objects.create(
                    report=report, from_status="published", to_status="in_progress", note="Équipe envoyée"
                )
            if status == "resolved":
                StatusChange.objects.create(
                    report=report, from_status="in_progress", to_status="resolved", note="Problème réglé"
                )
        self.stdout.write(self.style.SUCCESS(f"{len(DEMO_REPORTS)} signalements fictifs créés."))

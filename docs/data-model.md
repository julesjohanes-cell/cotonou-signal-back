# Modèle de données

Le code de référence est `backend/reports/models.py` ; le squelette ci-dessous en est une version simplifiée. Sont en place : `Service`, `Category`, `Report`, `CaptureSession`, `StatusChange` (historique) et `Zone` (polygone de Cotonou). `ReportSupport` et `AuditLog` (P2) se greffent ensuite sans rien casser. Un point d'attention : le signalement porte **deux positions distinctes**, le point public du problème et la position privée du citoyen.

Les 6 services de la mairie (et un groupe d'agents par service) sont créés par la migration `0002_seed_services` ; les catégories par la fixture `categories`. Un signalement rejeté par une vérification n'est **pas enregistré** pour l'instant : le statut `rejected` est réservé à la suite (journal des rejets).

Seule l'équipe 4 modifie `reports/models.py` et crée des migrations.

## Catégories et services (fixtures `categories`)
| Slug | Catégorie | Service(s) |
| --- | --- | --- |
| `depot_sauvage` | Dépôt sauvage d'ordures | Collecte des déchets |
| `caniveau_bouche` | Caniveau bouché | Assainissement |
| `brulage_dechets` | Brûlage de déchets | Collecte des déchets, Environnement |
| `eau_stagnante` | Eau stagnante ou inondation | Assainissement |
| `chaussee_degradee` | Chaussée dégradée | Services techniques |
| `regard_dalle` | Regard ou dalle dangereux | Services techniques |
| `eclairage_panne` | Éclairage public en panne | Éclairage public |
| `vehicule_abandonne` | Véhicule ou objet abandonné | Police municipale |
| `autre` | Autre problème | Modération (aucun service tant que non classé) |

## Modèles Django (squelette de départ)
```python
from django.contrib.gis.db import models
from django.contrib.auth.models import Group

class Service(models.Model):            # un service de la mairie
    name = models.CharField(max_length=80, unique=True)
    group = models.OneToOneField(Group, null=True, blank=True, on_delete=models.SET_NULL)

class Category(models.Model):
    slug = models.SlugField(unique=True)
    label = models.CharField(max_length=80)
    services = models.ManyToManyField(Service, blank=True)
    needs_moderation = models.BooleanField(default=False)   # vrai pour "autre"

class Report(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"          # en cours de vérification
        REJECTED = "rejected"        # position ou photo refusée
        MODERATION = "moderation"    # "Autre problème"
        PUBLISHED = "published"      # vérifié, visible sur la carte
        IN_PROGRESS = "in_progress"  # pris en charge par un service
        RESOLVED = "resolved"        # traité, photo "après" ajoutée

    tracking_code = models.CharField(max_length=12, unique=True)   # ex. CS-7K3F9Q
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    description = models.CharField(max_length=280, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    channel = models.CharField(max_length=10, choices=[("web", "web"), ("whatsapp", "whatsapp")])

    # Position PUBLIQUE : le point du problème (ajusté sur la carte)
    location = models.PointField(geography=True, srid=4326)
    # Position PRIVEE : où se trouvait le citoyen (jamais exposée par l'API publique)
    reporter_location = models.PointField(geography=True, srid=4326)
    reporter_accuracy_m = models.FloatField()
    distance_m = models.FloatField()          # distance entre les deux, calculée par le serveur

    photo = models.ImageField(upload_to="reports/%Y/%m/")
    photo_sha256 = models.CharField(max_length=64, db_index=True)
    photo_after = models.ImageField(upload_to="reports/after/%Y/%m/", null=True, blank=True)

    ai_verdict = models.JSONField(default=dict, blank=True)   # {match, confidence, reason, is_screenshot}
    reject_reason = models.CharField(max_length=40, blank=True)
    duplicate_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates")
    support_count = models.PositiveIntegerField(default=1)    # le compteur "+1"

    reporter_ref = models.CharField(max_length=64, blank=True)  # HMAC du numéro WhatsApp, jamais le numéro en clair
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

class CaptureSession(models.Model):     # lien unique de capture (web et WhatsApp)
    token = models.CharField(max_length=64, unique=True)
    channel = models.CharField(max_length=10)
    reporter_ref = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField()                      # création + 10 min
    used_at = models.DateTimeField(null=True, blank=True)    # usage unique

# P1/P2 : StatusChange(report, from_status, to_status, agent, note, at)
#         AuditLog(actor, action, target_type, target_id, payload, at)
```

## Cycle de vie d'un signalement
| Statut | Qui le déclenche | Visible sur la carte publique |
| --- | --- | --- |
| `pending` | Création par le citoyen, avant vérification | Non |
| `rejected` | Serveur : hors Cotonou, trop loin (> 100 m), GPS imprécis, photo hors sujet ou capture d'écran | Non (le citoyen voit la raison) |
| `moderation` | Serveur : catégorie « Autre problème » | Non |
| `published` | Serveur : toutes les vérifications passées | Oui |
| `in_progress` | Agent du service concerné | Oui |
| `resolved` | Agent, avec la photo « après » | Oui (avec avant/après) |

Transitions autorisées côté agent : `published` → `in_progress` → `resolved`. Toute autre transition renvoie `INVALID_TRANSITION`.

## Ce que chaque acteur voit
| Donnée | Public (carte) | Citoyen (suivi) | Agent de la mairie |
| --- | --- | --- | --- |
| Point du problème, catégorie, statut, `support_count` | Oui | Oui | Oui |
| Photo (floutée si le floutage est fait) | Oui | Oui | Oui |
| Position du citoyen, précision, distance | Non | Non | Non, réservée à l'audit |
| Verdict IA et raison du rejet | Non | Raison du rejet seulement | Oui |
| Numéro de téléphone | Jamais | Jamais | Jamais (seulement `reporter_ref`) |

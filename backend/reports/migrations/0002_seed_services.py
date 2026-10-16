"""
Données de structure : les services de la mairie et leur groupe d'agents.
Les catégories (et leur routage vers ces services) sont chargées par la fixture `categories`,
qui référence ces services par leur numéro (1 à 6, dans l'ordre ci-dessous).
"""

from django.db import migrations

SERVICES = [
    "Collecte des déchets",  # 1
    "Assainissement",  # 2
    "Services techniques",  # 3
    "Éclairage public",  # 4
    "Police municipale",  # 5
    "Environnement",  # 6
]


def create_services(apps, schema_editor):
    Service = apps.get_model("reports", "Service")
    Group = apps.get_model("auth", "Group")
    for name in SERVICES:
        group, _ = Group.objects.get_or_create(name=name)
        Service.objects.get_or_create(name=name, defaults={"group": group})


class Migration(migrations.Migration):
    dependencies = [("reports", "0001_initial")]
    operations = [migrations.RunPython(create_services, migrations.RunPython.noop)]

from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime, timezone

@api_view(['GET'])
def health_check(request):
    """
    Endpoint de vérification de santé pour le frontend Next.js.
    """
    return Response({
        "status": "healthy",
        "service": "SandBos Django API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    })

@api_view(['GET'])
def get_features(request):
    """
    Exemple d'endpoint fournissant des fonctionnalités ou données initiales.
    """
    return Response({
        "project": "SandBos",
        "architecture": "Monorepo (Next.js + Django REST Framework)",
        "items": [
            {"id": 1, "title": "Frontend Next.js (App Router, Tailwind CSS)", "status": "Prêt"},
            {"id": 2, "title": "Backend Django REST Framework", "status": "Actif"},
            {"id": 3, "title": "CORS & Communication API", "status": "Configuré"},
            {"id": 4, "title": "Base de données & Modèles", "status": "Prêt à être étendu"}
        ]
    })

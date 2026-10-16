"""
Réglages Django de Cotonou Signale.

Tout est lu depuis les variables d'environnement (fichier .env, voir .env.example) et possède une valeur
par défaut adaptée au développement. Les seuils des règles de vérification sont réunis dans la section
« Règles métier » : c'est le SEUL endroit où les modifier.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=True)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-change-me")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = [o for o in env.list("CSRF_TRUSTED_ORIGINS", default=[]) if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "reports",
    "verification",
    "whatsapp",
]

MIDDLEWARE = [
    "config.middleware.ApiTrailingSlashMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Base de données (PostgreSQL + PostGIS)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgis://cotonou:cotonou@db:5432/cotonou"
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Langue, fuseau, fichiers
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Porto-Novo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default="/data/media")

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    o
    for o in env.list(
        "CORS_ALLOWED_ORIGINS",
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
    )
    if o
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.errors.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "reports": env("THROTTLE_REPORTS", default="60/min"),
        "capture": env("THROTTLE_CAPTURE", default="30/min"),
        "login": env("THROTTLE_LOGIN", default="10/min"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Cotonou Signale · API",
    "DESCRIPTION": (
        "API de signalement citoyen d'insalubrité à Cotonou. "
        "Toute erreur a la forme {\"error\": {\"code\", \"message\", \"details\"}}. "
        "GeoJSON : [longitude, latitude]."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "ENUM_NAME_OVERRIDES": {
        "ReportStatusEnum": "reports.models.Report.Status",
        "AgentStatusEnum": "reports.serializers.AGENT_STATUS_CHOICES",
    },
}

# ---------------------------------------------------------------------------
# Règles métier : SEUL endroit où modifier les seuils (voir docs/verification.md)
# ---------------------------------------------------------------------------
GPS_MAX_ACCURACY_M = env.float("GPS_MAX_ACCURACY_M", default=50)
MAX_DISTANCE_M = env.float("MAX_DISTANCE_M", default=100)
DUPLICATE_RADIUS_M = env.float("DUPLICATE_RADIUS_M", default=30)
DUPLICATE_DAYS = env.int("DUPLICATE_DAYS", default=30)
AI_MIN_CONFIDENCE = env.float("AI_MIN_CONFIDENCE", default=0.6)
AI_TIMEOUT_S = env.int("AI_TIMEOUT_S", default=15)
CAPTURE_TOKEN_TTL_MIN = env.int("CAPTURE_TOKEN_TTL_MIN", default=10)
MAX_PHOTO_MB = env.int("MAX_PHOTO_MB", default=8)
ALLOWED_PHOTO_FORMATS = ("JPEG", "PNG", "WEBP")
REQUIRE_CAPTURE_TOKEN = env.bool("REQUIRE_CAPTURE_TOKEN", default=False)

# Zone provisoire de Cotonou (boîte englobante) : min_lng, min_lat, max_lng, max_lat.
# À VÉRIFIER. Remplacée par le vrai polygone dès qu'une zone est chargée (commande `load_zone`).
COTONOU_BBOX = tuple(
    float(v) for v in env.list("COTONOU_BBOX", default=["2.30", "6.32", "2.52", "6.45"])
)

# ---------------------------------------------------------------------------
# Intégrations externes (toutes simulables)
# ---------------------------------------------------------------------------
FRONT_URL = env("FRONT_URL", default="http://localhost:3000")
VERIFY_MODE = env("VERIFY_MODE", default="mock")  # mock | live
VISION_API_KEY = env("VISION_API_KEY", default="")
WHATSAPP_MODE = env("WHATSAPP_MODE", default="mock")  # mock | live
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN", default="cotonou-verify-token")
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", default="")
WHATSAPP_ACCESS_TOKEN = env("WHATSAPP_ACCESS_TOKEN", default="")
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID", default="")
REPORTER_HMAC_KEY = env("REPORTER_HMAC_KEY", default="dev-only-change-me")

# Comptes de démonstration (utilisés seulement par la commande seed_demo)
DEMO_ADMIN_PASSWORD = env("DEMO_ADMIN_PASSWORD", default="admin1234")
DEMO_AGENT_PASSWORD = env("DEMO_AGENT_PASSWORD", default="agent1234")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

"""
Vues de l'API (voir docs/api-contract.md). Les vues restent minces :
validation → serializers, règles → reports/checks.py et verification/, création → reports/services.py.
"""

from django.contrib.auth import authenticate
from django.contrib.gis.geos import Polygon
from django.db import connection
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.errors import ApiError

from .models import CaptureSession, Category, Report, StatusChange
from .serializers import (
    AfterPhotoSerializer,
    AgentReportSerializer,
    AgentStatusSerializer,
    CategorySerializer,
    LoginSerializer,
    ReportCreatedSerializer,
    ReportCreateSerializer,
    ReportDetailSerializer,
    report_to_feature,
)
from .services import create_report

MAX_GEOJSON_FEATURES = 2000


class PostOnlyScopedThrottle(ScopedRateThrottle):
    """Limite de débit appliquée seulement aux POST (la lecture de la carte reste libre)."""

    def allow_request(self, request, view):
        if request.method != "POST":
            return True
        return super().allow_request(request, view)


def agent_categories(user):
    """Catégories qu'un agent a le droit de traiter (selon les services de ses groupes). Admin : toutes."""
    if user.is_superuser:
        return Category.objects.all()
    return Category.objects.filter(services__group__in=user.groups.all()).distinct()


def agent_services(user):
    from .models import Service

    if user.is_superuser:
        return Service.objects.all()
    return Service.objects.filter(group__in=user.groups.all())


def get_report_or_404(tracking_code, queryset=None):
    queryset = queryset if queryset is not None else Report.objects.all()
    report = queryset.select_related("category").filter(tracking_code=tracking_code.upper()).first()
    if report is None:
        raise ApiError("NOT_FOUND", "Aucun signalement ne porte ce code.")
    return report


# --- Public -----------------------------------------------------------------------------------------------
class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        responses=inline_serializer(
            "Health",
            {
                "status": serializers.CharField(),
                "database": serializers.CharField(),
                "postgis": serializers.CharField(),
            },
        ),
        summary="Vérifie que l'API, la base et PostGIS répondent",
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT PostGIS_Version()")
                postgis = cursor.fetchone()[0]
        except Exception as exc:  # noqa: BLE001 — on veut un statut lisible, quelle que soit la panne
            return Response(
                {"status": "error", "database": "error", "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok", "postgis": postgis})


class CategoryListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=CategorySerializer(many=True), summary="Les catégories et leur routage vers les services")
    def get(self, request):
        categories = Category.objects.prefetch_related("services")
        return Response(CategorySerializer(categories, many=True).data)


class ReportListCreateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [PostOnlyScopedThrottle]
    throttle_scope = "reports"

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, description="Statuts séparés par des virgules (published, in_progress, resolved)"),
            OpenApiParameter("category", str, description="Slug d'une catégorie"),
            OpenApiParameter("bbox", str, description="min_lng,min_lat,max_lng,max_lat"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        operation_id="reports_geojson",
        summary="Signalements publiés au format GeoJSON (carte)",
    )
    def get(self, request):
        queryset = Report.objects.filter(status__in=Report.PUBLIC_STATUSES).select_related("category")

        statuses = request.query_params.get("status")
        if statuses:
            wanted = [s.strip() for s in statuses.split(",") if s.strip()]
            allowed = {s.value for s in Report.PUBLIC_STATUSES}
            invalid = [s for s in wanted if s not in allowed]
            if invalid:
                raise ApiError("INVALID_INPUT", details={"fields": {"status": [f"Valeurs inconnues : {invalid}"]}})
            queryset = queryset.filter(status__in=wanted)

        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)

        bbox = request.query_params.get("bbox")
        if bbox:
            try:
                min_lng, min_lat, max_lng, max_lat = (float(v) for v in bbox.split(","))
            except ValueError:
                raise ApiError(
                    "INVALID_INPUT", details={"fields": {"bbox": ["Format attendu : min_lng,min_lat,max_lng,max_lat"]}}
                )
            queryset = queryset.filter(
                location__intersects=Polygon.from_bbox((min_lng, min_lat, max_lng, max_lat))
            )

        features = [report_to_feature(r) for r in queryset[:MAX_GEOJSON_FEATURES]]
        return Response({"type": "FeatureCollection", "features": features})

    @extend_schema(
        request={"multipart/form-data": ReportCreateSerializer},
        responses={201: ReportCreatedSerializer, 200: ReportCreatedSerializer},
        operation_id="reports_create",
        summary="Créer un signalement (vérifie, puis publie ou rejette)",
        description=(
            "201 : publié (ou en modération pour « autre »). 200 : doublon fusionné (+1). "
            "422 : rejeté par une vérification (voir les codes d'erreur du contrat). "
            "Un rejet n'est pas enregistré et ne consomme pas le lien de capture."
        ),
    )
    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report, is_duplicate = create_report(serializer.validated_data)

        if is_duplicate:
            message = "Ce problème a déjà été signalé tout près. Votre signalement a été ajouté (+1)."
        elif report.status == Report.Status.MODERATION:
            message = "Signalement reçu. Il sera examiné avant publication. Suivez-le avec ce code."
        else:
            message = "Signalement publié. Suivez-le avec ce code."
        body = {
            "tracking_code": report.tracking_code,
            "status": report.status,
            "duplicate": is_duplicate,
            "support_count": report.support_count,
            "message": message,
        }
        return Response(body, status=status.HTTP_200_OK if is_duplicate else status.HTTP_201_CREATED)


class ReportDetailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=ReportDetailSerializer, summary="Détail et historique d'un signalement (suivi citoyen)")
    def get(self, request, tracking_code):
        report = get_report_or_404(tracking_code)
        return Response(ReportDetailSerializer(report).data)


class CaptureSessionCreateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "capture"

    @extend_schema(
        request=None,
        responses={
            201: inline_serializer(
                "CaptureSessionCreated",
                {
                    "token": serializers.CharField(),
                    "expires_at": serializers.DateTimeField(),
                    "capture_url": serializers.CharField(),
                },
            )
        },
        summary="Créer un lien de capture à usage unique (parcours web)",
    )
    def post(self, request):
        session = CaptureSession.create_for(channel=Report.Channel.WEB)
        return Response(
            {"token": session.token, "expires_at": session.expires_at, "capture_url": session.capture_url},
            status=status.HTTP_201_CREATED,
        )


class CaptureSessionDetailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        responses=inline_serializer(
            "CaptureSessionState", {"valid": serializers.BooleanField(), "expires_at": serializers.DateTimeField()}
        ),
        summary="Vérifier qu'un lien de capture est valide avant d'afficher la page",
    )
    def get(self, request, token):
        session = CaptureSession.objects.filter(token=token).first()
        if session is None:
            raise ApiError("NOT_FOUND", "Ce lien de signalement est inconnu.")
        session.assert_usable()  # TOKEN_USED (409) ou TOKEN_EXPIRED (410)
        return Response({"valid": True, "expires_at": session.expires_at})


# --- Agents de la mairie ----------------------------------------------------------------------------------
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        request=LoginSerializer,
        responses=inline_serializer(
            "LoginResult",
            {
                "token": serializers.CharField(),
                "user": inline_serializer(
                    "LoginUser", {"username": serializers.CharField(), "services": serializers.ListField(child=serializers.CharField())}
                ),
            },
        ),
        summary="Connexion d'un agent (renvoie un jeton à envoyer dans « Authorization: Token … »)",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            username=serializer.validated_data["username"], password=serializer.validated_data["password"]
        )
        if user is None:
            raise ApiError("UNAUTHENTICATED", "Identifiant ou mot de passe incorrect.")
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": {"username": user.username, "services": [s.name for s in agent_services(user)]}}
        )


class AgentReportListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, description="Filtrer sur un statut"),
            OpenApiParameter("limit", int, description="Nombre maximum de résultats (défaut 100, max 500)"),
            OpenApiParameter("offset", int, description="Décalage (pagination)"),
        ],
        responses=inline_serializer(
            "AgentReportList", {"count": serializers.IntegerField(), "results": AgentReportSerializer(many=True)}
        ),
        summary="Signalements des services de l'agent (avec verdict IA)",
    )
    def get(self, request):
        queryset = Report.objects.filter(category__in=agent_categories(request.user)).select_related("category")
        wanted = request.query_params.get("status")
        if wanted:
            queryset = queryset.filter(status=wanted)
        try:
            limit = min(int(request.query_params.get("limit", 100)), 500)
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except ValueError:
            raise ApiError("INVALID_INPUT", details={"fields": {"limit": ["Nombre entier attendu."]}})
        count = queryset.count()
        page = queryset.prefetch_related("history")[offset : offset + limit]
        return Response({"count": count, "results": AgentReportSerializer(page, many=True).data})


class AgentReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    # Transitions que l'agent peut déclencher : published → in_progress → resolved
    ALLOWED_TRANSITIONS = {
        Report.Status.PUBLISHED: {Report.Status.IN_PROGRESS},
        Report.Status.IN_PROGRESS: {Report.Status.RESOLVED},
    }

    @extend_schema(
        request=AgentStatusSerializer,
        responses=AgentReportSerializer,
        summary="Changer le statut d'un signalement (published → in_progress → resolved), avec une note",
    )
    def patch(self, request, tracking_code):
        report = get_report_or_404(tracking_code)
        if report.category not in agent_categories(request.user):
            raise ApiError("FORBIDDEN", "Ce signalement concerne un autre service.")

        serializer = AgentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = Report.Status(serializer.validated_data["status"])

        if new_status not in self.ALLOWED_TRANSITIONS.get(Report.Status(report.status), set()):
            raise ApiError(
                "INVALID_TRANSITION",
                details={"from": report.status, "to": new_status.value},
            )
        _apply_status(report, new_status, request.user, serializer.validated_data["note"])
        return Response(AgentReportSerializer(report).data)


class AgentAfterPhotoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": AfterPhotoSerializer},
        responses=AgentReportSerializer,
        summary="Ajouter la photo « après » et passer en resolved",
    )
    def post(self, request, tracking_code):
        report = get_report_or_404(tracking_code)
        if report.category not in agent_categories(request.user):
            raise ApiError("FORBIDDEN", "Ce signalement concerne un autre service.")

        serializer = AfterPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Autorisé depuis in_progress, ou depuis resolved si la photo « après » manque encore
        if report.status == Report.Status.RESOLVED and report.photo_after:
            raise ApiError("INVALID_TRANSITION", details={"from": report.status, "to": "resolved"})
        if report.status not in (Report.Status.IN_PROGRESS, Report.Status.RESOLVED):
            raise ApiError("INVALID_TRANSITION", details={"from": report.status, "to": "resolved"})

        report.photo_after = serializer.validated_data["photo"]
        report.save(update_fields=["photo_after", "updated_at"])
        if report.status != Report.Status.RESOLVED:
            _apply_status(report, Report.Status.RESOLVED, request.user, serializer.validated_data["note"])
        return Response(AgentReportSerializer(report).data)


def _apply_status(report, new_status, agent, note):
    old_status = report.status
    report.status = new_status
    if new_status == Report.Status.RESOLVED:
        report.resolved_at = timezone.now()
    report.save(update_fields=["status", "resolved_at", "updated_at"])
    StatusChange.objects.create(
        report=report, from_status=old_status, to_status=new_status, agent=agent, note=note
    )

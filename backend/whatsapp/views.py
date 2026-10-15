import json
import logging

from django.conf import settings
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.errors import ApiError

from .handlers import handle_incoming
from .signature import verify_signature

logger = logging.getLogger(__name__)


class WebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter("hub.mode", str, description="Toujours « subscribe »"),
            OpenApiParameter("hub.verify_token", str, description="Doit égaler WHATSAPP_VERIFY_TOKEN"),
            OpenApiParameter("hub.challenge", str, description="Texte à renvoyer tel quel"),
        ],
        responses={200: OpenApiTypes.STR},
        summary="Vérification du webhook par Meta (renvoie le hub.challenge)",
    )
    def get(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge", "")
        if mode == "subscribe" and token and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain")
        raise ApiError("FORBIDDEN", "Jeton de vérification incorrect.")

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses=inline_serializer("WebhookAck", {"status": serializers.CharField()}),
        summary="Réception des messages WhatsApp (signature X-Hub-Signature-256 vérifiée)",
    )
    def post(self, request):
        raw_body = request.body  # à lire AVANT request.data : la signature porte sur les octets exacts
        # Signature obligatoire dès qu'un secret est configuré ou que le mode n'est plus « mock »
        if settings.WHATSAPP_MODE != "mock" or settings.WHATSAPP_APP_SECRET:
            if not verify_signature(raw_body, request.headers.get("X-Hub-Signature-256", ""), settings.WHATSAPP_APP_SECRET):
                raise ApiError("FORBIDDEN", "Signature invalide.")
        try:
            payload = json.loads(raw_body or b"{}")
        except ValueError:
            raise ApiError("INVALID_INPUT", "Corps JSON illisible.")
        handle_incoming(payload)
        # Toujours répondre 200 rapidement, sinon Meta réessaie
        return Response({"status": "received"})

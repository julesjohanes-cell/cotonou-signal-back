import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from reports.models import CaptureSession, Report
from reports.utils import normalize_text, reporter_ref

from .client import mask_number, send_confirmation, send_text
from .handlers import HELP_MESSAGE, handle_incoming, iter_text_messages
from .signature import verify_signature

SECRET = "secret-de-test"
URL = "/api/v1/webhooks/whatsapp"

PAYLOAD = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {"from": "22990000000", "type": "text", "text": {"body": " Signaler "}},
                            {"from": "22990000000", "type": "image"},
                        ]
                    }
                },
                {"value": {"statuses": [{"status": "delivered"}]}},
            ]
        }
    ]
}


def sign(body, secret=SECRET):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# --- W-1 ---


class NormalizeTextTest(SimpleTestCase):
    def test_lowercase(self):
        self.assertEqual(normalize_text("SIGNALER"), "signaler")

    def test_mixed_case_with_accents(self):
        self.assertEqual(normalize_text("  SIGNALER  "), "signaler")

    def test_leading_trailing_spaces(self):
        self.assertEqual(normalize_text("  signaler  "), "signaler")

    def test_multiple_spaces(self):
        self.assertEqual(normalize_text("  signaler  probleme  "), "signaler probleme")

    def test_empty_string(self):
        self.assertEqual(normalize_text(""), "")

    def test_none(self):
        self.assertEqual(normalize_text(None), "")


# --- W-2 ---


@override_settings(WHATSAPP_MODE="mock", REPORTER_HMAC_KEY="test-hmac-key")
class HandleIncomingSignalerTest(TestCase):
    def test_signaler_creates_capture_session(self):
        handle_incoming(PAYLOAD)
        session = CaptureSession.objects.filter(channel=Report.Channel.WHATSAPP).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.channel, Report.Channel.WHATSAPP)
        self.assertNotEqual(session.reporter_ref, "22990000000")
        self.assertEqual(session.reporter_ref, reporter_ref("22990000000"))

    def test_signaler_stores_phone_number(self):
        handle_incoming(PAYLOAD)
        session = CaptureSession.objects.filter(channel=Report.Channel.WHATSAPP).first()
        self.assertEqual(session.phone_number, "22990000000")

    @override_settings(FRONT_URL="http://localhost:3000")
    def test_signaler_sends_capture_url(self):
        with patch("whatsapp.handlers.send_text") as mock_send:
            handle_incoming(PAYLOAD)
            mock_send.assert_called_once()
            to, body = mock_send.call_args[0][0], mock_send.call_args[0][1]
            self.assertEqual(to, "22990000000")
            self.assertIn("/capture/", body)

    def test_signaler_session_has_valid_token(self):
        handle_incoming(PAYLOAD)
        session = CaptureSession.objects.filter(channel=Report.Channel.WHATSAPP).first()
        self.assertTrue(len(session.token) > 10)
        from django.utils import timezone
        self.assertTrue(session.expires_at > timezone.now())

    def test_two_signaler_messages_create_two_sessions(self):
        handle_incoming(PAYLOAD)
        handle_incoming(PAYLOAD)
        self.assertEqual(CaptureSession.objects.filter(channel=Report.Channel.WHATSAPP).count(), 2)


# --- W-3 ---


@override_settings(WHATSAPP_MODE="mock", REPORTER_HMAC_KEY="test-hmac-key")
class HandleIncomingHelpTest(TestCase):
    def test_non_signaler_sends_help(self):
        payload = {
            "entry": [{"changes": [{"value": {"messages": [
                {"from": "22990000000", "type": "text", "text": {"body": "Bonjour"}}
            ]}}]}]
        }
        with patch("whatsapp.handlers.send_text") as mock_send:
            handle_incoming(payload)
            mock_send.assert_called_once_with("22990000000", HELP_MESSAGE)

    def test_non_signaler_does_not_create_session(self):
        payload = {
            "entry": [{"changes": [{"value": {"messages": [
                {"from": "22990000000", "type": "text", "text": {"body": "Aide"}}
            ]}}]}]
        }
        handle_incoming(payload)
        self.assertEqual(CaptureSession.objects.count(), 0)

    def test_help_message_content(self):
        self.assertIn("Signaler", HELP_MESSAGE)
        self.assertIn("Cotonou Signale", HELP_MESSAGE)

# --- W-4 ---


@override_settings(WHATSAPP_MODE="mock", REPORTER_HMAC_KEY="test-hmac-key")
class IgnoreNonTextEventsTest(TestCase):
    def setUp(self):
        self.api_client = APIClient()

    def test_status_events_are_ignored(self):
        payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
        with patch("whatsapp.handlers.send_text") as mock_send:
            handle_incoming(payload)
            mock_send.assert_not_called()
        self.assertEqual(CaptureSession.objects.count(), 0)

    def test_image_messages_are_ignored(self):
        payload = {"entry": [{"changes": [{"value": {"messages": [
            {"from": "22990000000", "type": "image"}
        ]}}]}]}
        with patch("whatsapp.handlers.send_text") as mock_send:
            handle_incoming(payload)
            mock_send.assert_not_called()

    def test_empty_payload_is_safe(self):
        with patch("whatsapp.handlers.send_text") as mock_send:
            handle_incoming({})
            mock_send.assert_not_called()

    @override_settings(WHATSAPP_APP_SECRET="")
    def test_webhook_returns_200_for_non_text(self):
        payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "read"}]}}]}]}
        response = self.api_client.post(URL, payload, format="json")
        self.assertEqual(response.status_code, 200)


# --- W-5 ---


@override_settings(WHATSAPP_MODE="mock", FRONT_URL="http://localhost:3000")
class SendConfirmationTest(SimpleTestCase):
    def test_confirmation_message_format(self):
        with patch("whatsapp.client.send_text") as mock_send:
            send_confirmation("22990000000", "CS-ABC123")
            mock_send.assert_called_once()
            body = mock_send.call_args[0][1]
            self.assertIn("CS-ABC123", body)
            self.assertIn("/suivi/CS-ABC123", body)
            self.assertIn("enregistr", body)

    def test_confirmation_uses_send_text(self):
        with patch("whatsapp.client.send_text") as mock_send:
            send_confirmation("22990000000", "CS-XYZ789")
            to = mock_send.call_args[0][0]
            self.assertEqual(to, "22990000000")

    def test_confirmation_tracking_url_format(self):
        with patch("whatsapp.client.send_text") as mock_send:
            send_confirmation("22990000000", "CS-TEST1")
            body = mock_send.call_args[0][1]
            self.assertIn("http://localhost:3000/suivi/CS-TEST1", body)

# --- Helpers ---


class HelpersTest(SimpleTestCase):
    def test_signature(self):
        body = b'{"a": 1}'
        self.assertTrue(verify_signature(body, sign(body), SECRET))
        self.assertFalse(verify_signature(body, sign(body, "autre"), SECRET))
        self.assertFalse(verify_signature(body, "", SECRET))
        self.assertFalse(verify_signature(body, sign(body), ""))

    def test_text_messages_only(self):
        self.assertEqual(list(iter_text_messages(PAYLOAD)), [("22990000000", " Signaler ")])
        self.assertEqual(list(iter_text_messages({})), [])

    def test_normalize_and_masking(self):
        self.assertEqual(normalize_text("  SIGNALER  "), "signaler")
        self.assertEqual(mask_number("22990000000"), "229****0000")

    @override_settings(REPORTER_HMAC_KEY="k")
    def test_reporter_ref_is_stable_and_hides_the_number(self):
        ref = reporter_ref("+229 90 00 00 00")
        self.assertEqual(ref, reporter_ref("22990000000"))
        self.assertNotIn("90000000", ref)
        self.assertEqual(reporter_ref(""), "")

    def test_mask_number_short(self):
        self.assertEqual(mask_number("123"), "****")

    def test_mask_number_empty(self):
        self.assertEqual(mask_number(""), "****")

    def test_mask_number_with_plus(self):
        self.assertEqual(mask_number("+22990000000"), "229****0000")


# --- Webhook ---


@override_settings(WHATSAPP_VERIFY_TOKEN="jeton")
class WebhookTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_verification_handshake(self):
        ok = self.client.get(URL, {"hub.mode": "subscribe", "hub.verify_token": "jeton", "hub.challenge": "12345"})
        self.assertEqual((ok.status_code, ok.content), (200, b"12345"))
        bad = self.client.get(URL, {"hub.mode": "subscribe", "hub.verify_token": "faux", "hub.challenge": "1"})
        self.assertEqual(bad.status_code, 403)

    @override_settings(WHATSAPP_MODE="mock", WHATSAPP_APP_SECRET="")
    def test_mock_mode_accepts_unsigned_requests(self):
        response = self.client.post(URL, PAYLOAD, format="json")
        self.assertEqual(response.status_code, 200)

    @override_settings(WHATSAPP_MODE="live", WHATSAPP_APP_SECRET=SECRET)
    def test_live_mode_requires_a_valid_signature(self):
        body = json.dumps(PAYLOAD).encode()
        unsigned = self.client.post(URL, body, content_type="application/json")
        self.assertEqual(unsigned.status_code, 403)
        forged = self.client.post(URL, body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sign(body, "autre"))
        self.assertEqual(forged.status_code, 403)
        signed = self.client.post(URL, body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sign(body))
        self.assertEqual(signed.status_code, 200)

    @override_settings(WHATSAPP_MODE="mock", WHATSAPP_APP_SECRET=SECRET)
    def test_a_configured_secret_is_always_enforced(self):
        response = self.client.post(URL, PAYLOAD, format="json")
        self.assertEqual(response.status_code, 403)

    @override_settings(WHATSAPP_MODE="mock", WHATSAPP_APP_SECRET="", REPORTER_HMAC_KEY="test-key")
    def test_full_signaler_flow_via_webhook(self):
        """Integration: POST webhook with Signaler -> session created."""
        response = self.client.post(URL, PAYLOAD, format="json")
        self.assertEqual(response.status_code, 200)
        session = CaptureSession.objects.filter(channel=Report.Channel.WHATSAPP).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.phone_number, "22990000000")
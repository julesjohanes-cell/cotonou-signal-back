from dataclasses import dataclass, field

from reports.geo import haversine_m


@dataclass
class Submission:
    """
    Ce que les vérifications examinent : les données envoyées par le citoyen, plus les résultats que les
    vérifications y déposent (`photo_sha256`, `ai_verdict`, `duplicate_of`).
    Une vérification ne renvoie rien : elle ne fait rien si tout va bien, ou lève `Rejection(code, ...)`.
    """

    category: object  # reports.models.Category
    description: str
    photo: object  # fichier envoyé (UploadedFile)
    point_lat: float  # le point du problème
    point_lng: float
    device_lat: float  # la position du téléphone
    device_lng: float
    device_accuracy_m: float
    channel: str = "web"
    capture_token: str = ""
    capture_session: object = None  # reports.models.CaptureSession ou None

    # Remplis par les vérifications
    photo_sha256: str = ""
    ai_verdict: dict = field(default_factory=dict)
    duplicate_of: object = None  # reports.models.Report si doublon

    @property
    def distance_m(self):
        """Distance en mètres entre le point du problème et la position du téléphone."""
        return haversine_m(self.device_lat, self.device_lng, self.point_lat, self.point_lng)

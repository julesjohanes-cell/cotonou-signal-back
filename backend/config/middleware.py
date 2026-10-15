class ApiTrailingSlashMiddleware:
    """
    Les routes de l'API n'ont pas de barre finale (`/api/v1/reports`). Ce middleware accepte aussi
    `/api/v1/reports/` : sans lui, un POST avec barre finale échouerait.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path.startswith("/api/v1/") and path.endswith("/") and len(path) > len("/api/v1/"):
            request.path_info = path.rstrip("/")
        return self.get_response(request)

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Bibliothèques géospatiales utilisées par GeoDjango (versions d'exécution seulement : image plus légère)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgdal32 libgeos-c1v5 libproj25 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Le script de démarrage vit hors de /app : en développement, /app est remplacé par le dossier local.
# Le sed retire les fins de ligne Windows (CRLF), qui feraient échouer le script.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh

COPY . .

EXPOSE 8000
ENTRYPOINT ["entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

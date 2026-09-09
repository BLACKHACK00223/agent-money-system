FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Native packages required by the PDF generation stack (pycairo, Pango, etc.).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libcairo2-dev \
        libgdk-pixbuf-2.0-dev \
        libpango1.0-dev \
        libxcb1-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

# Static files do not need production credentials.  Supplying temporary values
# only for this command keeps real Coolify secrets out of the image build.
RUN DJANGO_SECRET_KEY=build-only-key-not-used-at-runtime \
    DJANGO_ALLOWED_HOSTS=localhost \
    DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]

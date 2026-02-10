# Multi-stage build pour optimisation
FROM python:3.12-slim as builder

WORKDIR /app

# Installer dépendances de build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage final
FROM python:3.12-slim

WORKDIR /app

# Copier dépendances depuis builder
COPY --from=builder /root/.local /root/.local

# Installer curl pour healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copier le code source
COPY . .

# Variables d'environnement
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Exposer le port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Lancer l'application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

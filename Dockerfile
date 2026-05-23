# ─── Build stage ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Dependências do sistema (necessárias para scipy/numpy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# ─── Runtime stage ─────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copia pacotes instalados
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copia código da aplicação
COPY . .

# Cria diretório de dados (DB + subscribers)
RUN mkdir -p /app/data

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Porta padrão (Render sobrescreve via PORT)
EXPOSE 8000

# Gunicorn: 2 workers + 2 threads cada = suporta ~4 req simultâneas
CMD ["gunicorn", "wsgi:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--threads", "2", \
     "--timeout", "90", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

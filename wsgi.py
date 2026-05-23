"""Entrypoint para Gunicorn (produção).
  gunicorn wsgi:app --workers 2 --threads 2 --timeout 60
"""
from app import create_app

app = create_app()

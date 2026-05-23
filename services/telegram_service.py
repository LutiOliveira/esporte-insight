"""
Telegram Bot — notificações de gol e apostas de valor.
Configure TELEGRAM_BOT_TOKEN no .env.
Usuários se inscrevem enviando /start para o bot.
"""

import json
import os
import requests
from flask import current_app

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.getenv("DATA_DIR", os.path.join(_BASE, "data"))
SUBSCRIBERS_FILE = os.path.join(_DATA_DIR, "telegram_subscribers.json")


def _load_subscribers() -> list[int]:
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    try:
        with open(SUBSCRIBERS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _save_subscribers(subs: list[int]):
    os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(set(subs)), f)


def subscribe(chat_id: int):
    subs = _load_subscribers()
    if chat_id not in subs:
        subs.append(chat_id)
        _save_subscribers(subs)


def unsubscribe(chat_id: int):
    subs = [s for s in _load_subscribers() if s != chat_id]
    _save_subscribers(subs)


def subscriber_count() -> int:
    return len(_load_subscribers())


def send_message(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def broadcast(text: str):
    """Envia mensagem para todos os inscritos."""
    subs = _load_subscribers()
    for chat_id in subs:
        send_message(chat_id, text)


def notify_goal(home_team: str, away_team: str, home_score: int, away_score: int, minute: int = None):
    min_str = f" ({minute}')" if minute else ""
    text = (
        f"⚽ <b>GOL!</b>{min_str}\n"
        f"<b>{home_team} {home_score} – {away_score} {away_team}</b>\n"
        f"\n📊 Acompanhe em <b>Esporte Insight</b>"
    )
    broadcast(text)


def notify_value_bet(game_home: str, game_away: str, label: str, odd: float, edge: float, bookmaker: str, link: str):
    text = (
        f"💰 <b>APOSTA DE VALOR DETECTADA!</b>\n"
        f"{game_home} vs {game_away}\n\n"
        f"✅ <b>{label}</b>\n"
        f"Odd: <b>{odd}</b> | Vantagem: <b>+{edge}%</b>\n"
        f"Casa: {bookmaker}\n"
        f"👉 <a href='{link}'>Apostar agora</a>\n\n"
        f"📊 Análise completa em <b>Esporte Insight</b>"
    )
    broadcast(text)


def process_webhook(update: dict):
    """Processa mensagens recebidas do bot."""
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")

    if not chat_id:
        return

    if text.startswith("/start"):
        subscribe(chat_id)
        send_message(chat_id,
            "🎉 <b>Bem-vindo ao Esporte Insight!</b>\n\n"
            "Você receberá alertas de:\n"
            "⚽ Gols em tempo real\n"
            "💰 Apostas de valor detectadas\n\n"
            "Para cancelar, envie /stop"
        )
    elif text.startswith("/stop"):
        unsubscribe(chat_id)
        send_message(chat_id, "👋 Você cancelou as notificações. Envie /start para reativar.")
    elif text.startswith("/status"):
        count = subscriber_count()
        send_message(chat_id, f"📊 Esporte Insight tem <b>{count}</b> inscritos.")

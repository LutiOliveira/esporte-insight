import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Em produção (Render), o disco persistente monta em /opt/render/project/src/data
# Em desenvolvimento, usa BASE_DIR/data — ambos cobertos pelo mesmo caminho relativo
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
os.makedirs(DATA_DIR, exist_ok=True)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'copa.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
    ODDS_API_BASE = "https://api.the-odds-api.com/v4"

    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
    API_FOOTBALL_BASE = "https://v3.football.api-sports.io"

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Esportes monitorados (the-odds-api sport keys)
    SPORTS = ["soccer_fifa_world_cup", "soccer_brazil_campeonato"]

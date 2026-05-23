from extensions import db
from datetime import datetime


class Odds(db.Model):
    __tablename__ = "odds"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id = db.Column(db.String(64), db.ForeignKey("games.id"), nullable=False)
    bookmaker = db.Column(db.String(64), nullable=False)
    home_win = db.Column(db.Float, nullable=False)
    draw = db.Column(db.Float, nullable=False)
    away_win = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "bookmaker": self.bookmaker,
            "home_win": self.home_win,
            "draw": self.draw,
            "away_win": self.away_win,
        }

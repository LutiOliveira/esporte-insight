"""Odds de mercado Over/Under (totals) por jogo e bookmaker."""
from extensions import db
from datetime import datetime


class OddsTotal(db.Model):
    __tablename__ = "odds_totals"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id     = db.Column(db.String(64), db.ForeignKey("games.id"), nullable=False)
    bookmaker   = db.Column(db.String(64), nullable=False)
    line        = db.Column(db.Float, nullable=False)   # 0.5, 1.5, 2.5, 3.5, 4.5
    over_price  = db.Column(db.Float, nullable=False)
    under_price = db.Column(db.Float, nullable=False)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "bookmaker":   self.bookmaker,
            "line":        self.line,
            "over_price":  self.over_price,
            "under_price": self.under_price,
        }

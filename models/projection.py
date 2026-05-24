from extensions import db
from datetime import datetime


class Projection(db.Model):
    __tablename__ = "projections"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id     = db.Column(db.String(64), db.ForeignKey("games.id"), nullable=False, unique=True)
    home_win_prob   = db.Column(db.Float)
    draw_prob       = db.Column(db.Float)
    away_win_prob   = db.Column(db.Float)
    home_goals_proj = db.Column(db.Float)
    away_goals_proj = db.Column(db.Float)
    best_scoreline  = db.Column(db.String(8))
    scoreline_prob  = db.Column(db.Float)
    # NOVOS CAMPOS
    model_type  = db.Column(db.String(32), default="odds_derived")  # "elo" | "odds_derived"
    btts_yes    = db.Column(db.Float)   # P(ambos marcam = sim)
    btts_no     = db.Column(db.Float)   # P(ambos marcam = não)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "home_win_prob":    round(self.home_win_prob * 100, 1) if self.home_win_prob else None,
            "draw_prob":        round(self.draw_prob * 100, 1) if self.draw_prob else None,
            "away_win_prob":    round(self.away_win_prob * 100, 1) if self.away_win_prob else None,
            "home_goals_proj":  round(self.home_goals_proj, 2) if self.home_goals_proj else None,
            "away_goals_proj":  round(self.away_goals_proj * 100 / 100, 2) if self.away_goals_proj else None,
            "best_scoreline":   self.best_scoreline,
            "scoreline_prob":   round(self.scoreline_prob * 100, 1) if self.scoreline_prob else None,
            "model_type":       self.model_type or "odds_derived",
            "btts_yes":         round(self.btts_yes * 100, 1) if self.btts_yes else None,
            "btts_no":          round(self.btts_no * 100, 1) if self.btts_no else None,
        }

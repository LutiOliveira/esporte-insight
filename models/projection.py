from extensions import db
from datetime import datetime


class Projection(db.Model):
    __tablename__ = "projections"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id = db.Column(db.String(64), db.ForeignKey("games.id"), nullable=False, unique=True)
    home_win_prob = db.Column(db.Float, nullable=False)
    draw_prob = db.Column(db.Float, nullable=False)
    away_win_prob = db.Column(db.Float, nullable=False)
    home_goals_proj = db.Column(db.Float, nullable=False)
    away_goals_proj = db.Column(db.Float, nullable=False)
    best_scoreline = db.Column(db.String(16), nullable=False)
    scoreline_prob = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "home_win_prob": round(self.home_win_prob * 100, 1),
            "draw_prob": round(self.draw_prob * 100, 1),
            "away_win_prob": round(self.away_win_prob * 100, 1),
            "home_goals_proj": round(self.home_goals_proj, 2),
            "away_goals_proj": round(self.away_goals_proj, 2),
            "best_scoreline": self.best_scoreline,
            "scoreline_prob": round(self.scoreline_prob * 100, 1),
        }

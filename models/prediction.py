from extensions import db
from datetime import datetime


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id = db.Column(db.String(64), db.ForeignKey("games.id"), nullable=False, unique=True)
    predicted_outcome = db.Column(db.String(8), nullable=False)   # home/draw/away
    home_win_prob = db.Column(db.Float, nullable=False)
    draw_prob = db.Column(db.Float, nullable=False)
    away_win_prob = db.Column(db.Float, nullable=False)
    actual_outcome = db.Column(db.String(8), nullable=True)
    correct = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

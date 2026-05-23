from extensions import db
from datetime import datetime


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.String(64), primary_key=True)
    sport_key = db.Column(db.String(64), nullable=False)
    tournament = db.Column(db.String(128), nullable=False)
    home_team = db.Column(db.String(128), nullable=False)
    away_team = db.Column(db.String(128), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    stadium = db.Column(db.String(128), nullable=True)
    city = db.Column(db.String(128), nullable=True)
    broadcast = db.Column(db.String(256), nullable=True)
    group_name = db.Column(db.String(16), nullable=True)
    phase = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), default="upcoming")  # upcoming | live | finished
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    minute = db.Column(db.Integer, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    odds = db.relationship("Odds", backref="game", cascade="all, delete-orphan")
    projection = db.relationship("Projection", backref="game", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "sport_key": self.sport_key,
            "tournament": self.tournament,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "start_time": self.start_time.isoformat(),
            "stadium": self.stadium,
            "city": self.city,
            "broadcast": self.broadcast,
            "group_name": self.group_name,
            "phase": self.phase,
            "status": self.status,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "minute": self.minute,
            "odds": [o.to_dict() for o in self.odds],
            "projection": self.projection.to_dict() if self.projection else None,
        }

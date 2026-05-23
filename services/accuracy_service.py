from extensions import db
from models.game import Game
from models.prediction import Prediction
from datetime import datetime


def lock_prediction(game: Game):
    """Salva a projeção como predição antes do jogo começar."""
    if not game.projection or Prediction.query.filter_by(game_id=game.id).first():
        return
    proj = game.projection
    if proj.home_win_prob >= proj.draw_prob and proj.home_win_prob >= proj.away_win_prob:
        predicted = "home"
    elif proj.draw_prob >= proj.home_win_prob and proj.draw_prob >= proj.away_win_prob:
        predicted = "draw"
    else:
        predicted = "away"

    db.session.add(Prediction(
        game_id=game.id,
        predicted_outcome=predicted,
        home_win_prob=proj.home_win_prob,
        draw_prob=proj.draw_prob,
        away_win_prob=proj.away_win_prob,
    ))
    db.session.commit()


def resolve_predictions():
    """Compara predições com resultados reais de jogos encerrados."""
    finished = Game.query.filter(
        Game.status == "finished",
        Game.home_score.isnot(None),
    ).all()

    for game in finished:
        pred = Prediction.query.filter_by(game_id=game.id, actual_outcome=None).first()
        if not pred:
            continue

        h, a = game.home_score, game.away_score
        if h > a:
            actual = "home"
        elif h == a:
            actual = "draw"
        else:
            actual = "away"

        pred.actual_outcome = actual
        pred.correct = pred.predicted_outcome == actual
        pred.resolved_at = datetime.utcnow()

    db.session.commit()


def get_accuracy_stats() -> dict:
    total = Prediction.query.filter(Prediction.actual_outcome.isnot(None)).count()
    correct = Prediction.query.filter(Prediction.correct == True).count()
    pending = Prediction.query.filter(Prediction.actual_outcome.is_(None)).count()

    return {
        "total": total,
        "correct": correct,
        "pending": pending,
        "accuracy": round((correct / total * 100), 1) if total > 0 else None,
    }

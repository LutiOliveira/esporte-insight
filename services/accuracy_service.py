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


def get_accuracy_by_prob_range() -> list[dict]:
    """
    Agrupa predições resolvidas por faixa de probabilidade do modelo.
    Útil para verificar calibração: times com 70% de confiança devem acertar ~70%.
    """
    preds = Prediction.query.filter(Prediction.actual_outcome.isnot(None)).all()

    buckets = {
        "50-60%": {"total": 0, "correct": 0, "min": 0.50, "max": 0.60},
        "60-70%": {"total": 0, "correct": 0, "min": 0.60, "max": 0.70},
        "70-80%": {"total": 0, "correct": 0, "min": 0.70, "max": 0.80},
        "80%+":   {"total": 0, "correct": 0, "min": 0.80, "max": 1.01},
    }

    for pred in preds:
        if pred.predicted_outcome == "home":
            p = pred.home_win_prob
        elif pred.predicted_outcome == "draw":
            p = pred.draw_prob
        else:
            p = pred.away_win_prob

        for name, bk in buckets.items():
            if bk["min"] <= p < bk["max"]:
                bk["total"] += 1
                if pred.correct:
                    bk["correct"] += 1
                break

    result = []
    for name, bk in buckets.items():
        acc = round(bk["correct"] / bk["total"] * 100, 1) if bk["total"] > 0 else None
        result.append({
            "range": name,
            "total": bk["total"],
            "correct": bk["correct"],
            "accuracy": acc,
        })
    return result


def get_calibration_data() -> list[dict]:
    """
    Curva de calibração: probabilidade do modelo vs frequência real de acertos.
    Retorna pontos agrupados em decis (0-10%, 10-20%, …, 90-100%).
    """
    preds = Prediction.query.filter(Prediction.actual_outcome.isnot(None)).all()

    buckets = {i: {"total": 0, "correct": 0} for i in range(10)}

    for pred in preds:
        if pred.predicted_outcome == "home":
            p = pred.home_win_prob
        elif pred.predicted_outcome == "draw":
            p = pred.draw_prob
        else:
            p = pred.away_win_prob

        idx = min(9, int(p * 10))
        buckets[idx]["total"] += 1
        if pred.correct:
            buckets[idx]["correct"] += 1

    result = []
    for i, data in sorted(buckets.items()):
        low = i * 10
        high = low + 10
        freq = round(data["correct"] / data["total"], 3) if data["total"] > 0 else None
        result.append({
            "bucket": f"{low}-{high}%",
            "mid_prob": low + 5,
            "total": data["total"],
            "frequency": freq,
        })
    return result

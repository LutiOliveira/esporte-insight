from flask import Blueprint, jsonify, request
from models import Game
from datetime import datetime, timedelta

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _game_dict(game):
    """Serializa jogo com value bets incluídos."""
    from services.value_bet_service import analyze_game, get_affiliate_link
    d = game.to_dict()
    d["value_bets"] = analyze_game(game)
    # Adiciona affiliate link a cada odd
    for o in d.get("odds", []):
        o["affiliate_link"] = get_affiliate_link(o["bookmaker"])
    return d


@api_bp.get("/games")
def list_games():
    status = request.args.get("status")
    days = int(request.args.get("days", 60))
    tournament = request.args.get("tournament")

    query = Game.query
    if status:
        query = query.filter(Game.status == status)
    else:
        query = query.filter(Game.status.in_(["upcoming", "live"]))

    if tournament:
        query = query.filter(Game.tournament.ilike(f"%{tournament}%"))

    cutoff = datetime.utcnow() + timedelta(days=days)
    query = query.filter(Game.start_time <= cutoff).order_by(Game.start_time.asc())

    return jsonify([_game_dict(g) for g in query.all()])


@api_bp.get("/games/<game_id>")
def get_game(game_id):
    game = Game.query.get_or_404(game_id)
    return jsonify(_game_dict(game))


@api_bp.get("/tournaments")
def list_tournaments():
    rows = Game.query.with_entities(Game.tournament).distinct().all()
    return jsonify([r[0] for r in rows])


@api_bp.get("/standings")
def get_standings():
    from services.standing_service import calculate_standings
    return jsonify(calculate_standings())


@api_bp.get("/bracket")
def get_bracket():
    from services.bracket_service import build_bracket
    return jsonify(build_bracket())


@api_bp.get("/live")
def get_live():
    live = Game.query.filter(Game.status == "live").order_by(Game.start_time).all()
    return jsonify([_game_dict(g) for g in live])


@api_bp.get("/value-bets")
def get_value_bets():
    """Retorna todos os jogos com apostas de valor detectadas."""
    from services.value_bet_service import analyze_game
    games = Game.query.filter(Game.status.in_(["upcoming", "live"])).all()
    result = []
    for game in games:
        vb = analyze_game(game)
        if vb:
            d = _game_dict(game)
            d["value_bets"] = vb
            result.append(d)
    result.sort(key=lambda g: max(v["edge"] for v in g["value_bets"]), reverse=True)
    return jsonify(result)


@api_bp.get("/accuracy")
def get_accuracy():
    from services.accuracy_service import get_accuracy_stats
    return jsonify(get_accuracy_stats())


@api_bp.get("/quota")
def get_quota():
    from services.odds_service import OddsService
    return jsonify(OddsService.quota_status())


@api_bp.post("/refresh")
def manual_refresh():
    from services.odds_service import OddsService
    from services.projection_service import ProjectionService
    from services.accuracy_service import resolve_predictions
    OddsService().fetch_and_store()
    ProjectionService().calculate_all()
    resolve_predictions()
    return jsonify({"status": "ok", "message": "Dados atualizados"})


@api_bp.post("/telegram/webhook")
def telegram_webhook():
    from services.telegram_service import process_webhook
    update = request.get_json(silent=True) or {}
    process_webhook(update)
    return jsonify({"ok": True})


@api_bp.get("/telegram/stats")
def telegram_stats():
    from services.telegram_service import subscriber_count
    return jsonify({"subscribers": subscriber_count()})


# ─── Demo endpoints ───────────────────────────────────────────────
@api_bp.post("/demo/simulate-live")
def simulate_live():
    from extensions import db
    for gid, hs, as_, min_ in [("wc26_arg_bol", 2, 0, 67), ("wc26_bra_mar", 1, 1, 43)]:
        g = Game.query.get(gid)
        if g:
            g.status = "live"; g.home_score = hs; g.away_score = as_; g.minute = min_
    db.session.commit()
    return jsonify({"status": "ok"})


@api_bp.post("/demo/reset-live")
def reset_live():
    from extensions import db
    for gid in ["wc26_arg_bol", "wc26_bra_mar"]:
        g = Game.query.get(gid)
        if g:
            g.status = "upcoming"; g.home_score = None; g.away_score = None; g.minute = None
    db.session.commit()
    return jsonify({"status": "ok"})

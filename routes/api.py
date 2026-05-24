from flask import Blueprint, jsonify, request
from models import Game
from datetime import datetime, timedelta

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _game_dict(game):
    """Serializa jogo com value bets incluídos."""
    from services.value_bet_service import analyze_game, get_affiliate_link, compute_ou_probs
    d = game.to_dict()
    d["value_bets"] = analyze_game(game)
    # Adiciona affiliate link a cada odd
    for o in d.get("odds", []):
        o["affiliate_link"] = get_affiliate_link(o["bookmaker"])

    # O/U projections (modelo Poisson) + BTTS + model_type
    proj = game.projection
    if proj and proj.home_goals_proj and proj.away_goals_proj:
        d["ou_projections"] = compute_ou_probs(proj.home_goals_proj, proj.away_goals_proj)
        d["btts_yes"] = round(proj.btts_yes * 100, 1) if proj.btts_yes else None
        d["btts_no"]  = round(proj.btts_no * 100, 1) if proj.btts_no else None
        d["model_type"] = proj.model_type or "odds_derived"

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


@api_bp.get("/ranking")
def get_ranking():
    """Retorna times ordenados por força (média de ataque - defesa sofrida) a partir das projeções."""
    from services.projection_service import GLOBAL_ATTACK_MEAN

    # Agrega gols projetados por time
    games = Game.query.filter(Game.status.in_(["upcoming", "live"])).all()

    team_stats = {}  # team -> {attack_sum, defense_sum, count, group}

    for game in games:
        proj = game.projection
        if not proj:
            continue
        for team, goals_scored, goals_conceded, grp in [
            (game.home_team, proj.home_goals_proj, proj.away_goals_proj, game.group_name),
            (game.away_team, proj.away_goals_proj, proj.home_goals_proj, game.group_name),
        ]:
            if team not in team_stats:
                team_stats[team] = {"attack_sum": 0.0, "defense_sum": 0.0, "count": 0, "group": grp or ""}
            team_stats[team]["attack_sum"] += goals_scored
            team_stats[team]["defense_sum"] += goals_conceded
            team_stats[team]["count"] += 1

    FLAGS_MAP = {
        "Mexico": "🇲🇽", "South Africa": "🇿🇦", "Jamaica": "🇯🇲", "Honduras": "🇭🇳",
        "USA": "🇺🇸", "Panama": "🇵🇦", "Ecuador": "🇪🇨", "New Zealand": "🇳🇿",
        "Canada": "🇨🇦", "Morocco": "🇲🇦", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Haiti": "🇭🇹",
        "Brazil": "🇧🇷", "Algeria": "🇩🇿", "Ivory Coast": "🇨🇮", "DR Congo": "🇨🇩",
        "Argentina": "🇦🇷", "Chile": "🇨🇱", "Japan": "🇯🇵", "Norway": "🇳🇴",
        "Spain": "🇪🇸", "Portugal": "🇵🇹", "Uruguay": "🇺🇾", "Turkey": "🇹🇷",
        "France": "🇫🇷", "Netherlands": "🇳🇱", "Colombia": "🇨🇴", "Australia": "🇦🇺",
        "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Switzerland": "🇨🇭", "Paraguay": "🇵🇾", "Iran": "🇮🇷",
        "Germany": "🇩🇪", "Belgium": "🇧🇪", "South Korea": "🇰🇷", "Sweden": "🇸🇪",
        "Qatar": "🇶🇦", "Croatia": "🇭🇷", "Saudi Arabia": "🇸🇦", "Tunisia": "🇹🇳",
        "Ghana": "🇬🇭", "Senegal": "🇸🇳", "Egypt": "🇪🇬", "Cape Verde": "🇨🇻",
        "Austria": "🇦🇹", "Bosnia & Herzegovina": "🇧🇦", "Czech Republic": "🇨🇿", "Uzbekistan": "🇺🇿",
    }

    result = []
    for team, stats in team_stats.items():
        n = stats["count"]
        avg_attack = stats["attack_sum"] / n
        avg_def = stats["defense_sum"] / n
        force = avg_attack - avg_def
        result.append({
            "team": team,
            "flag": FLAGS_MAP.get(team, ""),
            "group": stats["group"],
            "avg_attack": round(avg_attack, 3),
            "avg_defense_conceded": round(avg_def, 3),
            "force": round(force, 3),
            "games_analyzed": n,
        })

    result.sort(key=lambda x: x["force"], reverse=True)
    for i, item in enumerate(result):
        item["rank"] = i + 1

    return jsonify(result)


@api_bp.get("/compare")
def compare_teams():
    """Simula confronto direto entre dois times usando médias das projeções."""
    import math

    home = request.args.get("home", "")
    away = request.args.get("away", "")

    if not home or not away:
        return jsonify({"error": "Parâmetros home e away obrigatórios"}), 400

    def poisson_prob(k, lam):
        return (lam ** k * math.exp(-lam)) / math.factorial(k)

    GLOBAL_MEAN = 1.35

    # Busca gols projetados médios dos jogos existentes para cada time
    def get_team_avg(team):
        games = Game.query.filter(
            Game.status.in_(["upcoming", "live"])
        ).all()
        attack_vals = []
        for g in games:
            if not g.projection:
                continue
            if g.home_team == team:
                attack_vals.append(g.projection.home_goals_proj)
            elif g.away_team == team:
                attack_vals.append(g.projection.away_goals_proj)
        return sum(attack_vals) / len(attack_vals) if attack_vals else GLOBAL_MEAN

    lam_home = max(0.3, min(get_team_avg(home) * 1.1, 4.0))  # vantagem casa
    lam_away = max(0.3, min(get_team_avg(away), 4.0))

    max_goals = 7
    score_probs = {}
    calc_home_win = 0.0
    calc_draw = 0.0
    calc_away_win = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            p = poisson_prob(h, lam_home) * poisson_prob(a, lam_away)
            score_probs[(h, a)] = p
            if h > a:
                calc_home_win += p
            elif h == a:
                calc_draw += p
            else:
                calc_away_win += p

    best_score = max(score_probs, key=score_probs.get)
    best_prob = score_probs[best_score]

    total = calc_home_win + calc_draw + calc_away_win

    return jsonify({
        "home_team": home,
        "away_team": away,
        "home_win_prob": round(calc_home_win / total * 100, 1),
        "draw_prob": round(calc_draw / total * 100, 1),
        "away_win_prob": round(calc_away_win / total * 100, 1),
        "best_scoreline": f"{best_score[0]}x{best_score[1]}",
        "scoreline_prob": round(best_prob * 100, 1),
    })


@api_bp.get("/tips")
def get_tips():
    """Retorna o melhor value bet do dia (maior edge)."""
    from services.value_bet_service import analyze_game
    games = Game.query.filter(Game.status.in_(["upcoming", "live"])).all()
    best_tip = None
    best_edge = -1
    for game in games:
        vbs = analyze_game(game)
        for vb in vbs:
            if vb["edge"] > best_edge:
                best_edge = vb["edge"]
                best_tip = {**vb, "home_team": game.home_team, "away_team": game.away_team}
    if not best_tip:
        return jsonify({})
    return jsonify(best_tip)


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

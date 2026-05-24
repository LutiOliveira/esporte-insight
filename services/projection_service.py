"""
Serviço de projeção Poisson para jogos de futebol.

Dois modos:
- ELO (preferido): usa ratings Elo independentes das odds → edge real
- ODDS (fallback): deriva lambdas das odds → modelo circular (sinalizado como tal)

Dixon-Coles: correção para sub/superestimação de baixos placares (0-0, 1-0, 0-1, 1-1).
ρ = -0.13 (valor empírico do paper Dixon & Coles 1997, válido para futebol internacional).
"""

import math
from extensions import db
from models import Game, Projection
from services.elo_service import (
    get_elo, elo_to_goal_lambda, has_elo_for_game,
    GLOBAL_GOAL_MEAN, HOME_ADVANTAGE_DOMESTIC,
)

GLOBAL_ATTACK_MEAN = GLOBAL_GOAL_MEAN   # compatibilidade reversa
DIXON_COLES_RHO = -0.13


def _poisson_prob(k: int, lam: float) -> float:
    if lam <= 0 or k < 0:
        return 0.0
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def _implied_prob(odd: float) -> float:
    return 1 / odd if odd > 0 else 0


def _dixon_coles_tau(home_goals: int, away_goals: int,
                     lam_h: float, lam_a: float, rho: float = DIXON_COLES_RHO) -> float:
    """
    Fator de correção Dixon-Coles para placares baixos.
    Multiplica a probabilidade Poisson base para calibrar melhor as extremidades.
    """
    if home_goals == 0 and away_goals == 0:
        return 1 - lam_h * lam_a * rho
    elif home_goals == 1 and away_goals == 0:
        return 1 + lam_a * rho
    elif home_goals == 0 and away_goals == 1:
        return 1 + lam_h * rho
    elif home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def _compute_match(lam_home: float, lam_away: float, max_goals: int = 8) -> dict:
    """
    Calcula probabilidades de placar, resultado e O/U com Dixon-Coles.
    Retorna dict com todos os outputs da projeção.
    """
    score_probs_raw = {}
    for h in range(max_goals):
        for a in range(max_goals):
            p = _poisson_prob(h, lam_home) * _poisson_prob(a, lam_away)
            tau = _dixon_coles_tau(h, a, lam_home, lam_away)
            score_probs_raw[(h, a)] = p * tau

    # Renormaliza
    total_raw = sum(score_probs_raw.values())
    score_probs = {k: v / total_raw for k, v in score_probs_raw.items()}

    calc_home_win = sum(p for (h, a), p in score_probs.items() if h > a)
    calc_draw = sum(p for (h, a), p in score_probs.items() if h == a)
    calc_away_win = sum(p for (h, a), p in score_probs.items() if a > h)

    best_score = max(score_probs, key=score_probs.get)
    best_prob = score_probs[best_score]

    # O/U cumulativo
    total_probs: dict[int, float] = {}
    for (h, a), p in score_probs.items():
        t = h + a
        total_probs[t] = total_probs.get(t, 0.0) + p

    ou_probs = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        floor_line = int(line)
        over = sum(v for k, v in total_probs.items() if k > floor_line)
        ou_probs[str(line)] = {"over": round(over, 4), "under": round(1 - over, 4)}

    # BTTS — Ambos Marcam
    p_home_scores = 1 - _poisson_prob(0, lam_home)
    p_away_scores = 1 - _poisson_prob(0, lam_away)
    btts_yes = p_home_scores * p_away_scores
    btts_no = 1 - btts_yes

    return {
        "home_win": calc_home_win,
        "draw": calc_draw,
        "away_win": calc_away_win,
        "best_score": best_score,
        "best_prob": best_prob,
        "ou_probs": ou_probs,
        "btts_yes": round(btts_yes, 4),
        "btts_no": round(btts_no, 4),
    }


class ProjectionService:

    def calculate_all(self):
        games = Game.query.filter(Game.status == "upcoming").all()
        for game in games:
            if not game.odds:
                continue
            self._calculate_game(game)
        db.session.commit()

    def _calculate_game(self, game: Game):
        """Despacha para método Elo (independente) ou odds (fallback circular)."""
        if has_elo_for_game(game.home_team, game.away_team):
            self._calculate_game_elo(game)
        else:
            self._calculate_game_odds(game)

    def _calculate_game_elo(self, game: Game):
        """Modelo independente: usa Elo ratings. Edge detectado aqui é REAL."""
        elo_home = get_elo(game.home_team)
        elo_away = get_elo(game.away_team)

        # Copa 2026 = sede neutra; outras competições internacionais = sem vantagem
        # Doméstico (ex: Brasileirão) = vantagem de campo normal
        is_copa = "world_cup" in game.sport_key or "copa" in game.sport_key.lower()
        home_adv = 1.0 if is_copa else HOME_ADVANTAGE_DOMESTIC

        lam_home, lam_away = elo_to_goal_lambda(elo_home, elo_away, home_advantage=home_adv)
        result = _compute_match(lam_home, lam_away)
        self._save_projection(game, lam_home, lam_away, result, model_type="elo")

    def _calculate_game_odds(self, game: Game):
        """
        Fallback circular: deriva lambdas das odds.
        Edge detectado aqui é artefato matemático, não vantagem real.
        Usado apenas para times sem Elo rating (Brasileirão, etc.)
        """
        home_odds = [o.home_win for o in game.odds]
        draw_odds = [o.draw for o in game.odds]
        away_odds = [o.away_win for o in game.odds]

        avg_home = sum(home_odds) / len(home_odds)
        avg_draw = sum(draw_odds) / len(draw_odds)
        avg_away = sum(away_odds) / len(away_odds)

        raw_home = _implied_prob(avg_home)
        raw_draw = _implied_prob(avg_draw)
        raw_away = _implied_prob(avg_away)
        total = raw_home + raw_draw + raw_away

        home_prob = raw_home / total
        draw_prob = raw_draw / total

        home_strength = home_prob / (1 - draw_prob)
        away_strength = (raw_away / total) / (1 - draw_prob)

        lam_home = max(0.3, min(GLOBAL_ATTACK_MEAN * home_strength * HOME_ADVANTAGE_DOMESTIC, 4.0))
        lam_away = max(0.3, min(GLOBAL_ATTACK_MEAN * away_strength, 4.0))

        result = _compute_match(lam_home, lam_away)
        self._save_projection(game, lam_home, lam_away, result, model_type="odds_derived")

    def _save_projection(self, game: Game, lam_home: float, lam_away: float,
                          result: dict, model_type: str):
        proj = game.projection
        if not proj:
            proj = Projection(game_id=game.id)
            db.session.add(proj)

        proj.home_win_prob    = result["home_win"]
        proj.draw_prob        = result["draw"]
        proj.away_win_prob    = result["away_win"]
        proj.home_goals_proj  = lam_home
        proj.away_goals_proj  = lam_away
        proj.best_scoreline   = f"{result['best_score'][0]}x{result['best_score'][1]}"
        proj.scoreline_prob   = result["best_prob"]
        proj.model_type       = model_type
        proj.btts_yes         = result["btts_yes"]
        proj.btts_no          = result["btts_no"]

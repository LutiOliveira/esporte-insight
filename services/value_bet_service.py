"""
Caçador de Valor — compara probabilidade do modelo Poisson
com a probabilidade implícita das odds para encontrar apostas com vantagem real.
Edge = prob_modelo - prob_implícita. Threshold mínimo: 5%.
"""

import math as _math

MIN_EDGE = 0.05

AFFILIATE_LINKS = {
    "Betano":      "https://record.betano.com/sign-up?affid=SEU_ID",
    "Bet365":      "https://www.bet365.com",
    "KTO":         "https://www.kto.com/pt-br/",
    "Betfair":     "https://www.betfair.com/exchange/plus/football",
    "Pinnacle":    "https://www.pinnacle.com/pt/",
    "William Hill":"https://sports.williamhill.com/betting/pt-br",
    "Sportingbet": "https://sports.sportingbet.com/pt-br/sports",
    "Betway":      "https://betway.com/pt/sports/",
    "Unibet":      "https://www.unibet.com/betting/sports/",
    "DraftKings":  "https://www.draftkings.com/",
    "FanDuel":     "https://www.fanduel.com/sportsbook",
    "Bovada":      "https://www.bovada.lv/",
    "BetUS":       "https://www.betus.com.pa/",
    "Betfair":     "https://www.betfair.com/",
}


def get_affiliate_link(bookmaker: str) -> str:
    return AFFILIATE_LINKS.get(bookmaker, "#")


def _poisson_prob_ou(k, lam):
    if lam <= 0 or k < 0:
        return 0
    return (lam ** k * _math.exp(-lam)) / _math.factorial(k)


def compute_ou_probs(lambda_home: float, lambda_away: float) -> dict:
    """Retorna probabilidades de Over/Under para 0.5, 1.5, 2.5, 3.5."""
    max_goals = 10
    total_probs = {}
    for h in range(max_goals):
        for a in range(max_goals):
            t = h + a
            p = _poisson_prob_ou(h, lambda_home) * _poisson_prob_ou(a, lambda_away)
            total_probs[t] = total_probs.get(t, 0.0) + p

    result = {}
    for line in [0.5, 1.5, 2.5, 3.5]:
        floor_line = int(line)
        over_prob = sum(v for k, v in total_probs.items() if k > floor_line)
        under_prob = 1.0 - over_prob
        result[str(line)] = {
            "over": round(over_prob, 4),
            "under": round(under_prob, 4),
        }
    return result


def analyze_game(game) -> list[dict]:
    """Retorna lista de apostas com valor positivo para o jogo."""
    proj = game.projection
    if not proj or not game.odds:
        return []

    model = {
        "home": proj.home_win_prob,   # já armazenado como decimal (0.0–1.0)
        "draw": proj.draw_prob,
        "away": proj.away_win_prob,
    }

    labels = {
        "home": f"Vitória {game.home_team}",
        "draw": "Empate",
        "away": f"Vitória {game.away_team}",
    }

    odd_fields = {"home": "home_win", "draw": "draw", "away": "away_win"}

    results = []
    for key, model_prob in model.items():
        field = odd_fields[key]
        best = max(game.odds, key=lambda o: getattr(o, field))
        best_odd = getattr(best, field)
        implied = 1 / best_odd
        edge = model_prob - implied

        if edge >= MIN_EDGE:
            kelly_pct = (model_prob * best_odd - 1) / (best_odd - 1)
            kelly_pct = max(0.001, min(kelly_pct, 0.25))
            results.append({
                "outcome": key,
                "label": labels[key],
                "model_prob": round(model_prob * 100, 1),
                "implied_prob": round(implied * 100, 1),
                "edge": round(edge * 100, 1),
                "best_odd": round(best_odd, 2),
                "bookmaker": best.bookmaker,
                "affiliate_link": get_affiliate_link(best.bookmaker),
                "kelly_pct": round(kelly_pct * 100, 1),
                "half_kelly_pct": round(kelly_pct * 50, 1),
                "market_type": "1x2",
            })

    return sorted(results, key=lambda x: x["edge"], reverse=True)

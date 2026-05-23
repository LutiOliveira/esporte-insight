"""
Caçador de Valor — compara probabilidade do modelo Poisson
com a probabilidade implícita das odds para encontrar apostas com vantagem real.
Edge = prob_modelo - prob_implícita. Threshold mínimo: 5%.
"""

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
            results.append({
                "outcome": key,
                "label": labels[key],
                "model_prob": round(model_prob * 100, 1),
                "implied_prob": round(implied * 100, 1),
                "edge": round(edge * 100, 1),
                "best_odd": round(best_odd, 2),
                "bookmaker": best.bookmaker,
                "affiliate_link": get_affiliate_link(best.bookmaker),
            })

    return sorted(results, key=lambda x: x["edge"], reverse=True)

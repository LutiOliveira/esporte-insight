"""
Caçador de Valor — detecta apostas com vantagem real sobre o mercado.

Modelo ELO (Copa 2026): edge detectado é REAL — modelo independente das odds.
Modelo ODDS_DERIVED (Brasileirão): edge é artefato circular — tratar com cautela.
"""

import math as _math

MIN_EDGE = 0.05

# Limite máximo de Kelly por tipo de mercado (gestão de risco)
KELLY_CAPS: dict[str, float] = {
    "1x2":  0.20,   # 1X2 — mercado mais líquido
    "ou":   0.12,   # Over/Under — incerteza maior
    "btts": 0.08,   # Ambos marcam — mercado menor
    "cs":   0.05,   # Placar correto — alta variância
}

AFFILIATE_LINKS = {
    "Betano":       "https://record.betano.com/sign-up?affid=SEU_ID",
    "Bet365":       "https://www.bet365.com",
    "KTO":          "https://www.kto.com/pt-br/",
    "Betfair":      "https://www.betfair.com/exchange/plus/football",
    "Pinnacle":     "https://www.pinnacle.com/pt/",
    "William Hill": "https://sports.williamhill.com/betting/pt-br",
    "Sportingbet":  "https://sports.sportingbet.com/pt-br/sports",
    "Betway":       "https://betway.com/pt/sports/",
    "Unibet":       "https://www.unibet.com/betting/sports/",
    "DraftKings":   "https://www.draftkings.com/",
    "FanDuel":      "https://www.fanduel.com/sportsbook",
    "Bovada":       "https://www.bovada.lv/",
    "BetMGM":       "https://sports.betmgm.com/",
    "Matchbook":    "https://www.matchbook.com/",
    "Betsson":      "https://www.betsson.com/",
    "1xBet":        "https://www.1xbet.com/",
    "888sport":     "https://www.888sport.com/",
    "Winamax (DE)": "https://www.winamax.de/",
    "Winamax (FR)": "https://www.winamax.fr/",
    "Marathon Bet": "https://www.marathonbet.com/",
}


def get_affiliate_link(bookmaker: str) -> str:
    return AFFILIATE_LINKS.get(bookmaker, "#")


def _kelly(model_prob: float, odd: float, market_type: str = "1x2") -> tuple[float, float]:
    """
    Retorna (full_kelly_pct, quarter_kelly_pct) como percentual 0-100.
    Aplica teto diferenciado por tipo de mercado (KELLY_CAPS).
    """
    if odd <= 1.0 or model_prob <= 0:
        return 0.0, 0.0
    k = (model_prob * odd - 1) / (odd - 1)
    cap = KELLY_CAPS.get(market_type, 0.20)
    k = max(0.0, min(k, cap))
    return round(k * 100, 1), round(k * 25, 1)


def _poisson_p(k: int, lam: float) -> float:
    if lam <= 0 or k < 0:
        return 0.0
    return (lam ** k * _math.exp(-lam)) / _math.factorial(k)


def compute_ou_probs(lambda_home: float, lambda_away: float) -> dict:
    """Probabilidades Over/Under para linhas 0.5-4.5 via Poisson."""
    max_goals = 12
    total_probs: dict[int, float] = {}
    for h in range(max_goals):
        for a in range(max_goals):
            t = h + a
            p = _poisson_p(h, lambda_home) * _poisson_p(a, lambda_away)
            total_probs[t] = total_probs.get(t, 0.0) + p
    result = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        fl = int(line)
        over = sum(v for k, v in total_probs.items() if k > fl)
        result[str(line)] = {"over": round(over, 4), "under": round(1 - over, 4)}
    return result


def analyze_game(game) -> list[dict]:
    proj = game.projection
    if not proj or not game.odds:
        return []

    model_type = getattr(proj, "model_type", None) or "odds_derived"
    is_real = model_type == "elo"
    results = []

    # ── 1X2 ───────────────────────────────────────────────────────────────────
    model_1x2 = {
        "home": proj.home_win_prob,
        "draw": proj.draw_prob,
        "away": proj.away_win_prob,
    }
    labels = {
        "home": f"Vitória {game.home_team}",
        "draw": "Empate",
        "away": f"Vitória {game.away_team}",
    }
    odd_fields = {"home": "home_win", "draw": "draw", "away": "away_win"}

    for key, model_prob in model_1x2.items():
        field = odd_fields[key]
        best = max(game.odds, key=lambda o: getattr(o, field))
        best_odd = getattr(best, field)
        implied = 1 / best_odd
        edge = model_prob - implied
        if edge >= MIN_EDGE:
            fk, qk = _kelly(model_prob, best_odd, "1x2")
            results.append({
                "outcome": key, "label": labels[key],
                "market_type": "1x2",
                "model_prob": round(model_prob * 100, 1),
                "implied_prob": round(implied * 100, 1),
                "edge": round(edge * 100, 1),
                "best_odd": round(best_odd, 2),
                "bookmaker": best.bookmaker,
                "affiliate_link": get_affiliate_link(best.bookmaker),
                "kelly_pct": fk, "quarter_kelly_pct": qk,
                "model_type": model_type, "is_real_edge": is_real,
            })

    # ── O/U com odds reais ────────────────────────────────────────────────────
    ou_probs = compute_ou_probs(proj.home_goals_proj, proj.away_goals_proj)
    odds_totals = getattr(game, "odds_total", [])
    seen_ou: dict[str, dict] = {}

    for ot in odds_totals:
        line_key = str(float(ot.line))
        if line_key not in ou_probs:
            continue
        probs = ou_probs[line_key]
        for side, price in [("over", ot.over_price), ("under", ot.under_price)]:
            if not price or price <= 1.0:
                continue
            model_prob = probs[side]
            implied = 1 / price
            edge = model_prob - implied
            if edge < MIN_EDGE:
                continue
            ou_key = f"{side}_{ot.line}"
            if ou_key not in seen_ou or edge > seen_ou[ou_key]["edge"]:
                fk, qk = _kelly(model_prob, price, "ou")
                seen_ou[ou_key] = {
                    "outcome": ou_key,
                    "label": f"{'Over' if side == 'over' else 'Under'} {ot.line} gols",
                    "market_type": "ou",
                    "model_prob": round(model_prob * 100, 1),
                    "implied_prob": round(implied * 100, 1),
                    "edge": round(edge * 100, 1),
                    "best_odd": round(price, 2),
                    "bookmaker": ot.bookmaker,
                    "affiliate_link": get_affiliate_link(ot.bookmaker),
                    "kelly_pct": fk, "quarter_kelly_pct": qk,
                    "model_type": model_type, "is_real_edge": is_real,
                }

    results.extend(seen_ou.values())
    return sorted(results, key=lambda x: x["edge"], reverse=True)

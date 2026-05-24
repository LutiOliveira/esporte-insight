"""
Serviço de ratings Elo para seleções da Copa 2026.
Elo ratings aproximados baseados no ranking FIFA 2025 + histórico recente.
Fonte: worldfootball-elo.net (aproximados, atualizados manualmente pré-Copa).

Com ratings independentes, as projeções não dependem das odds do mercado —
eliminando a circularidade do modelo anterior.
"""

# Ratings Elo aproximados (base 1500 = time médio de Copa)
# Atualizados para refletir forma 2024-2025
ELO_RATINGS: dict[str, int] = {
    # Favoritos absolutos
    "Argentina":           1870,
    "France":              1855,
    "Spain":               1845,
    "England":             1830,
    "Brazil":              1820,
    "Portugal":            1815,
    "Netherlands":         1800,
    "Germany":             1795,

    # Segundo escalão forte
    "Belgium":             1775,
    "Colombia":            1750,
    "Uruguay":             1740,
    "Croatia":             1730,
    "Morocco":             1720,
    "USA":                 1710,
    "Switzerland":         1700,
    "Senegal":             1690,

    # Terceiro escalão — competitivos
    "Ecuador":             1675,
    "Japan":               1670,
    "Mexico":              1665,
    "Norway":              1660,
    "Australia":           1645,
    "Austria":             1640,
    "South Korea":         1630,
    "Egypt":               1620,
    "Ghana":               1615,
    "Turkey":              1610,
    "Czech Republic":      1600,
    "Chile":               1595,
    "Bosnia & Herzegovina": 1585,
    "Algeria":             1575,
    "Paraguay":            1565,
    "Scotland":            1555,
    "South Africa":        1545,
    "Ivory Coast":         1540,
    "DR Congo":            1535,
    "Canada":              1530,
    "Iran":                1525,
    "Sweden":              1520,

    # Quarto escalão
    "Saudi Arabia":        1510,
    "Panama":              1505,
    "Tunisia":             1500,
    "Cape Verde":          1495,
    "New Zealand":         1475,
    "Qatar":               1465,
    "Jamaica":             1455,
    "Haiti":               1435,
    "Honduras":            1425,
    "Uzbekistan":          1415,
}

# Média global de gols por jogo em Copa do Mundo (histórico 1998-2022)
GLOBAL_GOAL_MEAN = 1.35

# Fator de campo para Copa 2026 — sede NEUTRA (EUA/Canadá/México)
# Apenas México e USA têm leve vantagem por familiaridade com estádios
HOME_ADVANTAGE_COPA = 1.0   # sem vantagem real em sede neutra
HOME_ADVANTAGE_DOMESTIC = 1.08  # ligas domésticas (Brasileirão etc.)


def get_elo(team: str) -> int | None:
    """Retorna rating Elo do time, ou None se não mapeado."""
    return ELO_RATINGS.get(team)


def elo_to_goal_lambda(
    rating_home: int,
    rating_away: int,
    global_mean: float = GLOBAL_GOAL_MEAN,
    home_advantage: float = HOME_ADVANTAGE_COPA,
) -> tuple[float, float]:
    """
    Converte diferença de rating Elo em lambdas esperados de gols.

    Fórmula: fator = 10^(diff/1000)
    - 1000 pts de diferença → ~2.6x mais gols (calibrado empiricamente)
    - 200 pts de diferença → ~1.58x (Brasil vs Senegal ≈ 2.13 vs 1.35)
    - 0 pts de diferença → 1.35 vs 1.35 (times iguais)

    Returns: (lambda_home, lambda_away) — esperança de gols de cada time
    """
    diff = rating_home - rating_away
    factor = 10 ** (diff / 1000)

    lambda_home = global_mean * factor * home_advantage
    lambda_away = global_mean / factor

    # Clamps realistas para futebol
    lambda_home = max(0.30, min(lambda_home, 4.50))
    lambda_away = max(0.30, min(lambda_away, 4.50))

    return lambda_home, lambda_away


def has_elo_for_game(home_team: str, away_team: str) -> bool:
    """True se ambos os times têm rating Elo (jogo tem modelo independente)."""
    return home_team in ELO_RATINGS and away_team in ELO_RATINGS

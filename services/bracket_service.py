"""
Bracket da Copa do Mundo 2026.
Formato: 12 grupos → 24 primeiros + 8 melhores 3os = 32 times → Rodada de 32 → ... → Final.
"""

from services.standing_service import calculate_standings

# Pairings oficiais da FIFA para a Copa 2026 (Rodada de 32)
# Formato: (referência do mandante, referência do visitante)
R32_PAIRINGS = [
    ("1A", "2B"), ("1C", "2D"), ("1E", "2F"), ("1G", "2H"),
    ("1I", "2J"), ("1K", "2L"), ("1B", "2C"), ("1D", "2A"),
    ("1F", "2E"), ("1H", "2G"), ("1J", "2I"), ("1L", "2K"),
    ("M3",  "N3"), ("O3",  "P3"), ("Q3",  "R3"), ("S3",  "T3"),
]

ROUND_NAMES = {
    "r32": "Rodada de 32",
    "r16": "Oitavas de Final",
    "qf":  "Quartas de Final",
    "sf":  "Semifinais",
    "f":   "Final",
    "3rd": "Disputa do 3º Lugar",
}


def _resolve_team(ref: str, standings: dict) -> str:
    """Converte '1A', '2B' em nome do time classificado ou 'placeholder'."""
    if len(ref) == 2 and ref[0].isdigit():
        pos = int(ref[0]) - 1
        group = ref[1]
        teams = standings.get(group, [])
        if len(teams) > pos and teams[pos]["P"] > 0:
            return teams[pos]["team"]
    return f"{ref[0]}º Grupo {ref[1]}" if len(ref) == 2 else "A definir"


def build_bracket() -> dict:
    standings = calculate_standings()

    r32_games = []
    for i, (home_ref, away_ref) in enumerate(R32_PAIRINGS, 1):
        home = _resolve_team(home_ref, standings)
        away = _resolve_team(away_ref, standings)
        r32_games.append({
            "slot": f"R32_{i}",
            "home_team": home,
            "away_team": away,
            "home_ref": home_ref,
            "away_ref": away_ref,
            "home_score": None,
            "away_score": None,
            "status": "upcoming",
        })

    # Rodadas eliminatórias (placeholders até R32 ser disputada)
    def empty_ko(prefix, n):
        return [
            {
                "slot": f"{prefix}_{i}",
                "home_team": "A definir",
                "away_team": "A definir",
                "home_score": None,
                "away_score": None,
                "status": "upcoming",
            }
            for i in range(1, n + 1)
        ]

    return {
        "rounds": [
            {"key": "r32", "name": ROUND_NAMES["r32"], "games": r32_games},
            {"key": "r16", "name": ROUND_NAMES["r16"], "games": empty_ko("R16", 8)},
            {"key": "qf",  "name": ROUND_NAMES["qf"],  "games": empty_ko("QF", 4)},
            {"key": "sf",  "name": ROUND_NAMES["sf"],  "games": empty_ko("SF", 2)},
            {"key": "3rd", "name": ROUND_NAMES["3rd"], "games": empty_ko("3RD", 1)},
            {"key": "f",   "name": ROUND_NAMES["f"],   "games": empty_ko("FIN", 1)},
        ]
    }

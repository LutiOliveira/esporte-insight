from models import Game


def calculate_standings():
    """Calcula a classificação de cada grupo a partir dos resultados dos jogos."""
    games = Game.query.filter(
        Game.group_name.isnot(None),
        Game.sport_key == "soccer_fifa_world_cup",
    ).all()

    groups: dict[str, dict] = {}

    for game in games:
        g = game.group_name
        if g not in groups:
            groups[g] = {}

        for team in [game.home_team, game.away_team]:
            if team not in groups[g]:
                groups[g][team] = {
                    "team": team, "P": 0, "W": 0, "D": 0,
                    "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0,
                    "live": False,
                }

        if game.home_score is not None and game.away_score is not None:
            h, a = game.home_score, game.away_score
            is_live = game.status == "live"

            for team, gf, ga in [
                (game.home_team, h, a),
                (game.away_team, a, h),
            ]:
                s = groups[g][team]
                s["GF"] += gf
                s["GA"] += ga
                s["GD"] = s["GF"] - s["GA"]
                s["P"] += 1
                if is_live:
                    s["live"] = True

            # Pontos computados igual para jogos ao vivo e encerrados
            if h > a:
                groups[g][game.home_team]["W"] += 1
                groups[g][game.home_team]["Pts"] += 3
                groups[g][game.away_team]["L"] += 1
            elif h == a:
                groups[g][game.home_team]["D"] += 1
                groups[g][game.home_team]["Pts"] += 1
                groups[g][game.away_team]["D"] += 1
                groups[g][game.away_team]["Pts"] += 1
            else:
                groups[g][game.away_team]["W"] += 1
                groups[g][game.away_team]["Pts"] += 3
                groups[g][game.home_team]["L"] += 1

    result = {}
    for g, teams in sorted(groups.items()):
        result[g] = sorted(
            teams.values(),
            key=lambda x: (x["Pts"], x["GD"], x["GF"]),
            reverse=True,
        )

    return result


def get_live_games():
    """Retorna jogos ao vivo com placar atual."""
    live = Game.query.filter(Game.status == "live").all()
    return [
        {
            "id": g.id,
            "home_team": g.home_team,
            "away_team": g.away_team,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "group_name": g.group_name,
            "minute": g.minute if hasattr(g, "minute") else None,
        }
        for g in live
    ]

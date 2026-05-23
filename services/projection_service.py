import math
from extensions import db
from models import Game, Projection

# Média global de gols por jogo em Copas do Mundo (histórico)
GLOBAL_ATTACK_MEAN = 1.35


def _poisson_prob(k: int, lam: float) -> float:
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def _implied_prob(odd: float) -> float:
    return 1 / odd if odd > 0 else 0


class ProjectionService:

    def calculate_all(self):
        games = Game.query.filter(Game.status == "upcoming").all()
        for game in games:
            if not game.odds:
                continue
            self._calculate_game(game)
        db.session.commit()

    def _calculate_game(self, game: Game):
        # Média das odds entre todas as casas disponíveis
        home_odds_list = [o.home_win for o in game.odds]
        draw_odds_list = [o.draw for o in game.odds]
        away_odds_list = [o.away_win for o in game.odds]

        avg_home = sum(home_odds_list) / len(home_odds_list)
        avg_draw = sum(draw_odds_list) / len(draw_odds_list)
        avg_away = sum(away_odds_list) / len(away_odds_list)

        # Probabilidades implícitas normalizadas (remove margem da casa)
        raw_home = _implied_prob(avg_home)
        raw_draw = _implied_prob(avg_draw)
        raw_away = _implied_prob(avg_away)
        total = raw_home + raw_draw + raw_away

        home_prob = raw_home / total
        draw_prob = raw_draw / total
        away_prob = raw_away / total

        # Estimativa de gols esperados via modelo de Dixon-Coles simplificado
        # Derivamos força de ataque/defesa a partir das probabilidades implícitas
        home_strength = home_prob / (1 - draw_prob)
        away_strength = away_prob / (1 - draw_prob)

        lambda_home = GLOBAL_ATTACK_MEAN * home_strength * 1.1  # vantagem de campo
        lambda_away = GLOBAL_ATTACK_MEAN * away_strength

        lambda_home = max(0.3, min(lambda_home, 4.0))
        lambda_away = max(0.3, min(lambda_away, 4.0))

        # Calcular probabilidade de cada placar até 6x6
        max_goals = 7
        score_probs = {}
        calc_home_win = 0.0
        calc_draw = 0.0
        calc_away_win = 0.0

        for h in range(max_goals):
            for a in range(max_goals):
                p = _poisson_prob(h, lambda_home) * _poisson_prob(a, lambda_away)
                score_probs[(h, a)] = p
                if h > a:
                    calc_home_win += p
                elif h == a:
                    calc_draw += p
                else:
                    calc_away_win += p

        # Placar mais provável
        best_score = max(score_probs, key=score_probs.get)
        best_prob = score_probs[best_score]

        proj = game.projection
        if not proj:
            proj = Projection(game_id=game.id)
            db.session.add(proj)

        proj.home_win_prob = calc_home_win
        proj.draw_prob = calc_draw
        proj.away_win_prob = calc_away_win
        proj.home_goals_proj = lambda_home
        proj.away_goals_proj = lambda_away
        proj.best_scoreline = f"{best_score[0]}x{best_score[1]}"
        proj.scoreline_prob = best_prob

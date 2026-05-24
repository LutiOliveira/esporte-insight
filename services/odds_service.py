import requests
from datetime import datetime, timedelta
from flask import current_app, g
from extensions import db
from models import Game, Odds

# Mapeamento equipe → grupo para Copa do Mundo 2026
# Grupos definidos pelo sorteio de dezembro/2024
COPA26_TEAM_GROUP: dict[str, str] = {
    # Grupo A — sede: México
    "Mexico": "A", "South Africa": "A", "Jamaica": "A", "Honduras": "A",
    # Grupo B — sede: EUA
    "USA": "B", "Panama": "B", "Ecuador": "B", "New Zealand": "B",
    # Grupo C — sede: Canadá
    "Canada": "C", "Morocco": "C", "Scotland": "C", "Haiti": "C",
    # Grupo D
    "Brazil": "D", "Algeria": "D", "Ivory Coast": "D", "DR Congo": "D",
    # Grupo E
    "Argentina": "E", "Chile": "E", "Japan": "E", "Norway": "E",
    # Grupo F
    "Spain": "F", "Portugal": "F", "Uruguay": "F", "Turkey": "F",
    # Grupo G
    "France": "G", "Netherlands": "G", "Colombia": "G", "Australia": "G",
    # Grupo H
    "England": "H", "Switzerland": "H", "Paraguay": "H", "Iran": "H",
    # Grupo I
    "Germany": "I", "Belgium": "I", "South Korea": "I", "Sweden": "I",
    # Grupo J
    "Qatar": "J", "Croatia": "J", "Saudi Arabia": "J", "Tunisia": "J",
    # Grupo K
    "Ghana": "K", "Senegal": "K", "Egypt": "K", "Cape Verde": "K",
    # Grupo L
    "Austria": "L", "Bosnia & Herzegovina": "L", "Czech Republic": "L", "Uzbekistan": "L",
}

# Grupos organizados para gerar calendário
COPA26_GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Africa", "Jamaica", "Honduras"],
    "B": ["USA", "Panama", "Ecuador", "New Zealand"],
    "C": ["Canada", "Morocco", "Scotland", "Haiti"],
    "D": ["Brazil", "Algeria", "Ivory Coast", "DR Congo"],
    "E": ["Argentina", "Chile", "Japan", "Norway"],
    "F": ["Spain", "Portugal", "Uruguay", "Turkey"],
    "G": ["France", "Netherlands", "Colombia", "Australia"],
    "H": ["England", "Switzerland", "Paraguay", "Iran"],
    "I": ["Germany", "Belgium", "South Korea", "Sweden"],
    "J": ["Qatar", "Croatia", "Saudi Arabia", "Tunisia"],
    "K": ["Ghana", "Senegal", "Egypt", "Cape Verde"],
    "L": ["Austria", "Bosnia & Herzegovina", "Czech Republic", "Uzbekistan"],
}

# Estádios por grupo (host region)
_STADIUMS: dict[str, list[tuple[str, str]]] = {
    "A": [("Estadio Azteca", "Cidade do México, MEX"), ("Estadio BBVA", "Monterrey, MEX"), ("Estadio Akron", "Guadalajara, MEX")],
    "B": [("AT&T Stadium", "Dallas, EUA"), ("Arrowhead Stadium", "Kansas City, EUA"), ("SoFi Stadium", "Los Angeles, EUA")],
    "C": [("BC Place", "Vancouver, CAN"), ("BMO Field", "Toronto, CAN"), ("MetLife Stadium", "Nova York, EUA")],
    "D": [("MetLife Stadium", "Nova York, EUA"), ("Hard Rock Stadium", "Miami, EUA"), ("Lincoln Financial Field", "Filadélfia, EUA")],
    "E": [("Rose Bowl", "Los Angeles, EUA"), ("Levi's Stadium", "San Francisco, EUA"), ("Lumen Field", "Seattle, EUA")],
    "F": [("SoFi Stadium", "Los Angeles, EUA"), ("Rose Bowl", "Los Angeles, EUA"), ("Lumen Field", "Seattle, EUA")],
    "G": [("AT&T Stadium", "Dallas, EUA"), ("NRG Stadium", "Houston, EUA"), ("Mercedes-Benz Stadium", "Atlanta, EUA")],
    "H": [("MetLife Stadium", "Nova York, EUA"), ("Empower Field", "Denver, EUA"), ("Lincoln Financial Field", "Filadélfia, EUA")],
    "I": [("Hard Rock Stadium", "Miami, EUA"), ("AT&T Stadium", "Dallas, EUA"), ("Mercedes-Benz Stadium", "Atlanta, EUA")],
    "J": [("Estadio Azteca", "Cidade do México, MEX"), ("Estadio BBVA", "Monterrey, MEX"), ("NRG Stadium", "Houston, EUA")],
    "K": [("BC Place", "Vancouver, CAN"), ("BMO Field", "Toronto, CAN"), ("Arrowhead Stadium", "Kansas City, EUA")],
    "L": [("Levi's Stadium", "San Francisco, EUA"), ("Lumen Field", "Seattle, EUA"), ("Rose Bowl", "Los Angeles, EUA")],
}

# Datas base por grupo (Round 1, +7 dias Round 2, +14 Round 3)
_BASE_DATES: dict[str, str] = {
    "A": "2026-06-11", "B": "2026-06-11", "C": "2026-06-12", "D": "2026-06-12",
    "E": "2026-06-13", "F": "2026-06-13", "G": "2026-06-14", "H": "2026-06-14",
    "I": "2026-06-15", "J": "2026-06-15", "K": "2026-06-16", "L": "2026-06-16",
}

# Times com transmissão Globo
_GLOBO_TEAMS = {"Brazil", "Argentina"}

BOOKMAKER_NAMES = {
    "betano": "Betano",
    "bet365": "Bet365",
    "betway": "Betway",
    "unibet": "Unibet",
    "williamhill": "William Hill",
    "pinnacle": "Pinnacle",
    "draftkings": "DraftKings",
    "fanduel": "FanDuel",
    "bovada": "Bovada",
}

# Cache em memória: evita gastar quota repetindo chamadas
_cache: dict = {"last_fetch": None, "remaining": None}
CACHE_TTL_MINUTES = 60


class OddsService:

    def fetch_and_store(self):
        # Garante que calendário da Copa 2026 existe (independente de API key)
        self.seed_copa26_schedule()

        api_key = current_app.config["ODDS_API_KEY"]
        if not api_key:
            current_app.logger.warning("ODDS_API_KEY não configurada — usando dados de demonstração")
            self._seed_demo_data()
            return

        # Respeita TTL para não queimar quota
        if _cache["last_fetch"]:
            age = datetime.utcnow() - _cache["last_fetch"]
            if age < timedelta(minutes=CACHE_TTL_MINUTES):
                current_app.logger.info(f"Cache válido ({int(age.total_seconds()/60)} min) — pulando fetch")
                return

        sports = current_app.config["SPORTS"]
        for sport in sports:
            self._fetch_sport(sport, api_key)

    def _fetch_sport(self, sport_key: str, api_key: str):
        base = current_app.config["ODDS_API_BASE"]
        url = f"{base}/sports/{sport_key}/odds/"
        params = {
            "apiKey": api_key,
            "regions": "eu,us",
            "markets": "h2h,totals",
            "oddsFormat": "decimal",
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()

            # Registra quota restante nos headers da API
            remaining = resp.headers.get("x-requests-remaining")
            used = resp.headers.get("x-requests-used")
            if remaining:
                _cache["remaining"] = int(remaining)
                current_app.logger.info(f"Odds API — usadas: {used}, restantes: {remaining}")

            _cache["last_fetch"] = datetime.utcnow()
            games_data = resp.json()
            self._upsert_games(games_data, sport_key)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar odds para {sport_key}: {e}")

    @staticmethod
    def quota_status() -> dict:
        return {
            "remaining": _cache["remaining"],
            "last_fetch": _cache["last_fetch"].isoformat() if _cache["last_fetch"] else None,
            "cache_ttl_minutes": CACHE_TTL_MINUTES,
        }

    def _upsert_games(self, games_data: list, sport_key: str):
        for g in games_data:
            home = g["home_team"]
            away = g["away_team"]

            # Enriquece jogos da Copa 2026 com informação de grupo
            group_name = None
            phase = None
            if sport_key == "soccer_fifa_world_cup":
                home_grp = COPA26_TEAM_GROUP.get(home)
                away_grp = COPA26_TEAM_GROUP.get(away)
                if home_grp and home_grp == away_grp:
                    group_name = f"Grupo {home_grp}"
                    phase = "Fase de Grupos"
                elif home_grp or away_grp:
                    # Fases eliminatórias (times de grupos diferentes)
                    phase = "Eliminatórias"

            # Para Copa 2026, tenta reutilizar jogo semeado pelo par de times
            game = None
            if sport_key == "soccer_fifa_world_cup":
                game = self._try_match_copa_game(home, away)

            if not game:
                game = Game.query.get(g["id"])

            if not game:
                game = Game(
                    id=g["id"],
                    sport_key=sport_key,
                    tournament=g.get("sport_title", sport_key),
                    home_team=home,
                    away_team=away,
                    start_time=datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00")),
                    group_name=group_name,
                    phase=phase,
                )
                db.session.add(game)
            else:
                # Atualiza data de início com dado real da API
                api_time = datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00"))
                game.start_time = api_time
                if group_name and not game.group_name:
                    game.group_name = group_name
                    game.phase = phase

            Odds.query.filter_by(game_id=game.id).delete()
            for bookmaker in g.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market["key"] != "h2h":
                        continue
                    outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
                    home = outcomes.get(game.home_team)
                    away = outcomes.get(game.away_team)
                    draw = outcomes.get("Draw")
                    if home and away and draw:
                        db.session.add(Odds(
                            game_id=game.id,
                            bookmaker=BOOKMAKER_NAMES.get(bookmaker["key"], bookmaker["title"]),
                            home_win=home,
                            draw=draw,
                            away_win=away,
                        ))

            # Processa mercado de totals (Over/Under)
            from models import OddsTotal
            OddsTotal.query.filter_by(game_id=game.id).delete()
            for bookmaker in g.get("bookmakers", []):
                bm_name = BOOKMAKER_NAMES.get(bookmaker["key"], bookmaker["title"])
                for market in bookmaker.get("markets", []):
                    if market["key"] != "totals":
                        continue
                    # Agrupa outcomes por linha (description = "2.5" etc.)
                    lines_dict: dict[float, dict] = {}
                    for outcome in market["outcomes"]:
                        try:
                            line_val = float(outcome.get("description", "0"))
                        except (ValueError, TypeError):
                            continue
                        if line_val not in lines_dict:
                            lines_dict[line_val] = {}
                        side = outcome["name"].lower()  # "over" ou "under"
                        lines_dict[line_val][side] = outcome["price"]
                    for line_val, sides in lines_dict.items():
                        if "over" in sides and "under" in sides:
                            db.session.add(OddsTotal(
                                game_id=game.id,
                                bookmaker=bm_name,
                                line=line_val,
                                over_price=sides["over"],
                                under_price=sides["under"],
                            ))
        db.session.commit()

    def seed_copa26_schedule(self):
        """Semeia todos os 72 jogos da fase de grupos da Copa 2026 com inglês e grupos corretos.
        Chamado sempre ao inicializar — cria apenas registros que ainda não existem."""
        from itertools import combinations
        seeded = 0
        for grp, teams in COPA26_GROUPS.items():
            base_date = datetime.fromisoformat(_BASE_DATES[grp])
            stadiums = _STADIUMS[grp]
            # 3 rodadas, 2 jogos por rodada = 6 jogos por grupo
            # Rodada 1: T0vT1, T2vT3 | Rodada 2: T0vT2, T1vT3 | Rodada 3: T0vT3, T1vT2
            schedule = [
                (0, 1, 0, 16), (2, 3, 0, 20),
                (0, 2, 7, 16), (1, 3, 7, 20),
                (0, 3, 14, 16), (1, 2, 14, 20),
            ]
            for i, (hi, ai, day_off, hour) in enumerate(schedule):
                home = teams[hi]
                away = teams[ai]
                game_id = f"copa26_{grp}_{home[:3].lower()}{away[:3].lower()}"
                if Game.query.get(game_id):
                    continue
                match_dt = base_date + timedelta(days=day_off, hours=hour)
                stadium, city = stadiums[i % len(stadiums)]
                has_globo = home in _GLOBO_TEAMS or away in _GLOBO_TEAMS
                if has_globo:
                    broadcast = "CazéTV (YouTube) · Globo · SporTV · Globoplay"
                elif i % 3 == 0:
                    broadcast = "CazéTV (YouTube) · SBT · NSports"
                else:
                    broadcast = "CazéTV (YouTube)"
                game = Game(
                    id=game_id,
                    sport_key="soccer_fifa_world_cup",
                    tournament="FIFA World Cup",
                    home_team=home,
                    away_team=away,
                    start_time=match_dt,
                    stadium=stadium,
                    city=city,
                    broadcast=broadcast,
                    group_name=f"Grupo {grp}",
                    phase="Fase de Grupos",
                )
                db.session.add(game)
                # Odds padrão enquanto API não retornou odds reais
                default_odds = self._default_odds(home, away)
                for bk, h, d, a in default_odds:
                    db.session.add(Odds(game_id=game_id, bookmaker=bk,
                                        home_win=h, draw=d, away_win=a))
                seeded += 1
        db.session.commit()
        if seeded:
            current_app.logger.info(f"Copa 2026: {seeded} jogos semeados no calendário")

    def _default_odds(self, home: str, away: str) -> list[tuple]:
        """Odds padrão baseados em 'força' dos times enquanto API real não chegou."""
        tier = {"Brazil": 1, "Argentina": 1, "France": 1, "Spain": 1, "England": 1,
                "Germany": 1, "Netherlands": 1, "Portugal": 1}
        ht = tier.get(home, 2)
        at = tier.get(away, 2)
        if ht < at:
            return [("Betano", 1.65, 3.80, 5.00), ("Bet365", 1.62, 3.85, 5.10)]
        elif at < ht:
            return [("Betano", 5.00, 3.80, 1.65), ("Bet365", 5.10, 3.85, 1.62)]
        else:
            return [("Betano", 2.50, 3.20, 2.80), ("Bet365", 2.45, 3.25, 2.85)]

    def _try_match_copa_game(self, home: str, away: str) -> "Game | None":
        """Procura jogo Copa semeado pelo par de times (ignora ID da API)."""
        from models import Game as G
        return G.query.filter_by(
            sport_key="soccer_fifa_world_cup",
            home_team=home, away_team=away
        ).first() or G.query.filter_by(
            sport_key="soccer_fifa_world_cup",
            home_team=away, away_team=home
        ).first()

    def _seed_demo_data(self):
        """Jogos reais da Copa do Mundo 2026 — fase de grupos."""
        # Horários já convertidos para Brasília (UTC-3)
        # Transmissão: CazéTV transmite TODOS os 104 jogos (YouTube, grátis)
        # Globo/SporTV transmite ~55 jogos (todos do Brasil)
        # SBT/NSports transmite ~32 jogos
        demo_games = [
            # ABERTURA
            {
                "id": "wc26_mex_rsa", "group": "A", "phase": "Fase de Grupos",
                "home": "México", "away": "África do Sul",
                "time": "2026-06-11T16:00:00",
                "stadium": "Estadio Azteca", "city": "Cidade do México, MEX",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 1.80, 3.60, 4.50), ("Bet365", 1.78, 3.65, 4.60)],
            },
            # GRUPO A
            {
                "id": "wc26_can_uru", "group": "A", "phase": "Fase de Grupos",
                "home": "Canadá", "away": "Uruguai",
                "time": "2026-06-12T22:00:00",
                "stadium": "BC Place", "city": "Vancouver, CAN",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 3.20, 3.30, 2.20), ("Bet365", 3.25, 3.25, 2.15)],
            },
            {
                "id": "wc26_mex_can", "group": "A", "phase": "Fase de Grupos",
                "home": "México", "away": "Canadá",
                "time": "2026-06-18T22:00:00",
                "stadium": "Estadio Azteca", "city": "Cidade do México, MEX",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 2.10, 3.40, 3.60), ("Bet365", 2.05, 3.45, 3.70)],
            },
            {
                "id": "wc26_uru_rsa", "group": "A", "phase": "Fase de Grupos",
                "home": "Uruguai", "away": "África do Sul",
                "time": "2026-06-18T19:00:00",
                "stadium": "Estadio BBVA", "city": "Monterrey, MEX",
                "broadcast": "CazéTV (YouTube)",
                "odds": [("Betano", 1.65, 3.80, 5.00), ("Bet365", 1.62, 3.85, 5.10)],
            },
            # GRUPO B
            {
                "id": "wc26_arg_bol", "group": "B", "phase": "Fase de Grupos",
                "home": "Argentina", "away": "Bolívia",
                "time": "2026-06-12T19:00:00",
                "stadium": "SoFi Stadium", "city": "Los Angeles, EUA",
                "broadcast": "CazéTV (YouTube) · Globo · SporTV",
                "odds": [("Betano", 1.20, 7.00, 12.0), ("Bet365", 1.18, 7.50, 13.0), ("KTO", 1.22, 6.80, 11.5)],
            },
            {
                "id": "wc26_pol_chi", "group": "B", "phase": "Fase de Grupos",
                "home": "Polônia", "away": "Chile",
                "time": "2026-06-13T16:00:00",
                "stadium": "AT&T Stadium", "city": "Dallas, EUA",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 2.30, 3.20, 3.10), ("Bet365", 2.25, 3.25, 3.20)],
            },
            # GRUPO C — BRASIL
            {
                "id": "wc26_bra_mar", "group": "C", "phase": "Fase de Grupos",
                "home": "Brasil", "away": "Marrocos",
                "time": "2026-06-13T19:00:00",
                "stadium": "MetLife Stadium", "city": "Nova York / Nova Jersey, EUA",
                "broadcast": "CazéTV (YouTube) · Globo · SporTV · Globoplay",
                "odds": [("Betano", 1.75, 3.70, 4.80), ("Bet365", 1.72, 3.75, 4.90), ("KTO", 1.78, 3.60, 4.70)],
            },
            {
                "id": "wc26_sco_hai", "group": "C", "phase": "Fase de Grupos",
                "home": "Escócia", "away": "Haiti",
                "time": "2026-06-13T22:00:00",
                "stadium": "Gillette Stadium", "city": "Boston, EUA",
                "broadcast": "CazéTV (YouTube)",
                "odds": [("Betano", 1.55, 4.00, 6.00), ("Bet365", 1.52, 4.10, 6.20)],
            },
            {
                "id": "wc26_bra_hai", "group": "C", "phase": "Fase de Grupos",
                "home": "Brasil", "away": "Haiti",
                "time": "2026-06-19T22:00:00",
                "stadium": "Lincoln Financial Field", "city": "Filadélfia, EUA",
                "broadcast": "CazéTV (YouTube) · Globo · SporTV · Globoplay",
                "odds": [("Betano", 1.10, 9.00, 20.0), ("Bet365", 1.08, 9.50, 22.0), ("KTO", 1.12, 8.50, 18.0)],
            },
            {
                "id": "wc26_mar_sco", "group": "C", "phase": "Fase de Grupos",
                "home": "Marrocos", "away": "Escócia",
                "time": "2026-06-19T16:00:00",
                "stadium": "Levi's Stadium", "city": "São Francisco, EUA",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 2.00, 3.40, 3.80), ("Bet365", 1.95, 3.45, 3.90)],
            },
            {
                "id": "wc26_bra_sco", "group": "C", "phase": "Fase de Grupos",
                "home": "Brasil", "away": "Escócia",
                "time": "2026-06-24T19:00:00",
                "stadium": "Hard Rock Stadium", "city": "Miami, EUA",
                "broadcast": "CazéTV (YouTube) · Globo · SporTV · Globoplay",
                "odds": [("Betano", 1.55, 4.00, 6.00), ("Bet365", 1.52, 4.10, 6.20), ("KTO", 1.58, 3.90, 5.80)],
            },
            {
                "id": "wc26_hai_mar", "group": "C", "phase": "Fase de Grupos",
                "home": "Haiti", "away": "Marrocos",
                "time": "2026-06-24T16:00:00",
                "stadium": "Arrowhead Stadium", "city": "Kansas City, EUA",
                "broadcast": "CazéTV (YouTube)",
                "odds": [("Betano", 8.00, 4.50, 1.40), ("Bet365", 8.50, 4.60, 1.38)],
            },
            # GRUPO D
            {
                "id": "wc26_fra_ita", "group": "D", "phase": "Fase de Grupos",
                "home": "França", "away": "Itália",
                "time": "2026-06-14T22:00:00",
                "stadium": "MetLife Stadium", "city": "Nova York / Nova Jersey, EUA",
                "broadcast": "CazéTV (YouTube) · Globo · SporTV",
                "odds": [("Betano", 2.10, 3.30, 3.50), ("Bet365", 2.05, 3.35, 3.60), ("KTO", 2.15, 3.25, 3.40)],
            },
            {
                "id": "wc26_bel_gha", "group": "D", "phase": "Fase de Grupos",
                "home": "Bélgica", "away": "Gana",
                "time": "2026-06-14T16:00:00",
                "stadium": "AT&T Stadium", "city": "Dallas, EUA",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 1.55, 3.90, 5.50), ("Bet365", 1.52, 4.00, 5.70)],
            },
            # GRUPO E
            {
                "id": "wc26_esp_cro", "group": "E", "phase": "Fase de Grupos",
                "home": "Espanha", "away": "Croácia",
                "time": "2026-06-15T22:00:00",
                "stadium": "SoFi Stadium", "city": "Los Angeles, EUA",
                "broadcast": "CazéTV (YouTube) · Globo · SporTV",
                "odds": [("Betano", 1.80, 3.60, 4.50), ("Bet365", 1.78, 3.65, 4.60), ("Pinnacle", 1.83, 3.55, 4.40)],
            },
            {
                "id": "wc26_jap_col", "group": "E", "phase": "Fase de Grupos",
                "home": "Japão", "away": "Colômbia",
                "time": "2026-06-15T16:00:00",
                "stadium": "Lumen Field", "city": "Seattle, EUA",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 2.60, 3.20, 2.70), ("Bet365", 2.55, 3.25, 2.75)],
            },
            # GRUPO F
            {
                "id": "wc26_por_eua", "group": "F", "phase": "Fase de Grupos",
                "home": "Portugal", "away": "EUA",
                "time": "2026-06-16T22:00:00",
                "stadium": "Arrowhead Stadium", "city": "Kansas City, EUA",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 1.90, 3.55, 4.20), ("Bet365", 1.87, 3.60, 4.30)],
            },
            {
                "id": "wc26_tur_nzl", "group": "F", "phase": "Fase de Grupos",
                "home": "Turquia", "away": "Nova Zelândia",
                "time": "2026-06-16T16:00:00",
                "stadium": "Estadio Akron", "city": "Guadalajara, MEX",
                "broadcast": "CazéTV (YouTube)",
                "odds": [("Betano", 1.55, 3.90, 5.50), ("Bet365", 1.52, 4.00, 5.70)],
            },
            # GRUPO G
            {
                "id": "wc26_eng_afg", "group": "G", "phase": "Fase de Grupos",
                "home": "Inglaterra", "away": "Afeganistão",
                "time": "2026-06-17T22:00:00",
                "stadium": "AT&T Stadium", "city": "Dallas, EUA",
                "broadcast": "CazéTV (YouTube) · Globo · SporTV",
                "odds": [("Betano", 1.08, 10.0, 25.0), ("Bet365", 1.07, 11.0, 27.0)],
            },
            {
                "id": "wc26_ned_sen", "group": "G", "phase": "Fase de Grupos",
                "home": "Holanda", "away": "Senegal",
                "time": "2026-06-17T16:00:00",
                "stadium": "Lincoln Financial Field", "city": "Filadélfia, EUA",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 1.75, 3.70, 4.80), ("Bet365", 1.72, 3.75, 4.90)],
            },
            # GRUPO H
            {
                "id": "wc26_ger_paq", "group": "H", "phase": "Fase de Grupos",
                "home": "Alemanha", "away": "Paquistão",
                "time": "2026-06-18T16:00:00",
                "stadium": "Hard Rock Stadium", "city": "Miami, EUA",
                "broadcast": "CazéTV (YouTube) · SBT · NSports",
                "odds": [("Betano", 1.12, 8.50, 22.0), ("Bet365", 1.10, 9.00, 24.0)],
            },
        ]

        for g in demo_games:
            if Game.query.get(g["id"]):
                continue
            game = Game(
                id=g["id"],
                sport_key="soccer_fifa_world_cup",
                tournament="Copa do Mundo 2026",
                home_team=g["home"],
                away_team=g["away"],
                start_time=datetime.fromisoformat(g["time"]),
                stadium=g["stadium"],
                city=g["city"],
                broadcast=g["broadcast"],
                group_name=g["group"],
                phase=g["phase"],
            )
            db.session.add(game)
            for b in g["odds"]:
                db.session.add(Odds(
                    game_id=game.id,
                    bookmaker=b[0],
                    home_win=b[1],
                    draw=b[2],
                    away_win=b[3],
                ))
        db.session.commit()

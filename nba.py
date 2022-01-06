from collections import defaultdict, namedtuple
from datetime import date
from pbpstats.client import Client
from pbpstats.resources.enhanced_pbp.enhanced_pbp_item import FieldGoal
from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import teamplayerdashboard


def seconds_from_time(time: str) -> int:
    """
    Return the amount of seconds represented by str time

    Args:
        time (str): time in 'm:ss' or 'mm:ss' format

    Returns:
        int:
    """
    [min, sec] = time.split(':')
    return int(min) * 60 + int(sec)


seasons = [
    "2000-01",
    "2001-02",
    "2002-03",
    "2003-04",
    "2004-05",
    "2005-06",
    "2006-07",
    "2007-08",
    "2008-09",
    "2009-10",
    "2010-11",
    "2011-12",
    "2012-13",
    "2013-14",
    "2014-15",
    "2015-16",
    "2016-17",
    "2017-18",
    "2018-19",
    "2019-20",
    "2020-21"
]  # 19-20 was bubble season


def previous_season(season):
    index = seasons.index(season)
    if index == 0:
        return None
    return seasons[index-1]


def next_season(season):
    index = seasons.index(season)
    if index == len(seasons) - 1:
        return None
    return seasons[index+1]


season_settings = {
    "dir": "C:/Users/bhalb/nbaproject/response_data",
    "Games": {"source": "file", "data_provider": "stats_nba"},
}
game_settings = {
    "dir": "C:/Users/bhalb/nbaproject/response_data",
    "Boxscore": {"source": "file", "data_provider": "stats_nba"},
}
game_possessions_settings = {
    "dir": "C:/Users/bhalb/nbaproject/response_data",
    "Possessions": {"source": "file", "data_provider": "stats_nba"},
}


Lineup = namedtuple('Lineup', 'off_team, off_players, def_team, def_players')


class LineupStats:
    def __init__(self):
        self.possessions = 0
        self.points = 0

    def add_possession(self, points):
        self.possessions += 1
        self.points += points


class PlayerContribution:
    """
    Measure how much a player contributes to a teams season
    """

    def __init__(self, id) -> None:
        self.id = id
        self.games = 0
        self.wins = 0
        self.start_G = 0
        self.start_F = 0
        self.start_C = 0
        self.game_time = 0
        self.total_pm = 0

        self.points = 0
        self.fg2a = 0
        self.fg2m = 0
        self.fg3a = 0
        self.fg3m = 0
        self.fta = 0
        self.ftm = 0

        self.off_rebounds = 0
        self.def_rebounds = 0
        self.assists = 0
        self.blocks = 0
        self.steals = 0

        self.turnovers = 0
        self.fouls = 0
        # self.off_fouls = 0
        # self.loose_ball_fouls = 0
        # self.def_fouls = 0

        # self.techs = 0

    def add_game(self, player_dict, isWin):
        if not player_dict['min'] or player_dict['min'] == '':
            return

        self.games += 1
        if isWin:
            self.wins += 1
        if player_dict['start_position'] == 'F':
            self.start_F += 1
        if player_dict['start_position'] == 'C':
            self.start_C += 1
        if player_dict['start_position'] == 'G':
            self.start_G += 1
        seconds = seconds_from_time(player_dict['min'])
        self.game_time += seconds
        self.total_pm += player_dict['plus_minus']

        self.points += player_dict['pts']
        self.fg2a += player_dict['fga'] - player_dict['fg3a']
        self.fg2m += player_dict['fgm'] - player_dict['fg3m']
        self.fg3a += player_dict['fg3a']
        self.fg3m += player_dict['fg3m']
        self.fta += player_dict['fta']
        self.ftm += player_dict['ftm']

        self.off_rebounds += player_dict['oreb']
        self.def_rebounds += player_dict['dreb']
        self.assists += player_dict['ast']
        self.steals += player_dict['stl']
        self.blocks += player_dict['blk']

        self.turnovers += player_dict['to']
        self.fouls += player_dict['pf']


class TeamSeason:
    def __init__(self, id) -> None:
        self.id = id

        self.total_games: int = 0
        self.wins: int = 0
        self.total_pm: int = 0

        self.player_contributions: dict[int, PlayerContribution] = {}

    def add_game_boxscore(self, team_dict, player_items):
        self.total_games += 1
        game_pm = team_dict['plus_minus']
        if game_pm > 0:
            self.wins += 1
            isWin = True
        else:
            isWin = False
        self.total_pm += game_pm

        for player_dict in player_items:
            player_id = player_dict['player_id']
            if player_id not in self.player_contributions:
                self.player_contributions[player_id] = PlayerContribution(
                    player_id)

            self.player_contributions[player_id].add_game(player_dict, isWin)

    @property
    def win_rate(self) -> float:
        if self.total_games > 0:
            return self.wins / self.total_games
        else:
            return 0

    @property
    def ave_pm(self) -> float:
        if self.total_games > 0:
            return self.total_pm / self.total_games
        else:
            return 0


class PlayerSeason:
    def __init__(self, player_id: int) -> None:
        self.id: int = player_id
        self.player_contributions: dict[int, PlayerContribution] = {}

    def __getattr__(self, name):
        val = 0
        for pc in self.player_contributions.values():
            val += getattr(pc, name)
        return val

    def add_shot(self, shot: FieldGoal):
        pass


class Season:
    def __init__(self, name, schedule) -> None:
        self.name: str = name

        # self.schedule = schedule
        self.first_game = date.fromisoformat(schedule.games.data[0]['date'])
        self.last_game = date.fromisoformat(schedule.games.data[-1]['date'])

        self.team_seasons: dict[int, TeamSeason] = {}
        self.player_seasons: dict[int, PlayerSeason] = {}

        self.lineups: defaultdict[Lineup,
                                  LineupStats] = defaultdict(LineupStats)

        self.total_possessions = 0
        self.total_points = 0

    @property
    def ave_ppp(self):
        return self.total_points / self.total_possessions

    def load_season_from_boxscores(self, schedule):
        game_client = Client(game_settings)
        for team in teams.get_teams():
            team_id = team['id']
            ts = TeamSeason(team_id)
            self.team_seasons[team_id] = ts

        for game_dict in schedule.games.final_games:
            game_id = game_dict['game_id']
            game = game_client.Game(game_id)
            for team in game.boxscore.team_items:
                team_id = team['team_id']
                players = list(
                    filter(lambda p: p['team_id'] == team_id, game.boxscore.player_items))
                self.team_seasons[team_id].add_game_boxscore(team, players)

        # remove teams w/ no games
        for team in teams.get_teams():
            team_id = team['id']
            if self.team_seasons[team_id].total_games == 0:
                del self.team_seasons[team_id]

        # build player seasons
        for team_season in self.team_seasons.values():
            team_id = team_season.id
            for player_contribution in team_season.player_contributions.values():
                player_id = player_contribution.id
                if player_id not in self.player_seasons:
                    self.player_seasons[player_id] = PlayerSeason(player_id)
                self.player_seasons[player_id].player_contributions[team_id] = player_contribution

    def add_possessions(self, possessions):
        for possession in possessions:
            self.add_possession(possession)

    def add_possession(self, possession):
        if possession.possession_stats == []:
            return
            # not really a possession

        total_points = 0

        for stat in possession.possession_stats:
            if stat['stat_key'] == 'OpponentPoints':
                total_points = stat['stat_value']
                off_team = stat['opponent_team_id']
                off_players = stat['opponent_lineup_id']
                def_team = stat['team_id']
                def_players = stat['lineup_id']
                break
        else:
            for stat in possession.possession_stats:
                if stat['stat_key'] == 'DefPoss':
                    off_team = stat['opponent_team_id']
                    off_players = stat['opponent_lineup_id']
                    def_team = stat['team_id']
                    def_players = stat['lineup_id']
                    break
            else:
                return

        lineup = Lineup(off_team, off_players, def_team, def_players)

        period = possession.period
        start_time = seconds_from_time(possession.start_time)
        end_time = seconds_from_time(possession.end_time)
        periods_left = max(4 - period, 0)
        game_seconds_left = periods_left*12*60 + start_time
        possession_seconds = end_time - start_time

        for event in possession.events:
            if isinstance(event, FieldGoal):
                self.add_shot(event.player1_id, event)

        self.lineups[lineup].add_possession(total_points)
        self.total_possessions += 1
        self.total_points += total_points

    def add_shot(self, player_id: int, shot: FieldGoal):
        self.player_seasons[player_id].add_shot(shot)


class NbaTracker:
    def __init__(self) -> None:
        self.current_season: Season = None
        self.seasons: dict[str, Season] = {}

    def load_seasons(self):
        for season_name in seasons:
            self.load_season(season_name)
            print("Loaded ", season_name)

    def load_season(self, season_name):
        season_client = Client(season_settings)
        schedule = season_client.Season("nba", season_name, "Regular Season")

        self.add_season(season_name, schedule)

        self.current_season.load_season_from_boxscores(schedule)  # faster

    # def load_possessions(self, season_name):
    #     if season_name not in self.seasons:
    #         self.load_season(season_name)

    #     season_client = Client(season_settings)
    #     schedule = season_client.Season("nba", season_name, "Regular Season")
    #     for game_dict in schedule.games.final_games:
    #         game_id = game_dict['game_id']
    #         game = possession_client.Game(game_id)
    #         self.seasons[season_name].add_possessions(game.possessions.items)

    def add_season(self, season_name, schedule):
        if season_name in self.seasons:
            print("Already loaded", season_name)
            return

        self.current_season = Season(
            season_name, schedule)
        self.seasons[season_name] = self.current_season

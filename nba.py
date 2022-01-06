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
# season_client = Client(season_settings)
# game_client = Client(game_settings)
# possession_client = Client(game_possessions_settings)


Lineup = namedtuple('Lineup', 'off_team, off_players, def_team, def_players')


class LineupStats:
    def __init__(self):
        self.possessions = 0
        self.points = 0

    def add_possession(self, points):
        self.possessions += 1
        self.points += points


# class Player:
#     def __init__(self, name: str, id, index: int):
#         self.name = name
#         self.names = set([name])
#         self.id = id
#         self.index = index

#     def update_name(self, name):
#         if name != self.name:
#             print("Player name change: ", self.name, name)
#             self.name = name
#             self.names.add(name)


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

    # def load_from_nba_api(self, player):
    #     self.games = player.GP
    #     self.wins = player.W
    #     self.start_G = 0
    #     self.start_F = 0
    #     self.start_C = 0
    #     self.game_time = int(player.MIN * 60)
    #     self.total_pm = player.PLUS_MINUS

    #     self.points = player.PTS
    #     self.fg2a = player.FGA - player.FG3A
    #     self.fg2m = player.FGM - player.FG3M
    #     self.fg3a = player.FG3A
    #     self.fg3m = player.FG3M
    #     self.fta = player.FTA
    #     self.ftm = player.FTM

    #     self.off_rebounds = player.OREB
    #     self.def_rebounds = player.DREB
    #     self.assists = player.AST
    #     self.blocks = player.BLK
    #     self.steals = player.STL

    #     self.blocks_against = player.BLKA

    #     self.turnovers = player.TOV
    #     self.fouls = player.PF

    #     self.fouls_drawn = player.PFD

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
        # self.players = set()
        # : defaultdict[int, PlayerContribution] = defaultdict(
        self.player_contributions: dict[int, PlayerContribution] = {}
        # PlayerContribution)

    # def load_from_nba_api(self, team):
    #     self.total_games = team.GP
    #     self.wins = team.W
    #     self.total_pm = int(team.PLUS_MINUS)

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

    # def add_team(self, ts: TeamSeason):
    #     if ts.id not in self.player_contributions:
    #         self.player_contributions[ts.id] = ts.player_contributions[self.id]

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

        # self.next_season: Season = next_season
        # self.previous_season: Season = previous_season
        # if self.previous_season:
        #     self.previous_season.next_season = self
        # if self.next_season:
        #     self.next_season.previous_season = self

        self.team_seasons: dict[int, TeamSeason] = {}
        self.player_seasons: dict[int, PlayerSeason] = {}

        self.lineups: defaultdict[Lineup,
                                  LineupStats] = defaultdict(LineupStats)

        self.total_possessions = 0
        self.total_points = 0

    @property
    def ave_ppp(self):
        return self.total_points / self.total_possessions
        # self.player_seasons = {}

    # def load_season_from_nba_api(self):
    #     for team in teams.get_teams():
    #         team_id = team['id']
    #         team_info = teamplayerdashboard.TeamPlayerDashboard(
    #             team_id, season=self.name)
    #         team_df = team_info.get_data_frames()[0]
    #         player_df = team_info.get_data_frames()[1]
    #         if player_df.size != 0:
    #             self.team_seasons[team_id] = TeamSeason(team_id)
    #             self.team_seasons[team_id].load_from_nba_api(team_df.loc[0])
    #             for player in player_df.itertuples():
    #                 pc = PlayerContribution(player.PLAYER_ID)
    #                 pc.load_from_nba_api(player)
    #                 self.team_seasons[team_id].player_contributions[player.PLAYER_ID] = pc

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


# class PlayerStint:
#     def __init__(self, id, team_id) -> None:
#         self.id: int = id
#         self.team_id: int = team_id
#         self.stints: list[tuple[date, date]] = []
#         self.first: date = None
#         self.last: date = None
#         self.current = False

#     def isAvailableAt(self, d: date):
#         if not self.first or self.first > d:
#             return False
#         if not self.current and self.last <= d:
#             return False

#         for s in self.stints:
#             if d >= s[0]:
#                 if not s[1] or d < s[1]:
#                     return True
#             else:
#                 return False
#         return False

#     def add(self, d: date):
#         if not self.first:
#             self.first = d
#         if not self.current:
#             self.current = True
#             self.last = None
#             self.stints.append((d, None))

#     def remove(self, d: date):
#         if self.current:
#             self.current = False
#             self.last = d
#             self.stints[-1] = (self.stints[-1][0], d)


# class Team:
#     def __init__(self, name: str, team_id: int, index: int) -> None:
#         self.name = name
#         self.names = set([name])
#         self.id = team_id
#         self.index = index

#         self.seasons = {}

        # # self.played_seasons = set()
        # self.all_players: dict[int, PlayerStint] = {}
        # self.current_players = set()

    # def add(self, player_id):
    #     if player_id not in self.all_players:
    #         ps = PlayerStint(player_id, self.id)
    #         self.all_players[player_id] = ps

    # def add_season(self, season_name: str, ts: TeamSeason):
    #     self.seasons[season_name] = ts

    # @property
    # def pm(self):
    #     return self.opm - self.dpm

    # def add_game(self, season, team_dict, player_items):
    #     self.played_season.add(season)
    #     self.seasons[season].add_game(team_dict, player_items)

    # def update_name(self, name):
    #     if name != self.name:
    #         print("Team name change: ", self.name, name)
    #         self.name = name
    #         self.names.add(name)

    # def add_player(self, player_id: int, d: date):
    #     if player_id not in self.all_players:
    #         stint = PlayerStint(player_id, self.id)
    #         self.all_players[player_id] = stint
    #     else:
    #         stint = self.all_players[player_id]
    #     stint.add(d)

    # def remove_player(self, player_id: int, d: date):
    #     if player_id not in self.all_players:
    #         self.all_players[player_id] = PlayerStint(player_id, self.id)
    #     self.all_players[player_id].remove(d)

    # def get_players(self, d: date):
    #     available_players = set()
    #     for player_id in self.all_players:
    #         if self.all_players[player_id].isAvailableAt(d):
    #             available_players.add(player_id)
    #     return available_players

    # def __getitem__(self, season) -> TeamSeason:
    #     return self.seasons[season]


class NbaTracker:
    def __init__(self) -> None:
        # self.all_teams: dict[int, Team] = {}
        # self.team_indicies: dict[int, Team] = {}
        # self.current_team_index = 0
        # self.team_by_name: dict[str, int] = {}

        # self.all_players: dict[int, Player] = {}
        # self.player_indicies: dict[int, Player] = {}
        # self.current_player_index = 0
        # self.players_by_name: defaultdict[str, set[int]] = defaultdict(set)

        self.current_season: Season = None
        self.seasons: dict[str, Season] = {}

        # for team in teams.get_teams():
        #     team_id = team['id']
        #     current_team = Team(
        #         team['nickname'], team_id, self.current_team_index)
        #     self.all_teams[team_id] = current_team
        #     self.team_indicies[self.current_team_index] = current_team
        #     self.current_team_index += 1

    def load_seasons(self):
        for season_name in seasons:
            self.load_season(season_name)
            print("Loaded ", season_name)

    def load_season(self, season_name):
        season_client = Client(season_settings)
        schedule = season_client.Season("nba", season_name, "Regular Season")

        self.add_season(season_name, schedule)

        # self.current_season.load_season_from_nba_api() # 43.6s
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

        # prev_name = previous_season(season_name)
        # if prev_name and prev_name in self.seasons:
        #     prev_season = self.seasons[prev_name]
        # else:
        #     prev_season = None
        # next_name = next_season(season_name)
        # if next_name and next_name in self.seasons:
        #     nxt_season = self.seasons[next_name]
        # else:
        #     nxt_season = None

        self.current_season = Season(
            season_name, schedule)
        self.seasons[season_name] = self.current_season

    # def update_team(self, team_dict, team_players):
    #     team_id: int = team_dict['team_id']
    #     name = team_dict['team_name']
    #     if team_id not in self.all_teams:
    #         current_team = Team(
    #             name, team_id, self.current_team_index)
    #         self.all_teams[team_id] = current_team
    #         self.team_indicies[self.current_team_index] = current_team
    #         self.current_team_index += 1
    #     else:
    #         current_team = self.all_teams[team_id]
    #         current_team.update_name(name)
    #     self.team_by_name[name] = team_id

    #     for player_dict in team_players:
    #         player_id: int = player_dict['player_id']
    #         current_team.add(player_id)

    # def add_player(self, player_id, name):
    #     if player_id not in self.all_players:
    #         current_player = Player(name, player_id, self.current_player_index)
    #         self.all_players[player_id] = current_player
    #         self.player_indicies[self.current_player_index] = current_player
    #         self.current_player_index += 1

    # def add_game(self, team_dict, team_player_items):
    #     for player_dict in team_player_items:
    #         self.add_player(player_dict)
    #     self.update_team(team_dict, team_player_items)

    #     self.current_season.add_game(team_dict, team_player_items)

    # def add_transaction(self, team_name, added_players, removed_players, d: date, notes):
    #     if team_name == 'Hornets':
    #         if d >= date.fromisoformat('2002-05-10') and d < date.fromisoformat('2013-04-18'):
    #             team_name = 'Pelicans'
    #         else:
    #             team_name = 'Bobcats'  # Hornets works too
    #     team = self.team_by_name(team_name)
    #     for player_name in added_players:
    #         pass
    #

        # team_id: int = team_dict['team_id']
        # self.all_teams[team_id].add_season(self.season)
        # self.current_season.add_game(team_dict, team_player_items)

        # @property
        # def teams(self):
        #     return self.all_teams.values()

        # @property
        # def team_seasons(self):
        #     return (team.seasons[self.season] for team in self.all_teams.values())

    # def __getitem__(self, id) -> Team:
    #     return self.all_teams[id]

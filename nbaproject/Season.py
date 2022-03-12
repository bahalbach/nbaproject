from datetime import date, datetime
from collections import defaultdict, deque, namedtuple

from os.path import isfile
import pickle
import time

import requests
from bs4 import BeautifulSoup

from pbpstats.client import Client
# FieldGoal, Rebound, Turnover, Timeout, FreeThrow
from pbpstats.resources import enhanced_pbp
from nba_api.stats.static.teams import find_team_name_by_id, get_teams
from nba_api.stats.endpoints import CommonTeamRoster

from nba_utils import get_team_abr, seasons, seconds_from_time, get_ln, abr_id_map
from nba_dataclasses import ShotStats, LineupPlayers, Official, TeamGameData, GameInfo
from load_roster_br import load_roster_br
from nba_dataclasses import GameStatus
from nba_utils import map_id

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
    "Boxscore": {"source": "file", "data_provider": "stats_nba"},
    "Possessions": {"source": "file", "data_provider": "stats_nba"},
}


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

        self.current_wins = 0
        self.current_games = 0
        self.current_pm = 0

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
            return 0.5

    @property
    def ave_pm(self) -> float:
        if self.total_games > 0:
            return self.total_pm / self.total_games
        else:
            return 0

    def reset_season(self):
        self.current_wins = 0
        self.current_games = 0
        self.current_pm = 0

    @property
    def current_wr(self) -> float:
        if self.current_games > 0:
            return self.current_wins / self.current_games
        else:
            return 0.5


class PlayerSeason:
    def __init__(self, player_id: int, name: str) -> None:
        self.id: int = player_id
        self.name = name
        self.player_contributions: dict[int, PlayerContribution] = {}
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
        # self.shots = [0, 0, 0, 0, 0, 0]
        # self.makes = [0, 0, 0, 0, 0, 0]

    def add_player_contribution(self, team_id, player_contribution):
        self.player_contributions[team_id] = player_contribution
        self.games += player_contribution.games
        self.wins += player_contribution.wins
        self.start_G += player_contribution.start_G
        self.start_F += player_contribution.start_F
        self.start_C += player_contribution.start_C
        self.game_time += player_contribution.game_time
        self.total_pm += player_contribution.total_pm

        self.points += player_contribution.points
        self.fg2a += player_contribution.fg2a
        self.fg2m += player_contribution.fg2m
        self.fg3a += player_contribution.fg3a
        self.fg3m += player_contribution.fg3m
        self.fta += player_contribution.fta
        self.ftm += player_contribution.ftm

        self.off_rebounds += player_contribution.off_rebounds
        self.def_rebounds += player_contribution.def_rebounds
        self.assists += player_contribution.assists
        self.blocks += player_contribution.blocks
        self.steals += player_contribution.steals

        self.turnovers += player_contribution.turnovers
        self.fouls += player_contribution.fouls

    def get_stats(self):
        mins = self.game_time / 60.0
        stats = []
        stats.append(self.total_pm / mins)

        stats.append(self.points / mins)
        stats.append(self.fg2a / mins)
        stats.append(self.fg2m / (self.fg2a if self.fg2a else 1))
        stats.append(self.fg2m / mins)
        stats.append(self.fg3a / mins)
        stats.append(self.fg3m / (self.fg3a if self.fg3a else 1))
        stats.append(self.fg3m / mins)
        stats.append(self.fta / mins)
        stats.append(self.ftm / (self.fta if self.fta else 1))
        stats.append(self.ftm / mins)

        stats.append(self.off_rebounds / mins)
        stats.append(self.def_rebounds / mins)
        stats.append(self.assists / mins)
        stats.append(self.blocks / mins)
        stats.append(self.steals / mins)

        stats.append(self.turnovers / mins)
        stats.append(self.fouls / mins)
        return stats
    # def __getattr__(self, name):
    #     val = 0
    #     for pc in self.player_contributions.values():
    #         val += getattr(pc, name)
    #     return val

    # @property
    # def points(self):
    #     points = 0
    #     for pc in self.player_contributions.values():
    #         points += pc.points
    #     return points

    # @property
    # def games(self):
    #     games = 0
    #     for pc in self.player_contributions.values():
    #         games += pc.games
    #     return games

    # @property
    # def game_time(self):
    #     game_time = 0
    #     for pc in self.player_contributions.values():
    #         game_time += pc.game_time
    #     return game_time

    # def add_shot(self, shot: ShotData):
    #     self.shots[shot.shot_type] += 1
    #     if shot.is_made:
    #         self.makes[shot.shot_type] += 1

    # def shot_chance(self, shot_type):
    #     if self.shots[shot_type]:
    #         return self.makes[shot_type] / self.shots[shot_type]
    #     else:
    #         return 0


class Season:
    def __init__(self, name) -> None:
        self.VERSION = 1

        self.name: str = name

        season_client = Client(season_settings)
        self.schedule = season_client.Season("nba", name, "Regular Season")

        self.first_game = date.fromisoformat(
            self.schedule.games.data[0]['date'])
        self.last_game = date.fromisoformat(
            self.schedule.games.data[-1]['date'])

        self.team_seasons: dict[int, TeamSeason] = None
        self.player_seasons: dict[int, PlayerSeason] = None

        self.game_infos: dict[int, GameInfo] = None

        # self.lineups: defaultdict[Lineup,
        #                           LineupStats] = defaultdict(LineupStats)

        self.total_possessions = 0
        self.total_points = 0

        # self.games: list[Game] = []

        # self.shots: list[Shot] = []

    @property
    def ave_ppp(self):
        return self.total_points / self.total_possessions

    def saveTeamSeasons(self):
        path = f"C:/Users/bhalb/nbaproject/data/season{self.name}TeamSeasons.pickle"
        with open(path, 'wb') as handle:
            pickle.dump(self.team_seasons, handle,
                        protocol=pickle.HIGHEST_PROTOCOL)

    def loadTeamSeasons(self):
        path = f"C:/Users/bhalb/nbaproject/data/season{self.name}TeamSeasons.pickle"
        if isfile(path):
            with open(path, 'rb') as handle:
                self.team_seasons = pickle.load(handle)
            self.load_rosters_statsnba()
            self.load_rosters_br()
            # self.build_player_seasons()
        else:
            self.load_season_from_boxscores()
            self.load_rosters_statsnba()
            self.load_rosters_br()
            # self.build_player_seasons()

    def saveGameInfos(self):
        path = f"C:/Users/bhalb/nbaproject/data/season{self.name}GameInfos.pickle"
        with open(path, 'wb') as handle:
            pickle.dump(self.game_infos, handle,
                        protocol=pickle.HIGHEST_PROTOCOL)

    def loadGameInfos(self):
        path = f"C:/Users/bhalb/nbaproject/data/season{self.name}GameInfos.pickle"
        if isfile(path):
            with open(path, 'rb') as handle:
                self.game_infos: dict[int, GameInfo] = pickle.load(handle)
        else:
            if self.game_infos is None:
                self.game_infos: dict[int, GameInfo] = {}

        count = 0
        for game_dict in self.schedule.games.final_games:
            game_id = game_dict['game_id']
            if game_id not in self.game_infos:
                game_info = self.load_game_data(game_dict)
                self.game_infos[game_id] = game_info
                count += 1
                print("loaded", count, game_id)
                time.sleep(5)
                if count % 100 == 0:
                    self.saveGameInfos()

        if count > 0:
            self.saveGameInfos()

    def save(self):
        path = f"C:/Users/bhalb/nbaproject/data/season{self.name}.pickle"
        with open(path, 'wb') as handle:
            pickle.dump(self, handle,
                        protocol=pickle.HIGHEST_PROTOCOL)

    def update(self):
        """To use when Season saved with old code"""
        return False
        # if not hasattr(self, 'VERSION') or self.VERSION < 4:

        #     print("Updating", self.name)
        #     self.games: list[Game] = []
        #     season_client = Client(season_settings)
        #     schedule = season_client.Season(
        #         "nba", self.name, "Regular Season")

        #     self.load_possessions(schedule, load_shots=False)

        #     self.VERSION = 4
        #     return True

        # return False

    def load_season_from_boxscores(self):
        print("Loading boxscores", datetime.now().time())
        for team in get_teams():
            team_id = team['id']
            ts = TeamSeason(team_id)
            self.team_seasons[team_id] = ts

        game_client = Client(game_settings)
        for game_dict in self.schedule.games.final_games:
            game_id = game_dict['game_id']
            game = game_client.Game(game_id)
            for team in game.boxscore.team_items:
                team_id = team['team_id']
                players = list(
                    filter(lambda p: p['team_id'] == team_id, game.boxscore.player_items))
                self.team_seasons[team_id].add_game_boxscore(team, players)

        # remove teams w/ no games
        for team in get_teams():
            team_id = team['id']
            if self.team_seasons[team_id].total_games == 0:
                del self.team_seasons[team_id]

    def load_rosters_statsnba(self):
        teams = self.team_seasons.values()

        added = False
        missing = True
        while missing:
            missing = False
            for team in teams:
                if not hasattr(team, 'roster_df'):
                    try:
                        roster = CommonTeamRoster(
                            team.id, season=self.name, timeout=60)
                        team.roster_df = roster.get_data_frames()[0]
                        team.coaches_df = roster.get_data_frames()[1]
                        print('adding', team.id)
                        added = True
                        time.sleep(5)
                    except:
                        missing = True
        if added:
            self.saveTeamSeasons()

    def load_rosters_br(self):
        teams = self.team_seasons.values()

        added = False
        missing = True
        while missing:
            missing = False
            for team in teams:
                if not hasattr(team, 'all_dfs'):
                    print('adding', team.id)
                    time.sleep(5)
                    player_data, salaries, all_dfs = load_roster_br(
                        team.id, self.name)
                    team.roster = player_data
                    team.salaries = salaries
                    team.all_dfs = all_dfs
                    added = True

        if added:
            self.fix_br_ids()
            self.saveTeamSeasons()

    def fix_br_ids(self):
        missing_ids = {}

        missing = 0
        found = 0
        # get missing ids from stat.nba roster if possible
        for ts in self.team_seasons.values():
            for row in ts.roster.itertuples():
                if row.id == 0:
                    missing += 1
                    for r2 in ts.roster_df.itertuples():
                        name1 = get_ln(row.name)
                        name2 = get_ln(r2.PLAYER)
                        if r2.NUM == row.number:
                            if name1 == name2:
                                found += 1
                                if row.br_id in missing_ids:
                                    if missing_ids[row.br_id] != r2.PLAYER_ID:
                                        print("two vals for", row.br_id)
                                missing_ids[row.br_id] = r2.PLAYER_ID
                                break
                            # else:
                            #     print("no id for", row.br_id, row.name, r2.PLAYER)
        if missing == 0:
            print("No missing ids")
            return
        print(missing, "missing ids,", found, "found")
        self.update_br_missing_ids(missing_ids)
        if found == missing:
            return

        # get missing ids from boxscores
        game_client = Client(game_settings)
        for game_dict in self.schedule.games.final_games:
            game_id = game_dict['game_id']
            game = game_client.Game(game_id)
            for team in game.boxscore.team_items:
                team_id = team['team_id']
                ts = self.team_seasons[team_id]
                players = list(
                    filter(lambda p: p['team_id'] == team_id, game.boxscore.player_items))
                for player_dict in players:
                    player_id = player_dict['player_id']

                    # if player_id not in roster
                    if len(ts.roster[ts.roster.id == player_id]) == 0:
                        # print("missing", player_id)
                        # print(player_dict)
                        name1 = get_ln(player_dict['name'])
                        for i in ts.roster.index:
                            if ts.roster.at[i, 'id'] == 0 and name1 == get_ln(ts.roster.at[i, 'name']):
                                # print("match", player_id, team_id)
                                br_id = ts.roster.at[i, 'br_id']
                                if br_id in missing_ids:
                                    if missing_ids[br_id] != player_id:
                                        print("two vals for", br_id)
                                missing_ids[br_id] = player_id
                                break
                        else:
                            print("no match", player_id, team_id)

        self.update_br_missing_ids(missing_ids)

    def update_br_missing_ids(self, missing_ids):
        for ts in self.team_seasons.values():
            for i in ts.roster.index:
                if ts.roster.at[i, 'id'] == 0:
                    if ts.roster.at[i, 'br_id'] in missing_ids:
                        ts.roster.at[i,
                                     'id'] = missing_ids[ts.roster.at[i, 'br_id']]
                        # print('added', ts.roster.at[i, 'id'],
                        #     ts.roster.at[i, 'br_id'])
                    else:
                        pass

    def load_game_data(self, game_dict):
        url = self.get_game_url(game_dict)

        loaded = False
        fail_count = 0
        while not loaded:
            try:
                page = requests.get(url, timeout=15)
                loaded = True
            except requests.exceptions.Timeout:
                print("failed to load", url)
                fail_count += 1
                if fail_count > 3:
                    raise requests.exceptions.Timeout
                time.sleep(5)

        soup = BeautifulSoup(page.text, features="lxml")

        home_id = game_dict['home_team_id']
        away_id = game_dict['visitor_team_id']

        game_stats = soup.find(id="content").find_all(
            "div", recursive=False)[-2]
        if game_stats.div.strong.string == 'Officials:\xa0':
            official_tags = game_stats.div.find_all('a')
            inactive_tags = []
        elif game_stats.div.strong.string == 'Inactive:\xa0':
            official_tags = game_stats.find_all('div')[1].find_all('a')
            inactive_tags = game_stats.div.contents
        else:
            print("Don't know how to handle structure for", url)
            print(game_stats)
            official_tags = []
            inactive_tags = []

        team_data = {home_id: TeamGameData(), away_id: TeamGameData()}
        officials = []

        for team_id in [home_id, away_id]:
            team_abr = get_team_abr(team_id, self.name)
            rows = soup.find(
                id=f"box-{team_abr}-game-basic").tbody.find_all('tr')
            ros = self.team_seasons[team_id].roster

            for row in rows[:5]:
                # starters
                br_id = row.find("th")['data-append-csv']
                id = ros[ros.br_id == br_id].id.item()
                team_data[team_id].starters.append(id)

            for row in rows[6:]:
                # bench
                br_id = row.find("th")['data-append-csv']
                try:
                    id = ros[ros.br_id == br_id].id.item()
                except ValueError:
                    name = row.th.a.string
                    try:
                        id = self.team_seasons[team_id].roster_df[self.team_seasons[team_id].roster_df.PLAYER == name].PLAYER_ID.item(
                        )
                    except ValueError:
                        id = map_id(br_id)
                    # For players who never played, like Aleksandar Radojević

                if row.td['data-stat'] == 'reason':
                    if row.td.string == 'Did Not Dress':
                        status = GameStatus.DND
                    elif row.td.string == 'Did Not Play':
                        status = GameStatus.DNP
                    elif row.td.string == 'Not With Team':
                        status = GameStatus.NOT_WITH_TEAM
                    elif row.td.string == 'Player Suspended':
                        status = GameStatus.SUSPENDED
                    else:
                        print("Game status", row.td.string, "for", url)
                        status = GameStatus.OTHER
                else:
                    status = GameStatus.PLAYED
                team_data[team_id].bench.append((id, status))

        for tag in inactive_tags:
            if tag.name == 'span':
                abr = tag.strong.string
                current_team = abr_id_map[abr]
                ros = self.team_seasons[current_team].roster
            elif tag.name == 'a':
                br_id = tag['href'].split('/')[-1][:-5]
                try:
                    id = ros[ros.br_id == br_id].id.item()
                except ValueError:
                    # for players who haven't played any games this season, like Klay
                    name = tag.string
                    try:
                        id = self.team_seasons[current_team].roster_df[self.team_seasons[current_team].roster_df.PLAYER == name].PLAYER_ID.item(
                        )
                    except ValueError:
                        id = map_id(br_id)
                team_data[current_team].inactive.append(id)

        for tag in official_tags:
            br_id = tag['href'].split('/')[-1][:-5]
            name = str(tag.string)
            officials.append(Official(name, br_id))

        game_info = GameInfo(game_dict['game_id'], game_dict['date'], home_id,
                             team_data[home_id], away_id, team_data[away_id], officials)
        return game_info

    def get_game_url(self, game):
        date = "".join(game['date'].split('-'))
        home_abr = get_team_abr(game['home_team_id'], self.name)
        url = f"https://www.basketball-reference.com/boxscores/{date}0{home_abr}.html"
        return url

    def build_player_seasons(self):
        self.player_seasons = {}
        for team_season in self.team_seasons.values():
            team_id = team_season.id
            for player_contribution in team_season.player_contributions.values():
                player_id = player_contribution.id

                if player_id not in self.player_seasons:
                    name = team_season.roster[team_season.roster.id == player_id].name.item(
                    )
                    self.player_seasons[player_id] = PlayerSeason(
                        player_id, name)
                self.player_seasons[player_id].add_player_contribution(
                    team_id, player_contribution)

    def build_shot_chance_data(self):
        possession_client = Client(game_possessions_settings)
        for game_dict in self.schedule.games.final_games:
            game_id = game_dict['game_id']
            game = possession_client.Game(game_id)
            possessions = game.possessions.items

            home_team = game.boxscore.team_items[0]['team_id']
            home_team_wr = self.team_seasons[home_team].current_wr
            road_team = game.boxscore.team_items[1]['team_id']
            road_team_wr = self.team_seasons[road_team].current_wr
            is_home_win = game.boxscore.team_items[0]['plus_minus'] > 0

    # def load_possessions(self, load_shots=True):
    #     print("Loading possessions", datetime.now().time())

    #     for team_season in self.team_seasons.values():
    #         team_season.reset_season()

    #     self.games = []

    #     possession_client = Client(game_possessions_settings)
    #     for game_dict in self.schedule.games.final_games:
    #         game_id = game_dict['game_id']
    #         game = possession_client.Game(game_id)
    #         possessions = game.possessions.items

    #         home_team = game.boxscore.team_items[0]['team_id']
    #         home_team_wr = self.team_seasons[home_team].current_wr
    #         road_team = game.boxscore.team_items[1]['team_id']
    #         road_team_wr = self.team_seasons[road_team].current_wr
    #         is_home_win = game.boxscore.team_items[0]['plus_minus'] > 0

    #         players = game.boxscore.player_items

    #         game_pos = []
    #         for possession in possessions:
    #             if load_shots:
    #                 self.add_possession(possession)

    #             seconds_left = max(4-possession.period, 0) * 12 * 60
    #             seconds_left += seconds_from_time(possession.start_time)
    #             score_margin = possession.start_score_margin
    #             offense_team_id = possession.offense_team_id
    #             shots = []
    #             # free_throws = []
    #             # TODO add data here
    #             # offensive rebound off free throw should be credited to that lineup
    #             # but the ft points go to the lineup that earned the foul
    #             # use .event_for_efficiency_stats property
    #             for event in possession.events:
    #                 if isinstance(event, enhanced_pbp.FieldGoal):
    #                     shooter: int = event.player1_id
    #                     shot_type = shot_type_value[event.shot_type]
    #                     is_made: bool = event.is_made
    #                     lineup = lineup_from_off_event(event)
    #                     is_and1 = event.is_and1
    #                     is_blocked = event.is_blocked
    #                     shot = Shot(shooter, shot_type, is_made,
    #                                 lineup, is_and1, is_blocked)
    #                     shots.append(shot)
    #                 # elif isinstance(event, enhanced_pbp.FreeThrow):
    #                 #     shooter: int = event.player1_id
    #                 #     is_made: bool = event.is_made
    #                 #     lineup = lineup_from_off_event(event)
    #                 #     free_throw = FreeThrow(shooter, is_made, lineup)
    #                 #     free_throws.append(free_throw)

    #             pos_info = PossessionInfo(
    #                 seconds_left, score_margin, offense_team_id, shots)
    #             game_pos.append(pos_info)

    #         self.games.append(Game(home_team, home_team_wr, road_team,
    #                                road_team_wr, is_home_win, game_pos, players))

    # def add_possession(self, possession):
    #     if possession.possession_stats == []:
    #         return PossessionStart.OTHER
    #         # not really a possession

    #     total_points = 0
    #     shot_points = 0

    #     for stat in possession.possession_stats:
    #         if stat['stat_key'] == 'OpponentPoints':
    #             total_points = stat['stat_value']
    #             off_team = stat['opponent_team_id']
    #             off_players = stat['opponent_lineup_id']
    #             def_team = stat['team_id']
    #             def_players = stat['lineup_id']
    #             break
    #     else:
    #         for stat in possession.possession_stats:
    #             if stat['stat_key'] == 'DefPoss':
    #                 off_team = stat['opponent_team_id']
    #                 off_players = stat['opponent_lineup_id']
    #                 def_team = stat['team_id']
    #                 def_players = stat['lineup_id']
    #                 break
    #         else:
    #             return None

    #     lineup = Lineup(off_team, off_players, def_team, def_players)

    #     # period = possession.period
    #     # start_time = seconds_from_time(possession.start_time)
    #     # end_time = seconds_from_time(possession.end_time)
    #     # periods_left = max(4 - period, 0)
    #     # game_seconds_left = periods_left*12*60 + start_time
    #     # possession_seconds = end_time - start_time

    #     last_shot = None

    #     for event in possession.events:
    #         if isinstance(event, enhanced_pbp.FieldGoal):
    #             is_made: bool = event.is_made
    #             player_id: int = event.player1_id
    #             if (player_id == 0):
    #                 print(event)
    #             shot_type: int = shot_type_value[event.shot_type]
    #             last_shot = (shot_type, player_id)

    #             if is_made:
    #                 shot_points += event.shot_value

    #             self.lineups[lineup].shots[last_shot].num_shots += 1

    #             is_and1 = event.is_and1
    #             is_blocked = event.is_blocked

    #             if is_and1:
    #                 self.lineups[lineup].shots[last_shot].and1s += 1

    #             shot = ShotData(is_made, is_and1, is_blocked, player_id,
    #                             shot_type, lineup)
    #             self.shots.append(shot)
    #             self.player_seasons[player_id].add_shot(shot)

    #         if isinstance(event, enhanced_pbp.FreeThrow):
    #             player_id: int = event.player1_id
    #             if (player_id == 0):
    #                 continue

    #             is_made = event.is_made
    #             if is_made:
    #                 shot_points += event.shot_value

    #             last_shot = (5, player_id)
    #             self.lineups[lineup].shots[last_shot].num_shots += 1

    #             shot = ShotData(is_made, False, False, player_id,
    #                             5, lineup)
    #             self.shots.append(shot)
    #             self.player_seasons[player_id].add_shot(shot)

    #         #     possession_start = PossessionStart.OREB
    #         # if isinstance(event, Timeout):
    #         #     possession_start = PossessionStart.TIMEOUT
    #         # if event.is_possession_ending_event:
    #         #     if isinstance(event, Turnover) and event.is_steal:
    #         #         possession_start = PossessionStart.STEAL
    #         #     else:
    #         #         possession_start = PossessionStart.OTHER

    #     self.lineups[lineup].add_possession(total_points, shot_points)
    #     self.total_possessions += 1
    #     self.total_points += total_points

    # # def add_shot(self, event: FieldGoal, lineup):
    # #     # get shot clock time, possession has starttime

    # #     is_made: bool = event.is_made
    # #     player_id: int = event.player1_id
    # #     shot_type: int = shot_type_value[event.shot_type]

    # #     is_and1 = event.is_and1
    # #     is_blocked = event.is_blocked

    # #     is_in_penalty = event.is_penalty_event()

    # #     # TODO get shot clock

    # #     # X, Y, score_margin, time_left, is_heave
    # #     shot = Shot(is_made, is_and1, is_blocked, player_id,
    # #                 shot_type, lineup)

    # #     # is_assisted
    # #     # is_blocked

    # #     # shot_type ‘AtRim’ 0, ‘ShortMidRange’ 1, ‘LongMidRange’ 2, ‘Arc3’ 3 or ‘Corner3’ 4

    # #     # is_putback

    # #     # distance
    # #     # locX
    # #     # locY

    # #     # seconds_remaining = shot.seconds_remaining
    # #     self.shots.append(shot)

    # #     self.player_seasons[player_id].add_shot(shot)

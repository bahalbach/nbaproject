from collections import defaultdict

from os.path import isfile
import pickle

import numpy as np
import pandas as pd
from sklearn import linear_model
from sklearn.model_selection import train_test_split


from nba_api.stats.static.players import find_player_by_id


from nba_utils import seasons, seconds_from_time
from nba_dataclasses import PlayerInfo, LineupPlayers, LineupStats, Lineup, ShotStats, Shot, Game, PossessionInfo
from Season import Season, TeamSeason, PlayerContribution, PlayerSeason


MOMENTUM = 0.9


class RollingAves:
    def __init__(self) -> None:
        self.games = 0
        self.game_time = 0
        self.points = 0
        self.fg2m = 0
        self.fg2a = 0
        self.fg3m = 0
        self.fg3a = 0
        self.fta = 0
        self.ftm = 0
        self.oreb = 0
        self.dreb = 0
        self.ast = 0
        self.stl = 0
        self.blk = 0
        self.to = 0
        self.pf = 0
        self.plus_minus = 0

    def add_game(self, p_dict):
        gt = seconds_from_time(p_dict['min'])
        if gt == 0:
            gt = 1
        self.games += 1
        self.game_time = (MOMENTUM * self.game_time) + (1-MOMENTUM) * gt

        self.points = (MOMENTUM * self.points) + \
            (1-MOMENTUM) * (p_dict['pts'] / gt)
        self.fg2m = (MOMENTUM * self.fg2m) + (1-MOMENTUM) * \
            ((p_dict['fgm'] - p_dict['fg3m']) / gt)
        self.fg2a = (MOMENTUM * self.fg2a) + (1-MOMENTUM) * \
            ((p_dict['fga'] - p_dict['fg3a']) / gt)
        self.fg3m = (MOMENTUM * self.fg3m) + \
            (1-MOMENTUM) * (p_dict['fg3m'] / gt)
        self.fg3a = (MOMENTUM * self.fg3a) + \
            (1-MOMENTUM) * (p_dict['fg3a'] / gt)
        self.ftm = (MOMENTUM * self.ftm) + (1-MOMENTUM) * (p_dict['ftm'] / gt)
        self.fta = (MOMENTUM * self.fta) + (1-MOMENTUM) * (p_dict['fta'] / gt)
        self.oreb = (MOMENTUM * self.oreb) + \
            (1-MOMENTUM) * (p_dict['oreb'] / gt)
        self.dreb = (MOMENTUM * self.dreb) + \
            (1-MOMENTUM) * (p_dict['dreb'] / gt)
        self.ast = (MOMENTUM * self.ast) + (1-MOMENTUM) * (p_dict['ast'] / gt)
        self.stl = (MOMENTUM * self.stl) + (1-MOMENTUM) * (p_dict['stl'] / gt)
        self.blk = (MOMENTUM * self.blk) + (1-MOMENTUM) * (p_dict['blk'] / gt)
        self.to = (MOMENTUM * self.to) + (1-MOMENTUM) * (p_dict['to'] / gt)
        self.pf = (MOMENTUM * self.pf) + (1-MOMENTUM) * (p_dict['pf'] / gt)
        self.plus_minus = (MOMENTUM * self.plus_minus) + \
            (1-MOMENTUM) * (p_dict['plus_minus'] / gt)

    def get_stats(self):
        stats = [self.games, self.game_time, self.points, self.fg2m, self.fg2a, self.fg3m, self.fg3a, self.ftm,
                 self.fta, self.oreb, self.dreb, self.ast, self.stl, self.blk, self.to, self.pf, self.plus_minus]
        if self.games == 0:
            return stats
        for i in range(1, len(stats)):
            stats[i] = stats[i] / (1 - (MOMENTUM ** self.games))
        return stats


class NbaTracker:
    def __init__(self) -> None:
        self.current_season: Season = None
        self.seasons: dict[str, Season] = {}

    def load_seasons(self):
        for season_name in seasons:
            self.load_season(season_name)
            print("Loaded ", season_name)

    def load_season(self, season_name):
        path = f"C:/Users/bhalb/nbaproject/data/season{season_name}.pickle"
        try:
            with open(path, 'rb') as handle:
                self.current_season: Season = pickle.load(handle)
                self.current_season.loadTeamSeasons()
                self.seasons[season_name] = self.current_season
            if self.current_season.update():
                with open(path, 'wb') as handle:
                    pickle.dump(self.current_season, handle,
                                protocol=pickle.HIGHEST_PROTOCOL)
        except:
            self.add_season(season_name)
        # self.seasons[season_name].saveTeamSeasons()

    def add_season(self, season_name):
        if season_name in self.seasons:
            print("Already loaded", season_name)
            return
        self.current_season = Season(season_name)
        self.current_season.loadTeamSeasons()
        self.seasons[season_name] = self.current_season

    def get_rosters(self):
        for season_name in seasons:
            self.load_season(season_name)
            season = self.seasons[season_name]
            season.load_rosters_statsnba()
            season.load_rosters_br()

            print('saved season', season_name)

    def build_points_data(self):
        # ave points this season
        # games played this season
        # ave points / min other starters
        # ave points / min allowed opponents
        # ave mins this season
        # ave points last season
        # games played last season
        # ave mins last season
        # points last game
        # min last game
        # points last 2 games
        # min last 2 games
        # points last X games
        # min last X games

        # usage?
        # was player availible last game

        # get all players to build dict of last season stats

        # possession ends: made basket/free throw, miss+dreb, turnover
        # and1, block, techs, subs
        # for each player, get
        # age
        # height
        # weight
        # years played nba
        # games played nba
        # if they were injured last game

        # for each player, get rolling averages of
        # minutes played

        # offensive possessions

        # % of teams shots
        # shots at rim
        # shots short midrange
        # shots long mid range
        # shots corner 3
        # shots arc 3
        # sum of % team shots for lineup
        # assists / shot chance
        # oreb / shot chance
        # turnover / shot chance
        # fouls drawn / shot chance

        # defensive possessions

        # dreb / shot chance
        # block / shot chance
        # and1s given / shot chance
        # def fouls / shot chance
        # steals / shot chance
        # off fouls drawn / shot chance

        # team stats when on floor?
        # team shots / shot chances (off pos + orebs)
        # team shots at rim/short midrange/long midrange/corner 3/arc 3
        # team assists / shot chances
        # team orebs / shot chances
        # team turnovers / shot chances
        # team fouls drawm / shot chance

        # shots allowed / shot chance
        # at rim/short midrange/long midrange/corner 3/arc 3
        # team drebs / shot chance
        # team orebs allowed / shot chance
        # team blocks / shot chance
        # team and1s allowed / shot chance
        # team forced turnover / shot chance
        # team steals / shot chance
        # team def fouls / shot chance
        # team off fouls drawn / shot chance

        # orebs / reboundable ft
        # team orbs allowed / reboundable ft

        points_scored = []

        ave_points_this_season = []
        games_played_this_season = []
        ave_gt_this_season = []

        ave_points_last_season = []
        games_played_last_season = []
        ave_gt_last_season = []

        played_last_game = []

        rolling_aves: defaultdict[int, RollingAves] = defaultdict(RollingAves)
        games = []

        for season_name in self.seasons:
            season = self.seasons[season_name]

            if season_name == "2000-01":
                for game in season.games:
                    for p_dict in game.players:
                        pid = p_dict['player_id']
                        rolling_aves[pid].add_game(p_dict)
                continue

            for game in season.games:
                # just get 5 starters for both teams
                players = []
                for p_dict in game.players:
                    pid = p_dict['player_id']

                    if p_dict['start_position'] == '':
                        continue

                    roster = season.team_seasons[p_dict['team_id']].roster
                    player = roster[roster['id'] == pid]
                    if len(player) == 1:
                        height = player['height'].item().split('-')
                        height = int(height[0]) + int(height[1]) / 12.0
                        weight = int(player['weight'].item())
                        age = int(player['age'].item())
                        exp = int(player['exp'].item())
                    else:
                        print("ERROR, missing player",
                              pid, p_dict['team_id'])
                        height, weight, age, exp = 0, 0, 0, 0

                    stats = [height, weight, age, exp] + \
                        rolling_aves[pid].get_stats()
                    targets = [p_dict['pts'], p_dict['reb'], p_dict['ast']]

                    players.append((stats, targets))

                for p_dict in game.players:
                    pid = p_dict['player_id']
                    rolling_aves[pid].add_game(p_dict)

                games.append(players)

            previous_season = season

        # df = pd.DataFrame({
        #     'points_scored': points_scored,
        #     "ave_points_this_season": ave_points_this_season,
        #     "games_played_this_season": games_played_this_season,
        #     "ave_gt_this_season": ave_gt_this_season,
        #     "ave_points_last_season": ave_points_last_season,
        #     "games_played_last_season": games_played_last_season,
        #     "ave_gt_last_season": ave_gt_last_season,
        #     "played_last_game": played_last_game,
        # })
        return games

    def build_win_prob_data(self):
        num_possessions = 0
        for season_name in self.seasons:
            season = self.seasons[season_name]
            for game in season.games:
                for pos in game.possessions:
                    num_possessions += 1

        is_win = np.zeros(num_possessions, dtype=bool)
        seconds_left = np.zeros(num_possessions, dtype=np.int16)
        score_margin = np.zeros(num_possessions, dtype=np.int8)
        is_home = np.zeros(num_possessions, dtype=bool)

        index = 0

        for season_name in self.seasons:
            season = self.seasons[season_name]
            for game in season.games:
                if game.is_home_win:
                    winning_team = game.home_team_id
                else:
                    winning_team = game.road_team_id

                for pos in game.possessions:
                    is_win[index] = pos.offense_team_id == winning_team
                    seconds_left[index] = pos.seconds_left
                    score_margin[index] = pos.score_margin
                    is_home[index] = pos.offense_team_id == game.home_team_id
                    index += 1

        df = pd.DataFrame({'is_win': is_win, 'seconds_left': seconds_left,
                          'score_margin': score_margin, 'is_home': is_home})
        return df

    def create_RAPM(self, season_name, num_seasons=1):
        # check if file already exists
        path = f"C:/Users/bhalb/nbaproject/data/rapm{season_name}_{num_seasons}season.pickle"
        if isfile(path):
            print("loading RAPM")
            with open(path, 'rb') as handle:
                player_indicies, intercept1, intercept2, reg1, reg2 = pickle.load(
                    handle)
                self.show_top_RAPMS(player_indicies)
            return player_indicies, intercept1, intercept2, reg1, reg2

        index = seasons.index(season_name)
        first_season = index - num_seasons + 1
        if first_season < 0:
            return None

        print("computing RAPM")
        # get all players and lineups who played in covered seasons
        player_index = 0
        player_indicies: dict[int, PlayerInfo] = {}
        lineup_index = 0
        num_lineups = 0
        for i in range(num_seasons):
            season_name = seasons[first_season+i]
            if season_name not in self.seasons:
                self.load_season(season_name)
            for player, ps in self.seasons[season_name].player_seasons.items():
                if player not in player_indicies:
                    player_indicies[player] = PlayerInfo(player_index)
                    player_index += 1
                for team in ps.player_contributions:
                    player_indicies[player].teams.add(team)
            num_lineups += len(self.seasons[season_name].lineups)
        num_players = player_index

        y = np.zeros(num_lineups)
        ey = np.zeros(num_lineups)
        X = np.zeros((num_lineups, num_players*2))
        sample_weights = np.zeros(num_lineups)

        for i in range(num_seasons):
            season_name = seasons[first_season+i]
            ps = self.seasons[season_name].player_seasons
            for lineup, stats in self.seasons[season_name].lineups.items():
                for player_id in lineup.off_players.split("-"):
                    player_id = int(player_id)
                    player_indicies[player_id].o_possessions += stats.possessions
                    i = player_indicies[player_id].index
                    X[lineup_index, i] = 1
                for player_id in lineup.def_players.split("-"):
                    player_id = int(player_id)
                    player_indicies[player_id].d_possessions += stats.possessions
                    i = player_indicies[player_id].index
                    X[lineup_index, i + num_players] = 1
                y[lineup_index] = stats.points / stats.possessions
                ey[lineup_index] = stats.expected_points(
                    ps) / stats.possessions
                sample_weights[lineup_index] = stats.possessions
                lineup_index += 1
        # return (X, y, ey, sample_weights)
        # X_train, X_test, y_train, y_test, sample_weights_train, sample_weights_test = train_test_split(X, y, sample_weights, random_state=3426415341)
        reg = linear_model.BayesianRidge()
        reg.fit(X, y, sample_weights)

        reg2 = linear_model.BayesianRidge()
        reg2.fit(X, ey, sample_weights)

        for player in player_indicies.values():
            player.e_opm = reg2.coef_[player.index]
            player.e_dpm = reg2.coef_[player.index + num_players]
            player.opm = reg.coef_[player.index]
            player.dpm = reg.coef_[player.index + num_players]

        with open(path, 'wb') as handle:
            pickle.dump((player_indicies, reg.intercept_, reg2.intercept_, reg, reg2), handle,
                        protocol=pickle.HIGHEST_PROTOCOL)

        self.show_top_RAPMS(player_indicies)

        return (player_indicies, reg.intercept_, reg2.intercept_, reg, reg2)

    def show_top_RAPMS(self, player_indicies, max_count=20):
        count = 0
        print("Top", max_count, "RAPM")
        for pid, player in sorted(player_indicies.items(), key=lambda p: p[1].epm, reverse=True):
            name = find_player_by_id(pid)['full_name']
            print(name, player.pm, player.epm)
            count += 1
            if count == max_count:
                break

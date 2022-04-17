from numpy import append
from PlayerSeasonData import PlayerSeasonData
from nba_utils import KeyDefaultDict
from collections import defaultdict
from pbpstats.client import Client
import pandas as pd

game_settings = {
    "dir": "C:/Users/bhalb/nbaproject/response_data",
    "Boxscore": {"source": "file", "data_provider": "stats_nba"},
}


class PlayerTracker:
    def __init__(self, season):
        self.season = season
        self.players: dict[int, PlayerSeasonData] = KeyDefaultDict(
            PlayerSeasonData)
        for team in season.team_seasons.values():
            team.roster_df.apply(
                lambda row: self.players[row.PLAYER_ID].add_roster_info(row), axis=1
            )
            team.roster.apply(
                lambda row: self.players[row.id].add_br_roster_info(row), axis=1
            )
        self.game_client = Client(game_settings)
        path = f"C:/Users/bhalb/nbaproject/data/season{self.season.name}player_tracking_df.csv"
        self.df = pd.read_csv(path)

        # players = list(self.players.keys())

        # self.rebound_teammates = defaultdict(
        #     lambda: defaultdict(lambda: [0, 0]))
        # """oreb teammates, dreb teammates"""

        # self.rebound_opponents = defaultdict(
        #     lambda: defaultdict(lambda: [0, 0]))
        # # {p: defaultdict(
        # #     lambda: [0, 0]) for p in players}
        # """oreb opponents, dreb opponents"""

    def __getitem__(self, key):
        return self.players[key]

    def add_games(self, game_ids: list[int]):
        for game_id in game_ids:
            game = self.game_client.Game(game_id)
            for player in game.boxscore.player_items:
                player_id = player['player_id']
                self.players[player_id].add_boxscore(player)

        self.df[self.df.GAME_ID.isin(map(int, game_ids))].apply(
            lambda row: self.players[row.PLAYER_ID].add_playertracking(row), axis=1)

    def undo_add_game(self, game_id):
        game = self.game_client.Game(game_id)
        for player in game.boxscore.player_items:
            player_id = player['player_id']
            self.players[player_id].undo_add_boxscore(player)

        self.df[self.df.GAME_ID.isin(map(int, [game_id]))].apply(
            lambda row: self.players[row.PLAYER_ID].undo_add_playertracking(row), axis=1)

    def add_game(self, game_id):
        game = self.game_client.Game(game_id)
        playing_players = []
        all_players = []

        for player in game.boxscore.player_items:
            player_id = player['player_id']
            self.players[player_id].add_boxscore(player)
            player = (player_id, (player['pts'], player['reb'], player['ast']))
            playing_players.append(player)

        def add_playertracking(row):
            self.players[row.PLAYER_ID].add_playertracking(row)
            all_players.append(row.PLAYER_ID)

        self.df[self.df.GAME_ID.isin(map(int, [game_id]))].apply(
            add_playertracking, axis=1)

        return playing_players, all_players

    def add_try_event(self, ge, rc_chances, shot_chances, epts, eofts, edfts):
        lineup = ge.lineup.lineup
        for team in [0, 1]:
            for player_id in lineup[team]:
                if team == 0:
                    self.players[player_id].add_off_try_event(
                        ge, rc_chances, shot_chances, epts, eofts, edfts)
                else:
                    self.players[player_id].add_def_try_event(
                        ge, rc_chances, shot_chances, epts, eofts, edfts)

    def add_rebound_event(self, ge, chances):
        lineup = ge.lineup.lineup
        for team in [0, 1]:
            # other_team = 1 - team
            for player_id in lineup[team]:
                if team == 0:
                    self.players[player_id].add_oreb_event(ge, chances)
                else:
                    self.players[player_id].add_dreb_event(ge, chances)
                # for teammate in lineup[team]:
                #     if player_id == teammate:
                #         continue
                #     self.rebound_teammates[player_id][teammate][team] += 1
                # for opponent in lineup[other_team]:
                #     self.rebound_opponents[player_id][opponent][team] += 1

    def undo_add_rebound_event(self, ge, chances):
        lineup = ge.lineup.lineup
        for team in [0, 1]:
            # other_team = 1 - team
            for player_id in lineup[team]:
                if team == 0:
                    self.players[player_id].undo_add_oreb_event(ge, chances)
                else:
                    self.players[player_id].undo_add_dreb_event(ge, chances)
                # for teammate in lineup[team]:
                #     if player_id == teammate:
                #         continue
                #     self.rebound_teammates[player_id][teammate][team] -= 1
                # for opponent in lineup[other_team]:
                #     self.rebound_opponents[player_id][opponent][team] -= 1

    def get_rebound_stats(self, pid):
        """Doesn't seem worth using"""
        # oreb stats
        p = self.players[pid]
        orebs = p.oreb_events if p.oreb_events else 1
        drebs = p.dreb_events if p.dreb_events else 1
        olo = p.oreb_team_live_oreb_dif
        odo = p.oreb_team_dead_oreb_dif
        dlo = p.dreb_team_live_oreb_dif
        ddo = p.dreb_team_dead_oreb_dif
        # for tid, (oreb_count, dreb_count) in self.rebound_teammates[pid].items():
        #     t = self.players[tid]
        #     olo -= t.oreb_team_live_oreb_dif * oreb_count / orebs / 4
        #     odo -= t.oreb_team_dead_oreb_dif * oreb_count / orebs / 4
        #     dlo -= t.dreb_team_live_oreb_dif * dreb_count / drebs / 4
        #     ddo -= t.dreb_team_dead_oreb_dif * dreb_count / drebs / 4
        # for oid, (oreb_count, dreb_count) in self.rebound_opponents[pid].items():
        #     o = self.players[oid]
        #     olo += o.dreb_team_live_oreb_dif * dreb_count / orebs / 5
        #     odo += o.dreb_team_dead_oreb_dif * dreb_count / orebs / 5
        #     dlo += o.oreb_team_live_oreb_dif * oreb_count / drebs / 5
        #     ddo += o.oreb_team_dead_oreb_dif * oreb_count / drebs / 5

        return [
            olo / orebs,
            odo / orebs,
            dlo / drebs,
            ddo / drebs,
        ]

from PlayerSeasonData import PlayerSeasonData
from nba_utils import KeyDefaultDict
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
        for team in self.team_seasons.values():
            team.roster_df.apply(
                lambda row: self.players[row.PLAYER_ID].add_roster_info(row), axis=1
            )

    def add_games(self, game_ids: list[int]):
        for game_id in game_ids:
            game = self.game_client.Game(game_id)
            for player in game.boxscore.player_items:
                player_id = player['player_id']
                self.players[player_id].add_boxscore(player)

        path = f"C:/Users/bhalb/nbaproject/data/season{self.season.name}player_tracking_df.csv"
        df = pd.read_csv(path)
        # for player in df[df.GAME_ID.isin(games)].itertuples():
        #     player_id = player.PLAYER_ID
        #     players[player_id].add_playertracking(player)
        df[df.GAME_ID.isin(map(int, game_ids))].apply(
            lambda row: self.players[row.PLAYER_ID].add_playertracking(row), axis=1)

    def undo_add_game(self, game_id):
        game = self.game_client.Game(game_id)
        for player in game.boxscore.player_items:
            player_id = player['player_id']
            self.players[player_id].undo_add_boxscore(player)

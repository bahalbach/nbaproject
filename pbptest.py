# -*- coding: utf-8 -*-
"""
Created on Mon Nov 18 11:18:56 2019

@author: bhalb
"""

import pprint

from pbpstats.client import Client

all_players = {}
all_teams = {}


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


class Player:
    def __init__(self, name: str):
        self.name = name
        self.total_seconds = 0
        self.total_pts = 0
        self.total_pm = 0

    def add_game(self, player_boxscore: dict):
        """
        Add information from this game to the Player.

        Args:
            player_boxscore (dict): boxscore data for the player from the given game.

        Returns:
            None
        """
        self.total_seconds += seconds_from_time(player_boxscore['min'])
        self.total_pts += int(player_boxscore['pts'])
        self.total_pm += int(player_boxscore['plus_minus'])

    @property
    def avg_points(self):
        """float: average points per minute"""
        if (self.total_seconds != 0):
            return self.total_pts / (self.total_seconds / 60)
        return 0

    @property
    def avg_pm(self):
        """float: average plus/minus per minute"""
        if (self.total_seconds != 0):
            return self.total_pm / (self.total_seconds / 60)
        return 0


season_settings = {
    "dir": "C:/Users/bhalb/nbaproject/response_data",
    "Games": {"source": "file", "data_provider": "stats_nba"},
    # "Boxscore": {"source": "web", "data_provider": "data_nba"},
    # "Possessions": {"source": "file", "data_provider": "data_nba"},
}
game_settings = {
    "dir": "C:/Users/bhalb/nbaproject/response_data",
    "Boxscore": {"source": "file", "data_provider": "stats_nba"},
    # "Possessions": {"source": "file", "data_provider": "stats_nba"},
}
season_client = Client(season_settings)
game_client = Client(game_settings)
season = season_client.Season("nba", "2017-18", "Regular Season")
for game_dict in season.games.final_games:
    game_id = game_dict['game_id']
    game = game_client.Game(game_id)
    for player in game.boxscore.player_items:
        player_id = player['player_id']
        if player_id not in all_players:
            all_players[player_id] = Player(player['name'])
        all_players[player_id].add_game(player)
    for team in game.boxscore.team_items:
        team_id = team['team_id']
        if team_id not in all_teams:
            all_teams[team_id] = team['team_name']


pprint.pp(list(map(lambda x: (x.name, x.avg_points * 36, x.avg_pm * 36),
                   list(all_players.values())[0:100])))
# game = season_client.Game("0021900001")
# for possession in game.possessions.items:
#     print(possession)

# settings = {
#     "dir": "C:/Users/bhalb/nbaproject/response_data/",
#     "Games": {"source": "file", "data_provider": "stats_nba"},
# }
# client = Client(settings)
# day = client.Day("02/03/2020", "nba")
# season = client.Season("nba", "2019-20", "Regular Season")
# postseason = client.Season("nba", "2019-20", postseason)
# for final_game in season.games.final_games:
#     print(final_game)

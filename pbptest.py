# -*- coding: utf-8 -*-
"""
Created on Mon Nov 18 11:18:56 2019

@author: bhalb
"""

# from pbpstats.data_game_data import DataGameData
# from pbpstats.stats_game_data import StatsGameData

# dgame_data = DataGameData('0021800143')
# dgame_data.get_game_data(ignore_rebound_and_shot_order=True)

#sgame_data = StatsGameData('0011800027')
# sgame_data.get_game_data()
# , response_data_directory='C:/Users/bhalb/nbaproject/data/'

# to ignore rebound event order
# game_data.get_game_data(ignore_rebound_and_shot_order=True)
# to ignore issues parsing pbp that result in a team having back-to-back possessions
# game_data.get_game_data(ignore_back_to_back_possessions=True)

from pbpstats.client import Client

settings = {
    "dir": "/response_data",
    "Boxscore": {"source": "file", "data_provider": "stats_nba"},
    "Possessions": {"source": "file", "data_provider": "stats_nba"},
}
client = Client(settings)
game = client.Game("0021900001")

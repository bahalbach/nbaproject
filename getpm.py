# -*- coding: utf-8 -*-
"""
Created on Fri Dec  6 14:11:17 2019

@author: bhalb
"""


import sys
sys.path.insert(1, 'C:/Users/bhalb/Documents/GitHub/pbpstats')

import pbpstats
from pbpstats import utils
from pbpstats.data_game_data import DataGameData

#get schedule 
seasonYear = '2018'
scheduleFilePath = f'{pbpstats.DATA_DIRECTORY}schedule/data_{seasonYear}.json' if pbpstats.DATA_DIRECTORY is not None else None
scheduleUrl = (f"http://data.nba.net/v2015/json/mobile_teams/nba/{seasonYear}/league/00_full_schedule.json")

response_json = utils.get_json_response(scheduleUrl, {}, scheduleFilePath)

# get pbp data for each game in schedule year
season = response_json['lscd']
index = 0
for month in season:
    index += 1
    month = month['mscd']
    if index != 10:
        continue
    for game in month['g']:
        gid = game['gid']
        dgame_data = DataGameData(gid)
        dgame_data.get_game_data(ignore_rebound_and_shot_order=True)
    
#get players


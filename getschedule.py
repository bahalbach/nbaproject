# -*- coding: utf-8 -*-
"""
Created on Fri Dec  6 14:11:17 2019

@author: bhalb
"""


import sys
sys.path.insert(1, 'C:/Users/bhalb/Documents/GitHub/pbpstats')

import pbpstats
from pbpstats import utils

#get schedule 
seasonYear = '2018'
scheduleFilePath = f'{pbpstats.DATA_DIRECTORY}schedule/data_{seasonYear}.json' if pbpstats.DATA_DIRECTORY is not None else None
scheduleUrl = (f"http://data.nba.net/v2015/json/mobile_teams/nba/{seasonYear}/league/00_full_schedule.json")

response_json = utils.get_json_response(scheduleUrl, {}, scheduleFilePath)

#get players

import pandas as pd

import unidecode

from nba_api.stats.static.teams import find_team_name_by_id, get_teams


# %% test print
VERSION = 2


def print_version():
    print(VERSION)

# %%


class KeyDefaultDict(dict):
    def __init__(self, factory):
        self.factory = factory

    def __missing__(self, key):
        self[key] = self.factory(key)
        return self[key]


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


def get_ln(name):
    name = unidecode.unidecode(name).lower().split(' ')
    name, name2 = name[-1], name[-2]
    if name in ['sr.', 'jr.', 'ii', 'iii', 'iv', 'v']:
        name = name2
    return name


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
]


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


path = f"C:/Users/bhalb/nbaproject/data/NBA_Player_IDs.csv"
ids_df = pd.read_csv(path, encoding='ANSI')


def map_id(br_id):
    try:
        return int(ids_df[ids_df['BBRefID'] == br_id]['NBAID'].item())
    except ValueError:
        return 0


def get_team_abr(team_id, season_name):
    if team_id == 1610612740:  # NOP
        if season_name <= "2004-05":
            return "NOH"
        elif season_name <= "2006-07":
            return "NOK"
        elif season_name <= "2012-13":
            return "NOH"
        else:
            return "NOP"
    elif team_id == 1610612751:  # BRK
        if season_name <= "2011-12":
            return "NJN"
        else:
            return "BRK"
    elif team_id == 1610612760:  # OKC
        if season_name <= "2007-08":
            return "SEA"
        else:
            return "OKC"
    elif team_id == 1610612763:  # MEM
        if season_name <= "2000-01":
            return "VAN"
        else:
            return "MEM"
    elif team_id == 1610612766:  # CHA
        if season_name <= "2001-02":
            return "CHH"
        elif season_name <= "2013-14":
            return "CHA"
        else:
            return "CHO"
    elif team_id == 1610612756:  # PHO
        return "PHO"
    else:
        return find_team_name_by_id(team_id)['abbreviation']


abr_id_map = {}
for team in get_teams():
    team_id = team['id']
    for season_name in seasons:
        abr = get_team_abr(team_id, season_name)
        if abr in abr_id_map and abr_id_map[abr] != team_id:
            print("Error", abr, abr_id_map[abr], team_id)
        abr_id_map[abr] = team_id

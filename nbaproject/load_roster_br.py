import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import datetime
import unidecode
import time

from nba_utils import get_team_abr, map_id


def load_roster_br(team_id, season_name):
    team_abr = get_team_abr(team_id, season_name)
    season_year = season_name[:2]+season_name[5:]
    url = f"https://www.basketball-reference.com/teams/{team_abr}/{season_year}.html"
    loaded = False
    while not loaded:
        try:
            page = requests.get(url, timeout=15)
            loaded = True
        except requests.exceptions.Timeout:
            time.sleep(5)

    soup = BeautifulSoup(page.text, features="lxml")
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))

    all_dfs = pd.read_html(page.text)
    for comment in comments:
        if 'table' in comment:
            try:
                all_dfs.append(pd.read_html(comment)[0])
            except:
                continue

    player_data = {}

    column_names = ['name', 'id', 'br_id', 'number', 'pos',
                    'height', 'weight', 'bday', 'country', 'exp', 'colleges']
    column_names += ["age", "games", "games_started", "minutes_played",
                     "pts", "fg2m", "fg2a", "fg3m", "fg3a", "ftm", "fta", "orb", "drb", "ast", "stl", "blk", "tov", "pf"]

    rows = soup.find(id="roster").tbody.find_all('tr')
    for row in rows:
        data = row.find_all('td')
        name = unidecode.unidecode(data[0].a.get_text())
        try:
            br_id = data[0]['data-append-csv']
        except KeyError:
            br_id = data[0].a['href'].split('/')[-1][:-5]
        id = map_id(br_id)
        number = row.find('th').get_text()
        pos = data[1].get_text()
        height = data[2].get_text()
        weight = int(data[3].get_text())
        bday = data[4].get_text()
        bday = datetime.datetime.strptime(bday, "%B %d, %Y")
        country = data[5].get_text()
        exp = data[6].get_text()
        exp = 0 if exp == 'R' else int(exp)
        colleges = data[7].get_text()
        player_data[name] = {'player_info': [name, id, br_id, number, pos,
                                             height, weight, bday, country, exp, colleges]}

    total_rows = soup.find(id="totals").tbody.find_all('tr')
    for row in total_rows:
        data = row.find_all('td')
        name = unidecode.unidecode(data[0].get_text())

        age = int(data[1].get_text())
        games = int(data[2].get_text())
        games_started = int(data[3].get_text())
        minutes_played = int(data[4].get_text())

        pts = int(data[26].get_text())

        fg2m = int(data[11].get_text())
        fg2a = int(data[12].get_text())

        fg3m = int(data[8].get_text())
        fg3a = int(data[9].get_text())

        ftm = int(data[15].get_text())
        fta = int(data[16].get_text())

        orb = int(data[18].get_text())
        drb = int(data[19].get_text())
        ast = int(data[21].get_text())
        stl = int(data[22].get_text())
        blk = int(data[23].get_text())
        tov = int(data[24].get_text())
        pf = int(data[25].get_text())

        player_data[name]['season_totals'] = [age, games, games_started, minutes_played,
                                              pts, fg2m, fg2a, fg3m, fg3a, ftm, fta, orb, drb, ast, stl, blk, tov, pf]

    salaries = {}
    for comment in comments:
        if 'salaries2' in comment:
            salary_table = BeautifulSoup(comment, features="lxml").table.tbody

            for row in salary_table.find_all('tr'):
                data = row.find_all('td')
                try:
                    br_id = data[0]['data-append-csv']
                    id = map_id(br_id)
                except KeyError:
                    id = 0
                try:
                    salary = data[1]['csk']
                except KeyError:
                    salary = 0
                salaries[id] = salary
    salaries

    players = []
    for player in player_data.values():
        player_array = player['player_info'] + \
            (player['season_totals'] if 'season_totals' in player else [0]*18)
        players.append(player_array)

    br_df = pd.DataFrame(players, columns=column_names)

    return br_df, salaries, all_dfs

from urllib.request import urlopen
from bs4 import BeautifulSoup
import pandas as pd


def get_player_transactions(year: int):
    begin_date = f"{str(year)}-01-01"
    end_date = f"{str(year)}-12-31"
    url = f"http://www.prosportstransactions.com/basketball/Search/SearchResults.php?Player=&Team=&BeginDate={begin_date}&EndDate={end_date}&PlayerMovementChkBx=yes&Submit=Search&start="
    start = 0

    transactions = []

    while True:
        # print("Start: ", start)
        current_url = url + str(start)
        start += 25

        html = urlopen(current_url)
        soup = BeautifulSoup(html)
        table_rows = soup.find_all('div')[3].table.find_all('tr')
        if len(table_rows) == 1:
            break

        for trans in table_rows[1:]:
            trans_data = trans.find_all('td')

            date = trans_data[0].contents[0]

            team = trans_data[1].contents[0].strip()

            acquired = trans_data[2].contents[0]
            if acquired:
                acquired = acquired[3:]

            relinquished = trans_data[3].contents[0]
            if relinquished:
                relinquished = relinquished[3:]

            notes = trans_data[4].contents[0]

            transactions.append((date, team, acquired, relinquished, notes))

    return transactions


def save_transaction_data(year):
    path = f"C:/Users/bhalb/nbaproject/data/transactions{str(year)}.pkl"
    trans = get_player_transactions(year)
    df = pd.DataFrame(
        trans, columns=["date", "team", "acquired", "relinquished", "notes"])
    df.to_csv(path, index=False)

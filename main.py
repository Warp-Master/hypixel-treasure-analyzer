import json
import os.path
from collections import Counter, namedtuple
from functools import partial
from itertools import filterfalse
from textwrap import fill
from urllib.request import urlopen
import configparser

import lxml.html
from lxml.cssselect import CSSSelector

sel = CSSSelector('.hp-tabber .hp-tabcontent:not(#Metal_Detector_)')
Location = namedtuple('Location', ('name', 'high_tier_table', 'low_tier_table'))
Drop = namedtuple('Drop', ('name', 'amount', 'chance'))

config = configparser.ConfigParser()
config.read('config.ini')
config = config['DEFAULT']

AH_PRICES_PATH = config['AH_PRICES_PATH']
NAME_MAP_PATH = config['NAME_MAP_PATH']
WIKI_URL = config['WIKI_URL']
BAZAAR_API_URL = config['BAZAAR_API_URL']
OUTPUT_WIDTH = int(config['OUTPUT_WIDTH'])
CHEST_SPAWN_CHANCE = float(config.get('CHEST_SPAWN_CHANCE', float('inf')))
SLUDGE_PICK = bool(int(config.get('SLUDGE_PICK', False)))

fill = partial(fill, width=OUTPUT_WIDTH)
ah_prices = dict()
updated_prices = set()
not_valuable_drops = {'Mithril Powder', 'Gemstone Powder'}

with open(NAME_MAP_PATH) as file:
    NAME_MAP = json.load(file)

def get_drops(tbody, chance_multiplier=1.0):
    res = []
    for line in tbody.findall('tr')[2:]:
        cols = [next(filterfalse(str.isspace, col.itertext()), '').strip() \
                for col in line.iterfind('td')]
        name = NAME_MAP.get(cols[0], cols[0])
        amounts = cols[1].replace(',', '').split('-')
        avg_amount = sum(map(int, amounts)) / len(amounts)
        chance = float(cols[-1].replace("%", "e-2")) * chance_multiplier
        res.append(Drop(name, avg_amount, chance))
    return res


def get_profit(drops, bazaar_data):
    res = Counter()
    for drop in drops:
        if drop.name in bazaar_data:
            price = bazaar_data[drop.name].get('quick_status', {}).get('buyPrice', 0)
        elif drop.name in not_valuable_drops:
            res[drop.name] += drop.amount * drop.chance
            continue
        elif drop.name in updated_prices:
            continue
        else:
            price_str = input(
                f'Input price for {drop.name} [{ah_prices.get(drop.name, 0)}]: '
            ).strip()
            if price_str:
                price = float(price_str)
                ah_prices[drop.name] = price
            else:
                price = ah_prices.get(drop.name, 0)
            updated_prices.add(drop.name)
        res['coins'] += price * drop.amount * drop.chance
    return res


def print_counts(counter):
    for location, count in counter.most_common():
        print(f'{location:<21}{count:{OUTPUT_WIDTH-21}.4f}')


def main():
    global ah_prices
    # load ah prices if file exists
    if os.path.exists(AH_PRICES_PATH):
        with open(AH_PRICES_PATH) as file:
            ah_prices = json.load(file)

    # load wiki page with chance information
    with urlopen(WIKI_URL) as resp:
        wiki_page = lxml.html.parse(resp)

    # load bazaar prices from hypixel API
    with urlopen(BAZAAR_API_URL) as resp:
        bazaar_data = json.load(resp)['products']

    coins_counter = Counter()
    mithril_dst_counter = Counter()
    gemstone_dst_counter = Counter()
    content = sel(wiki_page)
    print(fill("Press <Return> to use the default price in square brackets. The values will be saved between runs."))
    for el in content:
        location_name = el.attrib.get('id')[:-1]
        tables = el.findall('.//table/tbody')
        location = Location(location_name, *tables)
        # print(location)
        high_drops = get_drops(location.high_tier_table, chance_multiplier=0.05)
        location_profit = get_profit(high_drops, bazaar_data)
        low_drops = get_drops(location.low_tier_table, chance_multiplier=0.95)
        location_profit += get_profit(low_drops, bazaar_data)
        coins_counter[location_name] = location_profit['coins']
        mithril_dst_counter[location_name] = location_profit['Mithril Powder']
        gemstone_dst_counter[location_name] = location_profit['Gemstone Powder']
    
    # save cache to file
    with open(AH_PRICES_PATH, 'w') as file:
        json.dump(ah_prices, file)    

    sludge_pick_profit = get_profit(
        [Drop('SLUDGE_JUICE', 1e4 / CHEST_SPAWN_CHANCE, 0.03)],
        bazaar_data
    ).get('coins', 0)
    if SLUDGE_PICK:
        coins_counter['Jungle'] += sludge_pick_profit
    else:
        print('='*OUTPUT_WIDTH)
        print(fill(f"If you use Jungle Pickaxe don't forget to add extra Sludge Juice profits to Jungle location. [{sludge_pick_profit:.2f}]"))
        print(fill("Or add \"SLUDGE_PICK=1\" to config.ini to do it automaticly"))
    print(f"{'<COINS>':=^{OUTPUT_WIDTH}}")
    print_counts(coins_counter)
    print(f"{'<MITHRIL POWDER>':=^{OUTPUT_WIDTH}}")
    print_counts(mithril_dst_counter)
    print(f"{'<GEMSTONE POWDER>':=^{OUTPUT_WIDTH}}")
    print_counts(gemstone_dst_counter)

if __name__ == "__main__":
    main()

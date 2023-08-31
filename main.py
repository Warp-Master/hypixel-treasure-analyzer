import lxml.html
from urllib.request import urlopen
from lxml.cssselect import CSSSelector
from collections import namedtuple
from itertools import filterfalse
import json
from collections import Counter


sel = CSSSelector('.hp-tabber .hp-tabcontent:not(#Metal_Detector_)')
Location = namedtuple('Location', ('name', 'high_tier_table', 'low_tier_table'))
Drop = namedtuple('Drop', ('name', 'amount', 'chance'))

name_map = {
    'Ascension Rope': 'ASCENSION_ROPE',
    'Blue Goblin Egg': 'GOBLIN_EGG_BLUE',
    'Control Switch': 'CONTROL_SWITCH',
    'Electron Transmitter': 'ELECTRON_TRANSMITTER',
    'FTX 3070': 'FTX_3070',
    'Fine Amber Gemstone': 'FINE_AMBER_GEM',
    'Fine Amethyst Gemstone': 'FINE_AMETHYST_GEM',
    'Fine Jade Gemstone': 'FINE_JADE_GEM',
    'Fine Jasper Gemstone': 'FINE_JASPER_GEM',
    'Fine Ruby Gemstone': 'FINE_RUBY_GEM',
    'Fine Sapphire Gemstone': 'FINE_SAPPHIRE_GEM',
    'Fine Topaz Gemstone': 'FINE_TOPAZ_GEM',
    'Flawed Amber Gemstone': 'FLAWED_AMBER_GEM',
    'Flawed Amethyst Gemstone': 'FLAWED_AMETHYST_GEM',
    'Flawed Jade Gemstone': 'FLAWED_JADE_GEM',
    'Flawed Jasper Gemstone': 'FLAWED_JASPER_GEM',
    'Flawed Ruby Gemstone': 'FLAWED_RUBY_GEM',
    'Flawed Sapphire Gemstone': 'FLAWED_SAPPHIRE_GEM',
    'Flawed Topaz Gemstone': 'FLAWED_TOPAZ_GEM',
    'Flawless Amber Gemstone': 'FLAWLESS_AMBER_GEM',
    'Flawless Amethyst Gemstone': 'FLAWLESS_AMETHYST_GEM',
    'Flawless Jade Gemstone': 'FLAWLESS_JADE_GEM',
    'Flawless Jasper Gemstone': 'FLAWLESS_JASPER_GEM',
    'Flawless Ruby Gemstone': 'FLAWLESS_RUBY_GEM',
    'Flawless Sapphire Gemstone': 'FLAWLESS_SAPPHIRE_GEM',
    'Flawless Topaz Gemstone': 'FLAWLESS_TOPAZ_GEM',
    # 'Gemstone Powder': '',
    'Goblin Egg': 'GOBLIN_EGG',
    'Green Goblin Egg': 'GOBLIN_EGG_GREEN',
    'Jungle Heart': 'JUNGLE_HEART',
    # 'Mithril Powder': '',
    'Oil Barrel': 'OIL_BARREL',
    'Pickonimbus 2000': 'PICKONIMBUS',
    'Prehistoric Egg': 'PREHISTORIC_EGG',
    'Red Goblin Egg': 'GOBLIN_EGG_RED',
    'Robotron Reflector': 'ROBOTRON_REFLECTOR',
    'Rough Amber Gemstone': 'ROUGH_AMBER_GEM',
    'Rough Amethyst Gemstone': 'ROUGH_AMETHYST_GEM',
    'Rough Jade Gemstone': 'ROUGH_JADE_GEM',
    'Rough Jasper Gemstone': 'ROUGH_JASPER_GEM',
    'Rough Ruby Gemstone': 'ROUGH_RUBY_GEM',
    'Rough Sapphire Gemstone': 'ROUGH_SAPPHIRE_GEM',
    'Rough Topaz Gemstone': 'ROUGH_TOPAZ_GEM',
    'Sludge Juice': 'SLUDGE_JUICE',
    'Superlite Motor': 'SUPERLITE_MOTOR',
    'Synthetic Heart': 'SYNTHETIC_HEART',
    'Treasurite': 'TREASURITE',
    'Wishing Compass': 'WISHING_COMPASS',
    'Yellow Goblin Egg': 'GOBLIN_EGG_YELLOW',
    'Yoggie': 'YOGGIE'
}
price_cache = dict()
not_valuable_drops = {'Mithril Powder', 'Gemstone Powder'}

WIKI_URL = 'https://wiki.hypixel.net/Crystal_Hollows'
BAZAAR_API_URL = 'https://api.hypixel.net/skyblock/bazaar'

def get_drops(tbody, chance_multiplier=1.0):
    res = []
    for line in tbody.findall('tr')[2:]:
        cols = [next(filterfalse(str.isspace, col.itertext()), '').strip() \
                for col in line.iterfind('td')]
        name = name_map.get(cols[0], cols[0])
        amounts = cols[1].replace(',', '').split('-')
        avg_amount = sum(map(int, amounts)) / len(amounts)
        chance = float(cols[2][:-1]) / 100 * 4.5 * chance_multiplier
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
        elif drop.name in price_cache:
            price = price_cache[drop.name]
        else:
            price = float(input(f'Input price for {drop.name}: '))
            price_cache[drop.name] = price
        res['coins'] += price * drop.amount * drop.chance
    return res


def main():
    with urlopen(WIKI_URL) as resp:
        wiki_page = lxml.html.parse(resp)
    with urlopen(BAZAAR_API_URL) as resp:
        bazaar_data = json.load(resp)['products']

    coins_counter = Counter()
    mithril_dst_counter = Counter()
    gemstone_dst_counter = Counter()
    content = sel(wiki_page)
    for el in content:
        location_name = el.attrib.get('id')[:-1]
        tables = el.findall('.//div/table/tbody')
        location = Location(location_name, *tables)
        # print(location)
        high_drops = get_drops(location.high_tier_table, chance_multiplier=0.05)
        location_profit = get_profit(high_drops, bazaar_data)
        low_drops = get_drops(location.low_tier_table, chance_multiplier=0.95)
        location_profit += get_profit(low_drops, bazaar_data)
        coins_counter[location_name] = location_profit['coins']
        mithril_dst_counter[location_name] = location_profit['Mithril Powder']
        gemstone_dst_counter[location_name] = location_profit['Gemstone Powder']
    print(f"{'COINS':=^40}")
    print(*coins_counter.most_common(), sep='\n')
    print(f"{'MITHRIL POWDER':=^40}")
    print(*mithril_dst_counter.most_common(), sep='\n')
    print(f"{'GEMSTONE POWDER':=^40}")
    print(*gemstone_dst_counter.most_common(), sep='\n')

if __name__ == "__main__":
    main()

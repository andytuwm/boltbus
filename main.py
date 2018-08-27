import argparse
import dateutil.parser as dparser
import bolt

Boltbus = bolt.BoltAPI()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--date', help='the date to find fares for (ex. 11/25/2015)', required=True)
    parser.add_argument('-s', '--start', help='the starting location (ex. Philadelphia)', required=True)
    parser.add_argument('-e', '--end', help='the ending location (ex. Newark)', required=True)
    parser.add_argument('-t', '--text', action='store_true', help='if this flag is set, send results as a text message')

    args = parser.parse_args()

    leaving = dparser.parse(args.date, fuzzy=True)

    print('== BOLTBUS =====================')
    leavingStr = leaving.strftime('%a %b %d, %Y')
    print('== Departure date: ' + leavingStr)

    # set desired date to search
    Boltbus.set_outbound_date(leaving)

    cities = Boltbus.get_cities()

    startArr = [c for c in cities if args.start in c[1]]
    if len(startArr) == 0:
        citiesStr = ';\n\t'.join([', '.join(city) for city in cities])
        raise ValueError('Start location \"' + args.start + '\" not found in:\n\t' + citiesStr)
    startIndex = cities.index(startArr[0])
    print('== Start:', cities[startIndex][1])

    # set start location
    dests = Boltbus.set_start(startIndex)

    endArr = [c for c in cities if args.end in c[1]]
    if len(endArr) == 0:
        destsStr = ';\n\t'.join([', '.join(dest) for dest in dests])
        raise ValueError('End location \"' + args.end + '\" not found in:\n\t' + destsStr)
    endIndex = dests.index(endArr[0])
    print('== End:', dests[endIndex][1])

    # set end location
    fares = Boltbus.set_dest(endIndex)

    if len(fares) == 0:
        fares = 'None found.'
    # else:
    #     fares = json.dumps(fares, indent=2)
    print('Fares: ', fares)

    print('== end boltbus ==================')

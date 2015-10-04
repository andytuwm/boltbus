from boltbus import BoltbusScraper
import datetime
import json
import argparse
import dateutil.parser as dparser

Boltbus = BoltbusScraper()

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--date', help='the date to find fares for (ex. 11/25/2015)', required=True)
  parser.add_argument('-s', '--start', help='the starting location (ex. Philadelphia)', required=True)
  parser.add_argument('-e', '--end', help='the ending location (ex. Newark)', required=True)

  args = parser.parse_args()

  leaving = dparser.parse(args.date, fuzzy=True)

  print '== BOLTBUS ====================='

  print '== Departure date:', leaving.strftime('%a %b %d, %Y')

  Boltbus.set_outbound_date(leaving)

  cities = Boltbus.get_cities()

  startArr = [c for c in cities if args.start in c[1]]
  if len(startArr) == 0:
    citiesStr = ';\n\t'.join([', '.join(city) for city in cities])
    raise ValueError('Start location \"' + args.start + '\" not found in:\n\t' + citiesStr)
  startIndex = cities.index(startArr[0])
  print '== Start:', cities[startIndex][1]

  dests = Boltbus.set_start(startIndex)

  endArr = [c for c in cities if args.end in c[1]]
  if len(endArr) == 0:
    destsStr = ';\n\t'.join([', '.join(dest) for dest in dests])
    raise ValueError('End location \"' + args.end + '\" not found in:\n\t' + destsStr)
  endIndex = dests.index(endArr[0])
  print '== End:', dests[endIndex][1]

  fares = Boltbus.set_dest(endIndex)
  if len(fares) == 0:
    print '==     No fares found for this date :('
  else:
    print json.dumps(fares, indent=2)

  print '== end boltbus =================='


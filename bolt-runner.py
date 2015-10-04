import datetime
import json
import argparse
import dateutil.parser as dparser
import os
from boltbus import BoltbusScraper
from twilio.rest import TwilioRestClient

Twilio = TwilioRestClient()
Boltbus = BoltbusScraper()

twilio_dest = os.environ.get('MY_PHONE');
twilio_src = os.environ.get('TWILIO_PHONE');

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--date', help='the date to find fares for (ex. 11/25/2015)', required=True)
  parser.add_argument('-s', '--start', help='the starting location (ex. Philadelphia)', required=True)
  parser.add_argument('-e', '--end', help='the ending location (ex. Newark)', required=True)
  parser.add_argument('-t', '--text', action='store_true', help='if this flag is set, send results as a text message')

  args = parser.parse_args()

  leaving = dparser.parse(args.date, fuzzy=True)

  print '== BOLTBUS ====================='
  leavingStr = leaving.strftime('%a %b %d, %Y')
  print '== Departure date: ' + leavingStr

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
    fares = 'None found :('
  else:
    fares = json.dumps(fares, indent=2)
  print 'Fares: ', fares

  if args.text:
    twilio_msg_header = 'Fares from ' + args.start + ' to ' + args.end + ' on ' + leavingStr + ': ' + fares
    print '== Texting results to', twilio_dest
    Twilio.messages.create(to=twilio_dest, from_=twilio_src,
                           body=twilio_msg_header)

  print '== end boltbus =================='



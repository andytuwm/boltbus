from boltbus import BoltbusScraper
import random
import datetime
import json


bus = BoltbusScraper()

leaving = datetime.date.today() + datetime.timedelta(days=1)
print leaving.strftime("%m/%d/%Y")

bus.set_outbound_date(leaving)

cities = bus.get_cities()

start = random.randrange(len(cities))
print "Start", cities[start][1]

dests = bus.set_start(start)

end = random.randrange(len(dests))
print "End", dests[end][1]

fares = bus.set_dest(end)

print json.dumps(fares, indent=2)

from megabus import MegabusScraper
import random
import datetime


bus = MegabusScraper()

cities = bus.get_cities()

start = random.choice(cities.keys())
print "Start", cities[start]

dests = bus.set_start(start)

end = random.choice(dests.keys())
print "End", dests[end]

bus.set_dest(end)

leaving = datetime.date.today() + datetime.timedelta(days=1)
print leaving.strftime("%m/%d/%Y")

bus.set_outbound_date(leaving)

results = bus.get_results()

for result in results:
  print result[0].strftime("%I:%M %p"), result[1].strftime("%I:%M %p"), "$%.2f" % result[2]

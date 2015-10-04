# bus-scraper
Scrape schedule information from ~~Megabus and~~ Boltbus

It looks like Megabus has changed the way they fetch bus routes/fare information,
so this only works for Boltbus for the time being.

### Usage
```
bolt-runner.py [-h] -d DATE -s START -e END [-t]

arguments:
  -h, --help                show this help message and exit
  -d DATE, --date DATE      the date to find fares for (ex. 11/25/2015)
  -s START, --start START   the starting location (ex. Philadelphia)
  -e END, --end END         the ending location (ex. Newark)
  -t, --text                if this flag is set, send results as a text message
```

For example, `bolt-runner.py -d 10/3/2015 -s Philadelphia -e Boston` will find all Boltbus fares and departure/arrival times from Philadelphia to Boston 
for October 3, 2015.

Example output:
```
[
  [
    "$35.00",
    "6:45 AM",
    "1:30 PM"
  ],
  [
    "$35.00",
    "10:15 AM",
    "4:45 PM"
  ],
  [
    "$35.00",
    "1:00 PM",
    "7:45 PM"
  ]
]
```

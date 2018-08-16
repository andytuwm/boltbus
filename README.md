# bus-scraper
Scrape schedule information from Boltbus


### Usage
```
python main.py [-h] -d DATE -s START -e END

arguments:
  -h, --help                show this help message and exit
  -d DATE, --date DATE      the date to find fares for (ex. 11/25/2015)
  -s START, --start START   the starting location (ex. Philadelphia)
  -e END, --end END         the ending location (ex. Newark)
```

For example, `main.py -d 10/3/2015 -s Philadelphia -e Boston` will find all Boltbus fares and departure/arrival times from Philadelphia to Boston 
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

import re
from datetime import datetime
from datetime import timedelta, time
from enum import Enum
import dateutil.parser as dparser

from bolt import BoltAPI
from common import email_helper
from common import config


class Time(Enum):
    MORNING = 1
    NOON = 2
    AFTERNOON = 3


class Day(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class FareFinder:
    def __init__(self, start, end, search_after_week=3, max_price=15, preferred_time=None, preferred_days=None,
                 email_alert=True):
        self.bolt = BoltAPI()

        # initialize values
        self.max_price = float(max_price)
        self.pref_time = preferred_time
        self.email_alert = email_alert

        self.pref_days = {d.value for d in preferred_days} if preferred_days is not None else None

        self.start, self.end = {}, {}
        self.results = []

        # set searching start date
        # defaults to 3 weeks from now
        self.search_date = datetime.today() + timedelta(weeks=search_after_week) - timedelta(days=1)
        self.initial_date = self.search_date
        self._update_to_next_available_day()

        # get city information
        self.cities = self.bolt.get_cities()

        # set start location and get valid destinations
        dests = self.set_start_location(start)
        # set end location
        self.set_end_location(end, dests)

    def search(self):
        print("-- Searching from", self._format_date(self.search_date))

        fares = self.search_fare()

        while len(fares) > 0:
            # filter fare results for each day
            fares = self._filter_fares_by_price(fares)
            fares = self._filter_fares_by_time(fares)
            # save filtered fares to results
            num_found = self._save_fares(fares, self.search_date)
            # print updates to search progress
            print(self._format_date(self.search_date), "Found", num_found, "results.")
            # update day
            self._update_to_next_available_day()
            # search next day's fares
            fares = self.search_fare()

        print("-- Searched to", self._format_date(self.search_date))
        print("Found total", len(self.results), "results.")
        print(self.results)

        if self.email_alert and config.props:
            mail = email_helper.Gmail()
            mail.format_schedule_body(self)
            mail.send_schedule_alert()
            print("Email alert sent.")

    def search_fare(self):
        # sending end location finds fares
        return self.bolt.set_dest(self.end['index'])

    def set_start_location(self, start):
        startArr = [c for c in self.cities if start in c[1]]
        if len(startArr) == 0:
            citiesStr = '\n\t'.join([', '.join(city) for city in self.cities])
            raise ValueError('Start location \"' + start + '\" not found in:\n\t' + citiesStr)
        startIndex = self.cities.index(startArr[0])
        self.start = {
            "name": self.cities[startIndex][1],
            "geocode": self.cities[startIndex][0],
            "index": startIndex
        }
        print('-- Set start location to: ', self.start['name'])
        return self.bolt.set_start(self.start['index'])

    def set_end_location(self, end, dests):
        endArr = [d for d in dests if end in d[1]]
        if len(endArr) == 0:
            destsStr = '\n\t'.join([', '.join(dest) for dest in dests])
            raise ValueError('End location \"' + end + '\" not found in:\n\t' + destsStr)
        endIndex = dests.index(endArr[0])
        self.end = {
            "name": dests[endIndex][1],
            "geocode": dests[endIndex][0],
            "index": endIndex
        }
        print('-- Set end location to: ', self.end['name'])

    def _save_fares(self, fares, date):
        if self.pref_days is None or date.weekday() in self.pref_days:
            for fare in fares:
                self.results.append({
                    "date": self._format_date(date),
                    "price": fare[0],
                    "departure": fare[1],
                    "arrival": fare[2]
                })
        return len(fares)

    def _format_date(self, date):
        return date.strftime('%a %b %d, %Y')

    def _update_to_next_available_day(self):
        update_delta = timedelta(days=1)
        self.search_date += update_delta
        if self.pref_days is not None:
            while not self.search_date.weekday() in self.pref_days:
                self.search_date += update_delta
        self.bolt.set_outbound_date(self.search_date)
        return

    def _filter_fares_by_price(self, fares):
        filtered = []
        for fare in fares:
            price = float(re.search(r'\d{,2}\.\d{,2}', fare[0]).group())
            if price <= self.max_price:
                filtered.append(fare)
        return filtered

    def _filter_fares_by_time(self, fares):
        filtered = []
        if self.pref_time is None:
            return fares

        for fare in fares:
            departure_time = dparser.parse(fare[1]).time()
            if self.pref_time is Time.MORNING:
                if departure_time <= time(hour=12):
                    filtered.append(fare)
            elif self.pref_time is Time.NOON:
                if time(hour=9) < departure_time < time(hour=15):
                    filtered.append(fare)
            elif self.pref_time is Time.AFTERNOON:
                if departure_time >= time(hour=12):
                    filtered.append(fare)
        return filtered

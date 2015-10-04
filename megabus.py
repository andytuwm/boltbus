#!/usr/bin/env python
# -*- coding: utf-8 -*-
# megabus scraper
# 2011-03-05 john@lawnjam.com
# 2011-07-15 ted@shlashdot.org

import datetime
import re
from bs4 import BeautifulSoup
import urllib, urllib2, cookielib

START_URL = 'http://us.megabus.com/default.aspx'
RESULTS_URL = 'http://us.megabus.com/JourneyResults.aspx'
HEADERS = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
        ('Accept-Language', 'en-gb,en;q=0.8,en-us;q=0.5,gd;q=0.3'),
        ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7),*;q=0.7'),]
DEFAULT_VALUES = {
        'UserStatus_ScriptManager1_HiddenField': '',
        '__EVENTTARGET': 'JourneyPlanner$ddlLeavingFrom',
        '__EVENTARGUMENT': '',
        'Welcome1$hdnBasketItemCount': '0',
        'Language1$ddlLanguage': 'en',
        'JourneyPlanner$txtPassengers': '1',
        'JourneyPlanner$txtOutboundDate': '',
        'JourneyPlanner$txtReturnDate': '',
        'JourneyPlanner$txtPromotionalCode': '',
        'JourneyPlanner$DisabledPassengers': 'rdoDisabledPassengersNo',
        '__ASYNCPOST': 'true'
    }


class MegabusScraper(object):
    """Performs a Megabus search.  Such a request is stateful due to
    Megabus's use of ASP.Net, and this class maintains this state, which
    is updated after every POST request.
    """
    locations = {}
    start = None
    dest = None
    outbound_date = None
    possible_dests = {}
    def __init__(self, values={}, opener=None):
        self.values = DEFAULT_VALUES.copy()
        self.values.update(values)
        if opener is None:
            cj = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            opener.addheaders = HEADERS
        self.opener = opener

    def _init_locations_and_viewstate(self, force=False):
        if force or not self.locations:
            self.locations = _init_state(self.opener, self.values)

    def get_cities(self):
        """Returns a dict of names of Megabus stops, keyed by ID.
        These IDs are used to set the start and destination of a Megabus
        search.
        """
        self._init_locations_and_viewstate()
        return self.locations

    def set_start(self, key):
        """Sets the search request's starting city ID.
        
        Returns a dict of possible destinations."""
        self._init_locations_and_viewstate()
        if key not in self.locations:
            raise ValueError("%d is not a valid city ID" % key)
        dests = _set_start(self.opener, self.values, key)
        self.start = key
        self.possible_dests[key] = dests
        return dests

    def set_dest(self, key):
        """Sets the search request's destination city ID."""
        self._init_locations_and_viewstate()
        assert "__VIEWSTATE" in self.values
        if not self.start:
            raise IncompleteRequestError("Need to call set_start first")
        if key not in self.locations:
            raise ValueError("%d is not a valid city ID" % key)
        if key not in self.possible_dests[self.start]:
            raise ValueError("%s cannot be reached from %s" % (
                self.locations[key], self.locations[self.start]))
        _set_dest(self.opener, self.values, key)
        self.dest = key

    def set_outbound_date(self, outbound_date):
        """Sets the search request's outboundure date."""
        if not (self.start and self.dest):
            raise IncompleteRequestError("Start and dest cities must be set first")
        assert "__VIEWSTATE" in self.values
        prev_date = (self.outbound_date
                if self.outbound_date 
                else datetime.date.today())
        _set_outbound_date(self.opener, self.values, outbound_date, prev_date)
        self.outbound_date = outbound_date

    def get_results(self):
        """Performs the search request and returns a list of matching bus
        trips as tuples of (depart_datetime, arrive_datetime, fare).
        """
        if not (self.start or self.dest or self.outbound_date):
            raise IncompleteRequestError("Need to call set_start, set_dest "
                    "and set_outbound_date first")
        return _get_results(self.opener, self.values, self.outbound_date)

def _ajax_to_dict(piped_str):
    """Convert the pipe-separated KV pairs returned by Megabus to a dict"""
    L = piped_str.split('|')
    return dict(zip(L[::2],L[1::2]))


def _make_ajax_request(url, opener, values):
    """Make a Megabus AJAX request"""
    data = urllib.urlencode(values)
    response = opener.open(url, data)

    d = response.read()
    resp_dict = _ajax_to_dict(d)
    # save ASP.NET state junk
    try:
        values['__VIEWSTATE'] = resp_dict['__VIEWSTATE']
        values['__EVENTVALIDATION'] = resp_dict['__EVENTVALIDATION']
    except KeyError:
        raise MegabusException("The request was not completed successfully.")
    return resp_dict


def _init_state(opener, values):
    """Start a Megabus search.
    Returns a dict of possible starting locations and sets the VIEWSTATE
    and EVENTVALIDATION form values.
    """

    response = opener.open(START_URL, None)
    megaSoup = BeautifulSoup(response.read(), 'html.parser')
    viewstate = megaSoup.find(name='input', attrs={'name': '__VIEWSTATE'})['value']
    eventvalidation = megaSoup.find(name='input', attrs={'name': '__EVENTVALIDATION'})['value']
    options = megaSoup.find(name='select', attrs={'name': 'JourneyPlanner$ddlOrigin'}).findAll('option')
    startLocations = {}
    for o in options:
        startLocations[int(o['value'])] = o.find(text=True)
    del startLocations[0]  # index 0 is 'Select origin'
    opener.addheaders.append(('X-MicrosoftAjax', 'Delta=true'))
    values['__EVENTVALIDATION'] = eventvalidation
    values['__VIEWSTATE'] = viewstate
    return startLocations


def _set_start(opener, values, start):
    """Sets the starting location for a search by int ID."""

    values['JourneyPlanner$ddlLeavingFrom'] = start
    values['JourneyPlanner$hdnSelected'] = "%d" % start
    resp_dict = _make_ajax_request(START_URL, opener, values)
    html = resp_dict['JourneyPlanner_UpdatePanel1']

    # parse out destinations for start
    megaSoup = BeautifulSoup(html)
    options = megaSoup.find(name='select', attrs={'name': 'JourneyPlanner$ddlTravellingTo'}).findAll('option')
    endLocations = {}
    for o in options:
        if int(o['value']) > 0:
            endLocations[int(o['value'])] = o.find(text=True)
    return endLocations

def _set_dest(opener, values, dest):
    # values['Welcome1$ScriptManager1'] = 'SearchAndBuy1$upSearchAndBuy|SearchAndBuy1$ddlTravellingTo'
    values['__EVENTTARGET'] = 'JourneyPlanner$ddlTravellingTo'
    values['__LASTFOCUS'] = ''
    values['JourneyPlanner$ddlTravellingTo'] = dest
    values['JourneyPlanner$hdnSelected'] += ",%d" % dest
    resp_dict = _make_ajax_request(START_URL, opener, values)
    return (opener, values)

def _set_outbound_date(opener, values, date, prev_date):
    """Set the request's date. This may require multiple POSTs if the requested
    date is in a different month than the previously requested date, as
    Megabus's calendar widget needs to be advanced to the desired month."""
    datestr = date.strftime("%m/%d/%Y")

    values['__EVENTTARGET'] = 'JourneyPlanner$txtOutboundDate'
    values['__EVENTARGUMENT'] = ''
    values['JourneyPlanner$txtOutboundDate'] = datestr
    values['UserStatus$ScriptManager1'] = 'JourneyPlanner$UpdatePanel1|JourneyPlanner$txtOutboundDate'

    resp_dict = _make_ajax_request(START_URL, opener, values)

def _parse_row(row, depart_date):
    try:
        depart_time_s = row.find(text="Departs").next.strip().replace(u'\xa0', u' ')
        arrive_time_s = row.find(text="Arrives").next.strip().replace(u'\xa0', u' ')
        depart_dt = datetime.datetime.combine(depart_date,
                datetime.datetime.strptime(depart_time_s, u"%I:%M %p").time())
        arrive_dt = datetime.datetime.combine(depart_date,
                datetime.datetime.strptime(arrive_time_s, u"%I:%M %p").time())
        price_re = re.compile("\$\d+\.\d+")
        price_s = row.find(text=price_re)
        price = float(price_re.findall(price_s)[0][1:])
    except (AttributeError, TypeError):
        return None
    return (depart_dt, arrive_dt, price)

def _get_results(opener, values, outbound_date):
    """Load result page and return matching fares as a list of tuples of
    (depart_datetime, arrive_datetime, fare)"""

    params = {
        "originCode": values['JourneyPlanner$ddlLeavingFrom'],
        "destinationCode": values['JourneyPlanner$ddlTravellingTo'],
        "outboundDepartureDate": values['JourneyPlanner$txtOutboundDate'],
        "inboundDepartureDate": "",
        "passengerCount": "1",
        "transportType": "0",
        "concessionCount": "0",
        "nusCount": "0",
        "outboundWheelchairSeated": "0",
        "outboundOtherDisabilityCount": "0",
        "inboundWheelchairSeated": "0",
        "inboundOtherDisabilityCount": "0",
        "outboundPcaCount": "0",
        "inboundPcaCount": "0",
        "promotionCode": "",
        "withReturn": "0",
    }

    url = RESULTS_URL + "?" + urllib.urlencode(params)

    response = opener.open(url, None)
    soup = BeautifulSoup(response.read(), 'html.parser')
    table = soup.find("div", {"class": "JourneyList"})
    if not table:
        raise MegabusException("No trips available.")
    rows = table.findAll("ul", {"class": "journey standard"})
    return filter(None, (_parse_row(row, outbound_date) for row in rows))

class MegabusException(Exception):
    pass

class IncompleteRequestError(Exception):
    pass

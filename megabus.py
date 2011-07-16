#!/usr/bin/env python
# -*- coding: utf-8 -*-
# scrape megabus routes by select departure points one at a time and parsing
# AJAX updates to destinations select box 
# john@lawnjam.com
# also ted@shlashdot.org

import datetime
import re
from BeautifulSoup import BeautifulSoup
import urllib, urllib2, cookielib

START_URL = 'http://us.megabus.com/default.aspx'
RESULTS_URL = 'http://us.megabus.com/JourneyResults.aspx'
HEADERS = [('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
        ('Accept-Language', 'en-gb,en;q=0.8,en-us;q=0.5,gd;q=0.3'),
        ('Accept-Encoding', 'gzip,deflate'),
        ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7),*;q=0.7'),]
DEFAULT_VALUES = {
        'Welcome1_ScriptManager1_HiddenField': '',
        'Welcome1$ScriptManager1': 'SearchAndBuy1$upSearchAndBuy|SearchAndBuy1$ddlLeavingFrom',
        '__EVENTTARGET': 'SearchAndBuy1$ddlLeavingFrom',
        '__EVENTARGUMENT': '',
        'Welcome1$hdnBasketItemCount': '0',
        'Language1$ddlLanguage': 'en',
        'SearchAndBuy1$txtPassengers': '1',
        'SearchAndBuy1$txtConcessions': '0',
        'SearchAndBuy1$txtNUSExtra': '0',
        'SearchAndBuy1$txtOutboundDate': '',
        'SearchAndBuy1$txtReturnDate': '',
        'SearchAndBuy1$txtPromotionalCode': '',
        '__ASYNCPOST': 'true'
        }

class MegabusScraper(object):
    """Encapsulate a Megabus search request, which must be made
    through four separate POST requests (sigh).
    """
    locations = {}
    start = None
    dest = None
    date = None
    possible_dests = {}
    def __init__(self, values={}, opener=None):
        self.values = DEFAULT_VALUES.copy()
        self.values.update(values)
        if opener is None:
            cj = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            opener.addheaders = HEADERS
        self.opener = opener

    def init_viewstate(self):
        self.locations = _init_state(self.opener, self.values)

    def set_start(self, key):
        assert "__VIEWSTATE" in self.values 
        if not self.locations:
            raise IncompleteRequestError("Need to call init_viewstate first")
        if key not in self.locations:
            raise ValueError("%d is not in the list of starting cities" % key)
        dests = _set_start(self.opener, self.values, key)
        self.start = key
        self.possible_dests[key] = dests
        return dests

    def set_dest(self, key):
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

    def set_outbound_date(self, date):
        assert "__VIEWSTATE" in self.values
        _set_outbound_date(self.opener, self.values, date)
        self.date = date

    def get_results(self):
        assert self.start and self.dest and self.date
        _do_search(self.opener, self.values)
        return _get_results(self.opener, self.values, self.date)

def _ajax_to_dict(piped_str):
    """Convert the pipe-separated KV pairs returned by Megabus to a dict"""
    L = piped_str.split('|')
    return dict(zip(L[::2],L[1::2]))


def _make_ajax_request(url, opener, values):
    """Make a Megabus AJAX request"""
    data = urllib.urlencode(values)
    response = opener.open(url, data)
    resp_dict = _ajax_to_dict(response.read())
    # save ASP.NET state junk
    values['__VIEWSTATE'] = resp_dict['__VIEWSTATE']
    values['__EVENTVALIDATION'] = resp_dict['__EVENTVALIDATION']
    return resp_dict


def _init_state(opener, values):
    """Start a Megabus search.  
    Returns a dict of possible starting locations and sets the VIEWSTATE
    and EVENTVALIDATION form values.
    """

    response = opener.open(START_URL, None)
    megaSoup = BeautifulSoup(response.read())
    viewstate = megaSoup.find(name='input', attrs={'name': '__VIEWSTATE'})['value']
    eventvalidation = megaSoup.find(name='input', attrs={'name': '__EVENTVALIDATION'})['value']
    options = megaSoup.find(name='select', attrs={'name': 'SearchAndBuy1$ddlLeavingFrom'}).findAll('option')
    startLocations = {}
    for o in options:
        startLocations[int(o['value'])] = o.find(text=True)
    del startLocations[0] # 0 is "Select"
    opener.addheaders.append(('X-MicrosoftAjax', 'Delta=true'))
    values['__EVENTVALIDATION'] = eventvalidation
    values['__VIEWSTATE'] = viewstate
    return startLocations


def _set_start(opener, values, start):
    """Sets the starting location for a search by int ID."""

    values['SearchAndBuy1$ddlLeavingFrom'] = start
    resp_dict = _make_ajax_request(START_URL, opener, values)
    html = resp_dict['SearchAndBuy1_upSearchAndBuy']

    # parse out destinations for start
    megaSoup = BeautifulSoup(html)
    options = megaSoup.find(name='select', attrs={'name': 'SearchAndBuy1$ddlTravellingTo'}).findAll('option')
    endLocations = {}
    for o in options:
        if int(o['value']) > 0:
            endLocations[int(o['value'])] = o.find(text=True)
    return endLocations

def _set_dest(opener, values, dest):
    values['Welcome1$ScriptManager1'] = 'SearchAndBuy1$upSearchAndBuy|SearchAndBuy1$ddlTravellingTo'
    values['__EVENTTARGET'] = 'SearchAndBuy1$ddlTravellingTo'
    values['__LASTFOCUS'] = ''
    values['SearchAndBuy1$ddlTravellingTo'] = dest
    resp_dict = _make_ajax_request(START_URL, opener, values)
    html = resp_dict['SearchAndBuy1_upSearchAndBuy']
    return (opener, values)

def _set_outbound_date(opener, values, date):
    # 3rd POST: set date
    date_ref = datetime.datetime(2000, 1, 1)
    date_offset = (date - date_ref).days
    values['Welcome1$ScriptManager1'] = 'SearchAndBuy1$upOutboundDate|SearchAndBuy1$calendarOutboundDate'
    values['__EVENTTARGET'] = 'SearchAndBuy1$calendarOutboundDate'
    values['__EVENTARGUMENT'] = date_offset
    resp_dict = _make_ajax_request(START_URL, opener, values)
    html = resp_dict['SearchAndBuy1_upSearchAndBuy']


def _do_search(opener, values):
    """After calling set_start, set_dest and set_outbound_date, perform
    a megabus search."""
    values['Welcome1$ScriptManager1'] = 'SearchAndBuy1$upSearchAndBuy|SearchAndBuy1$btnSearch'
    values['__EVENTTARGET'] = ''
    values['__EVENTARGUMENT'] = ''
    _make_ajax_request(START_URL, opener, values)
    

def _parse_row(row, depart_date):
    try:
        depart_time_s = row.find(text="Departs").next.strip()
        arrive_time_s = row.find(text="Arrives").next.strip()
        depart_dt = datetime.datetime.combine(depart_date,
                datetime.datetime.strptime(depart_time_s, "%I:%M %p").time())
        arrive_dt = datetime.datetime.combine(depart_date,
                datetime.datetime.strptime(arrive_time_s, "%I:%M %p").time())
        price_re = re.compile("\$\d+\.\d+")
        price_s = row.find(text=price_re)
        price = float(price_re.findall(price_s)[0][1:])
    except (AttributeError, TypeError):
        return None
    return (depart_dt, arrive_dt, price)

def _get_results(opener, values, depart_date):
    """Load result page and return matching fares as a list of tuples of
    (depart_datetime, arrive_datetime, fare)"""
    response = opener.open(RESULTS_URL, None)
    soup = BeautifulSoup(response.read())
    table = soup.find("table")
    if not table:
        raise MegabusException("Search expired.")
    rows = table.findAll("tr")[1:]
    return filter(None, (_parse_row(row, depart_date) for row in rows))

class MegabusException(Exception):
    pass

class IncompleteRequestError(Exception):
    pass

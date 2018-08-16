import datetime
import re
from bs4 import BeautifulSoup
import urllib.parse
from urllib.request import build_opener, HTTPCookieProcessor
import http.cookiejar

START_URL = 'https://www.boltbus.com/Default.aspx'
HEADERS = [('User-Agent',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36'),
           ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
           ('Accept-Language', 'en-gb,en;q=0.8,en-us;q=0.5,gd;q=0.3'),
           ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7),*;q=0.7'), ]
DEFAULT_VALUES = {
    '__EVENTTARGET': 'ctl00$cphM$forwardRouteUC$lstRegion$repeater$ctl02$link',
    '__EVENTARGUMENT': '',
    '__VIEWSTATEENCRYPTED': '',
    'ctl00$toolkitScriptManager': '',
    'ctl00$cphM$forwardRouteUC$txtDepartureDate': '',
    'ctl00$cphM$forwardRouteUC$lstPaxCount': '1',
}


class BoltAPI:
    """Performs a Boltbus search.  Such a request is stateful due to
    Bolt Bus' use of ASP.Net, and this class maintains this state, which
    is updated after every POST request.
    """
    locations = {}
    start = None
    dest = None
    outbound_date = None
    possible_dests = {}

    def __init__(self, values={}, opener=None, west=True):
        self.values = DEFAULT_VALUES.copy()
        self.values.update(values)
        # change initial event target depending on which coast is desired.
        # default to west coast.
        if not west:
            self.values['__EVENTTARGET'] = 'ctl00$cphM$forwardRouteUC$lstRegion$repeater$ctl01$link'
        if opener is None:
            cj = http.cookiejar.CookieJar()
            opener = build_opener(HTTPCookieProcessor(cj))
            opener.addheaders = HEADERS
        self.opener = opener

    def _init_locations_and_viewstate(self, force=False):
        if force or not self.locations:
            self.locations = _init_state(self.opener, self.values)

    def get_cities(self):
        """Returns a dict of names of Boltbus stops, keyed by ID.
        These IDs are used to set the start and destination of a Boltbus
        search.
        """
        self._init_locations_and_viewstate()
        return self.locations

    def set_start(self, index):
        """Sets the search request's starting city ID.

        Returns a dict of possible destinations."""
        self._init_locations_and_viewstate()

        if index < 0 or len(self.locations) < index:
            raise ValueError("%d is not a valid city ID" % index)

        self.start = index
        dests = _set_start(self.opener, self.values, index)
        self.possible_dests[index] = dests
        return dests

    def set_dest(self, index):
        """Sets the search request's destination city ID."""
        self._init_locations_and_viewstate()
        assert "__VIEWSTATE" in self.values
        if not self.start:
            raise IncompleteRequestError("Need to call set_start first")

        if index < 0 or len(self.locations) < index:
            raise ValueError("%d is not a valid city ID" % index)

        if index < 0 or len(self.possible_dests[self.start]) < index:
            raise ValueError("%s cannot be reached from %s" % (
                self.locations[index], self.locations[self.start]))
        self.dest = index

        fares = _set_dest(self.opener, self.values, index)
        return fares

    def set_outbound_date(self, outbound_date):
        """Sets the search request's outbound date."""

        self.outbound_date = outbound_date

        datestr = outbound_date.strftime("%m/%d/%Y")

        self.values['ctl00$cphM$forwardRouteUC$txtDepartureDate'] = datestr


def _ajax_to_dict(piped_str):
    """Convert the pipe-separated KV pairs returned by Boltbus to a dict"""

    L = re.split("(?<!\|)\|(?!\|)", piped_str)
    return dict(zip(L[::2], L[1::2]))


def _make_ajax_request(url, opener, values):
    """Make a Boltbus AJAX request"""
    data = urllib.parse.urlencode(values)
    response = opener.open(url, data.encode())

    d_bytes = response.read()
    # decode response body to string
    d = d_bytes.decode("utf-8")
    resp_dict = _ajax_to_dict(d)
    # update ASP.NET state
    try:
        values['__VIEWSTATE'] = resp_dict['__VIEWSTATE']
        values['__EVENTVALIDATION'] = resp_dict['__EVENTVALIDATION']
    except KeyError:
        raise BoltbusException("The request was not completed successfully.")
    return resp_dict


def _init_state(opener, values):
    """Start a Boltbus search.
    Returns a dict of possible starting locations and sets the VIEWSTATE
    and EVENTVALIDATION form values.
    """

    response = opener.open(START_URL, None)
    megaSoup = BeautifulSoup(response.read(), 'html.parser')

    viewstate = megaSoup.find(name='input', attrs={'name': '__VIEWSTATE'})['value']
    eventvalidation = megaSoup.find(name='input', attrs={'name': '__EVENTVALIDATION'})['value']

    opener.addheaders.append(('X-MicrosoftAjax', 'Delta=true'))
    values['__EVENTVALIDATION'] = eventvalidation
    values['__VIEWSTATE'] = viewstate

    resp_dict = _make_ajax_request(START_URL, opener, values)

    megaSoup = BeautifulSoup(resp_dict['ctl00_cphM_updateOrigin'], 'html.parser')

    options = megaSoup.find(name='table', attrs={'id': 'ctl00_cphM_forwardRouteUC_lstOrigin_repeater'}).findAll('td')
    startLocations = []

    GEOCODE_EXPR = re.compile(r"ctl00\$cphM\$forwardRouteUC\$lstOrigin\$repeater\$ctl[0-9]{2}\$geoCode")

    for o in options:
        name = o.find('a').contents[0]
        geoCode = o.find('input', {'name': GEOCODE_EXPR})['value']

        startLocations.append([geoCode, name])

    return startLocations


def _set_start(opener, values, start):
    """Sets the starting location for a search by int ID."""

    start = "%02d" % start

    values['ctl00$toolkitScriptManager'] = \
        'ctl00$cphM$updateOrigin|ctl00$cphM$forwardRouteUC$lstOrigin$repeater$ctl%s$link' % start
    values['__EVENTTARGET'] = 'ctl00$cphM$forwardRouteUC$lstOrigin$repeater$ctl%s$link' % start

    resp_dict = _make_ajax_request(START_URL, opener, values)
    html = resp_dict['ctl00_cphM_updateOrigin']

    # parse out destinations for start
    megaSoup = BeautifulSoup(html, 'html.parser')
    options = megaSoup.find('table', attrs={'id': 'ctl00_cphM_forwardRouteUC_lstDestination_repeater'}).findAll('td')
    endLocations = []

    GEOCODE_EXPR = re.compile(r"ctl00\$cphM\$forwardRouteUC\$lstDestination\$repeater\$ctl[0-9]{2}\$geoCode")

    for o in options:
        name = o.find('a').contents[0]
        geoCode = o.find('input', {'name': GEOCODE_EXPR})['value']

        endLocations.append([geoCode, name])
    return endLocations


def _set_dest(opener, values, dest):
    dest = "%02d" % dest

    values[
        'ctl00$toolkitScriptManager'] = 'ctl00$cphM$updateOrigin|ctl00$cphM$forwardRouteUC$lstDestination$repeater$ctl%s$link' % dest
    values['__EVENTTARGET'] = 'ctl00$cphM$forwardRouteUC$lstDestination$repeater$ctl%s$link' % dest

    resp_dict = _make_ajax_request(START_URL, opener, values)

    html = resp_dict['ctl00_cphM_updateOriginSchedules']

    # parse out destinations for start
    megaSoup = BeautifulSoup(html, 'html.parser')
    table = megaSoup.find('table', attrs={'id': 'ctl00_cphM_forwardScheduleUC_ScheduleGrid'})

    cells = table.findAll('td', attrs={'class': 'faresColumn0'})
    fares = []

    for c in cells:
        price = c.contents[0].strip()
        leaves = c.nextSibling.contents[0].strip()
        arrives = c.nextSibling.nextSibling.contents[0].strip()

        if not price:
            continue

        fares.append([price, leaves, arrives])

    return fares


class BoltbusException(Exception):
    pass


class IncompleteRequestError(Exception):
    pass

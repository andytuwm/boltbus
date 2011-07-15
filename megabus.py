#!/usr/bin/env python
# -*- coding: utf-8 -*-
# scrape megabus routes by select departure points one at a time and parsing
# AJAX updates to destinations select box 
# john@lawnjam.com

import datetime
from BeautifulSoup import BeautifulSoup
import urllib, urllib2, cookielib

START_URL = 'http://us.megabus.com/default.aspx'
RESULTS_URL = 'http://us.megabus.com/JourneyResults.aspx'
HEADERS = [('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
        ('Accept-Language', 'en-gb,en;q=0.8,en-us;q=0.5,gd;q=0.3'),
        ('Accept-Encoding', 'gzip,deflate'),
        ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7),*;q=0.7'),]

def init_page(headers=HEADERS):
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = headers
    response = opener.open(START_URL, None)

    megaSoup = BeautifulSoup(response.read())
    viewstate = megaSoup.find(name='input', attrs={'name': '__VIEWSTATE'})['value']
    eventvalidation = megaSoup.find(name='input', attrs={'name': '__EVENTVALIDATION'})['value']
    options = megaSoup.find(name='select', attrs={'name': 'SearchAndBuy1$ddlLeavingFrom'}).findAll('option')
    startLocations = {}
    for o in options:
        startLocations[int(o['value'])] = o.find(text=True)
    del startLocations[0] # 0 is "Select"
    values = {
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
    opener.addheaders.append(('X-MicrosoftAjax', 'Delta=true'))
    values['__EVENTVALIDATION'] = eventvalidation
    values['__VIEWSTATE'] = viewstate
    return startLocations, (opener, values)


def ajax_to_dict(piped_str):
    L = piped_str.split('|')
    return dict(zip(L[::2],L[1::2]))

# set other form values

def set_start(start, (opener, values)):
    values['SearchAndBuy1$ddlLeavingFrom'] = start
    data = urllib.urlencode(values)
    response = opener.open(START_URL, data)

    # store the received (pipe-separated) data in a list
    resp_dict = ajax_to_dict(response.read())
    html = resp_dict['SearchAndBuy1_upSearchAndBuy']
    # save ASP.NET state junk
    viewstate = resp_dict['__VIEWSTATE']
    eventvalidation = resp_dict['__EVENTVALIDATION']

    megaSoup = BeautifulSoup(html)
    options = megaSoup.find(name='select', attrs={'name': 'SearchAndBuy1$ddlTravellingTo'}).findAll('option')
    endLocations = {}
    for o in options:
        if int(o['value']) > 0:
            #print '"' + startLocations[a] + '","' + o.find(text=True) + '"'
            endLocations[int(o['value'])] = o.find(text=True)
    values['__EVENTVALIDATION'] = eventvalidation
    values['__VIEWSTATE'] = viewstate
    return endLocations

#print endLocations

# 2nd POST: set travelling to
def set_dest(dest, (opener, values)):
    values['Welcome1$ScriptManager1'] = 'SearchAndBuy1$upSearchAndBuy|SearchAndBuy1$ddlTravellingTo'
    values['__EVENTTARGET'] = 'SearchAndBuy1$ddlTravellingTo'
    values['__LASTFOCUS'] = ''
    values['SearchAndBuy1$ddlTravellingTo'] = dest
    data = urllib.urlencode(values)
    response = opener.open(START_URL, data)

    # store the received (pipe-separated) data in a list
    resp_dict = ajax_to_dict(response.read())
    html = resp_dict['SearchAndBuy1_upSearchAndBuy']
    # save ASP.NET state junk
    viewstate = resp_dict['__VIEWSTATE']
    eventvalidation = resp_dict['__EVENTVALIDATION']
    values['__VIEWSTATE'] = viewstate
    values['__EVENTVALIDATION'] = eventvalidation
    return (opener, values)

def set_outbound_date(date, (opener, values)):
    # 3rd POST: set date
    date_ref = datetime.datetime(2000, 1, 1)
    date_offset = (date - date_ref).days
    values['Welcome1$ScriptManager1'] = 'SearchAndBuy1$upOutboundDate|SearchAndBuy1$calendarOutboundDate'
    values['__EVENTTARGET'] = 'SearchAndBuy1$calendarOutboundDate'
    values['__EVENTARGUMENT'] = date_offset
    data = urllib.urlencode(values)
    response = opener.open(START_URL, data)
    resp_dict = ajax_to_dict(response.read())
    print resp_dict
    html = resp_dict['SearchAndBuy1_upSearchAndBuy']
    # save ASP.NET state junk
    viewstate = resp_dict['__VIEWSTATE']
    eventvalidation = resp_dict['__EVENTVALIDATION']
    values['__VIEWSTATE'] = viewstate
    values['__EVENTVALIDATION'] = eventvalidation

def do_search((opener, values)):
    values['Welcome1$ScriptManager1'] = 'SearchAndBuy1$upSearchAndBuy|SearchAndBuy1$btnSearch'
    values['__EVENTTARGET'] = ''
    values['__EVENTARGUMENT'] = ''
    data = urllib.urlencode(values)
    response = opener.open(START_URL, data)
    resp_dict = ajax_to_dict(response.read())
    viewstate = resp_dict['__VIEWSTATE']
    eventvalidation = resp_dict['__EVENTVALIDATION']
    values['__VIEWSTATE'] = viewstate
    values['__EVENTVALIDATION'] = eventvalidation
    pass

def get_results((opener, values)):
# GET the results
    response = opener.open(RESULTS_URL, None)
    return response.read()

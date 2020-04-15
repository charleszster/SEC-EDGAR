#! /Users/chaz/opt/anaconda3/bin/python

import os
import sys
import requests
import re
from bs4 import BeautifulSoup
import json
import time
import datetime

sec_site = 'https://www.sec.gov/'
app = 'cgi-bin/browse-edgar/'
filing_type = '8-K'
save_location = os.path.join(os.path.expanduser('~'), 'Dropbox', 'Investing', 'Scripts', 'SEC EDGAR', 'output')
no_delete_location = os.path.join(os.path.expanduser('~'), 'Dropbox', 'Investing', 'Scripts', 'SEC EDGAR',
                                                                                                        'DO_NOT_DELETE')
last_filing_time_file = 'latest_filing_time.json'
if not os.path.exists(no_delete_location):
    os.mkdir(no_delete_location)
find_name = re.compile(r'Filer')
find_txt_link = re.compile(r'txt')
clean_name = re.compile(r'(.*?) (?:\()')
remove_weird_chars = re.compile(r'[,./\\\']')
find_sub_time = re.compile(r'\d\d:\d\d:\d\d')
find_date = re.compile(r'(\d\d\d\d)-(\d\d)-(\d\d)')
find_time = re.compile(r'(\d\d).(\d\d).(\d\d)')


def get_filing_data(start):
    count = 100
    payload = {'action': 'getcurrent', 'datea': '', 'dateb': '', 'company': '', 'type': filing_type, 'SIC': '',
               'State': '', 'Country': '', 'CIK': '', 'owner': 'include', 'accno': '', 'start': start, 'count': count}
    r = requests.get(sec_site + app, params=payload, timeout=10)
    page = r.text
    soup = BeautifulSoup(page, features='lxml')
    companies_table = soup.find_all('table')[6]
    names = []
    links = []
    times = []
    dates = []
    for tr_s in companies_table.find_all('tr'):
        for a_s in tr_s.find_all('a'):
            for content in a_s.contents:
                if find_name.search(content):
                    #print(content)
                    name = clean_name.search(content)
                    name = remove_weird_chars.sub('', name.groups()[0]).strip()
                    names.append(name)
                    #print(name)
            if find_txt_link.search(a_s['href']):
                links.append(''.join([sec_site, a_s['href']]))
                #print(a_s['href'])
        for td_s in tr_s.find_all('td'):
            found = False
    #        print(td_s.contents)
            for item in td_s.contents:
                if isinstance(item, str) and find_sub_time.search(item):
                    found = True
            if found:
                td_s.contents[2] = td_s.contents[2].replace(':', '.')
                dates.append(td_s.contents[0])
                times.append(td_s.contents[2])
    names_links = [{'company_name': name, 'filing_link': link, 'date': date, 'time': time} for name, link, date, time
                                                                                     in zip(names, links, dates, times)]
    if 'Next 100' in page:
        return names_links, True
    else:
        return names_links, False

def get_filing(company):
    r = requests.get(company['filing_link'], timeout=10)
    filing_stripped_pattern = re.compile(r'(<TEXT>)')
    filing_stripped_span = filing_stripped_pattern.search(r.text)
    filing_stripped = r.text[filing_stripped_span.span()[1] + 1:]
    return filing_stripped

def get_filings_from_list(names_links, last_saved_filing_datetime=None):
    save_count = 0
    for company in names_links:
        filing_datetime = get_datetime(company['date'], company['time'])
        if last_saved_filing_datetime:
            if filing_datetime > last_saved_filing_datetime:
                print('Saving filing for %s' % (company['company_name']))
                filing = get_filing(company)
                save_filing(filing, company)
                save_count += 1
#            else:
#                break
        else:
            print('Saving filing for %s' % (company['company_name']))
            filing = get_filing(company)
            save_filing(filing, company)
            save_count += 1
    return save_count

def save_filing(filing, company):
    text_file = open(os.path.join(save_location, ''.join([company['date'], ' ', company['time'], ' ',
                                                          company['company_name'], ".html"])), "w")
    text_file.write(filing)
    text_file.close()

def save_latest_filing_time(latest_filing_time):
    with open(os.path.join(no_delete_location, 'latest_filing_time.json'), 'w') as f:
        json.dump(latest_filing_time, f)

def get_last_saved_time():
    last_filing_time_fp = os.path.join(no_delete_location, last_filing_time_file)
    try:
        f = open(last_filing_time_fp, 'r')
        last_filing = json.load(f)
        last_saved_filing_datetime = get_datetime(last_filing['date'], last_filing['time'])
    except FileNotFoundError:
        return None
    return last_saved_filing_datetime

def get_datetime(date, time):
    date_parsed = find_date.search(date)
    time_parsed = find_time.search(time)
    latest_filing_datetime = datetime.datetime(int(date_parsed.group(1)), int(date_parsed.group(2)),
                                               int(date_parsed.group(3)), int(time_parsed.group(1)),
                                               int(time_parsed.group(2)), int(time_parsed.group(3)))
    return latest_filing_datetime

def run():
    get_more = True
    names_links = []
    start = 0
    latest_filing_datetime = ''
    save_count = 0
    while get_more:
        print('Getting filing info')
        filing_data, get_more = get_filing_data(start)
        if start == 0:
            latest_filing_time = {'date': filing_data[0]['date'], 'time': filing_data[0]['time']}
            latest_filing_datetime = get_datetime(filing_data[0]['date'], filing_data[0]['time'])
        names_links.extend(filing_data)
        start += 100
    last_saved_filing_datetime = get_last_saved_time()

    if last_saved_filing_datetime:
        if latest_filing_datetime > last_saved_filing_datetime:
            print('Only getting filings since last saved time.')
            save_count = get_filings_from_list(names_links, last_saved_filing_datetime)
        else:
            print('Latest filing time is same or earlier than last saved filing.  Nothing done.  Aborting.')
    else:
        print('Didn\'t have date/time of latest filing; downloading everything.')
        save_count = get_filings_from_list(names_links)
    if save_count and save_count > 0:
        save_latest_filing_time(latest_filing_time)
        print('%i filings saved.' % (save_count))
    else:
        print('No new filings downloaded.')

if __name__ == '__main__':
    run()
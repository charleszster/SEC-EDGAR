#! /Users/chaz/opt/anaconda3/bin/python

import os
import requests
import re
from bs4 import BeautifulSoup
import time

sec_site = 'https://www.sec.gov/'
app = 'cgi-bin/browse-edgar/'
filing_type = '8-K'
save_location = os.path.join(os.path.expanduser('~'), 'Downloads')
find_name = re.compile(r'Filer')
find_txt_link = re.compile(r'txt')
clean_name = re.compile(r'(.*?) (?:\()')
remove_weird_chars = re.compile(r'[,./\\\']')
find_sub_time = re.compile(r'\d\d:\d\d:\d\d')

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
                times.append(''.join([td_s.contents[0], ' ', td_s.contents[2]]))
    names_links = [{'company_name': name, 'filing_link': link, 'time': time} for name, link, time in zip(names, links,
                                                                                                                 times)]
    if 'Next 100' in page:
        return names_links, True
    else:
        return names_links, False

def get_filings(company):
    r = requests.get(company['filing_link'], timeout=10)
    filing_stripped_pattern = re.compile(r'(<TEXT>)')
    filing_stripped_span = filing_stripped_pattern.search(r.text)
    filing_stripped = r.text[filing_stripped_span.span()[1] + 1:]
    return filing_stripped

def save_filing(filing, company):
    text_file = open(os.path.join(save_location, ''.join([company['time'], ' ', company['company_name'], ".html"])),
                                                                                                                 "w")
    text_file.write(filing)
    text_file.close()

def run():
    get_more = True
    names_links = []
    start = 0
    while get_more:
        print('Getting filing info')
        filing_data, get_more = get_filing_data(start)
        names_links.extend(filing_data)
        start += 100
        time.sleep(2)
    for company in names_links:
        print('Saving filing for %s' % (company['company_name']))
        filing = get_filings(company)
        save_filing(filing, company)
    print('%i filings saved.' % (len(names_links)))

if __name__ == '__main__':
    run()
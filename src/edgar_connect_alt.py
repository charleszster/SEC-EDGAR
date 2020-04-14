#! /Users/chaz/opt/anaconda3/bin/python

import os
import sys
import requests
import re
import pdfkit
from bs4 import BeautifulSoup

sec_site = 'https://www.sec.gov'
save_location = os.path.join(os.path.expanduser('~'), 'Dropbox', 'Investing', 'Scripts', 'SEC EDGAR', 'output')

def get_links(r, date_final):
    links_names = []
    for line in r.text.splitlines():
        if date_final in line:
            filing_nums_pattern = re.compile(r'/Archives/edgar/data/(\d+)/(\d+)-(\d+)-(\d+)-index.html')
            filing_nums = filing_nums_pattern.search(line)
            file_num = filing_nums.group(2) + filing_nums.group(3) + filing_nums.group(4)
            text_filing_link = ''.join([sec_site, '/Archives/edgar/data/', filing_nums.group(1), '/', file_num, '/',
                                        filing_nums.group(2), '-', filing_nums.group(3), '-', filing_nums.group(4),
                                        '.txt'])

            company_name_search = re.compile(r'</a>')
            company_name = company_name_search.split(line)[-1].strip()
            company_name_clean_pattern = re.compile(r'[,./\\\']')
            company_name_clean = company_name_clean_pattern.sub('', company_name).title()
            links_names.append({'link': text_filing_link, 'company_name': company_name_clean})
    return links_names

def get_filing(filing):
    r = requests.get(filing['link'], timeout=10)
    filing_stripped_pattern = re.compile(r'(<TEXT>)')
    filing_stripped_span = filing_stripped_pattern.search(r.text)
    filing_stripped = r.text[filing_stripped_span.span()[1]+1:]
    return filing_stripped

def save_filing(filing, filing_stripped):
    text_file = open(''.join([filing['company_name'], ".html"]), "w")
    text_file.write(filing_stripped)
    text_file.close()

payload = {'q1': '0', 'q2': '4', 'q3': '0'}
r = requests.get(sec_site + '/cgi-bin/current', params=payload, timeout=10)
page = r.text
date_find_pattern = re.compile('The total number of matches for \d{4}-\d{2}-\d{2}', re.MULTILINE)
date_find = date_find_pattern.findall(page)

date_pattern = re.compile('(\d{4})-(\d{2})-(\d{2})')
date_orig = date_pattern.search(date_find[0])
date_final = date_orig.group(2) + '-' + date_orig.group(3) + '-' + date_orig.group(1)

links_names = get_links(r, date_final)
for filing in links_names:
    print('Downloading ' + filing['company_name'])
    filing_stripped = get_filing(filing)
    save_filing(filing, filing_stripped)
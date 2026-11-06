#!/usr/bin/env python3
"""Read-only SEC snapshot downloader; same source selection as the supplied K1 script.

The numerical comparison logic lives in spike.py and is unchanged. New live
responses go into a separate directory so the reference snapshot remains intact.
Python standard library only. Maximum request rate is under two per second.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir', type=Path, default=ROOT / 'data_live')
parser.add_argument('--refresh', action='store_true', help='Fetch again into data_live; preserve reference data/')
parser.add_argument('--max-retries', type=int, default=2)
args = parser.parse_args()
DATA = args.data_dir
if DATA.resolve() == (ROOT / 'data').resolve():
    parser.error('The reference data/ directory is immutable. Choose a different output directory.')
UA = os.environ.get('SEC_USER_AGENT', '').strip()
if not re.search(r'[^\s<>@]+@[^\s<>@]+\.[A-Za-z]{2,}', UA) or 'example.com' in UA:
    parser.error('Set SEC_USER_AGENT with your project name and real contact email. A placeholder is not accepted.')
DATA.mkdir(parents=True, exist_ok=True)
COMPANIES = {'NVDA': 1045810, 'INTC': 50863, 'QCOM': 804328, 'AVGO': 1730168,
             'MU': 723125, 'AMD': 2488, 'TXN': 97476, 'ADI': 6281, 'MCHP': 827054,
             'NXPI': 1413447, 'AAPL': 320193, 'MSFT': 789019}
manifest = []


def get(url, name):
    p = DATA / (name + '.gz')
    if p.exists() and not args.refresh:
        raw = gzip.decompress(p.read_bytes())
        event = {'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'url': url, 'status': 'CACHE', 'bytes': len(raw),
                 'sha256': hashlib.sha256(raw).hexdigest(), 'path': p.name,
                 'note': 'Cache hit is not a new HTTP request; original collection date is not inferred.'}
        manifest.append(event)
        print(json.dumps(event))
        return raw
    for attempt in range(args.max_retries + 1):
        time.sleep(0.6)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
                status = response.status
                headers = {k: v for k, v in response.headers.items()
                           if k.lower() in ['content-type', 'last-modified', 'date']}
            p.write_bytes(gzip.compress(raw, mtime=0))
            event = {'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'url': url, 'status': status, 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest(), 'path': p.name, 'headers': headers}
            manifest.append(event)
            print(json.dumps(event))
            return raw
        except urllib.error.HTTPError as exc:
            # Do not store arbitrary server error pages, which can contain request identifiers.
            event = {'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'url': url, 'status': exc.code, 'attempt': attempt + 1}
            manifest.append(event)
            print(json.dumps(event))
            if exc.code not in [429, 500, 502, 503, 504] or attempt == args.max_retries:
                return None
            time.sleep(min(2 ** (attempt + 1), 8))
        except Exception as exc:
            event = {'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'url': url, 'exception': type(exc).__name__, 'message': str(exc)}
            manifest.append(event)
            print(json.dumps(event))
            return None


for sym, cik in COMPANIES.items():
    print('\nCOMPANY', sym, cik)
    get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json', f'{sym}_companyfacts.json')
    raw = get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json', f'{sym}_submissions.json')
    if raw and sym not in ['AAPL', 'MSFT']:
        recent = json.loads(raw)['filings']['recent']
        for i, form in enumerate(recent['form']):
            if form in ['10-K', '20-F']:
                acc = recent['accessionNumber'][i]
                doc = recent['primaryDocument'][i]
                get(f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace("-", "")}/{doc}',
                    f'{sym}_annual.htm')
                break
get('https://data.sec.gov/api/xbrl/frames/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/USD/CY2024Q4.json',
    'frame_revenue_CY2024Q4.json')
(DATA / 'http_manifest.json').write_text(json.dumps({
    'user_agent': '[CONFIGURED THROUGH SEC_USER_AGENT; contact redacted from export]',
    'requests': manifest}, indent=2) + '\n')
print('DOWNLOAD_FINISHED', 'records', len(manifest))
if any(item.get('status') not in [200, 'CACHE'] for item in manifest):
    raise SystemExit(1)

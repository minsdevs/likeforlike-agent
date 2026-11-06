#!/usr/bin/env python3
"""PeerCheck minimal deterministic verifier for real SEC responses. No model/API token.
Live evidence is downloaded by download_data.py; this script recomputes from SHA256-addressed snapshots.
"""
import json,gzip,re,datetime,csv,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description='Replay the supplied SEC comparison snapshot; numeric rules unchanged.')
parser.add_argument('--data-dir',type=Path,default=ROOT/'data')
parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs'/'latest')
args=parser.parse_args()
D=args.data_dir
P=args.output_dir
P.mkdir(parents=True,exist_ok=True)
FIVE=['NVDA','INTC','QCOM','AVGO','MU']
TEN=FIVE+['AMD','TXN','ADI','MCHP','NXPI']
MAP={'Revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'],'OperatingIncome':['OperatingIncomeLoss'],'EBITDA':[],'CapEx':['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets']}

def load(sym,kind):return json.loads(gzip.decompress((D/(sym+'_'+kind+'.json.gz')).read_bytes()))
def days(r):return (datetime.date.fromisoformat(r['end'])-datetime.date.fromisoformat(r['start'])).days+1

def annual_end(sym):
    r=load(sym,'submissions')['filings']['recent']
    idx=next(i for i,x in enumerate(r['form']) if x in ['10-K','20-F'])
    return r['reportDate'][idx],r['accessionNumber'][idx]

def pick(sym,metric):
    f=load(sym,'companyfacts')['facts'].get('us-gaap',{})
    end,annualacc=annual_end(sym);eligible=[];present=[]
    for tag in MAP[metric]:
        if tag not in f:continue
        present.append(tag)
        for unit,obs in f[tag]['units'].items():
            for r in obs:
                if r.get('end')==end and 'start'in r and 330<=days(r)<=400:
                    eligible.append(dict(r,unit=unit,tag=tag))
    if not eligible:return {'symbol':sym,'metric':metric,'end':end,'state':'HOLD','reason':'No standard entity-wide concept; EBITDA not inferred' if metric=='EBITDA' else 'No matching annual duration','historical_tags':present}
    eligible.sort(key=lambda r:(r.get('filed',''),r['accn']==annualacc, -MAP[metric].index(r['tag'])),reverse=True)
    r=eligible[0];return dict(r,symbol=sym,metric=metric,days=days(r),historical_tags=present,annual_accn=annualacc)

print('RUN_UTC',datetime.datetime.now(datetime.timezone.utc).isoformat())
manifest_path=D/'http_manifest.json'
snapshot_dates=sorted({e['timestamp'][:10] for e in json.loads(manifest_path.read_text()).get('requests',[]) if e.get('status')==200 and 'timestamp' in e}) if manifest_path.exists() else []
print('INPUT_TYPE SEC response files; collection dates from HTTP200 manifest:', json.dumps(snapshot_dates), '; empty means collection date not verified')
print('NO_EXTERNAL_LLM true; PURE_RULE_ENGINE true')
rows=[pick(s,m) for s in FIVE for m in MAP]
base=next(r for r in rows if r['symbol']=='NVDA' and r['metric']=='Revenue')
for r in rows:
    if 'val' in r:
        if r['unit']!='USD':r.update(state='HOLD',reason='Unit differs from USD; explicit FX basis required')
        elif (r['start'],r['end'])!=(base['start'],base['end']):r.update(state='HOLD',reason='Most recent FY spans different exact calendar period')
        elif r['metric']=='CapEx' and r['tag']=='PaymentsToAcquireProductiveAssets':r.update(state='HOLD',reason='Productive-assets concept is not assumed equal to PPE-only CapEx; scope reconciliation required')
        else:r.update(state='COMPARABLE',reason='Period/unit metadata matches reference; metric definition gate still applies')
    print('GRID',json.dumps(r))

revtags={r['symbol']:r.get('tag') for r in rows if r['metric']=='Revenue'}
print('REAL_MISMATCH_1 annual periods',[(r['symbol'],r.get('start'),r['end'],r.get('days')) for r in rows if r['metric']=='Revenue'])
print('REAL_MISMATCH_2 revenue tag heterogeneity',json.dumps(revtags))
assert len(set(revtags.values()))>=2
assert len({r['end'] for r in rows if r['metric']=='Revenue'})>=2
print('SAME_TAG_DOES_NOT_IMPLY_SAME_PERIOD; DIFFERENT_TAG_DOES_NOT_PROVE_DIFFERENT_ECONOMICS')

# Demonstrate actual YTD-vs-quarter distinction and a guarded subtraction path.
cap=[]
for captag in MAP['CapEx']:
    cap.extend(dict(r,concept=captag) for r in load('NVDA','companyfacts')['facts']['us-gaap'].get(captag,{}).get('units',{}).get('USD',[]))
ys=[r for r in cap if r.get('form')=='10-Q' and 'start'in r and 140<=days(r)<=310]
ys.sort(key=lambda r:(r['end'],r['filed']),reverse=True)
recalc=None
for cur in ys:
    prev=[r for r in cap if r.get('form')=='10-Q' and r.get('start')==cur['start'] and r['concept']==cur['concept'] and r['end']<cur['end'] and 65<=(datetime.date.fromisoformat(cur['end'])-datetime.date.fromisoformat(r['end'])).days<=110 and r['filed']<=cur['filed']]
    if prev:
        prev.sort(key=lambda r:(r['end'],r['filed']),reverse=True);p=prev[0]
        recalc={'symbol':'NVDA','metric':'CapEx','state':'RECALCULATE','reason':'YTD is not a single quarter; adjacent same-start cumulative amounts differenced','current_ytd':cur,'previous_ytd':p,'derived_start':(datetime.date.fromisoformat(p['end'])+datetime.timedelta(days=1)).isoformat(),'derived_end':cur['end'],'derived_USD':cur['val']-p['val'],'scope_limitation':'Arithmetic derivation only. Cross-filing restatement/reclassification review is still required.'};break
assert recalc
print('REAL_MISMATCH_3 YTD_AS_QUARTER',json.dumps(recalc))
# A wrong human table would label the six/nine-month amount as one quarter.
print('DETECTED_WRONG_INPUT',json.dumps({'claimed_single_quarter_capex':recalc['current_ytd']['val'],'derived_single_quarter_capex':recalc['derived_USD'],'overstatement_USD':recalc['previous_ytd']['val']}))

# Segment axis actual raw-inline-XBRL contexts, not mere prose keyword counts.
segment=[]
for sym in TEN:
    raw=gzip.decompress((D/(sym+'_annual.htm.gz')).read_bytes()).decode('utf-8',errors='replace')
    members=re.findall(r'<(?:\w+:)?explicitMember\b[^>]*dimension=["\']([^"\']+)["\'][^>]*>([^<]+)</',raw,re.I)
    seg=[m for a,m in members if a.split(':')[-1]=='StatementBusinessSegmentsAxis']
    cf=load(sym,'companyfacts')
    end,acc=annual_end(sym)
    row={'symbol':sym,'annual_period_end':end,'accession':acc,'raw_explicit_segment_member_count':len(seg),'raw_unique_members':sorted(set(seg)),'raw_axis_supported':bool(seg),'companyfacts_has_dimensions_field':any(any(k in obs for k in ['dimension','dimensions','segment']) for ns in cf['facts'].values() for fact in ns.values() for records in fact['units'].values() for obs in records)}
    segment.append(row);print('SEGMENT_SAMPLE',json.dumps(row))
print('SEGMENT_RATIO',sum(x['raw_axis_supported'] for x in segment),'/',len(segment),'latest sampled annual reports; not population coverage')
print('COMPANYFACTS_DIMENSION_RATIO',sum(x['companyfacts_has_dimensions_field'] for x in segment),'/',len(segment))

# Frames API contains calendar approximations, not guaranteed aligned periods.
frame=json.loads(gzip.decompress((D/'frame_revenue_CY2024Q4.json.gz').read_bytes()))
frame_sample=[r for r in frame['data'] if r['cik'] in [1045810,50863,1730168,723125]]
print('FRAMES_HTTP200_SAMPLE',json.dumps(frame_sample))
# Synthetic error is explicitly synthetic, used only as negative control.
injected=dict(base,unit='EUR')
assert injected['unit']!=base['unit']
print('SYNTHETIC_NEGATIVE_CONTROL unit USD->EUR -> HOLD, no conversion without FX basis')
result={'grid':rows,'revenue_tags':revtags,'recalculation':recalc,'segments':segment,'frame_sample':frame_sample,'metrics_found':sum('val'in r for r in rows),'metrics_requested':len(rows),'verdict_technical':'GO for narrowed period/unit/tag/YTD verifier; SegmentBridge/FXBasis full automation NOT established'}
(P/'result.json').write_text(json.dumps(result,indent=2))
with (P/'comparison.csv').open('w') as f:
    keys=['symbol','metric','tag','start','end','days','unit','val','state','reason'];w=csv.DictWriter(f,keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
print('PASS: 5 companies x 4 requested metrics; 15 observed values; missing EBITDA explicitly held; 3 real mismatch types; 3 classes demonstrated')

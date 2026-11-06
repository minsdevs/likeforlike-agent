#!/usr/bin/env python3
"""Verify snapshot hashes and full replay equality against the supplied K1 outputs."""
import argparse
import csv
import datetime
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs' / 'replay')
args = parser.parse_args()
out = args.output_dir
out.mkdir(parents=True, exist_ok=True)
manifest = json.loads((ROOT / 'data' / 'http_manifest.json').read_text())
hash_checks = []
for item in manifest['requests']:
    relative = Path(item['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise SystemExit('Unsafe manifest path')
    raw = gzip.decompress((ROOT / relative).read_bytes())
    hash_checks.append({'file': relative.name, 'bytes_match': len(raw) == item['bytes'],
                        'sha256_match': hashlib.sha256(raw).hexdigest() == item['sha256']})

process = subprocess.run([sys.executable, str(ROOT / 'src' / 'spike.py'),
                          '--data-dir', str(ROOT / 'data'), '--output-dir', str(out)],
                         text=True, capture_output=True)
(out / 'run.log').write_text(process.stdout)
if process.stderr:
    # Do not ship environment-specific tracebacks with absolute paths.
    (out / 'error_summary.txt').write_text('Replay failed; inspect the local terminal.\n')
original = json.loads((ROOT / 'sample_results' / 'original' / 'result.json').read_text())
replayed = json.loads((out / 'result.json').read_text()) if (out / 'result.json').exists() else None


def csv_rows(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


csv_equal = (out / 'comparison.csv').exists() and csv_rows(out / 'comparison.csv') == csv_rows(ROOT / 'sample_results' / 'original' / 'comparison.csv')
result = {'run_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'execution': 'offline replay of supplied snapshot; no network or LLM call',
          'snapshot_files_checked': len(hash_checks),
          'snapshot_sha256_all_match': all(x['sha256_match'] and x['bytes_match'] for x in hash_checks),
          'exit_code': process.returncode, 'full_result_json_equal': replayed == original,
          'comparison_csv_rows_equal': csv_equal, 'hash_checks': hash_checks}
result['PASS'] = result['snapshot_sha256_all_match'] and process.returncode == 0 and result['full_result_json_equal'] and csv_equal
(out / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({key: value for key, value in result.items() if key != 'hash_checks'}, ensure_ascii=False, indent=2))
raise SystemExit(0 if result['PASS'] else 1)

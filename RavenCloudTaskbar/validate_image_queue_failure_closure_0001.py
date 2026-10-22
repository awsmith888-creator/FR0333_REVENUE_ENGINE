"""Bounded offline audit of evidence binding and append-only index integration."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
record = json.loads((ROOT / 'fr0333_image_queue_failure_closure_0001.json').read_text())
index = json.loads((ROOT / 'fr0333_golden_chain_index_0001.json').read_text())
if not record['closure']['live_provider_delivery'] == 'HOLD_NOT_REEXECUTED':
    raise ValueError('evidence validation failed')
if not record['verification']['current_tests']['evidence_class'] == 'SIMULATED_FIXTURE':
    raise ValueError('evidence validation failed')
if not record['verification']['historical_reproduction']['exit_code'] == 1:
    raise ValueError('evidence validation failed')
if not record['verification']['current_tests']['exit_code'] == 0:
    raise ValueError('evidence validation failed')
if not record['anti_loop']['automatic_provider_calls'] is False:
    raise ValueError('evidence validation failed')
if not record['anti_loop']['automatic_workflow_reruns'] is False:
    raise ValueError('evidence validation failed')
if not record['certificate_type'] == 'SELF_ISSUED_VERIFICATION_RECORD_NOT_EXTERNAL_ATTESTATION':
    raise ValueError('evidence validation failed')
for item in record['source_files']:
    data = (ROOT.parent / item['path']).read_bytes()
    if not hashlib.sha256(data).hexdigest() == item['sha256']:
        raise ValueError(item['path'])
    git_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest()
    if not git_blob == item['git_blob_sha']:
        raise ValueError(item['path'])
entries = index['entries']
if not len({e['index'] for e in entries}) == len(entries):
    raise ValueError('evidence validation failed')
if not len({e['identifier'] for e in entries}) == len(entries):
    raise ValueError('evidence validation failed')
matches = [e for e in entries if e['identifier'] == record['identifier']]
if not (len(matches) == 1 and matches[0]['index'] == '0.8'):
    raise ValueError('evidence validation failed')
if not matches[0]['state'] == 'DIAGNOSIS_VERIFIED_LOCAL_TEST_PASS_LIVE_REVERIFICATION_HOLD':
    raise ValueError('evidence validation failed')
print('PASS: source hashes / evidence boundaries / bounded rechecks / unique index')

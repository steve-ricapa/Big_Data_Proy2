"""Read cloud resource metadata only; never access secret versions."""
import json
from datetime import UTC, datetime
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

project = 'proyectobigdata2-514216'
out = {'at': datetime.now(UTC).isoformat()}
creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
with AuthorizedSession(creds) as s:
    def get(url, **params):
        r = s.get(url, params=params, timeout=60)
        if not r.ok:
            return {'http_status': r.status_code}
        return r.json()

    buckets = get('https://storage.googleapis.com/storage/v1/b', project=project)
    out['buckets'] = [{k: b.get(k) for k in ('name','location','storageClass','iamConfiguration','lifecycle','softDeletePolicy')} for b in buckets.get('items', [])]
    out['storage_bytes'] = {}
    for bucket in out['buckets']:
        name = bucket['name']
        if not name.startswith(project + '-ti-dev-'):
            continue
        objects = get(f'https://storage.googleapis.com/storage/v1/b/{name}/o', fields='items(name,size,metadata,updated),nextPageToken', maxResults=1000)
        out['storage_bytes'][name] = sum(int(o['size']) for o in objects.get('items', []))
        if name.endswith('processed'):
            out['backup_objects'] = [o for o in objects.get('items', []) if o['name'].startswith('backups/')]
    out['repositories'] = get(f'https://artifactregistry.googleapis.com/v1/projects/{project}/locations/us-central1/repositories')
    secrets = get(f'https://secretmanager.googleapis.com/v1/projects/{project}/secrets')
    out['secrets_metadata'] = [{'name': v['name'], 'createTime': v.get('createTime')} for v in secrets.get('secrets', [])]
    alerts = get(f'https://monitoring.googleapis.com/v3/projects/{project}/alertPolicies')
    out['monitoring_alerts'] = [{'name': a['name'], 'enabled': a.get('enabled'), 'displayName': a.get('displayName')} for a in alerts.get('alertPolicies', [])]
    billing = get(f'https://cloudbilling.googleapis.com/v1/projects/{project}/billingInfo')
    out['billing'] = billing
    if billing.get('billingAccountName'):
        out['budget_list'] = get(f'https://billingbudgets.googleapis.com/v1/{billing["billingAccountName"]}/budgets')
Path('docs/evidence/acceptance/gcp_inventory.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps({'buckets': len(out['buckets']), 'secrets': len(out['secrets_metadata']), 'alerts': len(out['monitoring_alerts']), 'budget_list': out.get('budget_list')}))

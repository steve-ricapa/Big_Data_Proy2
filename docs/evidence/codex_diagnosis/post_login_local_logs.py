"""Read Codex SQLite logs read-only; emit classifications, not raw auth bodies."""
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

db=Path.home()/'.codex/logs_2.sqlite'
c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
rows=c.execute("SELECT ts,level,target,feedback_log_body FROM logs WHERE ts>=? AND (target LIKE ? OR target LIKE ?) ORDER BY id",(1794415200,'%mcp%','%oauth%')).fetchall()
records=[]
for ts,level,target,body in rows:
 body=body or ''
 mentioned=('big_data_ii_-_threat_intelligence' in body)
 if not mentioned:continue
 event=None
 if 'Invalid scopes: openid ti:read offline_access' in body:event='refresh_rejected_invalid_scope_openid_ti_read_offline_access'
 elif 'omitting pending optional MCP server' in body:event='target_omitted_from_pending_optional_catalog'
 elif 'Auth required' in body and 'initialize' in body:event='initialize_requires_authentication'
 elif 'MCP server startup failed' in body:event='target_startup_failed'
 if event:
  records.append({'at':datetime.fromtimestamp(ts,UTC).isoformat(),'level':level,'target':target,'event':event,'desktop_client_span':'app_server.client_name="Codex Desktop"' in body})
c.close()
out={'at':datetime.now(UTC).isoformat(),'database':str(db),'read_only':True,'raw_messages_saved':False,'events':records[-60:]}
Path(__file__).with_name('post_login_local_logs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'events':len(out['events']),'classifications':sorted({r['event'] for r in records})},indent=2))

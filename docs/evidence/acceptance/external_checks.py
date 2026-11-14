"""Re-run existing read-only external checks, preserving old evidence."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / 'scripts'))
kind = sys.argv[1]
sources = {'http': 'verify_cloud_http.py', 'mcp': 'verify_cloud_mcp.py', 'browser': 'cloud_dashboard_shots.py'}
source = (root / 'scripts' / sources[kind]).read_text(encoding='utf-8')
for old, new in {
    'docs/evidence/gcp_https_validation.json': 'docs/evidence/acceptance/http.json',
    'docs/evidence/gcp_mcp_protocol_validation.json': 'docs/evidence/acceptance/mcp.json',
    'docs/evidence/gcp_dashboard_browser_validation.json': 'docs/evidence/acceptance/browser.json',
    'OUT = ROOT / "docs/evidence/screenshots"': 'OUT = ROOT / "docs/evidence/acceptance/screenshots"',
}.items():
    source = source.replace(old, new)
if kind == 'browser':
    source = source.replace('            shot = await send', '            if view == "Graph Intelligence":\n                time.sleep(10)\n                result["graph_dom"] = await evaluate("[...document.querySelectorAll(\'[data-testid]\')].filter(e=>e.getAttribute(\'data-testid\').toLowerCase().includes(\'graph\')).map(e=>({testid:e.getAttribute(\'data-testid\'),svg:e.querySelectorAll(\'svg\').length,text:e.textContent.slice(0,200)}))")\n            shot = await send')
exec(compile(source, str(root / 'scripts' / sources[kind]), 'exec'), {'__name__': '__main__', '__file__': str(root / 'scripts' / sources[kind])})

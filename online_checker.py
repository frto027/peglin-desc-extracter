import subprocess
import pathlib
import sys
import chevron
import pytz
import json

from datetime import datetime
now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y年%m月%d日 %H:%M")

def buffered(path, default = None):
    path = pathlib.Path('buffers') / path
    if path.exists():
        with path.open('r',encoding='utf8') as f:
            return json.loads(f.read())
    else:
        return default

term_maps_online_config = buffered('term_maps_online.json')
term_maps_online_result_cached = buffered('term_maps_online_result.json')
import trans_reader
term_maps_online_result = trans_reader.GetDictionary(term_maps_online_config["Google_WebServiceURL"], term_maps_online_config["Google_SpreadsheetKey"])

ONLINE_VERSION_CACHED = term_maps_online_result_cached["version"]
ONLINE_VERSION = term_maps_online_result["version"]

old = term_maps_online_result_cached["ret"]
new = term_maps_online_result["ret"]

need_update_cn_text = False


modified = []

for k in new:
    if not k in old:
        modified.append({
            'new':True,
            'key':k,
            'text':new[k] if new[k] != '' else '<空值>',
        })
        if new[k] != '':
            need_update_cn_text = True
    elif old[k] != new[k]:
        need_update_cn_text = True
        modified.append({
            'update':True,
            'key':k,
            'old-text':old[k] if old[k] != '' else '<空值>',
            'text':new[k] if new[k] != '' else '<空值>',
        })        

with open('docs/online_check.html','w',encoding='utf8') as f:
    with open('templates/online_check.html.mustache','r',encoding='utf8') as template:
        f.write(chevron.render(template,{
            'online_cache_version':ONLINE_VERSION_CACHED,
            'online_version':ONLINE_VERSION,
            'report_date': now,
            'need_update': need_update_cn_text,
            'version_consist':ONLINE_VERSION_CACHED == ONLINE_VERSION,
            'modified':modified,
            'has_modified':len(modified) > 0,
            }))

if need_update_cn_text:
    print("need auto update, run orb.py...")
    subprocess.call((sys.executable, 'orb.py', '-u'))
    print("auto update end.")

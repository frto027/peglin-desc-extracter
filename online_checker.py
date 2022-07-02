from datetime import date
import pathlib
import chevron
import pytz
import json

from datetime import datetime
from zoneinfo import ZoneInfo
now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y年%m月%d日 %H:%S")

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

with open('docs/online_check.html','w',encoding='utf8') as f:
    with open('templates/online_check.html.mustache','r',encoding='utf8') as template:
        f.write(chevron.render(template,{
            'online_cache_version':ONLINE_VERSION_CACHED,
            'online_version':ONLINE_VERSION,
            'report_date': now,
            'need_update':ONLINE_VERSION_CACHED != ONLINE_VERSION,
            }))



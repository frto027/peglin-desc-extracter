from urllib.request import urlopen
import re
def GetDictionary(Google_WebServiceURL, Google_SpreadsheetKey):
    lang_keyword = '[zh-CN]'
    CurrentVersion = 0
    ret = dict()

    url = f'{Google_WebServiceURL}?key={Google_SpreadsheetKey}&action=GetLanguageSource&version={CurrentVersion}'
    r = urlopen(url)
    if r.status != 200:
        return {'version':-1, 'ret':ret}
    
    txt = r.read().decode('utf8')
    version = re.match('version=([0-9]+),',txt)[1]

    for cate in txt.split('[i2category]')[1:]:
        cate_name, cate_txt = cate.split('[/i2category]')
        if cate_name == 'Default':
            cate_prefix = ''
        else:
            cate_prefix = cate_name + '/'
        cate_txts = cate_txt.split('[/i2csv]')[0].split('[ln]')
        headers = cate_txts[0].split('[*]')
        
        key_id = -1
        lang_id = -1
        for i in range(len(headers)):
            if headers[i] == 'Keys':
                key_id = i
            if lang_keyword in headers[i]:
                lang_id = i
        for entry in cate_txts[1:]:
            entry_txts = entry.split('[*]')
            key = cate_prefix + entry_txts[key_id]
            value = entry_txts[lang_id]
            ret[key] = value
    return {'version':version, 'ret':ret}
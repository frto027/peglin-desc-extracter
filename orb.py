# python -m pip install pyyaml

import json
import pathlib
import re
import yaml
import config
import chevron

PROJECT_PATH = config.PROJECT_PATH

I2Language = PROJECT_PATH / 'Assets' / 'Resources' / 'I2Languages.asset'

ORBS_FOLDER = PROJECT_PATH / 'Assets' / 'Resources'/ 'prefabs' / 'orbs'

term_maps = dict()

language_id = 8

with I2Language.open('r', encoding='utf8') as f:
    obj = yaml.load(f,Loader=yaml.BaseLoader)
    terms = obj["MonoBehaviour"]["mSource"]["mTerms"]
    for term in terms:
        term_maps[term["Term"]] = term["Languages"]

def get_translate(index):
    d = term_maps[index]
    return d[language_id] or d[0]

def parse_desc(desc, dict = {}):
    def rep(x):
        t = x[1]
        return dict[t] if t in dict else "" 
    desc = re.sub(r"\<style=([a-zA-Z0-9]+)\>", r'<span class="pg_style_\1">', desc)
    desc = re.sub(r'\</style\>', '</span>', desc)
    desc = re.sub(r'\<sprite name="([_A-Za-z0-9]+)"\>', r'<div class="pg_sprite pg_sprite_\1"></div>', desc)
    desc = re.sub(r'\{\[([a-zA-Z0-9_]+)\]\}', rep, desc)
    desc = desc.replace('\n','<br/>', -1)
    return desc
#orb name -> [orb desc(level1), orb desc(level2), orb desc(level3)]
orb_data = dict()

orb_info = []

orb_infobuffer = pathlib.Path('orb_buffer.json')
if orb_infobuffer.exists():
    with orb_infobuffer.open('r', encoding='utf8') as f:
        orb_info = json.loads(f.read())
else:
    for orbfile in ORBS_FOLDER.glob("*.prefab"):
        if not '-Lv' in orbfile.name:
            continue
        with orbfile.open('r', encoding='utf8') as f:
            txt = ""
            for line in f.readlines():
                if line.startswith('---'):
                    txt += '---\n'
                    continue
                txt += line
            
            args_obj = None
            desc_obj = None

            for orb in yaml.load_all(txt, Loader=yaml.BaseLoader):
                if "MonoBehaviour" in orb:
                    target = orb["MonoBehaviour"]
                    if "locNameString" in target and "locDescStrings" in target:
                        desc_obj = target
                    if "_Params" in target:
                        args_obj = target
            assert desc_obj, orbfile

            args = dict()
            if args_obj:
                for arg in args_obj["_Params"]:
                    args[arg["Name"]] = arg["Value"]

            # -- outputs

            descs = []
            for descitem in desc_obj["locDescStrings"]:
                descs.append({"desc":parse_desc(get_translate('Orbs/' + descitem),args)})


            orb_info.append({
                "name" :get_translate('Orbs/' + desc_obj["locNameString"] + '_name'),
                "level" : desc_obj["Level"],
                "dmg" : desc_obj["DamagePerPeg"],
                "cdmg" : desc_obj["CritDamagePerPeg"],
                "descs":descs,
            })

            # print(name + "(level " + level + ")" + "|" + dmg + "|" + cdmg + "|" + desc)

            # gentxt += name
            # gentxt += '(' + level + ')' + "<br/>"
            # gentxt += "<div class='pg_sprite pg_sprite_PEG'></div>" + dmg + '|' + "<div class='pg_sprite pg_sprite_CRIT_PEG'></div>" + cdmg + "<br/>"
            # gentxt += desc
            # gentxt += '<hr/>'
    with orb_infobuffer.open('w',encoding='utf8') as f:
        f.write(json.dumps(orb_info))
        
with open('docs/orb.html','w',encoding='utf8') as f:
    with open('templates/orb.html.mustache','r',encoding='utf8') as template:
        f.write(chevron.render(template, {"orbs":orb_info}))
        # f.write(template.read().replace('[[[ORB_LIST]]]',gentxt))



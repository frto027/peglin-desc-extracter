# python -m pip install pyyaml

import json
import pathlib
import re
from unittest import loader
import yaml
import config
import chevron
import cv2

PROJECT_PATH = config.PROJECT_PATH

I2Language = PROJECT_PATH / 'Assets' / 'Resources' / 'I2Languages.asset'

ORBS_FOLDER = PROJECT_PATH / 'Assets' / 'Resources'/ 'prefabs' / 'orbs'

orb_sprite_height_limit = 32

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

################ build guid -> png file name map ##############

guid_map = dict()
guid_map_buffer = pathlib.Path('buffers/guid_map.json')
generated_sprites_css = dict()
generated_sprites_css_buffer = pathlib.Path('buffers/guid_map_css.json')
if generated_sprites_css_buffer.exists():
    generated_sprites_css = json.loads(generated_sprites_css_buffer.open('r',encoding='utf8').read())

if guid_map_buffer.exists():
    with guid_map_buffer.open('r',encoding='utf8') as f:
        guid_map = json.loads(f.read())
else:
    for metafile in (PROJECT_PATH / 'Assets' / 'Texture2D').glob('*.meta'):
        with metafile.open('r',encoding='utf8') as f:
            obj = yaml.load(f, yaml.BaseLoader)

            internal_dict = []
            for item in obj['TextureImporter']["internalIDToNameTable"]:
                internal_dict.append({
                    'name': item['first']['213']
                })

            for i in range(len(internal_dict)):
                rect = obj['TextureImporter']['spriteSheet']['sprites'][i]['rect']
                internal_dict[i]['rect'] = rect
            
            sheets = dict()
            for s in internal_dict:
                sheets[s['name']] = s['rect']

            guid = obj['guid']
            guid_map[guid] = {
                'filename':metafile.name[:-5],
                'sheets':sheets
            }
    with guid_map_buffer.open('w',encoding='utf8') as f:
        f.write(json.dumps(guid_map))

################ generate orb info #########################

orb_info = []
orb_infobuffer = pathlib.Path('buffers/orb_buffer.json')

used_assets = set()

if orb_infobuffer.exists():
    with orb_infobuffer.open('r', encoding='utf8') as f:
        orb_info = json.loads(f.read())
else:
    for orbfile in ORBS_FOLDER.glob("*.prefab"):
        if not '-Lv' in orbfile.name:
            continue
        with orbfile.open('r', encoding='utf8') as f:

            
            args_obj = None
            desc_obj = None
            sprite_obj = None

            for orb in yaml.load_all(config.purge(f), Loader=yaml.BaseLoader):
                if "MonoBehaviour" in orb:
                    target = orb["MonoBehaviour"]
                    if "locNameString" in target and "locDescStrings" in target:
                        desc_obj = target
                    if "_Params" in target:
                        args_obj = target
                if "SpriteRenderer" in orb and not sprite_obj:
                    sprite_obj = orb["SpriteRenderer"]
            assert desc_obj, orbfile
            assert sprite_obj, orbfile
            asset_guid = sprite_obj["m_Sprite"]["guid"]
            asset_path = guid_map[asset_guid]['filename']
            asset_file = sprite_obj["m_Sprite"]['fileID']

            # read img height and width 
            (asset_h, asset_w, _) = cv2.imread(str(PROJECT_PATH / 'Assets' / 'Texture2D'/ asset_path)).shape
            style_name = asset_path[:-4] + '_' + asset_file
            style_has_rect = False
            style_rect = None
            if asset_file in guid_map[asset_guid]['sheets']:
                style_has_rect = True
                rect = guid_map[asset_guid]['sheets'][asset_file]
                
                scale = orb_sprite_height_limit / float(rect['height'])
                margin = (orb_sprite_height_limit - float(rect['height']))/2

                style_rect = {
                    'left' : rect['x'],
                    'top' : str(asset_h - float(rect['y']) - float(rect['height'])),
                    'width':rect['width'],
                    'height' : rect['height'],
                    'scale' : scale,
                    'margin':margin
                }
            if not style_name in generated_sprites_css:
                scale = orb_sprite_height_limit / asset_h
                margin = (orb_sprite_height_limit - asset_h)/2

                generated_sprites_css[style_name] = {
                    'style' : style_name,
                    'file':asset_path,
                    'has_rect':style_has_rect,
                    'rect':style_rect,
                    'width':asset_w,
                    'height':asset_h,
                    'scale':scale,
                    'margin':margin,
                }

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
                "sprite_guid" : asset_guid,
                "sprite" : style_name
            })

            if not asset_path in used_assets:
                used_assets.add(asset_path)

            # print(name + "(level " + level + ")" + "|" + dmg + "|" + cdmg + "|" + desc)

            # gentxt += name
            # gentxt += '(' + level + ')' + "<br/>"
            # gentxt += "<div class='pg_sprite pg_sprite_PEG'></div>" + dmg + '|' + "<div class='pg_sprite pg_sprite_CRIT_PEG'></div>" + cdmg + "<br/>"
            # gentxt += desc
            # gentxt += '<hr/>'
    with orb_infobuffer.open('w',encoding='utf8') as f:
        f.write(json.dumps(orb_info))
    
    with generated_sprites_css_buffer.open('w', encoding='utf8') as f:
        f.write(json.dumps(generated_sprites_css))

########## generate orb sprite css ##############

with open('docs/pg_orb_sprite.css','w', encoding='utf8') as f:
    with open('templates/pg_orb_sprite.css.mustache','r', encoding='utf8') as template:
        f.write(chevron.render(template, {
            'assets' :list(generated_sprites_css.values())
        }))


########## copy assets ##########

doc_assets = pathlib.Path('docs') / 'pg_assets'

if not doc_assets.exists():
    doc_assets.mkdir()
for png in used_assets:
    fr = PROJECT_PATH / 'Assets' / 'Texture2D'/ png
    to = doc_assets / png
    with fr.open('rb') as f:
        with to.open('wb') as t:
            t.write(f.read())



with open('docs/orb.html','w',encoding='utf8') as f:
    with open('templates/orb.html.mustache','r',encoding='utf8') as template:
        f.write(chevron.render(template, {"orbs":orb_info}))



# python -m pip install pyyaml

import json
import pathlib
import re
from telnetlib import theNULL
from typing import List
from unittest import loader
import yaml
import config
import chevron
import cv2

PROJECT_PATH = config.PROJECT_PATH

I2Language = PROJECT_PATH / 'Assets' / 'Resources' / 'I2Languages.asset'

ORBS_FOLDER = PROJECT_PATH / 'Assets' / 'Resources'/ 'prefabs' / 'orbs'

orb_sprite_height_limit = 32
language_id = 8

def buffered(path, default = None):
    path = pathlib.Path('buffers') / path
    if path.exists():
        with path.open('r',encoding='utf8') as f:
            return json.loads(f.read())
    else:
        return default

def buffer_save(path, value):
    path = pathlib.Path('buffers') / path
    with path.open('w',encoding='utf8') as f:
        f.write(json.dumps(value))

# return pathlib(xxx.asset)
def FindAssetByGuid(guid):
    for meta in (PROJECT_PATH / 'Assets' / 'MonoBehaviour').glob('*.asset.meta'):
        with meta.open('r',encoding='utf8') as f:
            purged_file = config.purge(f)
            if guid in purged_file:
                return meta.parent / meta.name[:-5]
    return None
    
def FindMonoBehavioursByGuid(guid):
    ret = []
    for asset in (PROJECT_PATH / 'Assets' / 'MonoBehaviour').glob('*.asset'):
        with asset.open('r',encoding='utf8') as f:
            purged_file = config.purge(f)
            if guid in purged_file:
                for mono in yaml.load_all(purged_file,yaml.SafeLoader):
                    if "MonoBehaviour" in mono:
                        if 'm_Script' in mono['MonoBehaviour'] and mono['MonoBehaviour']['m_Script']['guid'] == guid:
                            ret.append(mono)
    return ret

term_maps = buffered('term_maps.json')
if not term_maps:
    print('generate term_maps...')
    term_maps = dict()
    with I2Language.open('r', encoding='utf8') as f:
        obj = yaml.load(f,Loader=yaml.BaseLoader)
        terms = obj["MonoBehaviour"]["mSource"]["mTerms"]
        for term in terms:
            term_maps[term["Term"]] = term["Languages"]
    buffer_save('term_maps.json',term_maps)


def get_translate(index):
    d = term_maps[index]
    return d[language_id] or d[0]

def parse_desc(desc, dict = {}, keyword_out = None):
    def rep_var(x):
        t = x[1]
        if not t in dict:
            print("warning: unknwon variable " + t)
            return ""
        return dict[t]

    def rep_styles(x):
        style = x[1]
        if keyword_out != None:
            keyword_out.append(style)
        return f'<span class="pg_style_{style}">'
    desc = re.sub(r"\<style=([_a-zA-Z0-9]+)\>", rep_styles, desc)
    desc = re.sub(r'\</style\>', '</span>', desc)
    desc = re.sub(r'\<sprite name="([_A-Za-z0-9]+)"?\>', r'<div class="pg_sprite pg_sprite_\1"></div>', desc)
    desc = re.sub(r'\{\[([a-zA-Z0-9_]+)\]\}', rep_var, desc)
    desc = desc.replace('\n','<br/>', -1)
    return desc

#orb name -> [orb desc(level1), orb desc(level2), orb desc(level3)]

################ build guid -> png file name map ##############

guid_map = buffered('guid_map.json')
generated_sprites_css = buffered('guid_map_css.json', dict())
if not guid_map:
    print('generate guid_map...')
    guid_map = dict()
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
    buffer_save('guid_map.json', guid_map)

################ sprite helper ##############
used_assets = set()

def GenerateSpriteCss(sprite_obj):
    asset_guid = sprite_obj["guid"]
    asset_path = guid_map[asset_guid]['filename']
    asset_file = str(sprite_obj['fileID'])

    # read img height and width 
    (asset_h, asset_w, _) = cv2.imread(str(PROJECT_PATH / 'Assets' / 'Texture2D'/ asset_path)).shape
    style_name = asset_path[:-4] + '_' + str(asset_file)
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
    if not asset_path in used_assets:
        used_assets.add(asset_path)
    buffer_save('guid_map_css.json', generated_sprites_css)

    return style_name
################ generate orb info #########################

orb_info = buffered('orb_buffer.json')

if not orb_info:
    print('generate orb_info...')
    orb_info = []
    for orbfile in ORBS_FOLDER.glob("*.prefab"):
        if not '-Lv' in orbfile.name:
            continue
        with orbfile.open('r', encoding='utf8') as f:
            args_obj = None
            desc_obj = None
            sprite_obj = None
            tutorial_obj = None

            for orb in yaml.load_all(config.purge(f), Loader=yaml.BaseLoader):
                if "MonoBehaviour" in orb:
                    target = orb["MonoBehaviour"]
                    if "locNameString" in target and "locDescStrings" in target:
                        desc_obj = target
                    if "_Params" in target:
                        args_obj = target
                    if "_tutorialTextLocKey" in target and not tutorial_obj:
                        tutorial_obj = target['_tutorialTextLocKey']
                if "SpriteRenderer" in orb and not sprite_obj:
                    sprite_obj = orb["SpriteRenderer"]
            assert desc_obj, orbfile
            assert sprite_obj, orbfile
            style_name =GenerateSpriteCss(sprite_obj['m_Sprite'])            

            args = dict()
            if args_obj:
                for arg in args_obj["_Params"]:
                    args[arg["Name"]] = arg["Value"]

            with open(orbfile.parent / (orbfile.name + '.meta'),'r',encoding='utf8') as f:
                orb_file_guid = yaml.load(f,yaml.SafeLoader)['guid']

            tutorial = None
            if tutorial_obj:
                tutorial = []
                for t in tutorial_obj:
                    tutorial.append({'desc': parse_desc(get_translate('Tutorial/' + t))})
                tutorial[-1]['last'] = True
            # -- outputs

            descs = []
            descs_keywords = []
            for descitem in desc_obj["locDescStrings"]:
                descs.append({"desc":parse_desc(get_translate('Orbs/' + descitem),args, descs_keywords)})

            orb_info.append({
                "name" :get_translate('Orbs/' + desc_obj["locNameString"] + '_name'),
                "level" : desc_obj["Level"],
                "dmg" : desc_obj["DamagePerPeg"],
                "cdmg" : desc_obj["CritDamagePerPeg"],
                "descs":descs,
                "sprite" : style_name,
                "keywords" : descs_keywords,
                "guid" : orb_file_guid,
                "pool" : {},
                "has_tutorial": tutorial != None,
                "tutorial":tutorial,
            })


            # print(name + "(level " + level + ")" + "|" + dmg + "|" + cdmg + "|" + desc)

            # gentxt += name
            # gentxt += '(' + level + ')' + "<br/>"
            # gentxt += "<div class='pg_sprite pg_sprite_PEG'></div>" + dmg + '|' + "<div class='pg_sprite pg_sprite_CRIT_PEG'></div>" + cdmg + "<br/>"
            # gentxt += desc
            # gentxt += '<hr/>'
    
    # read orb pools
    with open(PROJECT_PATH / 'Assets' / 'MonoScript' / 'Assembly-CSharp' / 'OrbPool.cs.meta') as f:
        OrbPoolGUID = yaml.load(f,yaml.SafeLoader)['guid']
    orb_guid_map = dict()
    for mono in FindMonoBehavioursByGuid(OrbPoolGUID):
        name = mono['MonoBehaviour']['m_Name']
        print('orb pool name:', name)
        for orbs in mono['MonoBehaviour']['AvailableOrbs']:
            orb_guid = orbs['guid']
            if not orb_guid in orb_guid_map:
                orb_guid_map[orb_guid] = {}
            orb_guid_map[orb_guid][name] = True
    for orb in orb_info:
        if orb['guid'] in orb_guid_map:
            orb['pool'] = orb_guid_map[orb['guid']]

    buffer_save('orb_buffer.json',orb_info)

typed_orb_info_dict = dict()

for orb in orb_info:
    if not orb['name'] in typed_orb_info_dict:
        typed_orb_info_dict[orb['name']] = {"orbs":[]}
    typed_orb_info_dict[orb['name']]["orbs"].append(orb)
typed_orb_info = []
typed_orb_info = list(typed_orb_info_dict.values())


########## relics #########

with (PROJECT_PATH / 'Assets' / 'MonoScript' / 'Assembly-CSharp' / 'Relics' / 'RelicSet.cs.meta').open('r',encoding='utf8') as f:    
    RelicSetGuid = yaml.load(f,yaml.BaseLoader)['guid']
with (PROJECT_PATH / 'Assets' / 'MonoScript' / 'Assembly-CSharp' / 'Relics' / 'Relic.cs.meta').open('r',encoding='utf8') as f:    
    RelicGuid = yaml.load(f,yaml.BaseLoader)['guid']

RelicSets = buffered('relic_file_sets.json')
if not RelicSets:
    print('generate RelicSets...')
    RelicSets = []
    for asset in (PROJECT_PATH / 'Assets' / 'MonoBehaviour').glob('*.asset'):
        with asset.open('r',encoding='utf8') as f:
            purged_file = config.purge(f)
            if not RelicSetGuid in purged_file:
                continue

            for mono in yaml.load_all(purged_file,yaml.BaseLoader):
                if "MonoBehaviour" in mono:
                    target = mono["MonoBehaviour"]
                    if 'm_Script' in target and target['m_Script']['guid'] == RelicSetGuid:
                        RelicSets.append(target)
    buffer_save('relic_file_sets.json', RelicSets)


RelicInfoMap = buffered('relic_info_map.json')
if not RelicInfoMap:
    print("generate RelicInfoMap...")
    RelicInfoMap = dict()
    for RelicSet in RelicSets:
        name = RelicSet['m_Name']
        relics = RelicSet["_relics"]
        for relic in relics:
            relic_asset = FindAssetByGuid(relic['guid'])
            
            with relic_asset.open('r',encoding='utf8') as f:
                for obj in yaml.load_all(config.purge(f),yaml.BaseLoader):
                    if not obj['MonoBehaviour']['m_Script']['guid'] == RelicGuid:
                        continue
                    RelicName = obj["MonoBehaviour"]["m_Name"]
                    if not RelicName in RelicInfoMap:
                        RelicInfoMap[RelicName] = {
                            'pool':{
                                name : True
                            }
                        }
                    else:
                        RelicInfoMap[RelicName]['pool'][name] = True


    # load params
    global_local_params = dict()
    with (PROJECT_PATH / 'Assets'/'Scene'/'Scenes'/'MainMenu.unity').open('r',encoding='utf8') as f:
        for mono in yaml.load_all(config.purge(f),yaml.BaseLoader):
            if not 'MonoBehaviour' in mono:
                continue
            target = mono['MonoBehaviour']
            if '_Params' in target:
                for item in target['_Params']:
                    global_local_params[item['Name']] = str(item['Value'])

    global_local_params['DECK_SIZE_HEAL_TOTAL'] = '0' # default value
    
    # add unknwon relics and relic sprites

    for relic in FindMonoBehavioursByGuid(RelicGuid):
        RelicName = relic['MonoBehaviour']['m_Name']
        locKey = relic['MonoBehaviour']['locKey']
        descMod = relic['MonoBehaviour']['descMod']
        if descMod == None:
            descMod = ''
        else:
            descMod = str(descMod)

        style_name = GenerateSpriteCss(relic['MonoBehaviour']['sprite'])
        if not RelicName in RelicInfoMap:
            RelicInfoMap[RelicName] = {}
        RelicInfoMap[RelicName]['name'] = RelicName
        RelicInfoMap[RelicName]['sprite'] = style_name
        RelicInfoMap[RelicName]['locName'] = get_translate('Relics/' + locKey + '_name')
        desc_keywords = []
        RelicInfoMap[RelicName]['locDesc'] = parse_desc(get_translate('Relics/' + locKey + '_desc' + descMod),global_local_params, desc_keywords)
        RelicInfoMap[RelicName]['keywords'] = desc_keywords
    buffer_save('relic_info_map.json',RelicInfoMap)

relic_infos = []
for k in RelicInfoMap:
    relic_infos.append(RelicInfoMap[k])

########## orb keywords ##############
orb_keywords_map = buffered('orb_keyword_map.json')
if not orb_keywords_map:
    print('generate orb_keywords_map...')
    orb_keywords_map = dict()
    with (PROJECT_PATH / 'Assets' / 'PrefabInstance' / 'OrbInfoWidget.prefab').open('r', encoding='utf8') as f:
        for mono in yaml.load_all(config.purge(f), yaml.SafeLoader):
            if not 'MonoBehaviour' in mono:
                continue
            target = mono['MonoBehaviour']
            if '_keywordDescriptionMapping' in target:
                for item in target['_keywordDescriptionMapping']:
                    orb_keywords_map[item['Keyword']] =  parse_desc(get_translate('Statuses/' + item['DescriptionLoc']),global_local_params)
    buffer_save('orb_keyword_map.json', orb_keywords_map)



########## relic keywords ###########
relic_keywords_map = buffered('relic_keyword_map.json')
if not relic_keywords_map:
    print('generate relic_keywords_map...')
    relic_keywords_map = dict()
    with (PROJECT_PATH / 'Assets' / 'PrefabInstance' / 'RelicInfoWidget.prefab').open('r', encoding='utf8') as f:
        for mono in yaml.load_all(config.purge(f), yaml.SafeLoader):
            if not 'MonoBehaviour' in mono:
                continue
            target = mono['MonoBehaviour']
            if '_keywordDescriptionMapping' in target:
                for item in target['_keywordDescriptionMapping']:
                    relic_keywords_map[item['Keyword']] =  parse_desc(get_translate('Statuses/' + item['DescriptionLoc']),global_local_params)
    buffer_save('relic_keyword_map.json',relic_keywords_map)

# inject keywords into orb #
for orb in orb_info:
    keywords = []
    generated_keywords = set()
    for k in orb['keywords']:
        if k in orb_keywords_map:
            if k in generated_keywords:
                continue
            generated_keywords.add(k)
            keywords.append(
                {'keyword_desc':orb_keywords_map[k],'last?':False}
            )
    if len(keywords)>0:
        keywords[-1]['last?']=True
    orb['keywords'] = keywords
    orb['has_keywords'] = len(keywords) > 0

for relic in relic_infos:
    keywords = []
    generated_keywords = set()
    for k in relic['keywords']:
        if k in relic_keywords_map:
            if k in generated_keywords:
                continue
            generated_keywords.add(k)
            keywords.append(
                {
                    'keyword_desc':relic_keywords_map[k],
                    'last?':False
                }
            )
    if len(keywords) > 0:
        keywords[-1]['last?'] = True
    relic['keywords'] = keywords
    relic['has_keywords'] = len(keywords) > 0

########## get game version ########

with (PROJECT_PATH / 'ProjectSettings' / 'ProjectSettings.asset').open('r', encoding='utf8') as f:
    GAME_VERSION = yaml.load(config.purge(f), yaml.SafeLoader)['PlayerSettings']['bundleVersion']
print('game version: ' + GAME_VERSION)


########## generate sprite css ##############

with open('docs/pg_orb_sprite.css','w', encoding='utf8') as f:
    with open('templates/pg_orb_sprite.css.mustache','r', encoding='utf8') as template:
        f.write(chevron.render(template, {
            'assets' :list(generated_sprites_css.values())
        }))

########## copy assets ##########

doc_assets = pathlib.Path('docs') / 'pg_assets'

if not doc_assets.exists():
    doc_assets.mkdir()

print('copy assets...')
for png in used_assets:
    fr = PROJECT_PATH / 'Assets' / 'Texture2D'/ png
    to = doc_assets / png
    with fr.open('rb') as f:
        with to.open('wb') as t:
            t.write(f.read())

print('generate orb.html...')
with open('docs/orb.html','w',encoding='utf8') as f:
    with open('templates/orb.html.mustache','r',encoding='utf8') as template:
        f.write(chevron.render(template, {"orbs":orb_info, "typed_orbs": typed_orb_info, "version":GAME_VERSION}))

print('generate relic.html...')
with open('docs/relic.html','w',encoding='utf8') as f:
    with open('templates/relic.html.mustache','r',encoding='utf8') as template:
        f.write(chevron.render(template, {"relics":relic_infos, "version":GAME_VERSION}))

print('generate index.html')
with open('docs/index.html','w',encoding='utf8') as f:
    with open('templates/index.html.mustache','r',encoding='utf8') as template:
        f.write(chevron.render(template,{'version':GAME_VERSION}))

print('over')
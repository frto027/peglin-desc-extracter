import pathlib
import re
import config
import yaml
import chevron

PROJECT_PATH = config.PROJECT_PATH

Sprites = PROJECT_PATH / 'Assets' / 'Resources' / \
    'sprite assets' / 'TMP_Sprites.asset'
Sprites_png = PROJECT_PATH / 'Assets' / \
    'Resources' / 'sprite assets' / 'TMP_Atlas.png'
TARGET_PNG = pathlib.Path('docs/atlas.png')

TARGET_CSS = pathlib.Path('docs/pg_sprite.css')

with Sprites.open("r", encoding='utf8') as f:
    obj = yaml.load(f, Loader=yaml.BaseLoader)['MonoBehaviour']
    table = obj['m_SpriteCharacterTable']
    glyph = obj['m_SpriteGlyphTable']

    glyphs = dict()
    for g in glyph:
        glyphs[g['m_Index']] = {
            "width": g['m_GlyphRect']['m_Width'],
            "height": g['m_GlyphRect']['m_Height'],
            "left": g["m_GlyphRect"]['m_X'],
            # 100 - int(t['top']) - int(t['height']
            "top": str(100 - int(g["m_GlyphRect"]['m_Y']) - int(g['m_GlyphRect']['m_Height'])),
        }
    indexed_glyphs = dict()
    for g in table:
        target = dict(glyphs[g['m_GlyphIndex']])
        target['scale'] = float(g['m_Scale']) * 2
        target['margin'] = float(target['height']) * (target['scale'] - 1) / 2
        indexed_glyphs[g['m_Name']] = target
    # print(indexed_glyphs)

glyphs_arr = []
for k in indexed_glyphs:
    item = dict(indexed_glyphs[k])
    item['name'] = k
    glyphs_arr.append(item)

# copy png

with Sprites_png.open('rb') as f:
    with TARGET_PNG.open('wb') as t:
        t.write(f.read())


# styles

# style_css = ''

styles = []

with (PROJECT_PATH / 'Assets' / 'MonoBehaviour' / 'PeglinStyleSheet.asset').open('r', encoding='utf8') as f:
    for style in yaml.load(f, Loader=yaml.BaseLoader)['MonoBehaviour']['m_StyleList']:
        # print(style['m_Name'], style['m_OpeningDefinition'])
        gp = re.match(r'\<color=(#[a-f0-9A-F]+)\>',
                      style['m_OpeningDefinition'])
        if gp:
            name = style['m_Name']
            color = gp[1]
            # print(name, color)
            styles.append({
                "name": name,
                "color": color
            })
            # style_css += '.pg_style_' + name + '{color:' + color + '}\n'


# generate css

with open('templates/pg_sprite.css.mustache', 'r', encoding='utf8') as template:
    with TARGET_CSS.open('w', encoding='utf8') as f:
        f.write(chevron.render(template, {
            "styles": styles,
            "glyphs": glyphs_arr
        })
        )

# with TARGET_CSS.open('w', encoding='utf8') as f:
#     f.write(style_css)
#     f.write("""
# """)
#     for g in indexed_glyphs:
#         t = indexed_glyphs[g]
#         f.write('.pg_sprite_' + g + '{')
#         f.write(f"""
#     transform: scale({t["scale"]});
#     background-position: -{t['left']}px -{100 - int(t['top']) - int(t['height'])}px;
#     width: {t['width']}px;
#     height: {t['height']}px;
# """ + "}\n")

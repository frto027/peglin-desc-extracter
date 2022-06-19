import pathlib
import re
import config
import yaml

PROJECT_PATH = config.PROJECT_PATH

Sprites = PROJECT_PATH / 'Assets' / 'Resources' / 'sprite assets' / 'TMP_Sprites.asset'
Sprites_png = PROJECT_PATH / 'Assets' / 'Resources' / 'sprite assets' / 'TMP_Atlas.png'
TARGET_PNG = pathlib.Path('docs/atlas.png')

TARGET_CSS = pathlib.Path('docs/pg_sprite.css')

with Sprites.open("r", encoding='utf8') as f:
    obj = yaml.load(f, Loader=yaml.BaseLoader)['MonoBehaviour']
    table = obj['m_SpriteCharacterTable']
    glyph = obj['m_SpriteGlyphTable']

    glyphs = dict()
    for g in glyph:
        glyphs[g['m_Index']] = {
            "width" : g['m_GlyphRect']['m_Width'],
            "height" : g['m_GlyphRect']['m_Height'],
            "left" : g["m_GlyphRect"]['m_X'],
            "top" : g["m_GlyphRect"]['m_Y'],
        }
    indexed_glyphs = dict()
    for g in table:
        target=dict(glyphs[g['m_GlyphIndex']])
        target['scale'] = g['m_Scale']
        indexed_glyphs[g['m_Name']] = target
    # print(indexed_glyphs)

# copy png

with Sprites_png.open('rb') as f:
    with TARGET_PNG.open('wb') as t:
        t.write(f.read())


# styles

style_css = ''

with (PROJECT_PATH / 'Assets' / 'MonoBehaviour' / 'PeglinStyleSheet.asset').open('r',encoding='utf8') as f:
    for style in yaml.load(f,Loader=yaml.BaseLoader)['MonoBehaviour']['m_StyleList']:
        # print(style['m_Name'], style['m_OpeningDefinition'])
        gp = re.match(r'\<color=(#[a-f0-9A-F]+)\>',style['m_OpeningDefinition'])
        if gp:
            name = style['m_Name']
            color = gp[1]
            # print(name, color)
            style_css += '.pg_style_' + name + '{color:' + color + '}\n'


# generate css

with TARGET_CSS.open('w',encoding='utf8') as f:
    f.write(style_css)
    f.write("""
.pg_sprite{
    image-rendering:pixelated;
    background-image: url('atlas.png');
    display:inline-block;
}
""")
    for g in indexed_glyphs:
        t = indexed_glyphs[g]
        f.write('.pg_sprite_' + g + '{')
        f.write(f"""
    transform: scale({t["scale"]});
    background-position: -{t['left']}px -{100 - int(t['top']) - int(t['height'])}px;
    width: {t['width']}px;
    height: {t['height']}px;
""" + "}\n")
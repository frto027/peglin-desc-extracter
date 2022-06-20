import pathlib

PROJECT_PATH = pathlib.Path(r'E:\backup\PeglinExport\Peglin\ExportedProject')

# txt = config.purge(open("xxx"))
def purge(f):
    txt = ""
    for line in f.readlines():
        if line.startswith('---'):
            txt += '---\n'
            continue
        txt += line
    return txt
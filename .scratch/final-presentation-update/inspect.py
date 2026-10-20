from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[2]
out = Path(__file__).parent
ns = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
for path in (root/'presentations').glob('*.pptx'):
    lines=[]
    with ZipFile(path) as z:
        p=ET.fromstring(z.read('ppt/presentation.xml'))
        lines.append(str(p.find('p:sldSz',ns).attrib))
        names=sorted([n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')],key=lambda n:int(n.rsplit('slide',1)[1].split('.')[0]))
        for i,n in enumerate(names,1):
            r=ET.fromstring(z.read(n))
            lines.append(f'\nSLIDE {i}')
            for shape in r.findall('.//p:sp',ns):
                t='\n'.join(''.join(x.text or '' for x in para.findall('.//a:t',ns)) for para in shape.findall('.//a:p',ns))
                if t: lines.append(f"{shape.find('p:nvSpPr/p:cNvPr',ns).get('name')}: {t}")
            note=f'ppt/notesSlides/notesSlide{i}.xml'
            if note in z.namelist(): lines.append('NOTES: '+' | '.join(t.text or '' for t in ET.fromstring(z.read(note)).findall('.//a:t',ns)))
    (out/(path.stem+'.txt')).write_text('\n'.join(lines),encoding='utf-8')
    print(path.name,len(names),lines[0])
for path in (root/'docs/reports').glob('*.docx'):
    with ZipFile(path) as z:
        r=ET.fromstring(z.read('word/document.xml'))
        lines=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in r.findall('.//w:p',ns)]
    (out/(path.stem+'.txt')).write_text('\n'.join(lines),encoding='utf-8')
    print(path.name,len(lines))

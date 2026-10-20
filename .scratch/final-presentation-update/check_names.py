from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import re,json
root=Path(__file__).resolve().parents[2]
folder=Path(__file__).parent
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
deck=root/'presentations/Final Seminar.pptx'
with ZipFile(deck) as z:
    violations=[]
    for name in z.namelist():
        if re.match(r'ppt/(slides|notesSlides)/[^/]+\.xml$',name):
            text=' '.join(t.text or '' for t in ET.fromstring(z.read(name)).findall('.//a:t',ns))
            if re.search(r'basin[ -]hop|tabu|hill[ -]climb',text,re.I): violations.append(name)
    assert not violations,violations
    slide2=ET.fromstring(z.read('ppt/slides/slide2.xml'))
    assert 'Overview' in [t.text for t in slide2.findall('.//a:t',ns)]
    with ZipFile(folder/'Final Seminar.before-naming-fix.pptx') as before:
        media={n:z.read(n) for n in z.namelist() if n.startswith('ppt/media/')}
        original={n:before.read(n) for n in before.namelist() if n.startswith('ppt/media/')}
        assert media==original,'Source images changed'
    count=len(ET.fromstring(z.read('ppt/presentation.xml')).find('p:sldIdLst',ns))
    record={'slides':count,'overview_slide':2,'unwanted_algorithm_names':violations,'source_images_preserved':True}
    (folder/'naming-validation.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record))

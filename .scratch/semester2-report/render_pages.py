from pathlib import Path
import importlib.util, tempfile, sys, json
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parents[2]
work=ROOT/'.scratch/semester2-report'
report_name=sys.argv[1] if len(sys.argv)>1 else '2026-10-12-semester-2-complete-technical-report.docx'
render_folder=sys.argv[2] if len(sys.argv)>2 else 'render'
render_dir=work/render_folder
pdf=render_dir/'report.pdf'
tempfile.tempdir=str(work)
skill=Path('C:/Users/davsk/.codex/plugins/cache/openai-primary-runtime/documents/26.1007.11041/skills/documents/render_docx.py')
spec=importlib.util.spec_from_file_location('packaged_docx_renderer',skill)
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
# Preserve the packaged pagination-to-image workflow; native Word supplied the PDF.
r.convert_to_pdf=lambda *args,**kwargs:(str(pdf),'Rendered by native Microsoft Word')
def raster_pdf(path,dpi,fmt,thread_count,output_folder,paths_only,output_file):
    rendered=[]
    document=pdfium.PdfDocument(path)
    for i,page in enumerate(document):
        out=Path(output_folder)/f'wordpage-{i+1:02d}.png'
        page.render(scale=dpi/72).to_pil().save(out)
        rendered.append(str(out))
    return rendered
r.convert_from_path=raster_pdf
paths=r.rasterize(str(ROOT/'docs/reports'/report_name),str(render_dir),130,False,False)
document=pdfium.PdfDocument(pdf)
print('PAGE_COUNT',len(document))
for i,page in enumerate(document):
    text=page.get_textpage().get_text_range()
    print('PAGE',i+1,'CHARS',len(text),'START',text[:140].replace('\r\n',' | '),'END',text[-110:].replace('\r\n',' | '))
(render_dir/'page-text.json').write_text(json.dumps([page.get_textpage().get_text_range() for page in document],indent=2),encoding='utf-8')
print('PNG files',len(paths))

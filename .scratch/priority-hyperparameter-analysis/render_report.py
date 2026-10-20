from pathlib import Path
import importlib.util,tempfile,json,sys
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
report_name=sys.argv[1] if len(sys.argv)>1 else '2026-10-13-priority-based-selection-hyperparameter-analysis.docx'
render_folder=sys.argv[2] if len(sys.argv)>2 else 'priority-hyperparameter-render'
RENDER=ROOT/'.scratch/semester2-report'/render_folder
PDF=RENDER/'report.pdf'
DOC=ROOT/'docs/reports'/report_name
tempfile.tempdir=str(WORK)
skill=Path('C:/Users/davsk/.cache/codex-runtimes/codex-primary-runtime/plugins/openai-primary-runtime/plugins/documents/skills/documents/render_docx.py')
spec=importlib.util.spec_from_file_location('packaged_docx_renderer',skill)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
r.convert_to_pdf=lambda *args,**kwargs:(str(PDF),'Rendered by native Microsoft Word')
def raster_pdf(path,dpi,fmt,thread_count,output_folder,paths_only,output_file):
    paths=[]
    pdf=pdfium.PdfDocument(path)
    for i,page in enumerate(pdf):
        out=Path(output_folder)/f'wordpage-{i+1:02d}.png'
        page.render(scale=dpi/72).to_pil().save(out)
        paths.append(str(out))
    pdf.close()
    return paths
r.convert_from_path=raster_pdf
paths=r.rasterize(str(DOC),str(RENDER),130,False,False)
pdf=pdfium.PdfDocument(PDF)
texts=[page.get_textpage().get_text_range() for page in pdf]
(RENDER/'page-text.json').write_text(json.dumps(texts,indent=2),encoding='utf-8')
for i,text in enumerate(texts,1):
    print(i,len(text),text[:100].replace('\r\n',' | '),text[-100:].replace('\r\n',' | '))
print('PAGES',len(paths))

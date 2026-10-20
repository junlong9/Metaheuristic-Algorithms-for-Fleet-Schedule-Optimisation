from pathlib import Path
import win32com.client, json, sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parents[2]
out=Path(__file__).parent
app=win32com.client.Dispatch('PowerPoint.Application')
existing=[p.FullName for p in app.Presentations]
print('OPEN',existing)
for name, indices in [('Final Seminar.pptx',None),('Iteration 1 Milestones.pptx',[7,8])]:
    source=root/'presentations'/name
    p=app.Presentations.Open(str(source),True,False,False)
    folder=out/(source.stem+'-source')
    folder.mkdir(exist_ok=True)
    rows=[]
    for i in (indices or range(1,p.Slides.Count+1)):
        s=p.Slides(i)
        s.Export(str(folder/f'slide-{i:02}.png'),'PNG',1600,900)
        for sh in s.Shapes:
            if sh.HasTextFrame and sh.TextFrame.HasText:
                rows.append({'slide':i,'name':sh.Name,'text':sh.TextFrame.TextRange.Text,'x':sh.Left,'y':sh.Top,'w':sh.Width,'h':sh.Height,'font':sh.TextFrame.TextRange.Font.Name,'size':sh.TextFrame.TextRange.Font.Size})
    (folder/'shapes.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    p.Close()
    print('EXPORTED',name)
if not existing: app.Quit()

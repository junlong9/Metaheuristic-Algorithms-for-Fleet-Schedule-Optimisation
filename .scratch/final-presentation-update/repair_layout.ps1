$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path '.').Path
$buildRoot=Join-Path $taskRoot '.scratch/final-presentation-update'
$deckPath=Join-Path $taskRoot 'presentations/Final Seminar.pptx'
$app=New-Object -ComObject PowerPoint.Application
$existing=@($app.Presentations | ForEach-Object {$_.FullName})
if($existing -contains $deckPath){throw 'The final deck is already open.'}
$p=$app.Presentations.Open($deckPath,0,0,0)
function Shape($index,$name){foreach($s in $p.Slides.Item($index).Shapes){if($s.Name -eq $name){return $s}}; throw "Missing $name"}
$t=Shape 6 'Title 1'
$t.Left=36; $t.Top=31; $t.Width=888; $t.Height=45
$t.TextFrame.TextRange.Font.Size=32
$t.TextFrame.TextRange.ParagraphFormat.Alignment=1
(Shape 6 'Simple setup').Top=89
$s=Shape 7 'Rectangle 1'
$s.TextFrame.TextRange.Text="24 aircraft and 278 checks`rA, B, C and D maintenance checks`rSequence: A B A C A B A D`r12-year forecast"
$s.TextFrame.TextRange.ParagraphFormat.SpaceAfter=9
$s.Height=166
(Shape 8 'Rectangle 1').Height=325
foreach($name in @('TextBox 28','TextBox 30','TextBox 32')){(Shape 13 $name).Height=145}
foreach($name in @('TextBox 14','TextBox 18')){(Shape 19 $name).Height=165}
(Shape 25 'TextBox 16').Height=145
$s=Shape 11 'TextBox 13'
$s.TextFrame.TextRange.Text="Can basin-hopping improve the tuned baseline?`rHow much does the starting schedule affect the result?`rWhich neighbourhoods work across three forecasts?`rStudy scope: scheduled maintenance without operational constraints."
$s.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
$s.TextFrame.TextRange.Font.Size=19
$s=Shape 18 'TextBox 10'
$s.TextFrame.TextRange.Text="Original forecast: C57`rHalf steps plus 42 days`r`rModerate and wide: C30`r`rC30's original smoothness penalty is 0.56%.`rEarlier half steps reach 19 on wide, compared with 20 for C30."
$s.Top=172; $s.Height=295
$s.TextFrame.TextRange.Font.Size=19
$s.TextFrame.TextRange.ParagraphFormat.SpaceAfter=9
$s.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
foreach($i in 22..26){$p.Slides.Item($i).SlideShowTransition.Hidden=-1}
$p.Save()
$rows=@()
foreach($slide in $p.Slides){
    if($slide.SlideIndex -in @(6,7,8,11,13,18,19,25)){$slide.Export((Join-Path $buildRoot ('final-render/slide-{0:D2}.png' -f $slide.SlideIndex)),'PNG',1600,900)}
    foreach($s in $slide.Shapes){
        if($s.HasTextFrame -and $s.TextFrame.HasText){$rows += [pscustomobject]@{slide=$slide.SlideIndex;name=$s.Name;h=$s.Height;boundH=$s.TextFrame.TextRange.BoundHeight;size=$s.TextFrame.TextRange.Font.Size}}
    }
}
$rows | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $buildRoot 'repaired-shapes.json') -Encoding UTF8
$p.Close()
if($existing.Count -eq 0){$app.Quit()}
Write-Output 'Layout repaired and backup slides hidden in the slideshow'

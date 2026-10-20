$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path '.').Path
$folder=Join-Path $taskRoot '.scratch/final-presentation-update/readability-before'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$app=New-Object -ComObject PowerPoint.Application
$path=Join-Path $taskRoot 'presentations/Final Seminar.pptx'
$p=$null
foreach($deck in $app.Presentations){if($deck.FullName -eq $path){$p=$deck}}
$opened=$false
if($null -eq $p){$p=$app.Presentations.Open($path,-1,0,0);$opened=$true}
$all=@()
foreach($slide in $p.Slides){
    $rows=@()
    foreach($s in $slide.Shapes){
        if($s.HasTextFrame -and $s.TextFrame.HasText){$rows += [pscustomobject]@{name=$s.Name;text=$s.TextFrame.TextRange.Text;x=$s.Left;y=$s.Top;w=$s.Width;h=$s.Height;font=$s.TextFrame.TextRange.Font.Name;size=$s.TextFrame.TextRange.Font.Size}}
        if($s.HasTable){foreach($r in 1..$s.Table.Rows.Count){$values=@();foreach($c in 1..$s.Table.Columns.Count){$values+=$s.Table.Cell($r,$c).Shape.TextFrame.TextRange.Text};$rows += [pscustomobject]@{name=$s.Name;text=($values -join ' / ');row=$r}}}
    }
    $text=($rows.text -join "`n")
    $all += [pscustomobject]@{slide=$slide.SlideIndex;id=$slide.SlideID;text=$text;shapes=$rows}
    if($text -match 'HYPERPARAMETER|RECOMMENDED SETTINGS|LIMITS AND NEXT STEPS|FINAL RECOMMENDATION'){
        $slide.Export((Join-Path $folder ('slide-{0:D2}.png' -f $slide.SlideIndex)),'PNG',1600,900)
        Write-Output "SLIDE $($slide.SlideIndex) ID $($slide.SlideID)"
        Write-Output $text
    }
}
$all | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $folder 'inventory.json') -Encoding UTF8
if($opened){$p.Close()}

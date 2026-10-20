$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path '.').Path
$buildRoot = Join-Path $taskRoot '.scratch/final-presentation-update'
$deckPath = Join-Path $taskRoot 'presentations/Final Seminar.pptx'
$spec = Get-Content -LiteralPath (Join-Path $buildRoot 'content.json') -Raw | ConvertFrom-Json -AsHashtable
$app = New-Object -ComObject PowerPoint.Application
$existing = @($app.Presentations | ForEach-Object { $_.FullName })
if ($existing -contains $deckPath) { throw 'Final Seminar.pptx is already open. Exclusive edit is required.' }
Copy-Item -LiteralPath $deckPath -Destination (Join-Path $buildRoot 'Final Seminar.before-update.pptx')
$p = $app.Presentations.Open($deckPath, 0, 0, 0)
$slides = @{}
for ($i=1;$i -le $p.Slides.Count;$i++) { $slides["o$i"] = $p.Slides.Item($i) }

function Shape($slide,$name) {
    foreach ($s in $slide.Shapes) { if ($s.Name -eq $name) { return $s } }
    throw "Missing shape $name on slide $($slide.SlideIndex)"
}
function Text($slide,$name,$value,$size=0) {
    $s=Shape $slide $name
    $s.TextFrame.TextRange.Text=$value.Replace("`n","`r")
    $s.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
    if ($size -gt 0) { $s.TextFrame.TextRange.Font.Size=$size }
    $s.TextFrame.AutoSize=0
}
function Box($slide,$name,$value,$x,$y,$w,$h,$size=20,$bold=$false) {
    $s=$slide.Shapes.AddTextbox(1,$x,$y,$w,$h)
    $s.Name=$name
    $s.Fill.Visible=0
    $s.Line.Visible=0
    $s.TextFrame.MarginLeft=0
    $s.TextFrame.MarginRight=0
    $s.TextFrame.MarginTop=0
    $s.TextFrame.MarginBottom=0
    $s.TextFrame.TextRange.Text=$value.Replace("`n","`r")
    $s.TextFrame.TextRange.Font.Name='Calibri'
    $s.TextFrame.TextRange.Font.Size=$size
    $s.TextFrame.TextRange.Font.Bold= $(if($bold){-1}else{0})
    $s.TextFrame.TextRange.Font.Color.RGB=0
    $s.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
    $s.TextFrame.AutoSize=0
}
function ClearContent($slide) {
    for($i=$slide.Shapes.Count;$i -ge 1;$i--) {
        $s=$slide.Shapes.Item($i)
        if ($s.Name -in @('TextBox 3','TextBox 4')) { continue }
        if ($s.Top -lt 9 -and $s.Height -le 10) {continue}
        $s.Delete()
    }
}
function Table($slide,$name,$rows,$widths,$y=150,$rowHeight=54,$size=19) {
    $shape=$slide.Shapes.AddTable($rows.Count,$rows[0].Count,36,$y,888,($rows.Count*$rowHeight))
    $shape.Name=$name
    $t=$shape.Table
    for($c=1;$c -le $widths.Count;$c++) { $t.Columns.Item($c).Width=$widths[$c-1] }
    for($r=1;$r -le $rows.Count;$r++) {
        $t.Rows.Item($r).Height=$rowHeight
        for($c=1;$c -le $rows[0].Count;$c++) {
            $s=$t.Cell($r,$c).Shape
            $s.Fill.Solid()
            $s.Fill.ForeColor.RGB= $(if($r -eq 1){0}else{if($r % 2 -eq 0){15790320}else{16777215}})
            $s.TextFrame.MarginLeft=10
            $s.TextFrame.MarginRight=7
            $s.TextFrame.MarginTop=7
            $s.TextFrame.MarginBottom=7
            $s.TextFrame.VerticalAnchor=3
            $s.TextFrame.TextRange.Text=[string]$rows[$r-1][$c-1]
            $s.TextFrame.TextRange.Font.Name='Calibri'
            $s.TextFrame.TextRange.Font.Size= $(if($r -eq 1){16}else{$size})
            $s.TextFrame.TextRange.Font.Bold= $(if($r -eq 1){-1}else{0})
            $s.TextFrame.TextRange.Font.Color.RGB= $(if($r -eq 1){16777215}else{0})
            $s.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
            foreach($b in @(1,2,3,4)) { $t.Cell($r,$c).Borders.Item($b).ForeColor.RGB=11579568; $t.Cell($r,$c).Borders.Item($b).Weight=0.5 }
        }
    }
}
function Notes($slide,$value) {
    foreach($s in $slide.NotesPage.Shapes) {
        if($s.Type -eq 14 -and $s.PlaceholderFormat.Type -eq 2) {
            $s.TextFrame.TextRange.Text=$value
            return
        }
    }
    throw "No speaker-note body on slide $($slide.SlideIndex)"
}

try {
    $count=$p.Slides.Count
    [void]$p.Slides.InsertFromFile((Join-Path $taskRoot 'presentations/Iteration 1 Milestones.pptx'),$count,7,9)
    foreach($j in 7..9) {$slides["m$j"]=$p.Slides.Item($count+$j-6)}
    $slides['hyper_results']=$slides['o22'].Duplicate().Item(1)
    foreach($key in $spec.updates.Keys) {
        foreach($name in $spec.updates[$key].Keys) {Text $slides[$key] $name $spec.updates[$key][$name]}
    }
    # Existing slide objects and source masters remain intact.
    foreach($key in @('o13','o15','o16','o17','o18','o19','o20','o21','o22','hyper_results','m7','m8','m9','o14')) {
        $title=Shape $slides[$key] 'TextBox 4'
        $title.Left=36; $title.Top=42; $title.Width=888; $title.Height=52
        $title.TextFrame.TextRange.Font.Size= $(if($key -eq 'm7'){30}else{32})
        $label=Shape $slides[$key] 'TextBox 3'
        $label.Left=36; $label.Top=13; $label.Width=888; $label.Height=25
        $label.TextFrame.TextRange.Font.Size=15
    }
    $cover=Shape $slides.o1 'TextBox 8'
    $cover.Top=60; $cover.Height=385; $cover.TextFrame.TextRange.Font.Size=32
    (Shape $slides.o2 'Content Placeholder 2').TextFrame.TextRange.Font.Size=21
    (Shape $slides.o2 'Content Placeholder 2').TextFrame.TextRange.ParagraphFormat.SpaceAfter=14
    (Shape $slides.o3 'Content Placeholder 2').Top=182
    (Shape $slides.o3 'Content Placeholder 2').Height=310
    (Shape $slides.o3 'Content Placeholder 2').TextFrame.TextRange.Font.Size=23
    (Shape $slides.o3 'Content Placeholder 2').TextFrame.TextRange.ParagraphFormat.SpaceAfter=15
    (Shape $slides.o4 'Content Placeholder 2').TextFrame.TextRange.Font.Size=26
    (Shape $slides.o4 'Content Placeholder 2').TextFrame.TextRange.ParagraphFormat.SpaceAfter=10
    (Shape $slides.o7 'Title 1').TextFrame.TextRange.Font.Size=34
    Box $slides.o7 'Simple setup' '10 aircraft, 80 checks. Keep the best feasible improvement at each iteration.' 48 92 860 25 16
    (Shape $slides.o8 'Title 1').TextFrame.TextRange.Font.Size=36
    $heavy=Shape $slides.o8 'Rectangle 1'
    $heavy.Left=36; $heavy.Top=91; $heavy.Width=438; $heavy.Height=174
    $heavy.TextFrame.TextRange.Font.Size=21
    $heavy.TextFrame.TextRange.ParagraphFormat.SpaceAfter=12
    (Shape $slides.o9 'Title 1').TextFrame.TextRange.Font.Size=32
    (Shape $slides.o9 'Rectangle 1').TextFrame.TextRange.Font.Size=21
    (Shape $slides.o9 'Rectangle 1').TextFrame.TextRange.ParagraphFormat.SpaceAfter=15
    (Shape $slides.o6 'Rectangle 5').TextFrame.TextRange.Font.Size=21
    (Shape $slides.o6 'Rectangle 5').TextFrame.TextRange.ParagraphFormat.SpaceAfter=20
    foreach($name in @('TextBox 7','TextBox 10')) {
        $s=Shape $slides.o13 $name
        $s.TextFrame.TextRange.Font.Size=25
        $s.Height=55
    }
    (Shape $slides.o13 'TextBox 13').TextFrame.TextRange.Font.Size=19
    (Shape $slides.o13 'TextBox 13').TextFrame.TextRange.ParagraphFormat.SpaceAfter=14
    foreach($key in @('o15','o20')) {
        foreach($name in @('TextBox 7','TextBox 10')) {
            $s=Shape $slides[$key] $name
            $s.TextFrame.TextRange.Font.Size=20
            $s.TextFrame.TextRange.ParagraphFormat.SpaceAfter=12
        }
    }
    (Shape $slides.o15 'TextBox 12').TextFrame.TextRange.Font.Size=20
    (Shape $slides.o16 'TextBox 34').TextFrame.TextRange.Font.Size=17
    (Shape $slides.o16 'TextBox 34').Height=77
    foreach($name in @('TextBox 28','TextBox 30','TextBox 32')) {(Shape $slides.o16 $name).TextFrame.TextRange.Font.Size=18}
    foreach($name in @('TextBox 8','TextBox 11','TextBox 14')) {
        (Shape $slides.m8 $name).TextFrame.TextRange.Font.Size=20
        (Shape $slides.m8 $name).TextFrame.TextRange.ParagraphFormat.SpaceAfter=12
    }
    foreach($name in @('TextBox 7','TextBox 10','TextBox 13')) {(Shape $slides.m9 $name).TextFrame.TextRange.Font.Size=24}
    # Replace overfilled metric cards with editable comparison tables.
    ClearContent $slides.o17
    Table $slides.o17 'Method results' @(
        @('Method','Worst day','Std deviation','Runtime'),
        @('Tuned hill-climb','18','1.391860','115.6 s'),
        @('Basin-hopping median','18','1.390417','306.3 s'),
        @('Tightened median','18','1.391860','63.5 s')
    ) @(340,140,204,204) 136 55 20
    Box $slides.o17 'Decision finding' 'Smoothness gain: 0.00144 against a 0.005 threshold. Median runtime exceeded 300 s.' 42 383 875 65 21 $true
    Box $slides.o17 'Decision context' 'Earlier decision benchmark. Candidate seeds 1–3. Two candidate runs reached the time budget.' 42 465 875 38 16
    ClearContent $slides.o19
    Table $slides.o19 'Start schedule results' @(
        @('Start schedule','Initial worst day','Final worst day','Final std deviation'),
        @('As-loaded','15','18','1.391860'),
        @('Bunched','15','18','1.404629'),
        @('Spread','15','18','1.417282')
    ) @(270,190,190,238) 136 55 20
    Box $slides.o19 'Start finding' 'Same original checks and due dates. Tuned hill-climb endpoints shown.' 42 382 875 37 20 $true
    Box $slides.o19 'Start distinction' 'The later moderate and wide stagger datasets change maintenance ages and check mix. They are different problem instances.' 42 440 875 62 19
    ClearContent $slides.o22
    Box $slides.o22 'Study scale' '174 matched sweep cases, 203 completed run records' 48 127 864 41 25 $true
    Box $slides.o22 'Study content' "Settings: shift magnitudes, ladder order, priority selection and iteration budget`n`nInputs: original, moderate stagger and wide stagger forecasts`n`nMatched window: 21 January 2026 to 18 January 2038`n`nChecks: preserve opening due clocks, freeze commenced checks, replay rules and independently recompute availability" 48 192 864 242 21
    Box $slides.o22 'Study caveat' 'Each input is a distinct maintenance instance. Compare tuned and default settings within the same dataset.' 48 454 864 51 18 $true
    ClearContent $slides.hyper_results
    Table $slides.hyper_results 'Hyperparameter results' @(
        @('Dataset','Initial worst day','Tuned worst day','Default std','Tuned std','Best setting'),
        @('Original','15','18','1.4221','1.4019','C57'),
        @('Moderate','16','19','0.9117','0.8834','C30'),
        @('Wide','17','20','0.6167','0.5868','C30')
    ) @(160,142,142,148,148,148) 129 57 20
    Box $slides.hyper_results 'Quality gain' 'Smoothness improvement at the same worst day: 1.42%, 3.10% and 4.85%' 42 377 875 45 22 $true
    Box $slides.hyper_results 'Runtime evidence' 'Serial median search time: C57 original 32.16 s. C30 moderate 14.69 s, wide 28.55 s. Three repeats per setting on this machine.' 42 432 875 63 18
    Box $slides.hyper_results 'Results boundary' 'Matched scoring window. All listed winners reached local exhaustion.' 42 505 875 22 14
    foreach($name in @('TextBox 14','TextBox 18')) {(Shape $slides.o18 $name).TextFrame.TextRange.Font.Size=20}
    (Shape $slides.o18 'TextBox 7').TextFrame.TextRange.Font.Size=17
    foreach($name in @('TextBox 7','TextBox 10')) {
        (Shape $slides.o21 $name).TextFrame.TextRange.Font.Size=27
        (Shape $slides.o21 $name).Height=55
    }
    (Shape $slides.o21 'TextBox 13').TextFrame.TextRange.Font.Size=20
    (Shape $slides.o21 'TextBox 13').TextFrame.TextRange.ParagraphFormat.SpaceAfter=14
    (Shape $slides.o23 'Content Placeholder 2').TextFrame.TextRange.Font.Size=23
    (Shape $slides.o23 'Content Placeholder 2').Height=285
    Box $slides.o23 'Internal evidence' "Project evidence: Iteration 1 milestone deck, completed technical report (12 Oct 2026), three-forecast hyperparameter report (14 Oct 2026), and saved study results." 66 437 828 65 17
    $slides.o12.Delete()
    for($i=0;$i -lt $spec.order.Count;$i++) {$slides[$spec.order[$i]].MoveTo($i+1)}
    $qa=@()
    for($i=0;$i -lt $spec.order.Count;$i++) {
        $key=$spec.order[$i]
        $slide=$slides[$key]
        Notes $slide $spec.notes[$key]
        foreach($s in $slide.Shapes) {
            if($s.HasTextFrame -and $s.TextFrame.HasText) {
                $qa += [pscustomobject]@{slide=$i+1;name=$s.Name;text=$s.TextFrame.TextRange.Text;x=$s.Left;y=$s.Top;w=$s.Width;h=$s.Height;boundH=$s.TextFrame.TextRange.BoundHeight;size=$s.TextFrame.TextRange.Font.Size}
            }
        }
    }
    $p.Save()
    $render=Join-Path $buildRoot 'final-render'
    New-Item -ItemType Directory -Force -Path $render | Out-Null
    foreach($slide in $p.Slides) {$slide.Export((Join-Path $render ('slide-{0:D2}.png' -f $slide.SlideIndex)),'PNG',1600,900)}
    $qa | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $buildRoot 'final-shapes.json') -Encoding UTF8
    Write-Output "Saved and rendered $($p.Slides.Count) slides in place"
    $p.Close()
    if($existing.Count -eq 0){$app.Quit()}
} catch {
    $p.Saved=-1
    $p.Close()
    if($existing.Count -eq 0){$app.Quit()}
    throw
}

$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path '.').Path
$buildRoot=Join-Path $taskRoot '.scratch/final-presentation-update'
$deckPath=Join-Path $taskRoot 'presentations/Final Seminar.pptx'
$app=New-Object -ComObject PowerPoint.Application
$existing=@($app.Presentations | ForEach-Object {$_.FullName})
if($existing -contains $deckPath){throw 'The deck is open and requires exclusive edit confirmation.'}
Copy-Item -LiteralPath $deckPath -Destination (Join-Path $buildRoot 'Final Seminar.before-naming-fix.pptx')
$p=$app.Presentations.Open($deckPath,0,0,0)
function SetText($shape,$value,$size=0){
    $shape.TextFrame.TextRange.Text=$value.Replace("`n","`r")
    $shape.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
    if($size -gt 0){$shape.TextFrame.TextRange.Font.Size=$size}
}
function FindShape($slide,$name){foreach($s in $slide.Shapes){if($s.Name -eq $name){return $s}};throw "Missing shape $name"}
function ConvertName($value){
    $value=[regex]::Replace($value,'(?i)basin[- ]hopping with tabu polish','Simulated Annealing')
    $value=[regex]::Replace($value,'(?i)basin[- ]hopping','Simulated Annealing')
    $value=[regex]::Replace($value,'(?i)tuned (?:priority )?hill[- ]climb','tuned Priority Based Selection with VNS')
    $value=[regex]::Replace($value,'(?i)(?:priority )?hill[- ]climb','Priority Based Selection with VNS')
    return $value
}
function ProcessShape($s){
    if($s.Type -eq 6){foreach($child in $s.GroupItems){ProcessShape $child}}
    if($s.HasTable){
        foreach($r in 1..$s.Table.Rows.Count){foreach($c in 1..$s.Table.Columns.Count){ProcessShape $s.Table.Cell($r,$c).Shape}}
    }
    if($s.HasTextFrame -and $s.TextFrame.HasText){
        $value=ConvertName $s.TextFrame.TextRange.Text
        if($value -ne $s.TextFrame.TextRange.Text){$s.TextFrame.TextRange.Text=$value}
    }
}
function SetNotes($slide,$value){foreach($s in $slide.NotesPage.Shapes){if($s.Type -eq 14 -and $s.PlaceholderFormat.Type -eq 2){$s.TextFrame.TextRange.Text=$value;return}}}
try{
    $overview=$null;$method=$null;$comparison=$null;$recommendation=$null;$final=$null
    foreach($slide in $p.Slides){
        $allText=(@($slide.Shapes | Where-Object {$_.HasTextFrame -and $_.TextFrame.HasText} | ForEach-Object {$_.TextFrame.TextRange.Text}) -join "`n")
        if($allText -match 'The project journey'){$overview=$slide}
        if($allText -match 'CANDIDATE METHOD'){$method=$slide}
        if($allText -match 'METHOD COMPARISON'){$comparison=$slide}
        if($allText -match 'RECOMMENDED SETTINGS'){$recommendation=$slide}
        if($allText -match 'FINAL RECOMMENDATION'){$final=$slide}
        foreach($s in $slide.Shapes){ProcessShape $s}
        foreach($s in $slide.NotesPage.Shapes){ProcessShape $s}
        if($allText -match 'MILESTONE 4 · PRIORITY-BASED SELECTION'){
            SetText (FindShape $slide 'TextBox 3') 'PRIORITY BASED SELECTION WITH VARIABLE NEIGHBOURHOOD SEARCH' 14
            $s=FindShape $slide 'TextBox 3';$s.Left=36;$s.Width=888;$s.Height=27
        }
        if($allText -match 'ACCEPTANCE AND TESTING'){
            SetText (FindShape $slide 'TextBox 27') 'Annealing acceptance'
            SetText (FindShape $slide 'TextBox 34') 'Same input and half-step neighbourhoods. Compare tuned Priority Based Selection with VNS against Simulated Annealing, using the median of seeds 1–3. Keep only if all seeds retain 18 aircraft, smoothness improves by at least 0.005, and median runtime stays within 300 seconds.' 17
            (FindShape $slide 'TextBox 34').Height=96
        }
        if($allText -match 'CONTROLLED START SCHEDULES'){
            SetText (FindShape $slide 'Start finding') 'Same checks and due dates. Tuned Priority Based Selection with VNS results shown.' 20
        }
        if($allText -match 'BACKUP: SIMULATED ANNEALING'){
            SetNotes $slide 'Simulated Annealing allows temporary worsening to leave a local optimum. Higher temperature makes worse moves more likely, and cooling makes them rarer. The method retains the best-so-far schedule separately and returns it. It uses the same variable neighbourhoods and maintenance validity checks as Priority Based Selection with Variable Neighbourhood Search. Source: Iteration 2 Execution Plan.pptx and the completed technical report.'
        }
    }
    if($null -eq $overview){throw 'The existing overview was not found.'}
    SetText (FindShape $overview 'Title 1') 'Overview'
    SetText (FindShape $overview 'Content Placeholder 2') "Problem and optimisation objective`nIteration 1: simple fleet and heavy maintenance forecast`nFull neighbourhood search and random sampling`nPriority Based Selection with Variable Neighbourhood Search`nIteration 2: Simulated Annealing`nStarting schedules and hyperparameter analysis`nResults and final recommendation" 26
    SetNotes $overview 'I will first restate the maintenance scheduling problem and its objective. Then I will explain the first iteration, starting with the simple fleet, scaling to the heavy maintenance forecast, and progressing through full neighbourhood search and random sampling to Priority Based Selection with Variable Neighbourhood Search. In the second iteration I will cover Simulated Annealing, starting schedules, and the completed hyperparameter analysis. I will finish with the measured results and the final recommendation.'
    $overview.MoveTo(2)
    SetText (FindShape $method 'TextBox 3') 'SIMULATED ANNEALING'
    SetText (FindShape $method 'TextBox 4') 'Simulated Annealing with Variable Neighbourhood Search' 29
    SetText (FindShape $method 'TextBox 6') 'Priority Based Selection with VNS' 18
    SetText (FindShape $method 'TextBox 9') 'Simulated Annealing' 20
    SetText (FindShape $method 'TextBox 10') "Use the same variable neighbourhoods`nExplore feasible changes to the schedule`nAlways accept an improving schedule`nSometimes accept a worse schedule at high temperature`nCool down and return the best-so-far schedule" 20
    SetText (FindShape $method 'TextBox 12') 'Simulated Annealing adds temperature-based acceptance to the existing neighbourhood search' 19
    SetNotes $method 'The first-iteration method is Priority Based Selection with Variable Neighbourhood Search. It focuses on checks affecting the worst availability days, rebuilds later checks on the affected aircraft, and accepts improving schedules. Simulated Annealing uses the same variable neighbourhoods and maintenance rules while adding temperature-based acceptance. Better schedules are accepted, and a worse schedule can be accepted temporarily when temperature is high. As the method cools, those decisions become less likely. The best-so-far schedule remains separate and is the reported result. The following comparison holds the input and neighbourhood settings fixed. Source: completed Iteration 2 study and the technical report dated 12 October 2026.'
    SetText (FindShape $comparison 'TextBox 4') 'Simulated Annealing did not meet the keep rule' 32
    $table=(FindShape $comparison 'Method results').Table
    SetText $table.Cell(2,1).Shape "Tuned Priority Based`nSelection with VNS" 18
    SetText $table.Cell(3,1).Shape 'Simulated Annealing median' 18
    SetText $table.Cell(4,1).Shape 'Tightened acceptance median' 18
    SetText (FindShape $comparison 'Decision context') 'Earlier decision benchmark. Simulated Annealing seeds 1–3. Two runs reached the time budget.' 16
    SetText (FindShape $final 'TextBox 4') 'Final method: Priority Based Selection with VNS' 31
    SetText (FindShape $final 'TextBox 7') "Priority Based Selection`nwith VNS" 23
    (FindShape $final 'TextBox 7').Height=62
    SetText (FindShape $final 'TextBox 13') "Iteration 1 raised original worst-day availability from 15 to 18.`nSimulated Annealing offered too little smoothness gain for its runtime.`nThree-dataset tuning supports C30 as the shared setting.`nUse C57 when the original forecast needs the best measured smoothness." 20
    $p.Save()
    $render=Join-Path $buildRoot 'names-corrected-render'
    New-Item -ItemType Directory -Force -Path $render | Out-Null
    $rows=@()
    foreach($slide in $p.Slides){
        $slide.Export((Join-Path $render ('slide-{0:D2}.png' -f $slide.SlideIndex)),'PNG',1600,900)
        foreach($s in $slide.Shapes){if($s.HasTextFrame -and $s.TextFrame.HasText){$rows += [pscustomobject]@{slide=$slide.SlideIndex;name=$s.Name;text=$s.TextFrame.TextRange.Text;h=$s.Height;boundH=$s.TextFrame.TextRange.BoundHeight}}}
    }
    $rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $buildRoot 'names-corrected-shapes.json') -Encoding UTF8
    Write-Output "Saved $($p.Slides.Count) slides with Overview at slide 2"
    $p.Close()
    if($existing.Count -eq 0){$app.Quit()}
}catch{
    $p.Saved=-1;$p.Close()
    if($existing.Count -eq 0){$app.Quit()}
    throw
}

param([switch]$Finish)
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path '.').Path
$buildRoot=Join-Path $taskRoot '.scratch/final-presentation-update'
$path=Join-Path $taskRoot 'presentations/Final Seminar.pptx'
$app=New-Object -ComObject PowerPoint.Application
$p=$null
foreach($deck in $app.Presentations){if($deck.FullName -eq $path){$p=$deck}}
$opened=$false
if($null -eq $p){$p=$app.Presentations.Open($path,0,0,0);$opened=$true}
$p.SaveCopyAs((Join-Path $buildRoot 'Final Seminar.before-step-explanation.pptx'),24)
function Shape($slide,$name){foreach($s in $slide.Shapes){if($s.Name -eq $name){return $s}};throw "Missing $name"}
function Text($slide,$name,$value,$size){
    $s=Shape $slide $name
    $s.TextFrame.TextRange.Text=$value.Replace("`n","`r")
    $s.TextFrame.TextRange.Font.Size=$size
    $s.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
    $s.TextFrame.AutoSize=0
}
function Notes($slide,$value){foreach($s in $slide.NotesPage.Shapes){if($s.Type -eq 14 -and $s.PlaceholderFormat.Type -eq 2){$s.TextFrame.TextRange.Text=$value;return}}}
if($Finish){
    $p.Save()
    $render=Join-Path $buildRoot 'step-explanation-final'
    New-Item -ItemType Directory -Force -Path $render | Out-Null
    $rows=@()
    foreach($slide in $p.Slides){
        $text=(@($slide.Shapes | Where-Object {$_.HasTextFrame -and $_.TextFrame.HasText} | ForEach-Object {$_.TextFrame.TextRange.Text}) -join "`n")
        if($text -match 'HOW STEP SIZES WORK|HYPERPARAMETER SETTINGS'){
            $slide.Export((Join-Path $render ('slide-{0:D2}.png' -f $slide.SlideIndex)),'PNG',1600,900)
            foreach($s in $slide.Shapes){if($s.HasTextFrame -and $s.TextFrame.HasText){$rows += [pscustomobject]@{slide=$slide.SlideIndex;name=$s.Name;h=$s.Height;boundH=$s.TextFrame.TextRange.BoundHeight}}}
        }
    }
    $rows | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $render 'shapes.json') -Encoding UTF8
    Write-Output "Saved and rendered explanations. Total $($p.Slides.Count) slides."
    if($opened){$p.Close()}
    return
}
$settings=$null;$results=$null
foreach($slide in $p.Slides){
    $text=(@($slide.Shapes | Where-Object {$_.HasTextFrame -and $_.TextFrame.HasText} | ForEach-Object {$_.TextFrame.TextRange.Text}) -join "`n")
    if($text -match 'HYPERPARAMETER SETTINGS'){$settings=$slide}
    if($text -match 'HYPERPARAMETER RESULTS'){$results=$slide}
}
if($null -eq $settings){throw 'Settings slide was not found'}
$explanation=$settings.Duplicate().Item(1)
$explanation.MoveTo($settings.SlideIndex)
$explanation.SlideShowTransition.Hidden=0
Text $explanation 'TextBox 3' 'HOW STEP SIZES WORK' 15
Text $explanation 'TextBox 4' 'A step size is a trial change to a check start date' 30
Text $explanation 'TextBox 12' 'Example: try a 14-day move' 22
Text $explanation 'TextBox 14' "Current start: Day 100`n14 days earlier: Day 86`n14 days later: Day 114`n`nThese are two alternative schedules.`nKeep the better legal improvement." 21
Text $explanation 'TextBox 16' 'How the search repeats' 22
Text $explanation 'TextBox 18' "Try the largest step size first.`nKeep one best improving move.`nRestart from the largest step size.`n`nIf no move improves the schedule,`ntry the next, smaller step size." 21
Text $explanation 'TextBox 6' 'Which checks get tested first?' 21
Text $explanation 'TextBox 7' "For each step size, test checks covering the worst availability days first.`nOnly search the other priority groups if the earlier groups find no improvement." 18
Notes $explanation 'A step size means the number of days added to or subtracted from one check start. It does not change the duration of that check. For a check currently starting on day 100, a minus-14 trial starts on day 86 and a plus-14 trial starts on day 114. These are different candidate schedules, not two changes applied together. A trial is usable only if it remains in the legal start window and rebuilding the aircraft later checks keeps the full schedule legal. The score first protects worst-day availability, then improves smoothness, and finally considers mean availability. Each search iteration starts from the largest neighbourhood. Within that neighbourhood, checks are grouped by the worst availability day they cover, and the worst group is searched first. The method examines all improving candidates within that group and chooses the best, rather than taking the first candidate encountered. If that group has no improvement, it tries the next priority group. If all groups fail for that step-size neighbourhood, it tries the next, smaller neighbourhood. After one improvement is accepted, it starts a new iteration, recomputes the priorities, and returns to the largest neighbourhood. Source: .scratch/priority-hyperparameter-analysis/run_three_datasets.py, neighbours and solve functions.'

Text $settings 'TextBox 4' 'Which trial moves worked best?' 32
Text $settings 'TextBox 12' 'Original forecast' 23
Text $settings 'TextBox 14' "First try 42 days earlier or later.`nIf no move helps, try 28 or 14 days.`nNext try 14 or 7, then 7 or 3,`nthen 3 or 1 day.`n`nEach pair gives four trial moves." 21
Text $settings 'TextBox 16' 'Moderate and wide forecasts' 23
Text $settings 'TextBox 18' "First try 56 days earlier or later.`nIf no move helps, try 42 days,`nthen 28, 14, 7, 3 and 1 day.`n`nTry one size at a time.`nThis is the shared recommendation." 21
Text $settings 'TextBox 6' 'When does the search stop?' 21
Text $settings 'TextBox 7' "Stop when none of the listed moves improves the schedule, or after 400 search iterations.`nEach iteration accepts at most one move. The search can stop before reaching 400." 18
foreach($slide in @($settings,$explanation)){
    foreach($name in @('TextBox 14','TextBox 18')){
        $s=Shape $slide $name;$s.Top=169;$s.Height=203
        $s.TextFrame.TextRange.Font.Bold=0
        $s.TextFrame.TextRange.ParagraphFormat.SpaceAfter=5
    }
    (Shape $slide 'TextBox 7').Top=455
    (Shape $slide 'TextBox 7').Height=56
}
Notes $settings 'These settings tune Priority Based Selection with Variable Neighbourhood Search. On the original forecast, the tested winning order was: first only minus and plus 42 days. If no improving legal candidate exists in any priority group at that neighbourhood, try four alternatives: minus 28, minus 14, plus 14, and plus 28 days. If that neighbourhood also fails, try minus 14, minus 7, plus 7, and plus 14. The next neighbourhood uses minus 7, minus 3, plus 3, and plus 7. The last uses minus 3, minus 1, plus 1, and plus 3. A pair means two alternative magnitudes in the same candidate batch. It does not mean add the sizes or move a check twice. For a check currently on day 100, the 28-and-14 batch proposes starts on days 72, 86, 114, and 128, assuming those dates and the rebuilt schedule are legal. The method then chooses one best improving schedule within the first priority group that can improve. On the moderate and wide forecasts, the winning order uses one magnitude per neighbourhood: 56, 42, 28, 14, 7, 3, and 1 day in either direction. Larger trial changes can produce different search paths, while the small steps allow finer adjustments. The winning settings were established by comparing the measured endpoints, not by assuming larger shifts must be better. After accepting a move, both strategies restart at their largest neighbourhood. Stop when every neighbourhood and priority group finds no improvement, or when the iteration cap is reached. The recommended cap is 400 iterations. The recorded winners needed 302, 367, and 291 accepted moves on original, moderate, and wide respectively, so 400 leaves room to confirm the final no-improvement pass. The parameter sweep used an 800-move cap and finalist extensions where needed. Source: three-dataset-results.json and run_three_datasets.py in .scratch/priority-hyperparameter-analysis, and the completed three-forecast report dated 14 October 2026.'
if($null -ne $results){foreach($s in $results.Shapes){if($s.Name -eq 'Results boundary'){Text $results 'Results boundary' '58 step-size and selection combinations on each forecast. The next slides explain the trial moves.' 15}}}
$p.Save()
$render=Join-Path $buildRoot 'step-explanation-final'
New-Item -ItemType Directory -Force -Path $render | Out-Null
$rows=@()
foreach($slide in @($explanation,$settings)){
    $slide.Export((Join-Path $render ('slide-{0:D2}.png' -f $slide.SlideIndex)),'PNG',1600,900)
    foreach($s in $slide.Shapes){if($s.HasTextFrame -and $s.TextFrame.HasText){$rows += [pscustomobject]@{slide=$slide.SlideIndex;name=$s.Name;h=$s.Height;boundH=$s.TextFrame.TextRange.BoundHeight}}}
}
$rows | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $render 'shapes.json') -Encoding UTF8
Write-Output "Simplified slides $($explanation.SlideIndex) and $($settings.SlideIndex). Total $($p.Slides.Count) slides."
if($opened){$p.Close()}

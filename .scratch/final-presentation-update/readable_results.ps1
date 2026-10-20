$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path '.').Path
$buildRoot=Join-Path $taskRoot '.scratch/final-presentation-update'
$path=Join-Path $taskRoot 'presentations/Final Seminar.pptx'
$app=New-Object -ComObject PowerPoint.Application
$p=$null
foreach($deck in $app.Presentations){if($deck.FullName -eq $path){$p=$deck}}
$opened=$false
if($null -eq $p){$p=$app.Presentations.Open($path,0,0,0);$opened=$true}
# The user expressly authorised editing the open presentation.
$p.SaveCopyAs((Join-Path $buildRoot 'Final Seminar.before-readability.pptx'),24)
function Shape($slide,$name){foreach($s in $slide.Shapes){if($s.Name -eq $name){return $s}};throw "Missing $name"}
function Text($slide,$name,$value,$size=0){
    $s=Shape $slide $name
    $s.TextFrame.TextRange.Text=$value.Replace("`n","`r")
    $s.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
    $s.TextFrame.AutoSize=0
    if($size -gt 0){$s.TextFrame.TextRange.Font.Size=$size}
}
function Notes($slide,$value){foreach($s in $slide.NotesPage.Shapes){if($s.Type -eq 14 -and $s.PlaceholderFormat.Type -eq 2){$s.TextFrame.TextRange.Text=$value;return}}}
$limits=$null;$results=$null;$final=$null
foreach($slide in $p.Slides){
    $text=(@($slide.Shapes | Where-Object {$_.HasTextFrame -and $_.TextFrame.HasText} | ForEach-Object {$_.TextFrame.TextRange.Text}) -join "`n")
    if($text -match 'LIMITS AND NEXT STEPS'){$limits=$slide}
    if($text -match 'HYPERPARAMETER RESULTS'){$results=$slide}
    if($text -match 'FINAL RECOMMENDATION'){$final=$slide}
}
if($null -eq $limits -or $null -eq $results -or $null -eq $final){throw 'Required slide not found'}
$settings=$limits.Duplicate().Item(1)
$settings.MoveTo($results.SlideIndex+1)
$settings.SlideShowTransition.Hidden=0
Text $settings 'TextBox 3' 'HYPERPARAMETER SETTINGS'
Text $settings 'TextBox 4' 'The step sizes that gave the best results' 32
Text $settings 'TextBox 12' 'Original forecast: paired shifts' 21
Text $settings 'TextBox 14' "Level 1: ±42 days`nLevel 2: ±28 and ±14 days`nLevel 3: ±14 and ±7 days`nLevel 4: ±7 and ±3 days`nLevel 5: ±3 and ±1 days" 22
Text $settings 'TextBox 16' 'Moderate and wide: separate steps' 20
Text $settings 'TextBox 18' "One size at each level, in order:`n±56, ±42, ±28, ±14,`n±7, ±3 and ±1 days`n`nShared choice across all three forecasts" 22
foreach($name in @('TextBox 14','TextBox 18')){
    $s=Shape $settings $name;$s.Top=169;$s.Height=203
    $s.TextFrame.TextRange.Font.Bold=0
    $s.TextFrame.TextRange.ParagraphFormat.SpaceAfter=8
}
Text $settings 'TextBox 6' 'Selection and stopping rule' 21
Text $settings 'TextBox 7' "Choose the best improvement in the first priority group that can improve.`nUse a 400-iteration limit. ± means try earlier and later, within the legal start window." 18
(Shape $settings 'TextBox 7').Top=455;(Shape $settings 'TextBox 7').Height=56
Notes $settings 'The original forecast used the following neighbourhoods, in order: first minus and plus forty-two days. Then minus and plus twenty-eight and fourteen days together. Then fourteen and seven together, seven and three together, and three and one together. The paired sizes are evaluated within the same neighbourhood level, rather than as separate levels. Moderate and wide stagger used seven separate levels: minus and plus fifty-six, forty-two, twenty-eight, fourteen, seven, three, and one day. Positive shifts move a check later relative to its current start, but every move must stay inside its legal start window and cannot exceed its due date. Both winners use first-level priority selection: choose the best improving proposal from the first priority group that can improve. The search advances to finer neighbourhoods when the current one has no improvement. The recommended four-hundred-iteration cap covers the measured natural convergence counts of 302, 367, and 291 accepted moves, with room for the final no-improvement check. The study sweep used an eight-hundred-move cap, with finalist extensions when needed. Source: .scratch/priority-hyperparameter-analysis/three-dataset-results.json, configurations formerly labelled C57 and C30, and the 14 October 2026 three-forecast report.'

# Keep the results editable and replace opaque configuration IDs with strategy names.
$table=(Shape $results 'Hyperparameter results').Table
$widths=@(140,128,128,145,145,202)
for($c=1;$c -le 6;$c++){$table.Columns.Item($c).Width=$widths[$c-1]}
$labels=@('Step-size strategy','Paired shifts + 42 days','Separate wide steps','Separate wide steps')
for($r=1;$r -le 4;$r++){
    $s=$table.Cell($r,6).Shape
    $s.TextFrame.TextRange.Text=$labels[$r-1]
    $s.TextFrame.TextRange.Font.Size= $(if($r -eq 1){16}else{17})
    $s.TextFrame.TextRange.ParagraphFormat.Bullet.Visible=0
}
Text $results 'Runtime evidence' 'Median search time: original 32.16 s, moderate 14.69 s, wide 28.55 s. Three serial repeats per setting on this machine.' 18
Text $results 'Results boundary' '58 step-size and selection combinations on each forecast. Exact winning steps are on the next slide.' 15
Notes $results 'The study compared fifty-eight step-size and selection combinations on each of three matched forecasts, giving one hundred and seventy-four sweep cases. The default used separate shifts of minus and plus twenty-eight, fourteen, seven, and three days. For the original forecast, adding a forty-two-day level and pairing large and small shifts produced the best measured smoothness: 1.401929, with eighteen aircraft on the worst day. For moderate and wide stagger, the separate wide steps gave smoothness of 0.883419 and 0.586797, retaining nineteen and twenty aircraft respectively. The exact step sets appear on the next slide. Improvements against the default on the same input are 1.42, 3.10, and 4.85 percent. All runs preserve maintenance legality and opening due clocks on the matched dates from 21 January 2026 to 18 January 2038. Timings are medians of three serial repeats on this machine. Source: the completed hyperparameter report dated 14 October 2026 and saved three-dataset study records.'

Text $limits 'TextBox 4' 'Availability limits and remaining work' 32
Text $limits 'TextBox 12' 'Original forecast' 23
Text $limits 'TextBox 14' "18 aircraft`nBest possible worst-day availability`n`nSix D checks must overlap.`n24 aircraft − 6 in maintenance = 18" 22
Text $limits 'TextBox 16' 'Moderate and wide stagger' 23
Text $limits 'TextBox 18' "19 and 20 aircraft`nBest worst-day availability found so far`n`nUpper limit: 21 on each dataset`nWhether we can reach 21 is still open." 22
foreach($name in @('TextBox 14','TextBox 18')){
    $s=Shape $limits $name;$s.Top=161;$s.Height=211
    $s.TextFrame.TextRange.Font.Bold=0
    $s.TextFrame.TextRange.ParagraphFormat.SpaceAfter=8
    $s.TextFrame.TextRange.Paragraphs(1).Font.Size=34
    $s.TextFrame.TextRange.Paragraphs(1).Font.Bold=-1
}
Text $limits 'TextBox 6' 'What remains open' 21
Text $limits 'TextBox 7' "Search for smoother original schedules and higher worst-day availability on the stagger datasets.`nThese findings apply to the tested dummy maintenance forecasts." 18
(Shape $limits 'TextBox 7').Top=455;(Shape $limits 'TextBox 7').Height=56
Notes $limits 'Worst-day availability means the lowest number of aircraft available on any day of the forecast. In the original fleet, a D check lasts one hundred and twenty-six days and can start up to seventy days early. Every legal placement therefore covers a fixed fifty-six-day interval beginning at its due date. Six of those compulsory intervals overlap on the original forecast. That forces at least six aircraft into maintenance together, so the twenty-four-aircraft fleet can have no more than eighteen available on its worst day. Our result reaches eighteen, proving the primary objective optimal under these maintenance assumptions. This does not prove that the schedule has globally optimal smoothness. On the moderate and wide stagger inputs, the equivalent overlap gives an upper limit of twenty-one, but the best measured results reach nineteen and twenty. The bound does not prove twenty-one is reachable. The remaining work is to test whether those gaps can be reduced and whether smoother schedules exist. Source: 14 October 2026 three-forecast report, limits of the evidence section.'

Text $final 'TextBox 9' 'SHARED STEP SIZES' 17
Text $final 'TextBox 10' "±56, ±42, ±28, ±14,`n±7, ±3, ±1 days" 23
(Shape $final 'TextBox 10').Height=67
Text $final 'TextBox 13' "Iteration 1 raised original worst-day availability from 15 to 18.`nSimulated Annealing offered too little smoothness gain for its runtime.`nUse the separate wide steps with a 400-iteration limit across these forecasts.`nFor the original forecast, paired shifts plus 42 days give the best measured smoothness." 19
(Shape $final 'TextBox 13').Height=165
Notes $final 'The final method remains Priority Based Selection with Variable Neighbourhood Search. For a shared setting on these three forecasts, use seven separate neighbourhood levels of minus and plus fifty-six, forty-two, twenty-eight, fourteen, seven, three, and one day, first-level priority selection, and a four-hundred-iteration limit. On the original forecast, the best measured smoothness instead uses a forty-two-day level followed by paired twenty-eight and fourteen, fourteen and seven, seven and three, and three and one-day shifts. Simulated Annealing did not meet the decision-study smoothness and runtime thresholds. These are explicit settings recommendations for the tested forecasts, rather than unexplained configuration codes.'
# Remove remaining opaque IDs in speaker notes without changing source values.
foreach($slide in $p.Slides){foreach($s in $slide.NotesPage.Shapes){if($s.HasTextFrame -and $s.TextFrame.HasText){
    $value=$s.TextFrame.TextRange.Text.Replace('C57','paired shifts plus 42 days').Replace('C30','separate wide steps')
    if($value -ne $s.TextFrame.TextRange.Text){$s.TextFrame.TextRange.Text=$value}
}}}
$p.Save()
$render=Join-Path $buildRoot 'readability-final'
New-Item -ItemType Directory -Force -Path $render | Out-Null
$rows=@()
foreach($slide in @($results,$settings,$limits,$final)){
    $slide.Export((Join-Path $render ('slide-{0:D2}.png' -f $slide.SlideIndex)),'PNG',1600,900)
    foreach($s in $slide.Shapes){if($s.HasTextFrame -and $s.TextFrame.HasText){$rows += [pscustomobject]@{slide=$slide.SlideIndex;name=$s.Name;text=$s.TextFrame.TextRange.Text;h=$s.Height;boundH=$s.TextFrame.TextRange.BoundHeight}}}
}
$rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $render 'shapes.json') -Encoding UTF8
Write-Output "Updated live deck: results $($results.SlideIndex), step sizes $($settings.SlideIndex), limits $($limits.SlideIndex), recommendation $($final.SlideIndex). Total $($p.Slides.Count) slides."
if($opened){$p.Close()}

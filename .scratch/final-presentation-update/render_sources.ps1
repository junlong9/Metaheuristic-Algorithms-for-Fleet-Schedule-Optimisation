$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path '.').Path
$buildRoot = Join-Path $taskRoot '.scratch/final-presentation-update'
$app = New-Object -ComObject PowerPoint.Application
$existing = @($app.Presentations | ForEach-Object { $_.FullName })
Write-Output ('Open presentations: ' + ($existing -join ', '))
foreach ($name in @('Final Seminar.pptx', 'Iteration 1 Milestones.pptx')) {
    $p = $app.Presentations.Open((Join-Path $taskRoot "presentations/$name"), -1, 0, 0)
    $folder = Join-Path $buildRoot ($name.Replace('.pptx','') + '-source')
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    $indices = if ($name -eq 'Final Seminar.pptx') { 1..$p.Slides.Count } else { @(7,8,9) }
    $rows = @()
    foreach ($i in $indices) {
        $slide = $p.Slides.Item($i)
        $slide.Export((Join-Path $folder ('slide-{0:D2}.png' -f $i)), 'PNG',1600,900)
        foreach ($shape in $slide.Shapes) {
            if ($shape.HasTextFrame -and $shape.TextFrame.HasText) {
                $rows += [pscustomobject]@{slide=$i;name=$shape.Name;text=$shape.TextFrame.TextRange.Text;x=$shape.Left;y=$shape.Top;w=$shape.Width;h=$shape.Height;font=$shape.TextFrame.TextRange.Font.Name;size=$shape.TextFrame.TextRange.Font.Size}
            }
        }
    }
    $rows | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'shapes.json') -Encoding UTF8
    $p.Close()
    Write-Output "Exported $name"
}
if ($existing.Count -eq 0) { $app.Quit() }

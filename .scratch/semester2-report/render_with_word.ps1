param(
    [string]$ReportName = '2026-10-12-semester-2-complete-technical-report.docx',
    [string]$RenderFolder = 'render'
)
$ErrorActionPreference = 'Stop'
$reportRoot = 'C:\Users\davsk\OneDrive\The University of Queensland\Northrop Grumman\Iteration 1'
$reportPath = Join-Path (Join-Path $reportRoot 'docs\reports') $ReportName
$reportRenderDirectory = Join-Path (Join-Path $reportRoot '.scratch\semester2-report') $RenderFolder
[void][System.IO.Directory]::CreateDirectory($reportRenderDirectory)
$reportPdf = Join-Path $reportRenderDirectory 'report.pdf'
$reportWord = New-Object -ComObject Word.Application
$reportWord.Visible = $false
$reportWord.DisplayAlerts = 0
$reportDocument = $null
try {
    $reportDocument = $reportWord.Documents.Open($reportPath, $false, $true)
    $reportDocument.Repaginate()
    $reportDocument.ExportAsFixedFormat($reportPdf,17)
    Write-Output ('Pages: ' + $reportDocument.ComputeStatistics(2))
    Write-Output $reportPdf
}
finally {
    if ($null -ne $reportDocument) { $reportDocument.Close(0) }
    $reportWord.Quit(0)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($reportWord)
}

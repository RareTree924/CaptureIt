# Compare button: lists every difference between this computer and GitHub in a temp file
# - files only on GitHub / only on this computer / different on both
# - edit times on each side, and which side changed the file since you last synced
# - read-only: changes nothing; .gitignore'd files are skipped
Set-Location (Split-Path $PSScriptRoot)
$branch = git rev-parse --abbrev-ref HEAD
$remote = "origin/$branch"

git fetch origin $branch
if ($LASTEXITCODE -ne 0) { Write-Host "Fetch failed (offline, or branch not on GitHub?)" -ForegroundColor Red; exit 1 }

function GitLines { git -c core.quotePath=false @args | Where-Object { $_ } }
function Set-Of($lines) { $s = @{}; foreach ($l in $lines) { $s[$l] = 1 }; $s }
$dateFmt = '--date=format-local:%Y-%m-%d %H:%M'
function LocalTime($f) { "edited " + (Get-Item -LiteralPath $f).LastWriteTime.ToString("yyyy-MM-dd HH:mm") }
function GitHubInfo($f) { git -c core.quotePath=false log -1 --format="%ad by %an: %s" $dateFmt $remote -- $f }

# Base = last commit both sides share; tells which side changed a file since then
$base = git merge-base HEAD $remote
$onGitHub = Set-Of (GitLines ls-tree -r --name-only $remote)
$inBase = @{}; $changedHere = @{}; $changedGitHub = @{}
if ($base) {
    $inBase = Set-Of (GitLines ls-tree -r --name-only $base)
    $changedHere = Set-Of (GitLines diff --name-only --no-renames $base)
    $changedGitHub = Set-Of (GitLines diff --name-only --no-renames $base $remote)
}
$untracked = @(GitLines ls-files --others --exclude-standard)
foreach ($f in $untracked) { $changedHere[$f] = 1 }
$lineCounts = @{}
foreach ($l in GitLines diff --numstat --no-renames $remote) {
    $a, $d, $f = $l -split "`t", 3
    $lineCounts[$f] = if ($a -eq '-') { "binary file differs" } else { "+$a / -$d lines vs GitHub" }
}

# Sort every difference into one of three lists
$onlyGitHub = @(); $onlyHere = @(); $edited = @()
$untrackedSet = Set-Of $untracked
foreach ($l in GitLines diff --name-status --no-renames $remote) {
    $s, $f = $l -split "`t", 2
    if ($untrackedSet[$f]) { continue }
    switch ($s) { 'D' { $onlyGitHub += $f } 'A' { $onlyHere += $f } default { $edited += $f } }
}
foreach ($f in $untracked) { if ($onGitHub[$f]) { $edited += $f } else { $onlyHere += $f } }

$out = [System.Collections.Generic.List[string]]::new()
function Section($title, $files, $describe) {
    $out.Add(""); $out.Add("$title ($(@($files).Count))"); $out.Add("=" * 60)
    if (-not $files) { $out.Add("  (none)") }
    foreach ($f in $files | Sort-Object) { $out.Add("  $f"); foreach ($d in & $describe $f) { if ($d) { $out.Add("      $d") } } }
}

$out.Add("CaptureIt: this computer vs GitHub (branch $branch)")
$out.Add("Checked " + (Get-Date).ToString("yyyy-MM-dd HH:mm"))
if (-not ($onlyGitHub + $onlyHere + $edited)) { $out.Add(""); $out.Add("Everything matches. Nothing to push or pull.") }

Section "ON GITHUB, NOT ON THIS COMPUTER" $onlyGitHub {
    param($f)
    if ($inBase[$f]) { "you deleted it on this computer" } else { "added on GitHub" }
    "GitHub: " + (GitHubInfo $f)
}
Section "ON THIS COMPUTER, NOT ON GITHUB" $onlyHere {
    param($f)
    if ($inBase[$f]) { "deleted on GitHub" } else { "new on this computer" }
    "this computer: " + (LocalTime $f)
}
Section "DIFFERENT ON EACH SIDE" $edited {
    param($f)
    if ($changedHere[$f] -and $changedGitHub[$f]) { "CHANGED ON BOTH - Pull loses your edits, Push loses GitHub's" }
    elseif ($changedHere[$f]) { "changed on this computer" }
    elseif ($changedGitHub[$f]) { "changed on GitHub" }
    "this computer: " + (LocalTime $f)
    "GitHub: " + (GitHubInfo $f)
    $lineCounts[$f]
}

$behind = @(GitLines log "--format=  %ad  %an: %s" $dateFmt "HEAD..$remote")
$ahead = @(GitLines log "--format=  %ad  %an: %s" $dateFmt "$remote..HEAD")
$out.Add(""); $out.Add("COMMITS ON GITHUB YOU DON'T HAVE ($($behind.Count))"); $out.Add("=" * 60)
if ($behind) { $behind | ForEach-Object { $out.Add($_) } } else { $out.Add("  (none)") }
$out.Add(""); $out.Add("COMMITS HERE NOT ON GITHUB ($($ahead.Count))"); $out.Add("=" * 60)
if ($ahead) { $ahead | ForEach-Object { $out.Add($_) } } else { $out.Add("  (none)") }

# Write the report to a temp file and open it in VS Code (Notepad if VS Code's CLI isn't found)
$report = Join-Path ([System.IO.Path]::GetTempPath()) "CaptureIt-compare.txt"
$out | Set-Content -Encoding UTF8 $report
Write-Host "$($onlyGitHub.Count) only on GitHub, $($onlyHere.Count) only here, $($edited.Count) different" -ForegroundColor Cyan
$code = (Get-Command code -ErrorAction SilentlyContinue).Source
if (-not $code -and $env:VSCODE_GIT_ASKPASS_NODE) { $code = Join-Path (Split-Path $env:VSCODE_GIT_ASKPASS_NODE) "bin\code.cmd" }
if ($code -and (Test-Path $code)) { & $code -r $report } else { Invoke-Item $report }

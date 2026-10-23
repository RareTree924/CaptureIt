# Push button: makes GitHub match this computer exactly
# - commits every local change (new, edited, deleted files)
# - force-pushes the current branch, overwriting whatever GitHub had
# - .gitignore'd files (build/, secrets.h, gemini_key.txt) are never uploaded
param([string]$Repo = (Split-Path $PSScriptRoot))  # project folder; defaults to the one this script sits in
Set-Location $Repo
$branch = git rev-parse --abbrev-ref HEAD

git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "Sync from $env:COMPUTERNAME $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    if ($LASTEXITCODE -ne 0) { Write-Host "Commit failed" -ForegroundColor Red; exit 1 }
}

git push --force -u origin $branch
if ($LASTEXITCODE -ne 0) { Write-Host "Push failed" -ForegroundColor Red; exit 1 }
Write-Host "Pushed '$branch': GitHub now matches this computer" -ForegroundColor Green

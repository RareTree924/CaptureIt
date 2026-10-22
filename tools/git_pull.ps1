# Pull button: makes this computer match GitHub exactly
# - uncommitted local changes are stashed first as a backup (undo with: git stash pop)
# - the current branch is then reset to GitHub's copy and stray files removed
# - .gitignore'd files (build/, secrets.h, gemini_key.txt) are left alone
Set-Location (Split-Path $PSScriptRoot)
$branch = git rev-parse --abbrev-ref HEAD

git fetch origin $branch
if ($LASTEXITCODE -ne 0) { Write-Host "Fetch failed" -ForegroundColor Red; exit 1 }

if (git status --porcelain) {
    git stash push -u -m "Backup before pull $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    Write-Host "Local changes backed up (git stash pop to get them back)" -ForegroundColor Yellow
}

git reset --hard "origin/$branch"
git clean -fd
Write-Host "Pulled '$branch': this computer now matches GitHub" -ForegroundColor Green

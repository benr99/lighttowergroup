param(
    [string]$RepositoryRoot = "C:\Users\Ben\Downloads\Lighttowergroupsite",
    [string]$RuntimePath = "C:\Users\Ben\Downloads\Lighttowergroupsite\.agent-runtime"
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = (Resolve-Path $RepositoryRoot).Path

if (Test-Path $RuntimePath) {
    & git -C $RuntimePath rev-parse --is-inside-work-tree | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Runtime path exists but is not a Git worktree: $RuntimePath" }
    Write-Host "Runtime worktree already exists: $RuntimePath"
} else {
    & git -C $RepositoryRoot fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch origin/main before creating the runtime worktree." }
    & git -C $RepositoryRoot worktree add --detach $RuntimePath origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not create the isolated runtime worktree." }
    Write-Host "Created isolated runtime worktree: $RuntimePath"
}

$sourceEnv = Join-Path $RepositoryRoot "scripts\.env"
$runtimeEnv = Join-Path $RuntimePath "scripts\.env"
if ((Test-Path $sourceEnv) -and -not (Test-Path $runtimeEnv)) {
    Copy-Item -LiteralPath $sourceEnv -Destination $runtimeEnv
    Write-Host "Copied existing private agent configuration into the isolated runtime."
} elseif (-not (Test-Path $runtimeEnv)) {
    Write-Warning "No scripts\.env was found. Add API credentials to $runtimeEnv before the next scheduled run."
}

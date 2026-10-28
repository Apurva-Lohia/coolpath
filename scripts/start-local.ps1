# Prompts locally: never enter or send the database password in chat.
param([string]$Database = 'sydney_spatial_db', [string]$User = 'apurva')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Database) { $Database = Read-Host 'Existing CoolPath database name' }
if (-not $User) { $User = Read-Host 'Existing PostgreSQL user' }
if ([string]::IsNullOrWhiteSpace($Database) -or [string]::IsNullOrWhiteSpace($User)) { throw 'An existing database name and PostgreSQL user are required.' }
$secure = Read-Host 'PostgreSQL password (hidden)' -AsSecureString
$keys = @('PGHOST','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','DATABASE_URL')
$previous = @{}
foreach ($key in $keys) { $previous[$key] = [Environment]::GetEnvironmentVariable($key,'Process') }
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    $env:PGHOST = '127.0.0.1'
    $env:PGPORT = '5433'
    $env:PGDATABASE = $Database
    $env:PGUSER = $User
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    Push-Location $root
    try {
        & '.\.venv\Scripts\python.exe' 'scripts/check_database.py'
        if ($LASTEXITCODE -ne 0) { throw 'Connection check failed. No database changes were made.' }
        & '.\.venv\Scripts\python.exe' -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
    } finally { Pop-Location }
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $secure.Dispose()
    foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key,$previous[$key],'Process') }
}

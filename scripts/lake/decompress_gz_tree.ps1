<#
.SYNOPSIS
    Bulk decompress all .gz archives into a parallel decompressed root,
    preserving the original folder structure.

.DESCRIPTION
    Recursively discovers .gz files under a source root and streams each
    into a parallel destination tree with the .gz suffix stripped.
    Uses .NET GzipStream for memory-efficient decompression.

.PARAMETER SrcRoot
    Root directory containing .gz files (default: lake\openalex-snapshot)

.PARAMETER DstRoot
    Root directory for decompressed output (default: lake\openalex-snapshot_decompressed)

.PARAMETER Force
    Overwrite existing destination files

.PARAMETER DryRun
    Show what would be done without writing any files

.PARAMETER MaxFiles
    Process at most N files (useful for testing)

.PARAMETER Pattern
    Filter pattern applied to relative paths (e.g. "works" to only process works)

.EXAMPLE
    .\scripts\lake\decompress_gz_tree.ps1
    .\scripts\lake\decompress_gz_tree.ps1 -DryRun
    .\scripts\lake\decompress_gz_tree.ps1 -SrcRoot lake\openalex-snapshot -Force -MaxFiles 5
    .\scripts\lake\decompress_gz_tree.ps1 -Pattern "works"
#>

[CmdletBinding()]
param(
    [string]$SrcRoot = "lake\openalex-snapshot",
    [string]$DstRoot = "lake\openalex-snapshot_decompressed",
    [switch]$Force,
    [switch]$DryRun,
    [int]$MaxFiles = 0,
    [string]$Pattern = ""
)

Add-Type -AssemblyName System.IO.Compression

# ── Constants ──────────────────────────────────────────────────────────────
$BufferSize = 1MB

# ── Validate source ───────────────────────────────────────────────────────
$srcResolved = Resolve-Path -Path $SrcRoot -ErrorAction SilentlyContinue
if (-not $srcResolved) {
    Write-Error "Source root does not exist: $SrcRoot"
    exit 1
}
$SrcRoot = $srcResolved.Path
Write-Host "Source root : $SrcRoot"
Write-Host "Dest root   : $(Resolve-Path -Path $DstRoot -ErrorAction SilentlyContinue ?? $DstRoot)"
Write-Host "Force       : $Force"
Write-Host "Dry-run     : $DryRun"

# ── Discover .gz files ────────────────────────────────────────────────────
$allFiles = Get-ChildItem -Path $SrcRoot -Recurse -Filter "*.gz" -File
if ($Pattern) {
    $allFiles = $allFiles | Where-Object { $_.FullName -match $Pattern }
}
$allFiles = $allFiles | Sort-Object FullName
Write-Host "Discovered $($allFiles.Count) .gz file(s)"

if ($MaxFiles -gt 0 -and $allFiles.Count -gt $MaxFiles) {
    $allFiles = $allFiles | Select-Object -First $MaxFiles
    Write-Host "Limited to first $MaxFiles file(s)"
}

# ── Counters ──────────────────────────────────────────────────────────────
$discovered   = $allFiles.Count
$decompressed = 0
$skipped      = 0
$failed       = 0
$totalBytes   = [long]0

# ── Process each file ─────────────────────────────────────────────────────
foreach ($file in $allFiles) {
    $relPath = $file.FullName.Substring($SrcRoot.Length).TrimStart('\', '/')
    # Strip .gz extension
    if ($relPath.EndsWith(".gz")) {
        $relPath = $relPath.Substring(0, $relPath.Length - 3)
    }
    $dstPath = Join-Path $DstRoot $relPath

    if ($DryRun) {
        $action = if ((Test-Path $dstPath) -and -not $Force) { "SKIP (exists)" } else { "DECOMPRESS" }
        Write-Host "[DRY-RUN] $($file.FullName) -> $dstPath  [$action]"
        continue
    }

    # Skip existing
    if ((Test-Path $dstPath) -and -not $Force) {
        Write-Verbose "Skipped (exists): $dstPath"
        $skipped++
        continue
    }

    # Ensure dest directory exists
    $dstDir = Split-Path $dstPath -Parent
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }

    # Stream decompress via .NET GzipStream
    $tmpPath = "$dstPath.tmp"
    try {
        $inStream  = [System.IO.File]::OpenRead($file.FullName)
        $gzStream  = New-Object System.IO.Compression.GzipStream($inStream, [System.IO.Compression.CompressionMode]::Decompress)
        $outStream = [System.IO.File]::Create($tmpPath)
        $buffer    = New-Object byte[] $BufferSize
        $bytesWritten = [long]0

        do {
            $read = $gzStream.Read($buffer, 0, $buffer.Length)
            if ($read -gt 0) {
                $outStream.Write($buffer, 0, $read)
                $bytesWritten += $read
            }
        } while ($read -gt 0)

        $outStream.Close()
        $gzStream.Close()
        $inStream.Close()

        # Atomic rename
        if (Test-Path $dstPath) { Remove-Item $dstPath -Force }
        Move-Item -Path $tmpPath -Destination $dstPath -Force

        $totalBytes += $bytesWritten
        $decompressed++
        Write-Host "Decompressed: $($file.FullName) -> $dstPath ($bytesWritten bytes)"
    }
    catch {
        $failed++
        Write-Warning "FAILED: $($file.FullName) — $_"
        if (Test-Path $tmpPath) { Remove-Item $tmpPath -Force -ErrorAction SilentlyContinue }
    }
}

# ── Summary ───────────────────────────────────────────────────────────────
Write-Host ("-" * 60)
Write-Host "Summary"
Write-Host "  Discovered  : $discovered"
Write-Host "  Decompressed: $decompressed"
Write-Host "  Skipped     : $skipped"
Write-Host "  Failed      : $failed"
Write-Host "  Bytes written: $($totalBytes.ToString('N0'))"
Write-Host ("-" * 60)

if ($failed -gt 0) { exit 1 }
exit 0

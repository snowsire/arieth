param(
    [Parameter(Mandatory = $true)]
    [string]$BundlePath,
    [string]$WatchName = 'fenix 6X Sapphire',
    [ValidateRange(1, 60)]
    [int]$TimeoutMinutes = 10
)

$ErrorActionPreference = 'Stop'
$BundlePath = (Resolve-Path -LiteralPath $BundlePath).Path
$manifestPath = Join-Path $BundlePath 'export.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw 'The export manifest was not found.'
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $manifest.playlist -or -not $manifest.folder_name -or [int]$manifest.tracks -lt 1 -or
    @($manifest.files).Count -ne [int]$manifest.tracks) {
    throw 'The export manifest is incomplete or inconsistent.'
}

$shellApp = New-Object -ComObject Shell.Application
$watches = @($shellApp.Namespace(17).Items() | Where-Object { $_.Name -eq $WatchName })
if ($watches.Count -ne 1) { throw "Connect exactly one $WatchName by USB." }
$storages = @($watches[0].GetFolder.Items() | Where-Object { $_.Name -eq 'Primary' })
if ($storages.Count -ne 1) { throw 'The watch storage is not ready.' }
$musicItems = @($storages[0].GetFolder.Items() | Where-Object { $_.Name -eq 'Music' -and $_.IsFolder })
if ($musicItems.Count -ne 1) { throw 'The watch Music folder was not found.' }
$musicFolder = $musicItems[0].GetFolder
$existing = @($musicFolder.Items() | Where-Object { $_.Name -eq $manifest.folder_name })
if ($existing.Count -gt 0) {
    throw 'A playlist folder with this name already exists on the watch; inspect it before retrying.'
}
$requiredBytes = [long]$manifest.bytes
$freeBytes = $storages[0].ExtendedProperty('System.FreeSpace')
if ($null -eq $freeBytes -or [long]$freeBytes -lt ($requiredBytes + 10MB)) {
    throw 'Could not confirm enough free space on the watch.'
}

$trackMap = @{}
foreach ($track in $manifest.files) {
    $name = [string]$track.file
    if ([IO.Path]::GetFileName($name) -ne $name -or $name -notmatch '\.mp3$') {
        throw 'Unsafe track filename in export manifest.'
    }
    $source = Join-Path $BundlePath $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw ("Missing export file: " + $name) }
    $item = Get-Item -LiteralPath $source
    if ($item.Length -ne [long]$track.bytes -or
        (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $track.sha256) {
        throw ("Source checksum mismatch: " + $name)
    }
    $trackMap[[string]$track.id] = $name
}

$safeName = [regex]::Replace([string]$manifest.playlist, '[<>:"/\\|?*\x00-\x1f]', '_').Trim([char[]]@(' ', '.'))
$m3uPath = Join-Path $BundlePath ($safeName + '.m3u')
$m3u8Path = Join-Path $BundlePath ($safeName + '.m3u8')
if (-not (Test-Path -LiteralPath $m3uPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $m3u8Path -PathType Leaf)) {
    throw 'The M3U playlist files are missing from the export.'
}
$expectedOrder = @([IO.File]::ReadAllLines($m3uPath, [Text.Encoding]::UTF8) |
    Where-Object { $_.Trim() -ne '' })
if ($expectedOrder.Count -ne [int]$manifest.entries) { throw 'Playlist entry count does not match the manifest.' }
$allowed = @{}
foreach ($track in $manifest.files) { $allowed[[string]$track.file] = $true }
foreach ($name in $expectedOrder) {
    if (-not $allowed.ContainsKey($name)) { throw ('Playlist references a missing track: ' + $name) }
}

$transferRoot = Join-Path (Split-Path -Parent $BundlePath) 'transfers'
$transferId = [Guid]::NewGuid().ToString('N')
$runPath = Join-Path $transferRoot $transferId
$readbackPath = Join-Path $runPath 'readback'
New-Item -ItemType Directory -Path $readbackPath -Force | Out-Null
$copyFlags = 4 + 16 + 512 + 1024
$expectedTopLevel = @($manifest.files).Count + 3
Write-Output ("Copying " + $manifest.tracks + " unique MP3s for " + $manifest.entries + " playlist entries.")
$musicFolder.CopyHere($BundlePath, $copyFlags)

$deadline = [DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
$watchFolder = $null
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 2
    $matches = @($musicItems[0].GetFolder.Items() | Where-Object {
        $_.Name -eq $manifest.folder_name -and $_.IsFolder
    })
    if ($matches.Count -eq 1) {
        $watchFolder = $matches[0]
        if (@($watchFolder.GetFolder.Items()).Count -eq $expectedTopLevel) { break }
    }
}
if (-not $watchFolder -or @($watchFolder.GetFolder.Items()).Count -ne $expectedTopLevel) {
    throw 'Watch copy did not finish in time; leave the watch connected and inspect before retrying.'
}

Write-Output 'Copy finished. Reading the playlist folder back for SHA-256 verification.'
$shellApp.Namespace($readbackPath).CopyHere($watchFolder, $copyFlags)
$returnedRoot = Join-Path $readbackPath $manifest.folder_name
$deadline = [DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
do {
    Start-Sleep -Seconds 2
    $returnedM3u = Join-Path $returnedRoot ($safeName + '.m3u')
    $complete = Test-Path -LiteralPath $returnedM3u -PathType Leaf
    if ($complete) {
        foreach ($track in $manifest.files) {
            if (-not (Test-Path -LiteralPath (Join-Path $returnedRoot ([string]$track.file)) -PathType Leaf)) {
                $complete = $false
                break
            }
        }
    }
    if ($complete) { break }
    if ([DateTime]::UtcNow -gt $deadline) { throw 'Watch readback did not finish; transfer is not yet verified.' }
} while ($true)

foreach ($track in $manifest.files) {
    $returnedFile = Join-Path $returnedRoot ([string]$track.file)
    if ((Get-Item -LiteralPath $returnedFile).Length -ne [long]$track.bytes -or
        (Get-FileHash -LiteralPath $returnedFile -Algorithm SHA256).Hash -ne $track.sha256) {
        throw ('Watch readback checksum mismatch: ' + $track.file)
    }
}
$returnedOrder = @([IO.File]::ReadAllLines($returnedM3u, [Text.Encoding]::UTF8) |
    Where-Object { $_.Trim() -ne '' })
if ($returnedOrder.Count -ne $expectedOrder.Count) { throw 'Watch playlist entry count mismatch.' }
for ($index = 0; $index -lt $expectedOrder.Count; $index++) {
    if ($returnedOrder[$index] -ne $expectedOrder[$index]) { throw 'Watch playlist order mismatch.' }
}

$receipt = [PSCustomObject]@{
    watch = $WatchName
    playlist = $manifest.playlist
    destination = ('Music\' + $manifest.folder_name)
    unique_tracks = [int]$manifest.tracks
    playlist_entries = [int]$manifest.entries
    audio_bytes = $requiredBytes
    verified_utc = [DateTime]::UtcNow.ToString('o')
    readback_sha256_verified = $true
    playlist_order_verified = $true
}
$receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $runPath 'verified-transfer.json') -Encoding UTF8
$receipt | ConvertTo-Json -Depth 4

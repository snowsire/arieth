$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pythonPath = (Get-Command python.exe -ErrorAction Stop).Source
Start-Transcript -Path "$root\phone-install.log" -Append
try {
    $existing = Get-ScheduledTask -TaskName 'SnowMusicPhonePlayer' -ErrorAction SilentlyContinue
    if ($existing -and $existing.Description -notlike 'Snow Music Feishin*') {
        throw 'An unrelated task already uses this name'
    }
    $action = New-ScheduledTaskAction -Execute $pythonPath -Argument ('-I "{0}"' -f (Join-Path $root 'phone-server.py')) -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName 'SnowMusicPhonePlayer' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Snow Music Feishin phone web player; loopback only, exposed privately through Tailscale' -Force | Out-Null
    Start-ScheduledTask -TaskName 'SnowMusicPhonePlayer'
    'SUCCESS' | Set-Content "$root\phone-install-status.txt"
} catch {
    $_ | Out-String | Set-Content "$root\phone-install-status.txt"
    throw
} finally { Stop-Transcript }

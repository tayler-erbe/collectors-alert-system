# Registers the "CollectorsAlert" scheduled task: starts run_forever.cmd at logon, hidden, for the current user.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$a = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$dir\run_forever.cmd`"" -WorkingDirectory $dir
$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "CollectorsAlert" -Action $a -Trigger $t -Settings $s -Description "Drop alerts for collectors-alert-system" -Force
Start-ScheduledTask -TaskName "CollectorsAlert"

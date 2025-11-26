# record.ps1
# author: ChatGPT

# behaviors you might want to change
#
#     $ffmpeg: how to evoke ffmpeg, e.g. "C:\Download\ffmpeg\ffmpeg"
#     $outdir: output recorded audio files to \WallAudio\YYYY-MM-DD directory
#     $stopTime: stop at 6:59
#     $Env:AUDIO_DEV: substring used to pick the dshow audio device (e.g. "ATR2500")
#     $Env:STOP_AFTER_SECONDS: optional override for duration (handy for quick tests)
#     $Env:DEBUG_DEVICE: set to 1 to log device enumeration
#
#     -ac 1       mono
#     -c:a aac    *.m4a format
#     -segment_time 3600 -segment_atclocktime 1   splits every hour at xx:00

$ffmpeg   = "ffmpeg"
$outdir   = "\WallAudio"
$now      = Get-Date
$stopTime = Get-Date -Hour 6 -Minute 59 -Second 0
if ($now -gt $stopTime) { $stopTime = $stopTime.AddDays(1) }

$keyword = $Env:AUDIO_DEV
if (-not $keyword) {
    Write-Host "Environment variable AUDIO_DEV is not set.`nSet it to a keyword like 'ATR2500' to match your microphone."
    exit 1
}

$audio_dev = $null
if (-not $audio_dev) {
    $listOutput = & $ffmpeg -list_devices true -f dshow -i dummy 2>&1
    if ($Env:DEBUG_DEVICE) {
        Write-Host "DEBUG raw listOutput:"
        $listOutput | ForEach-Object { Write-Host $_ }
    }

    $patternName = '"([^"]*' + [regex]::Escape($keyword) + '[^"]*)"'
    $candidateNames = @()
    for ($i = 0; $i -lt $listOutput.Count; $i++) {
        $line = $listOutput[$i]
        if ($line -notmatch '\(audio\)') { continue }

        $nameMatch = [regex]::Match($line, $patternName, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if (-not $nameMatch.Success) { continue }

        $altCandidate = $null
        if ($i + 1 -lt $listOutput.Count) {
            $altMatch = [regex]::Match($listOutput[$i + 1], 'Alternative name "([^"]+)"')
            if ($altMatch.Success) { $altCandidate = $altMatch.Groups[1].Value }
        }

        $deviceName = if ($altCandidate) { $altCandidate } else { $nameMatch.Groups[1].Value }
        $candidateNames += $deviceName
    }
    if ($Env:DEBUG_DEVICE) {
        Write-Host "DEBUG audio candidates (after keyword filter):"
        $candidateNames | ForEach-Object { Write-Host $_ }
    }

    $matches = @($candidateNames | Where-Object { $_ })

    if ($matches.Count -eq 0) {
        Write-Host "No DirectShow audio device contained keyword '$keyword'.`nSet AUDIO_DEV manually to override."
        exit 1
    }
    if ($matches.Count -gt 1) {
        Write-Host ("Multiple devices matched '{0}'; using the first:`n{1}" -f $keyword, ($matches -join "`n"))
    }

    if ($Env:DEBUG_DEVICE) {
        Write-Host ("DEBUG first match raw: '{0}' length {1}" -f $matches[0], $matches[0].Length)
    }
    $audio_dev = "audio=" + $matches[0]
    Write-Host "Selected device: $audio_dev"
}

$duration    = $stopTime - $now
if ($Env:STOP_AFTER_SECONDS) {
    $duration = [TimeSpan]::FromSeconds([double]$Env:STOP_AFTER_SECONDS)
}
$durationStr = $duration.ToString('hh\:mm\:ss')

$startDate = $now.Date
$endDate   = $stopTime.Date
for ($d = $startDate; $d -le $endDate; $d = $d.AddDays(1)) {
    $folder = Join-Path $outdir ($d.ToString('yyyy-MM-dd'))
    if (-not (Test-Path $folder)) { New-Item -ItemType Directory -Path $folder | Out-Null }
}

$outputPattern = Join-Path $outdir '%Y-%m-%d/%Y-%m-%d_%H-%M-%S.m4a'

$args = @(
    '-hide_banner',
    '-f','dshow','-i', $audio_dev,
    '-ac','1',      # mono
    '-c:a', 'aac',  # *.m4a format
    '-f','segment','-strftime','1',
    '-segment_time','3600','-segment_atclocktime','1','-reset_timestamps','1',
    '-t', $durationStr,
    $outputPattern
)

Write-Host ((@($now, $ffmpeg) + $args) -join ' ')
& $ffmpeg @args
Write-Host "Recording finished"

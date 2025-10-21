# record.ps1
# author: ChatGPT

# behaviors you might want to change
#
#     $ffmpeg: how to evoke ffmpeg, e.g. "C:\Download\ffmpeg\ffmpeg"
#     $outdir: output recorded audio files to \WallAudio\YYYY-MM-DD directory
#     $stopTime: stop at 6:59
#
#     -ac 1       mono
#     -c:a aac    *.m4a format
#     -segment_time 3600 -segment_atclocktime 1   splits every hour at xx:00

$ffmpeg   = "ffmpeg"
$outdir   = "\WallAudio"
$now      = Get-Date
$stopTime = Get-Date -Hour 6 -Minute 59 -Second 0
if ($now -gt $stopTime) { $stopTime = $stopTime.AddDays(1) }

$audio_dev = $Env:AUDIO_DEV
if (-not $audio_dev) {
    Write-Host "Environment variable AUDIO_DEV is not set.`nPlease use ffmpeg -list_devices true -f dshow -i dummy to find out.`nFormat like 'audio=@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\\wave_{18E6F389-4A2F-4ACC-BBE4-F8C15FF28638}"
    exit 1
}

$duration    = $stopTime - $now
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
    '-c:a', 'aac',  # *.w4a format
    '-f','segment','-strftime','1',
    '-segment_time','3600','-segment_atclocktime','1',
    '-t', $durationStr,
    $outputPattern
)

Write-Host ((@($now, $ffmpeg) + $args) -join ' ')
& $ffmpeg @args
Write-Host "Recording finished"
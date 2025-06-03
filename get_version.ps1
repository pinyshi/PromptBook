$content = Get-Content main.py
$versionLine = $content | Select-String 'VERSION = '
$version = $versionLine.ToString().Split('"')[1].Replace('v','')
Write-Output $version 
@echo off
setlocal

REM ---- args ----
REM %1 = YouTube URL (optional)
REM %2 = action endpoint: download_audio | download_video | download_thumbnail | get_transcript (optional)
set "YTURL=%~1"
set "ACTION=%~2"

REM ---- Python env (create if missing) ----
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate

REM ---- deps ----
REM NOTE: add "requests" to requirements.txt if you use /download_thumbnail
if exist requirements.txt (
  pip install -r requirements.txt
) else (
  pip install Flask pytubefix youtube-transcript-api requests
)

REM ---- start server in a new window ----
start "flask" cmd /c "python downloader.py"

REM ---- wait for server (port 5000) to be ready ----
powershell -NoProfile -Command ^
  "$p=0; while($true){ try{ $c=New-Object Net.Sockets.TcpClient; $iar=$c.BeginConnect('127.0.0.1',5000,$null,$null); $ok=$iar.AsyncWaitHandle.WaitOne(500); if($ok){ $c.EndConnect($iar); $c.Close(); break } } catch{} Start-Sleep -Milliseconds 300; $p+=1; if($p -gt 60){ exit 1 } }"

if errorlevel 1 (
  echo Server didn't come up on port 5000. Exiting.
  exit /b 1
)

REM ---- if no args: just open the UI ----
if "%YTURL%"=="" (
  start "" http://127.0.0.1:5000/
  exit /b 0
)

REM ---- if URL given: optionally hit an action endpoint right away ----
if "%ACTION%"=="" set "ACTION=index"

REM URL-encode the YouTube URL using PowerShell
for /f "usebackq delims=" %%E in (`powershell -NoProfile -Command "[uri]::EscapeDataString('%YTURL%')"`) do set "ENC=%%E"

if /I "%ACTION%"=="index" (
  start "" "http://127.0.0.1:5000/?url=%ENC%"
) else (
  REM valid actions: download_audio, download_video, download_thumbnail, get_transcript
  start "" "http://127.0.0.1:5000/%ACTION%?url=%ENC%"
)

exit /b 0

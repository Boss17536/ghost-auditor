@echo off
color 0B
echo ==============================================================
echo GHOST AUDITOR - EXAMINER DEMO
echo ==============================================================
echo.
echo [1/2] Processing Slack Export Data...
python parse_slack_csv.py
echo.
echo [2/2] Starting Web Dashboard...
echo A browser window will open automatically.
echo (Press Ctrl+C to stop the server when done)
echo.

:: Wait 2 seconds to let the parser finish writing file
timeout /t 2 /nobreak > NUL

:: Open browser
start http://127.0.0.1:5000

:: Run the flask app
python app.py

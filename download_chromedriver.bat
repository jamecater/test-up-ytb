@echo off
echo 🔧 ChromeDriver Auto-Download Helper
echo.
echo This tool will automatically download the correct ChromeDriver
echo for your Chrome browser version.
echo.
echo 📋 What this tool does:
echo   1. Detect your Chrome browser version
echo   2. Download matching ChromeDriver from official sources
echo   3. Extract chromedriver.exe to current folder
echo   4. Clean up temporary files
echo.
echo ⚠️  Make sure you have Google Chrome installed first!
echo.
pause
python download_chromedriver.py
pause
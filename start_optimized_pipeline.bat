@echo off
echo 🚀 Starting OPTIMIZED TikTok Auto-Upload Pipeline
echo.
echo 📊 Key Performance Improvements:
echo   ✅ Target: Under 30s per video (Scan → Download → Process → Upload)
echo   ✅ FFmpeg ultrafast preset with CRF 28
echo   ✅ WebDriverWait instead of sleep() calls  
echo   ✅ Parallel processing with dedicated ThreadPoolExecutors
echo   ✅ Optimized yt-dlp with lower quality for faster downloads
echo   ✅ Detailed timing logs saved to upload_time.log
echo   ✅ Up to 10 concurrent workers (profiles)
echo.
echo 📝 Requirements:
echo   - mapping.xlsx or mapping.csv file with channel_url and profile_id columns
echo   - GPMLogin running on port 19995
echo   - ChromeDriver at the specified path
echo   - FFmpeg at the specified path
echo.
pause
python main_fix3_quetsieunhanh_25_7_optimized.py
pause
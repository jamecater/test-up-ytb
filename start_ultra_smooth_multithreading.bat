@echo off
echo 🚀 Starting ULTRA-SMOOTH Multi-Threading TikTok Pipeline
echo.
echo 🎯 TARGET: Perfect multi-threading with 100%% "Post now" popup handling
echo.
echo ✅ YÊU CẦU 2 - POPUP "POST NOW" CHUẨN 100%%:
echo   🎯 WebDriverWait(driver, 4) để đợi popup "Post now"
echo   🎯 Không dùng sleep cứng - chỉ WebDriverWait thông minh  
echo   🎯 Log chi tiết từng bước: Post clicked → Popup detected → Clicked
echo   🎯 Alternative selectors cho các loại popup khác nhau
echo   🎯 Timeout handling và fallback logic hoàn chỉnh
echo.
echo ✅ YÊU CẦU 3 - ĐA LUỒNG MƯỢT MÀ 100%%:
echo   🔄 Thread isolation: Unique file paths, session IDs, thread tracking
echo   🔄 No shared Selenium drivers: Mỗi upload = 1 driver riêng biệt
echo   🔄 No variable conflicts: Thread-safe với unique identifiers
echo   🔄 No GPM port conflicts: Staggered API calls + session isolation
echo   🔄 15 concurrent profiles max: Ổn định hơn so với 20 profiles
echo   🔄 2 workers per profile: Tránh nghẽn Chrome instances
echo   🔄 Staggered starts: Random delays tránh cùng khởi động
echo.
echo 🔥 MULTI-THREADING ENHANCEMENTS:
echo   • Thread Isolation: Unique IDs cho mỗi download/upload instance
echo   • File Path Isolation: profile_thread_timestamp naming
echo   • Chrome Session Isolation: Unique debugging endpoints
echo   • GPM API Staggering: Random delays tránh cùng gọi API
echo   • Process Staggering: Random delays giữa process starts
echo   • Resource Cleanup: Thread-aware cleanup với detailed logging
echo.
echo 📊 Expected Multi-Threading Performance:
echo   • 15 profiles concurrent (giảm từ 20 để ổn định)
echo   • 2 workers per profile (giảm từ 3 để tránh nghẽn)
echo   • Staggered upload starts (0.1-2s random delays)
echo   • Perfect isolation (no resource conflicts)
echo   • 100%% popup handling (4s WebDriverWait)
echo.
echo 🔍 Advanced Isolation Features:
echo   • Thread ID tracking: [Thread:123456, Process:789]
echo   • Unique file naming: video_profile_thread_timestamp.mp4
echo   • Session isolation: Each Chrome = unique session ID
echo   • API call staggering: Avoid simultaneous GPM API hits
echo   • Resource cleanup: Thread-aware driver/profile cleanup
echo   • Worker monitoring: Active thread count per profile
echo.
echo ⚠️  IMPORTANT MULTI-THREADING NOTES:
echo   • Each upload runs in completely isolated thread context
echo   • No shared variables or resources between uploads
echo   • Selenium drivers are never reused across uploads  
echo   • GPM profiles are properly isolated per thread
echo   • File paths include unique identifiers to prevent conflicts
echo   • Chrome instances are fully independent
echo.
echo 📋 Multi-Threading Compatibility:
echo   • 10-20 simultaneous uploads: ✅ FULLY SUPPORTED
echo   • Different profiles uploading same video: ✅ NO CONFLICTS
echo   • Concurrent Chrome instances: ✅ ISOLATED SESSIONS
echo   • GPM API rate limiting: ✅ STAGGERED CALLS
echo   • Resource cleanup: ✅ THREAD-AWARE
echo.
pause
python main_fix3_quetsieunhanh_25_7_ultra_optimized_fixed.py
pause
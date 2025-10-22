# 🚀 TikTok Auto-Upload Pipeline - OPTIMIZED VERSION

## 📊 Performance Target: < 30 seconds per video

Toàn bộ pipeline từ **phát hiện video mới** → **tải xuống** → **xử lý** → **upload lên TikTok** đã được tối ưu để hoàn thành **dưới 30 giây**.

---

## 🔥 Key Performance Improvements

### 1. **FFmpeg Tối Ưu SIÊU NHANH**
```bash
# Video ≥60s: Cắt nhanh với -ss trước -i
ffmpeg -y -ss 0 -i input.mp4 -t 65 -c:v libx264 -preset ultrafast -crf 28 -c:a aac

# Video <60s: Concat và cắt trong 1 lệnh duy nhất  
ffmpeg -y -f concat -safe 0 -i list.txt -t 65 -c:v libx264 -preset ultrafast -crf 28 -c:a aac
```
- **ultrafast preset**: Tốc độ encode nhanh nhất
- **CRF 28**: Chất lượng vừa đủ cho TikTok
- **-ss trước -i**: Seek nhanh không cần decode toàn bộ video

### 2. **Upload TikTok SIÊU NHANH**
- ✅ **WebDriverWait** thay vì `sleep()` cố định
- ✅ **Chrome options tối ưu**: `--disable-extensions`, `--disable-logging`
- ✅ **Page load strategy**: `eager` không chờ load hoàn toàn
- ✅ **Timeout ngắn**: 20s thay vì 30s
- ✅ **Auto handle "Post now" popup** trong 3s
- ✅ **URL change detection** để xác nhận upload thành công

### 3. **yt-dlp Download Tối Ưu**
```python
ydl_opts = {
    'format': 'worst[height<=720]/worst',  # Chất lượng thấp = tải nhanh
    'retries': 2,                          # Giảm retry từ 10→2
    'socket_timeout': 15,                  # Timeout ngắn
    'http_chunk_size': 1048576,            # 1MB chunks
}
```

### 4. **Parallel Processing Architecture**
- 🔄 **10 concurrent processes** cho 10 profiles khác nhau
- 🔄 **ThreadPoolExecutor riêng** cho mỗi profile (2 workers)
- 🔄 **Global ThreadPool** 30 workers cho edit+upload tasks
- 🔄 **Non-blocking task submission** với `executor.submit()`

### 5. **Smart Error Handling & Sleep**
```python
if error_count <= 3:
    sleep_time = 2-4s      # Lỗi ít
elif error_count <= 8:
    sleep_time = 8-15s     # Lỗi nhiều  
else:
    sleep_time = 25-45s    # Lỗi rất nhiều
```

### 6. **Detailed Timing Logs**
```
📊 [10:30:15] [Profile1] 🎉 PIPELINE SUCCESS!
   📊 Download: 8.2s
   📊 Process:  3.1s
   📊 Upload:   12.7s
   📊 TOTAL:    24.0s
```
- Logs lưu vào `upload_time.log` với format CSV
- Timing cho từng bước: Download → Process → Upload → Total

---

## 📁 File Structure

```
📦 TikTok Upload Pipeline
├── 🎯 main_fix3_quetsieunhanh_25_7_optimized.py   # Version tối ưu mới
├── 🚀 start_optimized_pipeline.bat                # Batch script khởi động
├── 📊 mapping.xlsx                                 # Channel-Profile mapping
├── 📋 upload_time.log                             # Log thời gian (auto-created)
├── 📁 downloads/                                   # Video temp download  
├── 📁 processed/                                   # Video sau khi xử lý
└── 📁 ffmpeg-7.1.1-essentials_build/             # FFmpeg binaries
```

---

## 🛠️ Configuration Requirements

### 1. **FFmpeg & ChromeDriver Paths**
```python
FFPROBE_PATH = r'C:\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe'
FFMPEG_PATH = r'C:\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe' 
CHROMEDRIVER_PATH = r'D:\Test up ytb\chromedriver.exe'
```

### 2. **Mapping File Format**
```csv
channel_url,profile_id,video_id
https://www.youtube.com/@channel1,profile_001,dQw4w9WgXcQ
https://www.youtube.com/@channel2,profile_002,dQw4w9WgXcQ
```

### 3. **GPMLogin API**
- Must be running on `http://127.0.0.1:19995`
- Profiles must be configured and accessible

---

## 🚀 Usage Instructions

### Quick Start:
```bash
# 1. Chạy GPMLogin
# 2. Double-click start_optimized_pipeline.bat
# 3. Theo dõi logs trong console
```

### Monitor Performance:
```bash
# Xem timing logs realtime
tail -f upload_time.log

# Check active processes 
[10:30:45] Active workers: 8/10 | Runtime: 45.2m
```

---

## 📊 Expected Performance Metrics

| Stage | Target Time | Optimization |
|-------|-------------|--------------|
| **Scan** | 1-3s | yt-dlp timeout 10s |
| **Download** | 5-12s | worst quality, 2 retries |
| **Process** | 2-8s | ultrafast preset, CRF 28 |
| **Upload** | 8-18s | WebDriverWait, no sleep() |
| **🎯 TOTAL** | **< 30s** | **End-to-end optimization** |

---

## 🔧 Troubleshooting

### Common Issues:
1. **"GPM start failed"** → Check GPMLogin API running
2. **"Chrome driver error"** → Update ChromeDriver path
3. **"FFmpeg error"** → Verify FFmpeg installation
4. **"Mapping error"** → Check mapping.xlsx format

### Performance Tuning:
- Giảm `max_concurrent` nếu system lag
- Tăng `socket_timeout` với internet chậm  
- Adjust `http_chunk_size` theo bandwidth

---

## 📈 Monitoring & Analytics

The system automatically creates `upload_time.log` with:
```csv
timestamp,video_id,profile_id,total_time_seconds
2024-01-15 10:30:15,dQw4w9WgXcQ,profile_001,24.5
2024-01-15 10:32:48,xyz123abc,profile_002,18.2
```

Use this data to:
- Track performance trends
- Identify bottleneck profiles  
- Optimize further based on real metrics

---

## 🎯 Next Level Optimizations

For even faster performance:
1. **GPU-accelerated FFmpeg** với NVENC
2. **Multi-region CDN downloads** 
3. **Predictive pre-processing** 
4. **Load balancing** across multiple machines
5. **Database-driven mapping** instead of Excel/CSV

---

**🚀 Enjoy your OPTIMIZED TikTok Auto-Upload Pipeline!**
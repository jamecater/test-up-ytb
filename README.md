# 🎵 TikTok Tool CLI

Tool Python CLI chuyên nghiệp để tìm video TikTok trùng lặp và phân tích trending videos theo quốc gia/hashtag.

## ✨ Tính năng chính

### 🔍 Chức năng 1: Reup Detection (Tìm video trùng lặp)
- Tải và phân tích video TikTok gốc
- Tạo fingerprint sử dụng perceptual hash (pHash)
- Tự động tìm kiếm video tương tự bằng từ khóa thông minh
- So sánh độ tương đồng với ngưỡng có thể điều chỉnh (mặc định 80%)
- Xuất kết quả chi tiết ra file CSV

### 🔥 Chức năng 2: Trending Finder (Tìm video trending)
- Tìm video trending theo quốc gia (15+ quốc gia hỗ trợ) 
- Tìm video trending theo hashtag
- Bộ lọc đa dạng: lượt xem, thích, độ dài, thời gian đăng
- Phân tích từ khóa và hashtag trending
- Xuất kết quả ra CSV hoặc JSON

## 🚀 Cài đặt

### 1. Clone repository

```bash
git clone <repository-url>
cd tiktok-tool
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Cài đặt Chrome driver (tự động)

Tool sẽ tự động tải Chrome driver khi chạy lần đầu thông qua `webdriver-manager`.

## 📖 Hướng dẫn sử dụng

### Xem help tổng quát

```bash
python main.py --help
```

### 🔍 Tìm video trùng lặp (Reup Detection)

```bash
# Cơ bản - tìm video trùng lặp
python main.py detect-reup "https://www.tiktok.com/@username/video/1234567890"

# Với video ID
python main.py detect-reup "1234567890"

# Điều chỉnh ngưỡng tương đồng (85%)
python main.py detect-reup "https://..." --threshold 0.85

# Tùy chỉnh từ khóa tìm kiếm
python main.py detect-reup "https://..." --keywords "funny,meme,viral"

# Tăng số video ứng viên
python main.py detect-reup "https://..." --max-results 200

# Không lưu CSV
python main.py detect-reup "https://..." --no-csv
```

### 🔥 Tìm video trending

```bash
# Trending theo quốc gia
python main.py find-trending --country US --max-results 50
python main.py find-trending --country VN --max-results 30

# Trending theo hashtag  
python main.py find-trending --hashtag funny --max-results 100
python main.py find-trending --hashtag meme --max-results 50

# Với bộ lọc
python main.py find-trending --country US \
  --min-views 100000 \
  --min-likes 5000 \
  --min-duration 15 \
  --max-duration 60

# Lưu JSON thay vì CSV
python main.py find-trending --hashtag viral --save-json

# Lọc theo từ khóa trong tiêu đề
python main.py find-trending --country JP --title-contains "dance"

# Video đăng trong 24 giờ qua
python main.py find-trending --hashtag trending --max-hours-ago 24
```

### 📍 Xem danh sách quốc gia hỗ trợ

```bash
python main.py countries
```

### 🔄 Chạy batch từ file cấu hình

```bash
python main.py batch config.json
```

**Ví dụ file config.json:**

```json
{
  "tasks": [
    {
      "type": "reup_detect",
      "video_url": "https://www.tiktok.com/@user/video/123456789",
      "max_results": 100,
      "threshold": 0.8,
      "keywords": ["funny", "viral"]
    },
    {
      "type": "trending",
      "country": "US",
      "max_results": 50,
      "filters": {
        "min_views": 10000,
        "min_duration_seconds": 15,
        "max_duration_seconds": 60
      }
    },
    {
      "type": "trending", 
      "hashtag": "meme",
      "max_results": 30,
      "save_json": true
    }
  ]
}
```

## 🌍 Quốc gia hỗ trợ

- **US** - United States
- **VN** - Vietnam  
- **JP** - Japan
- **KR** - South Korea
- **GB** - United Kingdom
- **DE** - Germany
- **FR** - France
- **IT** - Italy
- **ES** - Spain
- **BR** - Brazil
- **IN** - India
- **CN** - China
- **RU** - Russia
- **AU** - Australia
- **CA** - Canada

## ⚙️ Tùy chọn nâng cao

### Sử dụng proxy

```bash
python main.py --proxy "http://proxy:8080" detect-reup "https://..."
```

### Bật verbose logging

```bash
python main.py --verbose find-trending --country US
```

### Bộ lọc trending videos

| Tham số | Mô tả | Ví dụ |
|---------|-------|-------|
| `--min-views` | Lượt xem tối thiểu | `--min-views 100000` |
| `--min-likes` | Lượt thích tối thiểu | `--min-likes 5000` |
| `--min-duration` | Độ dài tối thiểu (giây) | `--min-duration 15` |
| `--max-duration` | Độ dài tối đa (giây) | `--max-duration 60` |
| `--max-hours-ago` | Video trong vòng X giờ | `--max-hours-ago 24` |
| `--title-contains` | Tiêu đề chứa từ khóa | `--title-contains "dance"` |

## 📁 Cấu trúc thư mục

```
tiktok-tool/
├── main.py                 # CLI entry point
├── reup_detector.py        # Module tìm video trùng lặp
├── trending_finder.py      # Module tìm video trending
├── requirements.txt        # Dependencies
├── README.md              # Hướng dẫn sử dụng
├── utils/                 # Utilities
│   ├── __init__.py
│   ├── config.py          # Cấu hình global
│   ├── video_downloader.py # Tải video TikTok
│   ├── hash_processor.py  # Xử lý perceptual hash
│   └── scraper.py         # Scraping TikTok
├── downloads/             # Video đã tải
├── temp/                  # Files tạm
└── output/               # Kết quả CSV/JSON
```

## 📊 Format kết quả

### Reup Detection CSV

| Cột | Mô tả |
|-----|-------|
| `url` | Link video trùng lặp |
| `username` | Tên người dùng |
| `title` | Tiêu đề/mô tả video |
| `view_count` | Lượt xem |
| `like_count` | Lượt thích |
| `comment_count` | Lượt bình luận |
| `similarity_percent` | Độ tương đồng (%) |
| `music` | Nhạc nền |
| `detected_at` | Thời gian phát hiện |

### Trending Videos CSV

| Cột | Mô tả |
|-----|-------|
| `url` | Link video |
| `video_id` | ID video |
| `username` | Tên người dùng |
| `title` | Tiêu đề/mô tả |
| `view_count` | Lượt xem |
| `like_count` | Lượt thích |
| `comment_count` | Lượt bình luận |
| `share_count` | Lượt chia sẻ |
| `music` | Nhạc nền |
| `duration_seconds` | Độ dài (giây) |
| `hashtags` | Danh sách hashtag |
| `engagement_rate` | Tỷ lệ tương tác (%) |
| `scraped_at` | Thời gian scrape |

## 🛡️ Tính năng chống detect

- Rotation User-Agent ngẫu nhiên
- Random delay giữa các request
- Hỗ trợ proxy
- Headless browser mode
- Anti-bot detection headers
- Concurrent processing được kiểm soát

## ⚡ Tối ưu hiệu suất

- Multi-threading cho so sánh video
- Batch processing với progress bar
- Memory-efficient video processing
- Automatic cleanup temporary files
- Configurable concurrency limits

## 🐛 Xử lý lỗi

Tool được thiết kế để handle các lỗi phổ biến:

- Network timeouts
- TikTok rate limiting  
- Invalid video URLs
- Missing dependencies
- Browser crashes
- Memory limitations

## 📝 Logs

Tool tự động ghi log chi tiết:

- **INFO**: Tiến trình chính
- **WARNING**: Cảnh báo không nghiêm trọng
- **ERROR**: Lỗi cần chú ý
- **DEBUG**: Chi tiết kỹ thuật (với `--verbose`)

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Tạo Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## ⚠️ Disclaimer

Tool này chỉ dành cho mục đích nghiên cứu và giáo dục. Hãy tuân thủ Terms of Service của TikTok và sử dụng có trách nhiệm. Không spam hoặc lạm dụng platform.

## 🆘 Hỗ trợ

Nếu gặp vấn đề, vui lòng:

1. Kiểm tra logs với `--verbose`
2. Đảm bảo dependencies được cài đúng
3. Kiểm tra network connection
4. Tạo issue với thông tin chi tiết

---

**Happy TikTok analysis! 🎵✨**